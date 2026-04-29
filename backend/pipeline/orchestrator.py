import time
from logger import setup_logger
from pipeline.intent import extract_intent
from pipeline.design import design_system
from pipeline.schema import generate_schema
from pipeline.validator import validate_schema
from pipeline.repair import repair_schema
from pipeline.evaluator import evaluate

logger = setup_logger(__name__)


def run_pipeline(prompt: str) -> dict:
    """
    Orchestrates the complete AI Compiler pipeline.

    Stages:
      1. Intent Extraction        — parse user intent, detect vague prompts
      2. System Design            — entities, flows, roles
      3. Schema Generation        — UI / API / DB / Auth config
      4. Structural Validation    — JSON / cross-layer checks
      5. Repair Loop              — targeted fix, max 2 attempts
      6. Pre-Execution Evaluation — score, simulate execution, gate UI render
      7. DB Auto-Creation         — execute CREATE TABLE IF NOT EXISTS
    """
    logs = []

    def log_step(step_name: str, duration_ms: float, details: str = None):
        entry = f"[{step_name}] completed in {duration_ms:.2f}ms"
        if details:
            entry += f" — {details}"
        logs.append(entry)
        logger.info(entry)

    logger.info(f"Pipeline started for prompt: \"{prompt}\"")

    try:
        # ── Stage 1: Intent Extraction ────────────────────────────────────────
        start  = time.time()
        intent = extract_intent(prompt)
        log_step("Intent Extraction", (time.time() - start) * 1000)

        if intent.get("needs_clarification"):
            logger.warning("Pipeline halted — vague prompt detected.")
            return {
                "config":                  None,
                "logs":                    logs,
                "valid":                   False,
                "needs_clarification":     True,
                "clarification_questions": intent.get("clarification_questions", []),
                "assumptions":             intent.get("assumptions", []),
                "message":                 "Your prompt is too vague. Please answer the clarification questions.",
            }

        # ── Stage 2: System Design ────────────────────────────────────────────
        start  = time.time()
        design = design_system(intent)
        log_step("System Design", (time.time() - start) * 1000)

        # ── Stage 3: Schema Generation ────────────────────────────────────────
        start  = time.time()
        schema = generate_schema(design)
        log_step("Schema Generation", (time.time() - start) * 1000)

        # ── Stage 4: Structural Validation ────────────────────────────────────
        start      = time.time()
        validation = validate_schema(schema)
        log_step("Structural Validation", (time.time() - start) * 1000,
                 f"Valid: {validation['is_valid']}")

        # ── Stage 5: Repair Loop (max 10 cycles) ───────────────────────────────
        repair_count = 0
        max_repairs  = 10

        while not validation.get("is_valid") and repair_count < max_repairs:
            repair_count += 1
            logger.info(f"Repair cycle {repair_count}/{max_repairs}")

            start  = time.time()
            schema = repair_schema(schema, validation["errors"])
            log_step(f"Repair Cycle {repair_count}", (time.time() - start) * 1000)

            start      = time.time()
            validation = validate_schema(schema)
            log_step(f"Validation (Post-Repair {repair_count})",
                     (time.time() - start) * 1000, f"Valid: {validation['is_valid']}")

        # ── Stage 6: Pre-Execution Evaluation & Functional Loop ────────────────
        start      = time.time()
        evaluation = evaluate(schema)
        log_step("Pre-Execution Evaluation", (time.time() - start) * 1000,
                 f"Score: {evaluation['score']} | Status: {evaluation['status']}")

        # Loop to enforce perfect execution score (100) based on functional simulation
        eval_repair_count = 0
        max_eval_repairs = 10
        stalled_count = 0
        previous_score = evaluation.get("score", 0)
        
        while not evaluation.get("ready") and eval_repair_count < max_eval_repairs:
            eval_repair_count += 1
            logger.warning(f"Evaluation Score {previous_score}/100. "
                           f"Running Functional Perfection Repair {eval_repair_count}/{max_eval_repairs}.")
            
            # Re-run structural validation just to fetch any new EXECUTION_ERRORs we added
            # The evaluator uses validator outputs in part.
            val_check = validate_schema(schema)
            errors_to_fix = evaluation.get("errors", []) + val_check.get("errors", [])
            
            start  = time.time()
            schema = repair_schema(schema, errors_to_fix)
            log_step(f"Functional Repair {eval_repair_count}", (time.time() - start) * 1000)

            start      = time.time()
            evaluation = evaluate(schema)
            current_score = evaluation.get("score", 0)
            log_step(f"Re-Evaluation {eval_repair_count}", (time.time() - start) * 1000,
                     f"Score: {current_score} | Status: {evaluation['status']}")
                     
            if current_score <= previous_score:
                stalled_count += 1
            else:
                stalled_count = 0
                
            if stalled_count >= 2:
                logger.warning("Score has stalled for 2 consecutive iterations. Breaking early to save tokens.")
                log_step("Smart Early-Exit", 0, "Score stalled.")
                break
                
            previous_score = current_score

        # ── Stage 7: DB Auto-Creation ──────────────────────────────────────────
        # Always try to create DB tables so the frontend preview doesn't crash with 404s
        try:
            start = time.time()
            from schema_interpreter import interpret_and_create_tables
            interpret_and_create_tables(schema.get("db", {}))
            log_step("Database Schema Auto-Creation", (time.time() - start) * 1000)
            if not evaluation.get("ready", False):
                logger.warning("DB tables created, but evaluation indicates app is NOT_READY. Some routes may fail.")
        except Exception as e:
            logger.error(f"DB auto-creation failed: {e}")

        return {
            "config":     schema,
            "logs":       logs,
            "valid":      validation.get("is_valid", False),
            "evaluation": evaluation,
        }

    except Exception as e:
        logger.error(f"Pipeline fatal error: {e}")
        logs.append(f"[FATAL] {str(e)}")
        return {
            "config":     None,
            "logs":       logs,
            "valid":      False,
            "evaluation": None,
        }
