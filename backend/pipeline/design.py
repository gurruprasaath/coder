import os
import json
import logging
from typing import List
from pydantic import BaseModel, Field
from groq import Groq

from backend.logger import setup_logger

logger = setup_logger(__name__)

class EntitySchema(BaseModel):
    name: str = Field(description="Name of the entity (e.g., User, Task)")
    fields: List[str] = Field(description="List of fields belonging to the entity")

class RequiredModulesSchema(BaseModel):
    auth: bool = Field(description="Whether authentication/login is required. Assume true if unclear.")
    dashboard: bool = Field(description="Whether a dashboard/home page is required. Always include if multi-entity.")
    crud_entities: List[str] = Field(description="List of entities that require full CRUD operations")

class SystemDesignSchema(BaseModel):
    entities: List[EntitySchema] = Field(description="List of database entities derived from the features")
    relationships: List[str] = Field(description="List of relationships between entities (e.g. User -> Contact (1-to-many))")
    roles: List[str] = Field(description="List of user roles that interact with the system")
    features: List[str] = Field(description="List of extracted features (e.g. authentication, dashboard, analytics)")
    flows: List[str] = Field(description="High-level user flows or processes (e.g. login -> dashboard -> manage contacts)")
    required_modules: RequiredModulesSchema = Field(description="Required architectural modules for the system")

# Initialize Groq Client
try:
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
except Exception as e:
    logger.warning(f"Failed to initialize Groq Client: {e}")
    client = None

def design_system(intent: dict) -> dict:
    """
    Stage 2: Structured Intent -> System Architecture (Planning Layer)
    Calls Groq API to convert extracted intent into system design entities, roles, features, and flows.
    """
    logger.info(f"design_system called with intent: {json.dumps(intent)}")
    
    if not client:
        logger.error("Groq client is not initialized.")
        raise RuntimeError("Groq client is not initialized.")

    instruction = f"""
    You are the Planning Layer of an AI application compiler.
    Your job is to convert user intent into a COMPLETE and CONSISTENT system plan BEFORE schema generation.

    RULES:
    1. COMPLETENESS: Identify ALL entities required for the app. For each entity, ensure CRUD is required unless explicitly unnecessary. Include at least one main entry page (dashboard or home).
    2. AUTH DETECTION: If login, roles, admin, or user mentioned, set auth = true. If unclear, assume auth = true.
    3. RELATIONSHIPS: Define relationships between entities (e.g. User -> Contact (1-to-many)).
    4. FEATURE EXTRACTION: Extract features like authentication, dashboard, analytics, payments, role-based access.
    5. FLOW DEFINITION: Define user flows (e.g. login -> dashboard -> manage contacts).
    6. CONSISTENCY CHECK: Ensure entities align with features, flows reference entities, and roles are used in flows.
    7. DO NOT SKIP REQUIRED MODULES: Always include dashboard (if multi-entity app) and CRUD for each entity.
    
    IMPORTANT BEHAVIOR:
    - If something is missing -> ADD it
    - If unclear -> make reasonable assumptions
    - DO NOT leave incomplete plan
    - DO NOT generate schema here, only the structural plan

    Return ONLY JSON matching the required schema.

    REQUIRED JSON SCHEMA:
    {json.dumps(SystemDesignSchema.model_json_schema(), indent=2)}

    Application Intent:
    {json.dumps(intent, indent=2)}
    """

    max_retries = 1
    attempt = 0
    
    while attempt <= max_retries:
        try:
            logger.info(f"Calling Groq API for System Design (Attempt {attempt + 1})")
            response = client.chat.completions.create(
                model='llama-3.3-70b-versatile',
                messages=[{"role": "user", "content": instruction}],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            
            output_json = json.loads(response.choices[0].message.content)
            logger.info(f"Successfully generated system design: {json.dumps(output_json, indent=2)}")
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
