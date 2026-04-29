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
            
        # Extract all errors for this section
        raw_section_errors = [
            e for e in errors 
            if e.get('path', '').startswith(section) or e.get('path', '') == f'root.{section}'
        ]
        
        # Deduplicate errors based on type and path to find root causes and prevent overwhelming the LLM
        unique_errors = {}
        for e in raw_section_errors:
            key = f"{e.get('type')}_{e.get('path')}"
            if key not in unique_errors:
                unique_errors[key] = e
        section_errors = list(unique_errors.values())
        
        if not section_errors:
            continue
            
        context_config = {k: v for k, v in repaired_config.items() if k != section}
        broken_part = repaired_config.get(section, {})
        
        # Extract error types for targeted strategies
        error_types = {e.get('type') for e in section_errors}
        strategy_hints = ""
        
        if "EXECUTION_ERROR" in error_types:
            strategy_hints += "-> EXECUTION_ERROR STRATEGY:\n"
            strategy_hints += "   - For Missing CRUD: If an entity is missing POST/GET/PUT/DELETE, explicitly add the missing endpoints to 'api.endpoints'.\n"
            strategy_hints += "   - For Orphan Tables: Ensure the table is referenced in 'related_table' of at least one API endpoint.\n"
            strategy_hints += "   - For Orphan Endpoints: Ensure the endpoint is referenced in 'endpoint_ref' of at least one UI component.\n"
            strategy_hints += "   - For UI/DB Mismatch: If fields don't match, strictly rename the UI fields or API request_body fields to match the DB fields EXACTLY.\n"
            strategy_hints += "   - For Auth: Ensure 'roles' array is populated and all 'access_role' or 'role' fields reference an existing role.\n"
            
        instruction = f"""
        You are the Repair Engine of an AI application compiler.
        Your job is to FIX ONLY the broken parts of the '{section}' schema based on validation errors.

        RULES (STRICT):
        1. DO NOT REGENERATE EVERYTHING: Fix ONLY the specific broken section ('{section}').
        2. PRESERVE EXISTING STRUCTURE: Do NOT modify parts that are already valid. Keep naming consistent. Keep relationships intact. If a part already exists and is valid -> DO NOT TOUCH IT.
        3. ERROR-DRIVEN FIXING: For each error:
           - Missing endpoint -> add ONLY that endpoint
           - UI field not in API -> update API OR adjust UI (minimal change)
           - API field not in DB -> update DB schema ONLY
           - Missing CRUD -> add only missing operations
        4. NO OVER-ENGINEERING: Do NOT add new features. Do NOT redesign system. Do NOT change working logic.
        5. MINIMAL PATCH OUTPUT: Return only the corrected section and a list of changes made.
        
        {strategy_hints}
        
        Make sure the fixed '{section}' perfectly aligns with the rest of the configuration below.
        
        CRITICAL OUTPUT FORMAT:
        Your response MUST be a single JSON object with EXACTLY TWO keys:
        1. "changes": A list of strings describing the exact minimal changes you made to fix the errors.
        2. "fixed_section": The actual valid repaired JSON object for the '{section}'.
        
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
        13. COMPLETENESS: UI must include a 'Dashboard' page (route '/dashboard') and a 'Home' page (route '/home' or '/').
        14. COMPLETENESS: UI must include navigation (multiple pages).
        15. COMPLETENESS: API must include full CRUD endpoints (GET, POST, PUT, DELETE) for every DB table.
        16. COMPLETENESS: Auth must include at least one role.
        17. COMPLETENESS: Every UI page MUST have at least one component in `components`.
        18. COMPLETENESS: Every API endpoint MUST be referenced by at least one UI component's `endpoint_ref`.
        19. FUNCTIONAL: UI components MUST be 'form', 'table', or 'button'. DO NOT invent types.
        20. FUNCTIONAL: 'form' MUST perfectly match API request_body fields. 'table' MUST map to a GET endpoint returning an array.
        21. FUNCTIONAL: 'button' MUST map to an action (e.g. DELETE or parameter-less POST). Buttons have NO input fields. If inputs are needed, use a 'form'.

        REQUIRED JSON SCHEMA FOR fixed_section:
        {json.dumps(schema_model.model_json_schema(), indent=2)}

        Reported Errors to fix (READ CAREFULLY AND FIX ALL OF THEM):
        {json.dumps(section_errors, indent=2)}

        Context (The rest of the system config, use this to ensure alignment):
        {json.dumps(context_config, indent=2)}
        
        Current Broken '{section}' config to be fixed:
        {json.dumps(broken_part, indent=2)}
        """
        
        max_retries = 3
        attempt = 0
        success = False
        
        while attempt <= max_retries and not success:
            try:
                logger.info(f"Calling Groq API to repair '{section}' (Attempt {attempt + 1}/{max_retries + 1})")
                response = client.chat.completions.create(
                    model='llama-3.3-70b-versatile',
                    messages=[{"role": "user", "content": instruction}],
                    temperature=0.0,
                    max_tokens=4000,
                    response_format={"type": "json_object"}
                )
                
                result_json = json.loads(response.choices[0].message.content)
                
                # Check for early exit if no errors
                if result_json.get("status") == "no_fix_needed":
                    logger.info(f"LLM reported no fixes needed for '{section}'.")
                    return repaired_config
                
                logger.info(f"AI Changes for '{section}':\n{json.dumps(result_json.get('changes', []), indent=2)}")
                
                fixed_section = result_json.get("fixed_section")
                if not fixed_section:
                    raise ValueError("The LLM did not return the 'fixed_section' key in the JSON.")
                
                # Self-Verification: Validate against Pydantic schema
                try:
                    schema_model.model_validate(fixed_section)
                except Exception as ve:
                    # Append this validation error to instruction for next retry
                    instruction += f"\n\n[SYSTEM FEEDBACK ON PREVIOUS ATTEMPT]: Your last attempt failed structural validation. Error: {ve}. Please fix this!"
                    raise ValueError(f"Self-Verification Failed: The returned JSON is structurally invalid according to the Pydantic schema. Details: {ve}")

                logger.info(f"Successfully repaired '{section}': {json.dumps(fixed_section, indent=2)}")
                
                repaired_config[section] = fixed_section
                success = True
                
            except Exception as e:
                logger.error(f"Error repairing '{section}' on attempt {attempt + 1}: {e}")
                attempt += 1
                if attempt > max_retries:
                    logger.error(f"Max retries reached. Could not repair '{section}'.")
                    
    return repaired_config
