import os
import json
import logging
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from groq import Groq

from logger import setup_logger

logger = setup_logger(__name__)

class DBField(BaseModel):
    name: str
    type: Literal["string", "number", "boolean", "date"]
    required: bool = True
    is_primary: bool = False
    foreign_key: Optional[str] = Field(default=None, description="e.g., 'User.id'")
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    format: Optional[str] = None

class DBTable(BaseModel):
    name: str = Field(description="Name of the database table")
    fields: List[DBField] = Field(description="Fields in the table with their data types")

class DBConfig(BaseModel):
    tables: List[DBTable]

class APIField(BaseModel):
    name: str
    type: str
    required: bool = True
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    format: Optional[str] = None

class APIError(BaseModel):
    code: int
    message: str

class APIEndpoint(BaseModel):
    id: str = Field(description="Unique identifier for the endpoint, e.g. 'get_users'")
    method: str = Field(description="HTTP method (GET, POST, etc.)")
    path: str = Field(description="Endpoint path (e.g., '/users')")
    description: str
    related_table: str = Field(description="Exact name of the DB table this endpoint interacts with")
    request_body: List[APIField] = Field(default=[], description="Fields required in request")
    response_body: List[APIField] = Field(default=[], description="Fields returned")
    errors: List[APIError] = Field(default=[])

class APIConfig(BaseModel):
    endpoints: List[APIEndpoint]

class UIComponent(BaseModel):
    type: Literal["table", "form", "button"]
    name: str = Field(description="Name of the UI component")
    endpoint_ref: str = Field(description="ID of the API endpoint this component interacts with")
    fields: List[str] = Field(default=[], description="Fields used for forms/tables (must exist in DB)")

class UIPage(BaseModel):
    name: str = Field(description="Name of the page")
    route: str = Field(description="URL route for the page")
    access_role: str = Field(description="Role required to access this page")
    components: List[UIComponent] = Field(description="Components rendered on this page")

class UIConfig(BaseModel):
    pages: List[UIPage]

class AuthRule(BaseModel):
    role: str
    allowed_endpoints: List[str] = Field(description="List of endpoint IDs this role can access")

class AuthConfig(BaseModel):
    roles: List[str]
    rules: List[AuthRule] = Field(default=[])

class SystemSchemaOutput(BaseModel):
    ui: UIConfig
    api: APIConfig
    db: DBConfig
    auth: AuthConfig

# Initialize Groq Client
try:
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
except Exception as e:
    logger.warning(f"Failed to initialize Groq Client: {e}")
    client = None

def generate_schema(design: dict) -> dict:
    """
    Stage 3: System Architecture -> Schema Generation
    Calls Groq API to generate the full system configuration based on the design.
    """
    logger.info(f"generate_schema called with design: {json.dumps(design)}")
    
    if not client:
        raise RuntimeError("Groq client is not initialized.")

    instruction = f"""
    Based on the following system architecture design, generate the full system configuration.
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

    Return ONLY JSON matching the required schema with NO missing keys.

    REQUIRED JSON SCHEMA:
    {json.dumps(SystemSchemaOutput.model_json_schema(), indent=2)}

    System Design:
    {json.dumps(design, indent=2)}
    """

    max_retries = 1
    attempt = 0
    
    while attempt <= max_retries:
        try:
            logger.info(f"Calling Groq API for Schema Generation (Attempt {attempt + 1})")
            response = client.chat.completions.create(
                model='openai/gpt-oss-120b',
                messages=[{"role": "user", "content": instruction}],
                temperature=0.0,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            
            output_json = json.loads(response.choices[0].message.content)
            logger.info(f"Successfully generated schema: {json.dumps(output_json, indent=2)}")
            return output_json
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received from Groq on attempt {attempt + 1}: {e}")
            attempt += 1
            if attempt > max_retries:
                raise ValueError("Failed to parse valid JSON from Groq API after retries.")
        except Exception as e:
            logger.error(f"API Error on attempt {attempt + 1}: {e}")
            attempt += 1
            if attempt > max_retries:
                raise e
