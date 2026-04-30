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

from backend.logger import setup_logger

logger = setup_logger(__name__)




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
        deduction += 20
    if len(eps) < 1:
        errors.append(_err("NO_API_ENDPOINTS", "No API endpoints defined.", "api.endpoints"))
        deduction += 20
    if len(pages) < 1:
        errors.append(_err("NO_UI_PAGES", "No UI pages defined.", "ui.pages"))
        deduction += 20
    if len(roles) < 1:
        errors.append(_err("EXECUTION_ERROR", "No auth roles defined. Public access by default is blocked.", "auth.roles"))
        deduction += 20

    return deduction


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
            deduction += 15
            continue

        # Duplicate field check
        field_names = [f.get("name") for f in fields if f.get("name")]
        if len(field_names) != len(set(field_names)):
            duplicates = [n for n in field_names if field_names.count(n) > 1]
            errors.append(_err("DUPLICATE_FIELDS",
                               f"Table '{t_name}' has duplicate fields: {list(set(duplicates))}",
                               f"{path}.fields"))
            deduction += 15

        table_field_map[t_name] = set(field_names)

        # Primary key check
        pks = [f.get("name") for f in fields if f.get("is_primary")]
        pk_map[t_name] = pks
        if not pks:
            errors.append(_err("MISSING_PRIMARY_KEY",
                               f"Table '{t_name}' has no primary key.",
                               f"{path}.fields"))
            deduction += 20

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
                deduction += 15
            else:
                ref_table, ref_field = parts
                if ref_table not in table_field_map:
                    # No forward references allowed in zero-tolerance mode
                    errors.append(_err("EXECUTION_ERROR",
                                         f"FK '{fk}' in '{t_name}' references unknown table '{ref_table}'.",
                                         f"{path}.fields[{f_idx}].foreign_key"))
                    deduction += 20
                elif ref_field not in table_field_map[ref_table]:
                    errors.append(_err("FK_FIELD_NOT_FOUND",
                                       f"FK '{fk}' in '{t_name}' references unknown field '{ref_field}'.",
                                       f"{path}.fields[{f_idx}].foreign_key"))
                    deduction += 15

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
            deduction += 15

        # related_table check
        if related not in table_field_map:
            errors.append(_err("EXECUTION_ERROR",
                               f"Endpoint '{ep_id}' references unknown table '{related}'.",
                               f"{path}.related_table"))
            deduction += 20
            continue

        valid_fields = table_field_map[related]

        # request_body field check
        for f_idx, field_obj in enumerate(ep.get("request_body", [])):
            fname = field_obj.get("name")
            if fname and fname not in valid_fields:
                errors.append(_err("EXECUTION_ERROR",
                                   f"Endpoint '{ep_id}' request_body field '{fname}' "
                                   f"not in table '{related}'.",
                                   f"{path}.request_body[{f_idx}].name"))
                deduction += 20

        # response_body field check
        for f_idx, field_obj in enumerate(ep.get("response_body", [])):
            fname = field_obj.get("name")
            if fname and fname not in valid_fields and fname != "success":
                errors.append(_err("EXECUTION_ERROR",
                                   f"Endpoint '{ep_id}' response_body field '{fname}' "
                                   f"not in table '{related}'.",
                                   f"{path}.response_body[{f_idx}].name"))
                deduction += 20

        # Security check — no passwords in response
        sensitive = {"password", "secret", "hash", "token"}
        resp_names = {f.get("name", "").lower() for f in ep.get("response_body", [])}
        exposed = sensitive & resp_names
        if exposed:
            errors.append(_err("SECURITY_VIOLATION",
                               f"Endpoint '{ep_id}' exposes sensitive fields: {exposed}.",
                               f"{path}.response_body"))
            deduction += 25
            
    # Orphan Checking: Find tables that have no API endpoints
    used_tables = {ep.get("related_table") for ep in endpoints if ep.get("related_table")}
    unused_tables = set(table_field_map.keys()) - used_tables
    for unused in unused_tables:
        errors.append(_err("EXECUTION_ERROR",
                           f"Database Table '{unused}' has no API endpoints referencing it. It is orphaned.",
                           "db.tables"))
        deduction += 20

    return deduction, endpoint_ids


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 4 — UI ↔ API Consistency
# ─────────────────────────────────────────────────────────────────────────────
def _check_ui_api(config: dict, endpoint_ids: set, table_field_map: dict,
                  errors: list, warnings: list,
                  all_endpoints: list) -> int:
    deduction = 0
    pages = config.get("ui", {}).get("pages", [])
    total_components = 0

    used_endpoints = set()
    for p_idx, page in enumerate(pages):
        page_name = page.get("name", f"page_{p_idx}")

        for c_idx, comp in enumerate(page.get("components", [])):
            total_components += 1
            comp_name = comp.get("name", f"comp_{c_idx}")
            ep_ref    = comp.get("endpoint_ref")
            path      = f"ui.pages[{p_idx}].components[{c_idx}]"

            if not ep_ref:
                errors.append(_err("EXECUTION_ERROR",
                                   f"Component '{comp_name}' has no endpoint_ref.",
                                   path))
                deduction += 20
                continue
                
            used_endpoints.add(ep_ref)

            if ep_ref not in endpoint_ids:
                errors.append(_err("EXECUTION_ERROR",
                                   f"Component '{comp_name}' references unknown endpoint '{ep_ref}'.",
                                   f"{path}.endpoint_ref"))
                deduction += 20
                continue

            # Cross-validate form/table fields with API body
            ep_obj = next((e for e in all_endpoints if e.get("id") == ep_ref), None)
            if ep_obj:
                related = ep_obj.get("related_table", "")
                valid_fields = table_field_map.get(related, set())

                for f_idx, field in enumerate(comp.get("fields", [])):
                    if field not in valid_fields:
                        errors.append(_err("EXECUTION_ERROR",
                                           f"Component '{comp_name}' field '{field}' "
                                           f"not in table '{related}'.",
                                           f"{path}.fields[{f_idx}]"))
                        deduction += 20

    if total_components == 0:
        errors.append(_err("EXECUTION_ERROR",
                           "No UI components found. The app will be empty.", "ui.pages"))
        deduction += 20
        
    # Orphan Checking: Find endpoints that are never used in UI
    unused_endpoints = endpoint_ids - used_endpoints
    for unused in unused_endpoints:
        errors.append(_err("EXECUTION_ERROR",
                           f"API Endpoint '{unused}' is never used by any UI component.",
                           "api.endpoints"))
        deduction += 20

    return deduction


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 5 — Auth Validation
# ─────────────────────────────────────────────────────────────────────────────
def _check_auth(config: dict, endpoint_ids: set, errors: list, warnings: list) -> int:
    deduction = 0
    roles     = set(config.get("auth", {}).get("roles", []))
    rules     = config.get("auth", {}).get("rules", [])
    pages     = config.get("ui",   {}).get("pages",  [])

    if not roles:
        errors.append(_err("EXECUTION_ERROR", "Auth has no roles defined.", "auth.roles"))
        deduction += 20

    # UI access_role validation
    for p_idx, page in enumerate(pages):
        access_role = page.get("access_role")
        if access_role and access_role.lower() != "public" and access_role not in roles:
            errors.append(_err("EXECUTION_ERROR",
                               f"Page '{page.get('name')}' requires role '{access_role}' "
                               "which is not defined in auth.roles.",
                               f"ui.pages[{p_idx}].access_role"))
            deduction += 20

    # Auth rule endpoint reference check
    for r_idx, rule in enumerate(rules):
        role = rule.get("role")
        if role not in roles:
            errors.append(_err("EXECUTION_ERROR",
                               f"Auth rule references undefined role '{role}'.",
                               f"auth.rules[{r_idx}].role"))
            deduction += 20

        for a_idx, ep_ref in enumerate(rule.get("allowed_endpoints", [])):
            if ep_ref not in endpoint_ids:
                errors.append(_err("EXECUTION_ERROR",
                                   f"Auth rule for '{role}' references unknown endpoint '{ep_ref}'.",
                                   f"auth.rules[{r_idx}].allowed_endpoints[{a_idx}]"))
                deduction += 20

    return deduction


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
                    errors.append(_err("EXECUTION_ERROR",
                                       f"FORM SIM: '{comp_name}' submits fields {missing_in_req} "
                                       f"not present in API '{ep_ref}' request_body. "
                                       "Form will fail at runtime.",
                                       f"ui.component.{comp_name}.fields"))
                    deduction += 20

                # Check: all request_body fields exist in DB
                missing_in_db = req_fields - db_fields
                # exclude auth-specific fields
                missing_in_db -= {"password", "secret", "token"}
                if missing_in_db:
                    errors.append(_err("EXECUTION_ERROR",
                                       f"API SIM: Endpoint '{ep_ref}' requests fields {missing_in_db} "
                                       f"that don't exist in DB table '{related}'. "
                                       "DB insert will fail at runtime.",
                                       f"api.endpoints.{ep_ref}.request_body"))
                    deduction += 20

            # Simulate table data load
            if comp_type == "table":
                if method not in ("GET",):
                    errors.append(_err("EXECUTION_ERROR",
                                         f"TABLE SIM: Table component '{comp_name}' uses a "
                                         f"non-GET endpoint '{ep_ref}' ({method}). Data may not load.",
                                         f"ui.component.{comp_name}.endpoint_ref"))
                    deduction += 20

    return deduction


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 7 — CRUD Entity Coverage
# ─────────────────────────────────────────────────────────────────────────────
def _check_crud_coverage(config: dict, errors: list, warnings: list) -> int:
    deduction = 0
    tables = config.get("db", {}).get("tables", [])
    endpoints = config.get("api", {}).get("endpoints", [])
    pages = config.get("ui", {}).get("pages", [])

    for table in tables:
        t_name = table.get("name")
        if not t_name: continue
        
        # 1. API Coverage
        has_post = False
        has_get = False
        has_put = False
        has_delete = False
        
        for ep in endpoints:
            if ep.get("related_table") == t_name:
                method = ep.get("method", "").upper()
                if method == "POST": has_post = True
                elif method == "GET": has_get = True
                elif method in ("PUT", "PATCH"): has_put = True
                elif method == "DELETE": has_delete = True
                
        if not (has_post and has_get and has_put and has_delete):
            errors.append(_err("EXECUTION_ERROR",
                               f"Entity '{t_name}' missing full API CRUD operations. Found: POST={has_post}, GET={has_get}, PUT={has_put}, DELETE={has_delete}.",
                               f"api.endpoints"))
            deduction += 20
            
        # 2. UI Coverage
        has_form = False
        has_table = False
        has_button = False
        
        for page in pages:
            for comp in page.get("components", []):
                ep_ref = comp.get("endpoint_ref")
                comp_type = comp.get("type", "").lower()
                
                # Check if this component's endpoint is related to this table
                ep = next((e for e in endpoints if e.get("id") == ep_ref), None)
                if ep and ep.get("related_table") == t_name:
                    if comp_type == "form": has_form = True
                    elif comp_type == "table": has_table = True
                    elif comp_type == "button": has_button = True
                    
        if not (has_form and has_table and has_button):
            errors.append(_err("EXECUTION_ERROR",
                               f"Entity '{t_name}' missing full UI CRUD bindings. Found: form={has_form}, table={has_table}, action_button={has_button}.",
                               f"ui.pages"))
            deduction += 20

    return deduction


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY BUDGETS
# ─────────────────────────────────────────────────────────────────────────────
CATEGORY_BUDGETS = {
    "structure":   20,   # Root keys, table/endpoint/page existence
    "consistency": 25,   # API↔DB field matching, UI↔API binding
    "execution":   30,   # Simulation dry-runs, form→API→DB chain
    "coverage":    15,   # CRUD completeness per entity
    "ux":          10,   # Auth roles, dashboard/home pages, navigation
}


# ─────────────────────────────────────────────────────────────────────────────
# MAIN EVALUATOR
# ─────────────────────────────────────────────────────────────────────────────
def evaluate(config: dict) -> dict:
    """
    Pre-Execution Evaluation Engine.
    Scores across 5 categories: structure, consistency, execution, coverage, ux.
    Returns { ready, score, scores, execution_errors, coverage_pct, errors, warnings, metrics }
    """
    logger.info("Pre-Execution Evaluator starting...")

    errors:   list = []
    warnings: list = []

    # Category deduction accumulators
    cat_deductions = {k: 0 for k in CATEGORY_BUDGETS}

    # ── 1. Structural (budget: 20) ─────────────────────────────────────────
    d1 = _check_structural(config, errors, warnings)
    cat_deductions["structure"] += d1

    if d1 >= 20:
        logger.error("Structural failure — skipping deeper checks.")
        return _build_result(cat_deductions, errors, warnings, config)

    # ── 2. Database (feeds into consistency) ────────────────────────────────
    d2, table_field_map, pk_map = _check_database(config, errors, warnings)
    cat_deductions["structure"] += d2   # DB structural issues count as structure

    # ── 3. API ↔ DB consistency (budget: 25) ────────────────────────────────
    all_endpoints = config.get("api", {}).get("endpoints", [])
    d3, endpoint_ids = _check_api_db(config, table_field_map, pk_map, errors, warnings)
    cat_deductions["consistency"] += d3

    # ── 4. UI ↔ API consistency (also consistency) ──────────────────────────
    d4 = _check_ui_api(config, endpoint_ids, table_field_map, errors, warnings, all_endpoints)
    cat_deductions["consistency"] += d4

    # ── 5. Auth → UX category (budget: 10) ──────────────────────────────────
    d5 = _check_auth(config, endpoint_ids, errors, warnings)
    cat_deductions["ux"] += d5

    # ── 6. Execution Simulation (budget: 30) ────────────────────────────────
    d6 = _simulate_execution(config, table_field_map, errors, warnings)
    cat_deductions["execution"] += d6

    # ── 7. CRUD Coverage (budget: 15) ───────────────────────────────────────
    d7 = _check_crud_coverage(config, errors, warnings)
    cat_deductions["coverage"] += d7

    # ── UX bonus checks ─────────────────────────────────────────────────────
    pages = config.get("ui", {}).get("pages", [])
    routes = [p.get("route", "").lower() for p in pages]
    has_dashboard = any("dashboard" in r for r in routes)
    has_home = any(r in ("/", "/home", "home", "") for r in routes)
    if not has_dashboard:
        errors.append(_err("EXECUTION_ERROR", "Missing required Dashboard page (route '/dashboard').", "ui.pages"))
        cat_deductions["ux"] += 5
    if not has_home:
        errors.append(_err("EXECUTION_ERROR", "Missing required Home page (route '/' or '/home').", "ui.pages"))
        cat_deductions["ux"] += 5

    logger.info(f"Evaluation complete. Category deductions: {cat_deductions}")

    return _build_result(cat_deductions, errors, warnings, config)


# ─────────────────────────────────────────────────────────────────────────────
# RESULT BUILDER
# ─────────────────────────────────────────────────────────────────────────────
def _build_result(cat_deductions: dict, errors: list, warnings: list, config: dict) -> dict:
    """
    Computes per-category scores, total score, coverage %, execution_errors count,
    and the strict readiness gate.
    """
    # ── Per-category scores (clamped to [0, budget]) ────────────────────────
    scores = {}
    for cat, budget in CATEGORY_BUDGETS.items():
        scores[cat] = max(0, budget - cat_deductions.get(cat, 0))

    total_score = sum(scores.values())   # out of 100

    # ── Execution errors count ──────────────────────────────────────────────
    execution_errors = sum(1 for e in errors if e.get("type") in ("EXECUTION_ERROR", "EXECUTION_FAIL"))

    # ── Coverage percentage ─────────────────────────────────────────────────
    tables = config.get("db", {}).get("tables", []) if config else []
    endpoints = config.get("api", {}).get("endpoints", []) if config else []
    pages = config.get("ui", {}).get("pages", []) if config else []

    if tables:
        covered_count = 0
        for table in tables:
            t_name = table.get("name")
            if not t_name:
                continue

            # Check API CRUD coverage
            methods_found = set()
            for ep in endpoints:
                if ep.get("related_table") == t_name:
                    methods_found.add(ep.get("method", "").upper())

            has_crud = {"POST", "GET"}.issubset(methods_found) and \
                       ({"PUT", "PATCH"} & methods_found) and \
                       "DELETE" in methods_found

            # Check UI coverage
            has_form = has_table_comp = has_button = False
            for page in pages:
                for comp in page.get("components", []):
                    ep_ref = comp.get("endpoint_ref")
                    ep = next((e for e in endpoints if e.get("id") == ep_ref), None)
                    if ep and ep.get("related_table") == t_name:
                        ct = comp.get("type", "").lower()
                        if ct == "form": has_form = True
                        elif ct == "table": has_table_comp = True
                        elif ct == "button": has_button = True

            if has_crud and has_form and has_table_comp and has_button:
                covered_count += 1

        coverage_pct = round((covered_count / len(tables)) * 100)
    else:
        coverage_pct = 0

    # ── Strict readiness gate ───────────────────────────────────────────────
    ready = (
        total_score >= 90 and
        execution_errors == 0 and
        coverage_pct == 100
    )

    if ready:
        status = "READY"
    elif total_score >= 70:
        status = "NOT_READY_PARTIAL"
    else:
        status = "NOT_READY"

    # ── Metrics ─────────────────────────────────────────────────────────────
    roles = config.get("auth", {}).get("roles", []) if config else []

    metrics = {
        "table_count":       len(tables),
        "endpoint_count":    len(endpoints),
        "page_count":        len(pages),
        "role_count":        len(roles),
        "error_count":       len(errors),
        "warning_count":     len(warnings),
        "execution_errors":  execution_errors,
        "coverage_pct":      coverage_pct,
        "category_scores":   scores,
        "category_budgets":  CATEGORY_BUDGETS,
    }

    logger.info(f"Score={total_score}/100 | Exec Errors={execution_errors} | Coverage={coverage_pct}% | Ready={ready}")

    return {
        "ready":            ready,
        "status":           status,
        "score":            total_score,
        "scores":           scores,
        "execution_errors": execution_errors,
        "coverage_pct":     coverage_pct,
        "errors":           errors,
        "warnings":         warnings,
        "metrics":          metrics,
    }

