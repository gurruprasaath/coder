import json
import logging
from typing import List
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from logger import setup_logger

logger = setup_logger(__name__)

class DatabaseTable(BaseModel):
    table_name: str
    columns: List[str] = Field(description="List of column names with their types (e.g., 'id: uuid')")

class ApiEndpoint(BaseModel):
    method: str = Field(description="HTTP method (GET, POST, etc.)")
    path: str = Field(description="Endpoint path (e.g., '/users')")
    description: str = Field(description="What the endpoint does")

class ApplicationSchema(BaseModel):
    database_tables: List[DatabaseTable] = Field(description="List of database tables needed for the application")
    api_endpoints: List[ApiEndpoint] = Field(description="List of REST/GraphQL endpoints required")
    environment_variables: List[str] = Field(description="List of environment variables required (e.g., DATABASE_URL)")

try:
    client = genai.Client()
except Exception as e:
    logger.warning(f"Failed to initialize Gemini Client: {e}")
    client = None

def generate_schemas(design_data: dict) -> dict:
    """
    Stage 3: System Design -> Schema Generation
    Calls Gemini API to generate database and API schemas from the system design.
    """
    logger.info(f"generate_schemas called with design data: {json.dumps(design_data)}")
    
    if not client:
        logger.error("Gemini client is not initialized.")
        raise RuntimeError("Gemini client is not initialized.")

    instruction = f"""
    Based on the following system design, generate the concrete technical schemas.
    Return ONLY JSON matching the required schema.

    System Design:
    {json.dumps(design_data, indent=2)}
    """

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=ApplicationSchema,
        temperature=0.0,
    )

    max_retries = 1
    attempt = 0
    
    while attempt <= max_retries:
        try:
            logger.info(f"Calling Gemini API for Schema Generation (Attempt {attempt + 1})")
            response = client.models.generate_content(
                model='gemini-2.5-pro',
                contents=instruction,
                config=config,
            )
            
            output_json = json.loads(response.text)
            logger.info(f"Successfully generated schemas: {json.dumps(output_json, indent=2)}")
            return output_json
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received from Gemini on attempt {attempt + 1}: {e}")
            attempt += 1
            if attempt > max_retries:
                raise ValueError("Failed to parse valid JSON from Gemini API after retries.")
        except Exception as e:
            logger.error(f"API Error on attempt {attempt + 1}: {e}")
            attempt += 1
            if attempt > max_retries:
                raise e
