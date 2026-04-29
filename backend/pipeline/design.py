import os
import json
import logging
from typing import List
from pydantic import BaseModel, Field
from groq import Groq

from logger import setup_logger

logger = setup_logger(__name__)

class EntitySchema(BaseModel):
    name: str = Field(description="Name of the entity (e.g., User, Task)")
    fields: List[str] = Field(description="List of fields belonging to the entity")

class SystemDesignSchema(BaseModel):
    entities: List[EntitySchema] = Field(description="List of database entities derived from the features")
    roles: List[str] = Field(description="List of user roles that interact with the system")
    flows: List[str] = Field(description="High-level user flows or processes")

# Initialize Groq Client
try:
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
except Exception as e:
    logger.warning(f"Failed to initialize Groq Client: {e}")
    client = None

def design_system(intent: dict) -> dict:
    """
    Stage 2: Structured Intent -> System Architecture
    Calls Groq API to convert extracted intent into system design entities, roles, and flows.
    """
    logger.info(f"design_system called with intent: {json.dumps(intent)}")
    
    if not client:
        logger.error("Groq client is not initialized.")
        raise RuntimeError("Groq client is not initialized.")

    instruction = f"""
    Based on the following application intent, design a system architecture.
    Extract the necessary entities (with their fields), user roles, and main user flows.
    Ensure entities relate strictly to the requested features. Do not hallucinate unnecessary fields.
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
