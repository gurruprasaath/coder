import os
import json
import logging
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from groq import Groq

from backend.logger import setup_logger

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

def _call_llm(instruction: str, schema_model) -> dict:
    max_retries = 1
    attempt = 0
    while attempt <= max_retries:
        try:
            logger.info(f"Calling Groq API for Schema Generation (Attempt {attempt + 1})")
            response = client.chat.completions.create(
                model='llama-3.3-70b-versatile',
                messages=[{"role": "user", "content": instruction}],
                temperature=0.0,
                max_tokens=4000,
                response_format={"type": "json_object"}
            )
            
            output_json = json.loads(response.choices[0].message.content)
            logger.info(f"Successfully generated schema layer: {json.dumps(output_json, indent=2)}")
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


def generate_schema(design: dict) -> dict:
    """
    Stage 3: System Architecture -> Schema Generation
    Calls Groq API in layers (DB -> API -> UI/Auth) to guarantee strict cross-layer dependencies.
    """
    logger.info(f"generate_schema called with design: {json.dumps(design)}")
    
    if not client:
        raise RuntimeError("Groq client is not initialized.")

    # ─────────────────────────────────────────────────────────────────────────
    # LAYER 1: DB CONFIG
    # ─────────────────────────────────────────────────────────────────────────
    db_instruction = f"""
    Based on the system architecture design, generate the Database configuration (DBConfig).
    CRITICAL CONSTRAINTS:
    1. Every DB table MUST have at least one field with `is_primary: true`.
    2. If a DB entity logically belongs to another, add a `foreign_key` like "TableName.fieldName".
    3. Add validation metadata (min_length, max_length, format) to fields where appropriate.

    Return ONLY JSON matching the required schema with NO missing keys.

    REQUIRED JSON SCHEMA:
    {json.dumps(DBConfig.model_json_schema(), indent=2)}

    System Design:
    {json.dumps(design, indent=2)}
    """
    db_output = _call_llm(db_instruction, DBConfig)

    # ─────────────────────────────────────────────────────────────────────────
    # LAYER 2: API CONFIG
    # ─────────────────────────────────────────────────────────────────────────
    api_instruction = f"""
    Based on the system architecture design and the existing Database configuration, generate the API configuration (APIConfig).
    
    CRITICAL CONSTRAINTS:
    1. API MUST include full CRUD endpoints (GET, POST, PUT, DELETE) for EVERY DB table.
    2. API request_body and response_body field names MUST exactly match DB table fields.
    3. SECURITY: The `response_body` MUST NEVER contain passwords, secrets, hashes, or tokens.
    4. LOGIC: `POST` endpoints MUST NOT include auto-generated `is_primary` DB fields (like `id`) in their `request_body`.
    5. LOGIC: `GET` and `DELETE` endpoints MUST have an empty `request_body`.
    6. LOGIC: Any login endpoint MUST be `POST` and MUST include `password` in `request_body`.
    7. LOGIC: Every `DELETE` endpoint MUST have exactly one field in `response_body`: {{ "name": "success", "type": "boolean", "required": true }}.
       IMPORTANT: `success` is a computed response field and MUST NOT be added to the DB schema.

    Return ONLY JSON matching the required schema with NO missing keys.

    REQUIRED JSON SCHEMA:
    {json.dumps(APIConfig.model_json_schema(), indent=2)}

    System Design:
    {json.dumps(design, indent=2)}
    
    DB Configuration (USE THIS TO MATCH TABLE NAMES AND FIELDS EXACTLY):
    {json.dumps(db_output, indent=2)}
    """
    api_output = _call_llm(api_instruction, APIConfig)

    # ─────────────────────────────────────────────────────────────────────────
    # LAYER 3: UI & AUTH CONFIG
    # ─────────────────────────────────────────────────────────────────────────
    # Create a wrapper model schema for UI and Auth together
    class UIAuthOutput(BaseModel):
        ui: UIConfig
        auth: AuthConfig

    ui_auth_instruction = f"""
    Based on the system architecture design, DB configuration, and API configuration, generate the UI and Auth configurations.
    
    CRITICAL CONSTRAINTS:
    1. UI component fields MUST exactly match DB table fields.
    2. UI component endpoint_ref MUST exactly match an API endpoint ID from the API config.
    3. Auth roles and rules MUST be consistent with endpoints and UI pages.
    4. COMPLETENESS: UI must include a 'Dashboard' page (route '/dashboard') and a 'Home' page (route '/home' or '/').
    5. COMPLETENESS: UI must include navigation (multiple pages).
    6. COMPLETENESS: Auth must include at least one role.
    7. COMPLETENESS: Every UI page MUST have at least one component in `components`.
    8. COMPLETENESS: Every API endpoint MUST be referenced by at least one UI component's `endpoint_ref`.
    9. FUNCTIONAL: UI components MUST be 'form', 'table', or 'button'. DO NOT invent types.
    10. FUNCTIONAL: 'form' MUST perfectly match API request_body fields. 'table' MUST map to a GET endpoint returning an array.
    11. FUNCTIONAL: 'button' MUST map to an action (e.g. DELETE or parameter-less POST). Buttons have NO input fields. If inputs are needed, use a 'form'.

    Return ONLY JSON matching the required schema with NO missing keys.

    REQUIRED JSON SCHEMA:
    {json.dumps(UIAuthOutput.model_json_schema(), indent=2)}

    System Design:
    {json.dumps(design, indent=2)}
    
    DB Configuration (USE THIS TO MATCH UI FIELDS TO DATABASE FIELDS EXACTLY):
    {json.dumps(db_output, indent=2)}
    
    API Configuration (USE THIS TO MATCH UI endpoint_ref TO API endpoint IDs EXACTLY):
    {json.dumps(api_output, indent=2)}
    """
    ui_auth_output = _call_llm(ui_auth_instruction, UIAuthOutput)

    # Combine everything into the final SystemSchemaOutput
    return {
        "db": db_output,
        "api": api_output,
        "ui": ui_auth_output.get("ui", {}),
        "auth": ui_auth_output.get("auth", {})
    }
