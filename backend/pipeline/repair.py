import os
import json
import copy
import logging
from groq import Groq
from logger import setup_logger
from pipeline.schema import UIConfig, APIConfig, DBConfig, AuthConfig

logger = setup_logger(__name__)

# Initialize Groq Client
try:
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
except Exception as e:
    logger.warning(f"Failed to initialize Groq Client: {e}")
    client = None

def repair_schema(config: dict, errors: list) -> dict:
    """
    Stage 5: Repair
    Analyzes schema validation errors and fixes ONLY the broken sections using Groq.
    """
    if not errors:
        return config
        
    logger.info(f"Starting schema repair for {len(errors)} validation errors.")
    if not client:
        return config
        
    repaired_config = copy.deepcopy(config)
    
    broken_sections = set()
    for error in errors:
        path = error.get('path', '')
        if path.startswith('ui'): broken_sections.add('ui')
        elif path.startswith('api'): broken_sections.add('api')
        elif path.startswith('db'): broken_sections.add('db')
        elif path.startswith('auth'): broken_sections.add('auth')
        elif path.startswith('root.'):
            key = path.split('.')[-1]
            if key in ['ui', 'api', 'db', 'auth']:
                broken_sections.add(key)
                
    schema_map = {
        'ui': UIConfig,
        'api': APIConfig,
        'db': DBConfig,
        'auth': AuthConfig
    }
    
    for section in broken_sections:
        logger.info(f"Repairing broken section: '{section}'")
        schema_model = schema_map.get(section)
        if not schema_model:
            continue
            
        section_errors = [
            e for e in errors 
            if e.get('path', '').startswith(section) or e.get('path', '') == f'root.{section}'
        ]
        
        if not section_errors:
            continue
            
        context_config = {k: v for k, v in repaired_config.items() if k != section}
        broken_part = repaired_config.get(section, {})
        
        instruction = f"""
        Fix only the '{section}' schema to correct the reported errors.
        Make sure it matches and respects the rest of the configuration.
        Do not modify anything else. Return ONLY the JSON for the '{section}' object.
        
        CRITICAL CONSTRAINTS:
        1. API request_body and response_body field names MUST exactly match DB table fields.
        2. UI component fields MUST exactly match DB table fields.
        3. UI component endpoint_ref MUST match an API endpoint ID.
        4. Auth roles and rules MUST be consistent with endpoints and UI pages.
        5. SECURITY: The `response_body` MUST NEVER contain passwords, secrets, hashes, or tokens.
        6. LOGIC: `POST` endpoints MUST NOT include auto-generated `is_primary` DB fields (like `id`) in their `request_body`.
        7. LOGIC: `GET` and `DELETE` endpoints MUST have an empty `request_body`.
        8. LOGIC: Any login endpoint MUST be `POST` and MUST include `password` in `request_body`.
        9. LOGIC: If a DB entity logically belongs to another, add a `foreign_key` like "TableName.fieldName".
        10. LOGIC: Every DB table MUST have at least one field with `is_primary: true`.
        11. LOGIC: Every `DELETE` endpoint MUST have exactly one field in `response_body`: {{ "name": "success", "type": "boolean", "required": true }}.
        12. LOGIC: Add validation metadata (min_length, max_length, format) to DB and API fields where appropriate.

        REQUIRED JSON SCHEMA:
        {json.dumps(schema_model.model_json_schema(), indent=2)}

        Reported Errors to fix:
        {json.dumps(section_errors, indent=2)}

        Context (The rest of the system config):
        {json.dumps(context_config, indent=2)}
        
        Current Broken '{section}' config to be fixed:
        {json.dumps(broken_part, indent=2)}
        """
        
        max_retries = 2
        attempt = 0
        success = False
        
        while attempt <= max_retries and not success:
            try:
                logger.info(f"Calling Groq API to repair '{section}' (Attempt {attempt + 1}/{max_retries + 1})")
                response = client.chat.completions.create(
                    model='openai/gpt-oss-120b',
                    messages=[{"role": "user", "content": instruction}],
                    temperature=0.0,
                    max_tokens=4000,
                    response_format={"type": "json_object"}
                )
                
                fixed_section = json.loads(response.choices[0].message.content)
                logger.info(f"Successfully repaired '{section}': {json.dumps(fixed_section, indent=2)}")
                
                repaired_config[section] = fixed_section
                success = True
                
            except Exception as e:
                logger.error(f"Error repairing '{section}' on attempt {attempt + 1}: {e}")
                attempt += 1
                if attempt > max_retries:
                    logger.error(f"Max retries reached. Could not repair '{section}'.")
                    
    return repaired_config
