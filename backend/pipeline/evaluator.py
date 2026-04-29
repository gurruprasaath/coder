"""
Pre-Execution Evaluation Engine
================================
Runs AFTER schema generation, BEFORE rendering.
Validates structural correctness, logical consistency, and execution readiness.

Output:
{
  "ready": bool,
  "score": 0-100,
  "errors": [...],
  "warnings": [...],
  "metrics": {...}
}
"""

from logger import setup_logger

logger = setup_logger(__name__)

# ── Score deductions ─────────────────────────────────────────────────────────
DEDUCTIONS = {
    "structural":    20,
    "api_db":        15,
    "ui_api":        15,
    "auth":          10,
    "execution":     20,
}

# ── Score thresholds ─────────────────────────────────────────────────────────
THRESHOLD_READY          = 85
THRESHOLD_READY_WARNINGS = 70


def _err(err_type: str, message: str, path: str = "") -> dict:
    return {"type": err_type, "message": message, "path": path}


def _warn(warn_type: str, message: str, path: str = "") -> dict:
    return {"type": warn_type, "message": message, "path": path}


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 1 — Structural Validation
# ─────────────────────────────────────────────────────────────────────────────
def _check_structural(config: dict, errors: list, warnings: list) -> int:
    deduction = 0
    required = ["ui", "api", "db", "auth"]

    for key in required:
        if key not in config:
            errors.append(_err("MISSING_ROOT_KEY", f"Root key '{key}' is missing.", f"root.{key}"))
            deduction += DEDUCTIONS["structural"] // len(required)
        elif not config[key]:
            errors.append(_err("EMPTY_SECTION", f"Root section '{key}' is null or empty.", f"root.{key}"))
            deduction += DEDUCTIONS["structural"] // len(required)

    # Check minimums
    tables  = config.get("db",  {}).get("tables",    [])
    eps     = config.get("api", {}).get("endpoints",  [])
    pages   = config.get("ui",  {}).get("pages",     [])
    roles   = config.get("auth",{}).get("roles",     [])

    if len(tables) < 1:
        errors.append(_err("NO_DB_TABLES", "No database tables defined — cannot generate an executable app.", "db.tables"))
        deduction += 5
    if len(eps) < 1:
        errors.append(_err("NO_API_ENDPOINTS", "No API endpoints defined.", "api.endpoints"))
        deduction += 5
    if len(pages) < 1:
        errors.append(_err("NO_UI_PAGES", "No UI pages defined.", "ui.pages"))
        deduction += 5
    if len(roles) < 1:
        warnings.append(_warn("NO_AUTH_ROLES", "No auth roles defined. Defaulting to public access.", "auth.roles"))

    return min(deduction, DEDUCTIONS["structural"])


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 2 — Database Validation
# ─────────────────────────────────────────────────────────────────────────────
def _check_database(config: dict, errors: list, warnings: list) -> dict:
    """
    Returns:
      deduction (int),
      table_field_map  { table_name: set(field_names) },
      pk_map           { table_name: list(pk_names) }
    """
    deduction   = 0
    table_field_map = {}
    pk_map          = {}

    tables = config.get("db", {}).get("tables", [])

    for t_idx, table in enumerate(tables):
        t_name  = table.get("name")
        fields  = table.get("fields", [])
        path    = f"db.tables[{t_idx}]"

        if not t_name:
            errors.append(_err("TABLE_NO_NAME", "A DB table is missing a name.", path))
            deduction += 3
            continue

        # Duplicate field check
        field_names = [f.get("name") for f in fields if f.get("name")]
        if len(field_names) != len(set(field_names)):
            duplicates = [n for n in field_names if field_names.count(n) > 1]
            errors.append(_err("DUPLICATE_FIELDS",
                               f"Table '{t_name}' has duplicate fields: {list(set(duplicates))}",
                               f"{path}.fields"))
            deduction += 2

        table_field_map[t_name] = set(field_names)

        # Primary key check
        pks = [f.get("name") for f in fields if f.get("is_primary")]
        pk_map[t_name] = pks
        if not pks:
            errors.append(_err("MISSING_PRIMARY_KEY",
                               f"Table '{t_name}' has no primary key.",
                               f"{path}.fields"))
            deduction += 4

        # Foreign key validation
        for f_idx, field in enumerate(fields):
            fk = field.get("foreign_key")
            if not fk:
                continue
            parts = fk.split(".")
            if len(parts) != 2:
                errors.append(_err("INVALID_FK_FORMAT",
                                   f"FK '{fk}' in '{t_name}' must be 'Table.field'.",
                                   f"{path}.fields[{f_idx}].foreign_key"))
                deduction += 2
            else:
                ref_table, ref_field = parts
                if ref_table not in table_field_map:
                    # May be forward-reference — raise warning only
                    warnings.append(_warn("FK_TABLE_NOT_FOUND",
                                         f"FK '{fk}' in '{t_name}' references unknown table '{ref_table}'. "
                                         "It may be a forward reference.",
                                         f"{path}.fields[{f_idx}].foreign_key"))
                elif ref_field not in table_field_map[ref_table]:
                    errors.append(_err("FK_FIELD_NOT_FOUND",
                                       f"FK '{fk}' in '{t_name}' references unknown field '{ref_field}'.",
                                       f"{path}.fields[{f_idx}].foreign_key"))
                    deduction += 2

    return deduction, table_field_map, pk_map


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 3 — API ↔ DB Consistency
# ─────────────────────────────────────────────────────────────────────────────
def _check_api_db(config: dict, table_field_map: dict, pk_map: dict,
                  errors: list, warnings: list) -> tuple:
    """Returns (deduction, endpoint_id_set)"""
    deduction    = 0
    endpoint_ids = set()

    valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH"}
    endpoints = config.get("api", {}).get("endpoints", [])

    for idx, ep in enumerate(endpoints):
        ep_id   = ep.get("id",     f"endpoint_{idx}")
        method  = ep.get("method", "").upper()
        related = ep.get("related_table", "")
        path    = f"api.endpoints[{idx}]"

        if ep_id:
            endpoint_ids.add(ep_id)

        # Method check
        if method not in valid_methods:
            errors.append(_err("INVALID_HTTP_METHOD",
                               f"Endpoint '{ep_id}' has invalid method '{method}'.",
                               f"{path}.method"))
            deduction += 3

        # related_table check
        if related not in table_field_map:
            errors.append(_err("API_DB_MISMATCH",
                               f"Endpoint '{ep_id}' references unknown table '{related}'.",
                               f"{path}.related_table"))
            deduction += 4
            continue

        valid_fields = table_field_map[related]

        # request_body field check
        for f_idx, field_obj in enumerate(ep.get("request_body", [])):
            fname = field_obj.get("name")
            if fname and fname not in valid_fields:
                errors.append(_err("API_DB_MISMATCH",
                                   f"Endpoint '{ep_id}' request_body field '{fname}' "
                                   f"not in table '{related}'.",
                                   f"{path}.request_body[{f_idx}].name"))
                deduction += 3

        # response_body field check
        for f_idx, field_obj in enumerate(ep.get("response_body", [])):
            fname = field_obj.get("name")
            if fname and fname not in valid_fields and fname != "success":
                errors.append(_err("API_DB_MISMATCH",
                                   f"Endpoint '{ep_id}' response_body field '{fname}' "
                                   f"not in table '{related}'.",
                                   f"{path}.response_body[{f_idx}].name"))
                deduction += 2

        # Security check — no passwords in response
        sensitive = {"password", "secret", "hash", "token"}
        resp_names = {f.get("name", "").lower() for f in ep.get("response_body", [])}
        exposed = sensitive & resp_names
        if exposed:
            errors.append(_err("SECURITY_VIOLATION",
                               f"Endpoint '{ep_id}' exposes sensitive fields: {exposed}.",
                               f"{path}.response_body"))
            deduction += 5

    return min(deduction, DEDUCTIONS["api_db"]), endpoint_ids


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 4 — UI ↔ API Consistency
# ─────────────────────────────────────────────────────────────────────────────
def _check_ui_api(config: dict, endpoint_ids: set, table_field_map: dict,
                  errors: list, warnings: list,
                  all_endpoints: list) -> int:
    deduction = 0
    pages = config.get("ui", {}).get("pages", [])
    total_components = 0

    for p_idx, page in enumerate(pages):
        page_name = page.get("name", f"page_{p_idx}")

        for c_idx, comp in enumerate(page.get("components", [])):
            total_components += 1
            comp_name = comp.get("name", f"comp_{c_idx}")
            ep_ref    = comp.get("endpoint_ref")
            path      = f"ui.pages[{p_idx}].components[{c_idx}]"

            if not ep_ref:
                warnings.append(_warn("COMPONENT_NO_ENDPOINT",
                                      f"Component '{comp_name}' has no endpoint_ref.",
                                      path))
                continue

            if ep_ref not in endpoint_ids:
                errors.append(_err("UI_API_MISMATCH",
                                   f"Component '{comp_name}' references unknown endpoint '{ep_ref}'.",
                                   f"{path}.endpoint_ref"))
                deduction += 5
                continue

            # Cross-validate form/table fields with API body
            ep_obj = next((e for e in all_endpoints if e.get("id") == ep_ref), None)
            if ep_obj:
                related = ep_obj.get("related_table", "")
                valid_fields = table_field_map.get(related, set())

                for f_idx, field in enumerate(comp.get("fields", [])):
                    if field not in valid_fields:
                        warnings.append(_warn("UI_DB_MISMATCH",
                                              f"Component '{comp_name}' field '{field}' "
                                              f"not in table '{related}'.",
                                              f"{path}.fields[{f_idx}]"))

    if total_components == 0:
        errors.append(_err("NO_USABLE_COMPONENTS",
                           "No UI components found. The app will be empty.", "ui.pages"))
        deduction += 10

    return min(deduction, DEDUCTIONS["ui_api"])


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 5 — Auth Validation
# ─────────────────────────────────────────────────────────────────────────────
def _check_auth(config: dict, endpoint_ids: set, errors: list, warnings: list) -> int:
    deduction = 0
    roles     = set(config.get("auth", {}).get("roles", []))
    rules     = config.get("auth", {}).get("rules", [])
    pages     = config.get("ui",   {}).get("pages",  [])

    if not roles:
        warnings.append(_warn("NO_ROLES", "Auth has no roles defined.", "auth.roles"))
        deduction += 3

    # UI access_role validation
    for p_idx, page in enumerate(pages):
        access_role = page.get("access_role")
        if access_role and access_role.lower() != "public" and access_role not in roles:
            errors.append(_err("INVALID_ACCESS_ROLE",
                               f"Page '{page.get('name')}' requires role '{access_role}' "
                               "which is not defined in auth.roles.",
                               f"ui.pages[{p_idx}].access_role"))
            deduction += 3

    # Auth rule endpoint reference check
    for r_idx, rule in enumerate(rules):
        role = rule.get("role")
        if role not in roles:
            errors.append(_err("AUTH_ROLE_MISMATCH",
                               f"Auth rule references undefined role '{role}'.",
                               f"auth.rules[{r_idx}].role"))
            deduction += 2

        for a_idx, ep_ref in enumerate(rule.get("allowed_endpoints", [])):
            if ep_ref not in endpoint_ids:
                warnings.append(_warn("AUTH_ENDPOINT_MISMATCH",
                                      f"Auth rule for '{role}' references unknown endpoint '{ep_ref}'.",
                                      f"auth.rules[{r_idx}].allowed_endpoints[{a_idx}]"))

    return min(deduction, DEDUCTIONS["auth"])


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 6 — Execution Simulation
# ─────────────────────────────────────────────────────────────────────────────
def _simulate_execution(config: dict, table_field_map: dict,
                        errors: list, warnings: list) -> int:
    """
    Dry-run simulation of:
      1. Form submission → payload field matching
      2. API call → schema match
      3. DB insert → field compatibility
    """
    deduction   = 0
    endpoints   = config.get("api", {}).get("endpoints", [])
    pages       = config.get("ui",  {}).get("pages", [])

    for page in pages:
        for comp in page.get("components", []):
            comp_name = comp.get("name", "unknown")
            comp_type = comp.get("type", "")
            ep_ref    = comp.get("endpoint_ref")

            if not ep_ref:
                continue

            # Find matching endpoint
            ep = next((e for e in endpoints if e.get("id") == ep_ref), None)
            if not ep:
                continue

            method  = ep.get("method", "GET").upper()
            related = ep.get("related_table", "")

            # Simulate form submission
            if comp_type == "form":
                comp_fields = set(comp.get("fields", []))
                req_fields  = {f.get("name") for f in ep.get("request_body", [])}
                db_fields   = table_field_map.get(related, set())

                # Check: all form fields exist in request_body
                missing_in_req = comp_fields - req_fields
                if missing_in_req:
                    errors.append(_err("EXECUTION_FAIL",
                                       f"FORM SIM: '{comp_name}' submits fields {missing_in_req} "
                                       f"not present in API '{ep_ref}' request_body. "
                                       "Form will fail at runtime.",
                                       f"ui.component.{comp_name}.fields"))
                    deduction += 5

                # Check: all request_body fields exist in DB
                missing_in_db = req_fields - db_fields
                # exclude auth-specific fields
                missing_in_db -= {"password", "secret", "token"}
                if missing_in_db:
                    errors.append(_err("EXECUTION_FAIL",
                                       f"API SIM: Endpoint '{ep_ref}' requests fields {missing_in_db} "
                                       f"that don't exist in DB table '{related}'. "
                                       "DB insert will fail at runtime.",
                                       f"api.endpoints.{ep_ref}.request_body"))
                    deduction += 5

            # Simulate table data load
            if comp_type == "table":
                if method not in ("GET",):
                    warnings.append(_warn("EXECUTION_WARN",
                                         f"TABLE SIM: Table component '{comp_name}' uses a "
                                         f"non-GET endpoint '{ep_ref}' ({method}). Data may not load.",
                                         f"ui.component.{comp_name}.endpoint_ref"))

    return min(deduction, DEDUCTIONS["execution"])


# ─────────────────────────────────────────────────────────────────────────────
# MAIN EVALUATOR
# ─────────────────────────────────────────────────────────────────────────────
def evaluate(config: dict) -> dict:
    """
    Pre-Execution Evaluation Engine.
    Returns { ready, score, errors, warnings, metrics }
    """
    logger.info("Pre-Execution Evaluator starting...")

    errors:   list = []
    warnings: list = []
    score          = 100

    # ── Run all checks ────────────────────────────────────────────────────────

    # 1. Structural
    d1 = _check_structural(config, errors, warnings)
    score -= d1

    # If structural is broken, skip deeper checks (config may be None-like)
    if d1 >= DEDUCTIONS["structural"]:
        logger.error("Structural failure — skipping deeper checks.")
        return _build_result(score, errors, warnings, config)

    # 2. Database
    d2, table_field_map, pk_map = _check_database(config, errors, warnings)
    score -= d2

    # 3. API ↔ DB
    all_endpoints = config.get("api", {}).get("endpoints", [])
    d3, endpoint_ids = _check_api_db(config, table_field_map, pk_map, errors, warnings)
    score -= d3

    # 4. UI ↔ API
    d4 = _check_ui_api(config, endpoint_ids, table_field_map, errors, warnings, all_endpoints)
    score -= d4

    # 5. Auth
    d5 = _check_auth(config, endpoint_ids, errors, warnings)
    score -= d5

    # 6. Execution Simulation
    d6 = _simulate_execution(config, table_field_map, errors, warnings)
    score -= d6

    score = max(0, score)
    logger.info(f"Evaluation complete. Score={score}, Errors={len(errors)}, Warnings={len(warnings)}")

    return _build_result(score, errors, warnings, config,
                         deductions={"structural": d1, "api_db": d3, "ui_api": d4, "auth": d5, "execution": d6})


def _build_result(score: int, errors: list, warnings: list, config: dict,
                  deductions: dict = None) -> dict:
    score = max(0, score)

    if score >= THRESHOLD_READY:
        ready  = True
        status = "READY"
    elif score >= THRESHOLD_READY_WARNINGS:
        ready  = True
        status = "READY_WITH_WARNINGS"
    else:
        ready  = False
        status = "NOT_READY"

    tables    = config.get("db",  {}).get("tables",    []) if config else []
    endpoints = config.get("api", {}).get("endpoints",  []) if config else []
    pages     = config.get("ui",  {}).get("pages",     []) if config else []
    roles     = config.get("auth",{}).get("roles",     []) if config else []

    metrics = {
        "table_count":     len(tables),
        "endpoint_count":  len(endpoints),
        "page_count":      len(pages),
        "role_count":      len(roles),
        "error_count":     len(errors),
        "warning_count":   len(warnings),
        "deductions":      deductions or {},
    }

    return {
        "ready":    ready,
        "status":   status,
        "score":    score,
        "errors":   errors,
        "warnings": warnings,
        "metrics":  metrics,
    }
