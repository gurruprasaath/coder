import os
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from groq import Groq

from logger import setup_logger

logger = setup_logger(__name__)

# ── Schema for a CLEAR, well-specified prompt ────────────────────────────────

class IntentSchema(BaseModel):
    app_type: str = Field(description="The type of application (e.g., Web App, Mobile App, API)")
    features: List[str] = Field(description="List of specific features requested")
    roles: List[str] = Field(description="List of user roles mentioned or implied")
    uncertainties: List[str] = Field(description="Minor ambiguities that can be handled with safe assumptions")
    needs_clarification: bool = Field(
        description="True ONLY if critical info is missing and the pipeline CANNOT proceed safely"
    )
    clarification_questions: Optional[List[str]] = Field(
        default=None,
        description="2-3 targeted questions to ask the user when needs_clarification is true"
    )
    assumptions: Optional[List[str]] = Field(
        default=None,
        description="Reasonable assumptions made for minor gaps — always included"
    )

# ── Groq Client ──────────────────────────────────────────────────────────────

try:
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
except Exception as e:
    logger.warning(f"Failed to initialize Groq Client: {e}")
    client = None

# ── Vagueness Rules (fast, deterministic pre-check) ─────────────────────────

VAGUE_SIGNALS = [
    "app", "website", "system", "tool", "platform", "something",
    "build me", "make a", "create a"
]

def _is_critically_vague(prompt: str) -> bool:
    """
    Fast heuristic: flag prompts that are dangerously short or contain
    only generic terms with no domain-specific detail.
    """
    words = prompt.strip().split()
    if len(words) < 5:
        return True
    # Short prompt that only contains vague signals
    meaningful = [w for w in words if w.lower() not in VAGUE_SIGNALS
                  and len(w) > 3]
    return len(meaningful) < 2


# ── Main extraction function ─────────────────────────────────────────────────

def extract_intent(prompt: str) -> dict:
    """
    Stage 1: Intent Extraction
    Returns structured intent. If the prompt is critically vague,
    sets needs_clarification = True and returns clarification questions
    WITHOUT calling later pipeline stages.
    """
    logger.info(f"extract_intent called with: \"{prompt}\"")

    if not client:
        raise RuntimeError("Groq client is not initialized.")

    instruction = f"""
You are the Intent Extraction stage of an AI application compiler.
Your job is to parse a user's application description and decide:
1. Whether it contains ENOUGH information to generate a complete app schema.
2. What the structured intent is.

CRITICAL VAGUENESS RULES — set needs_clarification: true if ANY of these apply:
- No domain / use-case mentioned (e.g., just "build me an app")
- No features or entities mentioned (e.g., no users, products, orders, etc.)
- Completely contradictory requirements (e.g., "offline AND real-time sync")
- Fewer than 3 meaningful concepts present

If needs_clarification is TRUE:
- Generate exactly 2-3 SHORT, specific clarification_questions
- DO NOT populate features/roles with hallucinated data
- Set features: [] and roles: []

If needs_clarification is FALSE:
- Fill ALL fields fully
- List assumptions you made for any minor gaps

Return ONLY valid JSON matching this schema:
{json.dumps(IntentSchema.model_json_schema(), indent=2)}

User Prompt:
"{prompt}"
"""

    max_retries = 1
    attempt = 0

    while attempt <= max_retries:
        try:
            logger.info(f"Calling Groq API for Intent Extraction (Attempt {attempt + 1})")
            response = client.chat.completions.create(
                model='llama-3.1-8b-instant',
                messages=[{"role": "user", "content": instruction}],
                temperature=0.0,
                response_format={"type": "json_object"}
            )

            output_json = json.loads(response.choices[0].message.content)

            # --- Fast deterministic override ---
            # If our local heuristic detects critical vagueness but the LLM missed it,
            # we enforce needs_clarification = True
            if _is_critically_vague(prompt) and not output_json.get("needs_clarification"):
                logger.warning("Heuristic override: prompt is critically vague — forcing clarification.")
                output_json["needs_clarification"] = True
                output_json.setdefault("clarification_questions", [
                    "What is the main purpose or domain of this application?",
                    "Who are the intended users and what roles do they have?",
                    "What are the 3–5 core features you need?"
                ])
                output_json["features"] = []
                output_json["roles"] = []

            logger.info(f"Intent extracted: needs_clarification={output_json.get('needs_clarification')}, "
                        f"features={output_json.get('features')}")
            return output_json

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON from Groq on attempt {attempt + 1}: {e}")
            attempt += 1
            if attempt > max_retries:
                raise ValueError("Failed to parse valid JSON from Groq API after retries.")
        except Exception as e:
            logger.error(f"API Error on attempt {attempt + 1}: {e}")
            attempt += 1
            if attempt > max_retries:
                raise e
