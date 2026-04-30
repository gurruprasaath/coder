import time
import json
import hashlib
import datetime
from backend.logger import setup_logger
from backend.pipeline.intent import extract_intent
from backend.pipeline.design import design_system
from backend.pipeline.schema import generate_schema
from backend.pipeline.validator import validate_schema
from backend.pipeline.repair import repair_schema
from backend.pipeline.evaluator import evaluate

logger = setup_logger(__name__)

# ── In-memory evaluation log store ───────────────────────────────────────────
evaluation_logs = []

# ── Prompt-level result cache ────────────────────────────────────────────────
_pipeline_cache = {}

def _cache_key(prompt: str) -> str:
    """Generate a deterministic hash for a prompt."""
    return hashlib.sha256(prompt.strip().lower().encode()).hexdigest()

def _config_hash(config: dict) -> str:
    """Hash a config dict to detect changes."""
    return hashlib.md5(json.dumps(config, sort_keys=True).encode()).hexdigest()


def get_evaluation_logs():
    """Return all evaluation logs and a computed summary."""
    total = len(evaluation_logs)
    successes = sum(1 for l in evaluation_logs if l["success"])
    failures = total - successes
    avg_latency = round(sum(l["latency_ms"] for l in evaluation_logs) / total, 1) if total else 0

    # Aggregate failure types
    failure_types = {}
    for log in evaluation_logs:
        for err_type in log.get("error_types", []):
            failure_types[err_type] = failure_types.get(err_type, 0) + 1

    return {
        "logs": evaluation_logs,
        "summary": {
            "total_generations": total,
            "successes": successes,
            "failures": failures,
            "success_rate": round((successes / total) * 100, 1) if total else 0,
            "avg_latency_ms": avg_latency,
            "failure_types": failure_types,
        }
    }


def run_pipeline(prompt: str) -> dict:
    """
    Orchestrates the complete AI Compiler pipeline.

    Stages:
      1. Intent Extraction        — parse user intent, detect vague prompts
      2. System Design            — entities, flows, roles
      3. Schema Generation        — UI / API / DB / Auth config
      4. Structural Validation    — JSON / cross-layer checks
      5. Repair Loop              — targeted fix, max 5 attempts (CONDITIONAL)
      6. Pre-Execution Evaluation — score, simulate execution, gate UI render
      7. DB Auto-Creation         — execute CREATE TABLE IF NOT EXISTS

    Optimizations:
      - Prompt caching: identical prompts return cached results instantly
      - Conditional repair: repair only runs if validation fails
      - Config hashing: skip re-validation if config unchanged
      - Fast exit: critical failures halt the pipeline immediately
      - API call tracking: every LLM call is counted
    """
    logs = []
    api_calls = 0     # Track total LLM API calls

    def log_step(step_name: str, duration_ms: float, details: str = None):
        entry = f"[{step_name}] completed in {duration_ms:.2f}ms"
        if details:
            entry += f" — {details}"
        logs.append(entry)
        logger.info(entry)

    logger.info(f"Pipeline started for prompt: \"{prompt}\"")
    pipeline_start = time.time()

    # ── Cache Check ────────────────────────────────────────────────────────
    ck = _cache_key(prompt)
    if ck in _pipeline_cache:
        logger.info("Cache HIT — returning cached result.")
        cached = _pipeline_cache[ck]
        log_step("Cache Hit", 0, "Returning previously computed result")

        eval_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "prompt": prompt[:120],
            "success": cached.get("evaluation", {}).get("ready", False),
            "score": cached.get("evaluation", {}).get("score", 0),
            "retries": 0,
            "structural_repairs": 0,
            "functional_repairs": 0,
            "latency_ms": round((time.time() - pipeline_start) * 1000, 1),
            "execution_errors": cached.get("evaluation", {}).get("execution_errors", 0),
            "coverage_pct": cached.get("evaluation", {}).get("coverage_pct", 0),
            "error_types": [],
            "error_count": 0,
            "api_calls": 0,
            "cached": True,
        }
        evaluation_logs.append(eval_entry)
        return {**cached, "logs": logs, "eval_metrics": eval_entry}

    try:
        # ── Stage 1: Intent Extraction (1 API call) ───────────────────────────
        start  = time.time()
        intent = extract_intent(prompt)
        api_calls += 1
        log_step("Intent Extraction", (time.time() - start) * 1000)

        # FAST EXIT: vague prompt
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

        # FAST EXIT: intent extraction returned nothing usable
        if not intent or not intent.get("app_type"):
            logger.error("Fast Exit — intent extraction returned no usable data.")
            log_step("Fast Exit", 0, "Intent extraction failed critically")
            raise ValueError("Intent extraction returned no usable data. Please refine your prompt.")

        # ── Stage 2: System Design (1 API call) ──────────────────────────────
        start  = time.time()
        design = design_system(intent)
        api_calls += 1
        log_step("System Design", (time.time() - start) * 1000)

        # FAST EXIT: design returned no entities
        if not design or not design.get("entities"):
            logger.error("Fast Exit — system design produced no entities.")
            log_step("Fast Exit", 0, "Design stage failed critically")
            raise ValueError("System design produced no entities. Cannot proceed.")

        # ── Stage 3: Schema Generation (1 API call for layered pipeline) ─────
        start  = time.time()
        schema = generate_schema(design)
        api_calls += 1
        log_step("Schema Generation", (time.time() - start) * 1000)

        # FAST EXIT: schema generation returned nothing
        if not schema or not isinstance(schema, dict):
            logger.error("Fast Exit — schema generation returned invalid data.")
            log_step("Fast Exit", 0, "Schema generation failed critically")
            raise ValueError("Schema generation returned invalid data.")

        # ── Stage 4: Structural Validation (NO API call — local) ─────────────
        start      = time.time()
        validation = validate_schema(schema)
        log_step("Structural Validation", (time.time() - start) * 1000,
                 f"Valid: {validation['is_valid']}")

        # ── Stage 5: Conditional Repair (max 5 cycles, only if needed) ───────
        repair_count = 0
        max_repairs  = 5

        if validation.get("is_valid"):
            logger.info("Validation passed — skipping repair entirely.")
            log_step("Repair Skipped", 0, "Validation passed on first try")
        else:
            last_config_hash = _config_hash(schema)

            while not validation.get("is_valid") and repair_count < max_repairs:
                repair_count += 1
                logger.info(f"Repair cycle {repair_count}/{max_repairs}")

                start  = time.time()
                schema = repair_schema(schema, validation["errors"])
                api_calls += 1  # Each repair section = 1 API call per broken section
                log_step(f"Repair Cycle {repair_count}", (time.time() - start) * 1000)

                # Check if config actually changed — skip validation if identical
                new_hash = _config_hash(schema)
                if new_hash == last_config_hash:
                    logger.warning(f"Repair {repair_count} produced no changes — breaking early.")
                    log_step(f"Repair Stalled {repair_count}", 0, "No config changes detected")
                    break

                last_config_hash = new_hash

                start      = time.time()
                validation = validate_schema(schema)
                log_step(f"Validation (Post-Repair {repair_count})",
                         (time.time() - start) * 1000, f"Valid: {validation['is_valid']}")

        # ── Stage 6: Pre-Execution Evaluation (NO API call — local) ──────────
        start      = time.time()
        evaluation = evaluate(schema)
        log_step("Pre-Execution Evaluation", (time.time() - start) * 1000,
                 f"Score: {evaluation['score']} | Status: {evaluation['status']}")

        # Functional repair loop — max 5 cycles, with smart stall detection
        eval_repair_count = 0
        max_eval_repairs = 5
        stalled_count = 0
        previous_score = evaluation.get("score", 0)
        
        if evaluation.get("ready"):
            logger.info("Evaluation passed — skipping functional repair.")
            log_step("Functional Repair Skipped", 0, "All quality gates passed")
        else:
            while not evaluation.get("ready") and eval_repair_count < max_eval_repairs:
                eval_repair_count += 1
                logger.warning(f"Evaluation Score {previous_score}/100. "
                               f"Running Functional Repair {eval_repair_count}/{max_eval_repairs}.")
                
                errors_to_fix = evaluation.get("errors", [])
                
                start  = time.time()
                schema = repair_schema(schema, errors_to_fix)
                api_calls += 1
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
                    logger.warning("Score stalled for 2 iterations. Breaking early to save tokens.")
                    log_step("Smart Early-Exit", 0, "Score stalled.")
                    break
                    
                previous_score = current_score

        # ── Stage 7: DB Auto-Creation ──────────────────────────────────────────
        try:
            start = time.time()
            from schema_interpreter import interpret_and_create_tables
            interpret_and_create_tables(schema.get("db", {}))
            log_step("Database Schema Auto-Creation", (time.time() - start) * 1000)
        except Exception as e:
            logger.error(f"DB auto-creation failed: {e}")

        # ── Track evaluation metrics ───────────────────────────────────────────
        total_retries = repair_count + eval_repair_count
        latency_ms = round((time.time() - pipeline_start) * 1000, 1)
        error_types = list({e.get("type") for e in evaluation.get("errors", [])})

        eval_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "prompt": prompt[:120],
            "success": evaluation.get("ready", False),
            "score": evaluation.get("score", 0),
            "retries": total_retries,
            "structural_repairs": repair_count,
            "functional_repairs": eval_repair_count,
            "latency_ms": latency_ms,
            "execution_errors": evaluation.get("execution_errors", 0),
            "coverage_pct": evaluation.get("coverage_pct", 0),
            "error_types": error_types,
            "error_count": len(evaluation.get("errors", [])),
            "api_calls": api_calls,
            "cached": False,
        }
        evaluation_logs.append(eval_entry)
        logger.info(f"Eval logged: success={eval_entry['success']}, score={eval_entry['score']}, "
                     f"retries={total_retries}, api_calls={api_calls}, latency={latency_ms}ms")

        result = {
            "config":     schema,
            "logs":       logs,
            "valid":      validation.get("is_valid", False),
            "evaluation": evaluation,
            "eval_metrics": eval_entry,
        }

        # ── Cache the successful result ────────────────────────────────────────
        _pipeline_cache[ck] = {
            "config":     schema,
            "valid":      validation.get("is_valid", False),
            "evaluation": evaluation,
        }
        logger.info(f"Result cached for prompt hash: {ck[:12]}...")

        return result

    except Exception as e:
        logger.error(f"Pipeline fatal error: {e}")
        logs.append(f"[FATAL] {str(e)}")

        latency_ms = round((time.time() - pipeline_start) * 1000, 1)
        eval_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "prompt": prompt[:120],
            "success": False,
            "score": 0,
            "retries": 0,
            "structural_repairs": 0,
            "functional_repairs": 0,
            "latency_ms": latency_ms,
            "execution_errors": 0,
            "coverage_pct": 0,
            "error_types": ["FATAL_ERROR"],
            "error_count": 1,
            "api_calls": api_calls,
            "cached": False,
        }
        evaluation_logs.append(eval_entry)

        return {
            "config":     None,
            "logs":       logs,
            "valid":      False,
            "evaluation": None,
            "eval_metrics": eval_entry,
        }
