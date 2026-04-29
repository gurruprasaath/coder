from logger import setup_logger

logger = setup_logger(__name__)

def validate_schema(config: dict) -> dict:
    """
    Stage 4: Validation
    Deterministically validates the system schema cross-layer guarantees.
    """
    logger.info("Running deterministic strict cross-layer schema validation.")
    errors = []
    
    required_keys = ['ui', 'api', 'db', 'auth']
    for key in required_keys:
        if key not in config:
            errors.append({
                "type": "MISSING_KEY",
                "message": f"Missing required root key: '{key}'",
                "path": f"root.{key}"
            })
            
    if errors:
        return {"is_valid": False, "errors": errors}

    db_tables = config.get('db', {}).get('tables', [])
    api_endpoints = config.get('api', {}).get('endpoints', [])
    ui_pages = config.get('ui', {}).get('pages', [])
    auth_roles = config.get('auth', {}).get('roles', [])
    auth_rules = config.get('auth', {}).get('rules', [])

    # Map tables for easy field lookup
    table_fields = {}
    for table in db_tables:
        table_name = table.get('name')
        if table_name:
            table_fields[table_name] = {f.get('name') for f in table.get('fields', [])}

    # Map endpoints
    endpoint_ids = set()
    for ep in api_endpoints:
        ep_id = ep.get('id')
        if ep_id:
            endpoint_ids.add(ep_id)

    # 1. DB Foreign Key Validation
    for t_idx, table in enumerate(db_tables):
        t_name = table.get('name', f'table_{t_idx}')
        for f_idx, field in enumerate(table.get('fields', [])):
            fk = field.get('foreign_key')
            if fk:
                parts = fk.split('.')
                if len(parts) != 2:
                    errors.append({
                        "type": "INVALID_FOREIGN_KEY_FORMAT",
                        "message": f"Foreign key '{fk}' in table '{t_name}' must be formatted as 'Table.field'",
                        "path": f"db.tables[{t_idx}].fields[{f_idx}].foreign_key"
                    })
                else:
                    ref_table, ref_field = parts
                    if ref_table not in table_fields:
                        errors.append({
                            "type": "FOREIGN_KEY_TABLE_NOT_FOUND",
                            "message": f"Foreign key '{fk}' references unknown table '{ref_table}'",
                            "path": f"db.tables[{t_idx}].fields[{f_idx}].foreign_key"
                        })
                    elif ref_field not in table_fields[ref_table]:
                        errors.append({
                            "type": "FOREIGN_KEY_FIELD_NOT_FOUND",
                            "message": f"Foreign key '{fk}' references unknown field '{ref_field}' in table '{ref_table}'",
                            "path": f"db.tables[{t_idx}].fields[{f_idx}].foreign_key"
                        })

    # 2. API Cross-Layer Checks
    for idx, ep in enumerate(api_endpoints):
        ep_id = ep.get('id', f'unknown_{idx}')
        related_table = ep.get('related_table')
        
        if related_table not in table_fields:
            errors.append({
                "type": "INVALID_TABLE_REFERENCE",
                "message": f"API endpoint '{ep_id}' references unknown table '{related_table}'.",
                "path": f"api.endpoints[{idx}].related_table"
            })
            continue
            
        valid_fields = table_fields[related_table]
        
        for f_idx, field_obj in enumerate(ep.get('request_body', [])):
            field_name = field_obj.get('name')
            if field_name not in valid_fields:
                errors.append({
                    "type": "INVALID_REQUEST_FIELD",
                    "message": f"API endpoint '{ep_id}' request_body field '{field_name}' not found in table '{related_table}'.",
                    "path": f"api.endpoints[{idx}].request_body[{f_idx}].name"
                })
                
        for f_idx, field_obj in enumerate(ep.get('response_body', [])):
            field_name = field_obj.get('name')
            if field_name not in valid_fields:
                errors.append({
                    "type": "INVALID_RESPONSE_FIELD",
                    "message": f"API endpoint '{ep_id}' response_body field '{field_name}' not found in table '{related_table}'.",
                    "path": f"api.endpoints[{idx}].response_body[{f_idx}].name"
                })

    # 3. UI Cross-Layer Checks
    for p_idx, page in enumerate(ui_pages):
        page_name = page.get('name', 'unknown')
        access_role = page.get('access_role')
        if access_role and access_role not in auth_roles:
            errors.append({
                "type": "INVALID_PAGE_ACCESS_ROLE",
                "message": f"UI page '{page_name}' requires role '{access_role}' which does not exist.",
                "path": f"ui.pages[{p_idx}].access_role"
            })

        for c_idx, comp in enumerate(page.get('components', [])):
            ep_ref = comp.get('endpoint_ref')
            comp_name = comp.get('name', 'unknown')
            
            if ep_ref not in endpoint_ids:
                errors.append({
                    "type": "UI_API_MISMATCH",
                    "message": f"UI component '{comp_name}' references unknown endpoint ID '{ep_ref}'.",
                    "path": f"ui.pages[{p_idx}].components[{c_idx}].endpoint_ref"
                })
                continue
                
            # Cross-verify fields with the related table of the endpoint
            ep_obj = next((e for e in api_endpoints if e.get('id') == ep_ref), None)
            if ep_obj:
                related_table = ep_obj.get('related_table')
                if related_table in table_fields:
                    valid_fields = table_fields[related_table]
                    for f_idx, field in enumerate(comp.get('fields', [])):
                        if field not in valid_fields:
                            errors.append({
                                "type": "UI_DB_MISMATCH",
                                "message": f"UI component '{comp_name}' field '{field}' not found in table '{related_table}'.",
                                "path": f"ui.pages[{p_idx}].components[{c_idx}].fields[{f_idx}]"
                            })

    # 4. Auth Cross-Layer Checks
    for r_idx, rule in enumerate(auth_rules):
        role = rule.get('role')
        if role not in auth_roles:
            errors.append({
                "type": "AUTH_ROLE_MISMATCH",
                "message": f"Auth rule references unknown role '{role}'.",
                "path": f"auth.rules[{r_idx}].role"
            })
            
        for a_idx, ep_ref in enumerate(rule.get('allowed_endpoints', [])):
            if ep_ref not in endpoint_ids:
                 errors.append({
                    "type": "AUTH_API_MISMATCH",
                    "message": f"Auth rule for role '{role}' references unknown endpoint '{ep_ref}'.",
                    "path": f"auth.rules[{r_idx}].allowed_endpoints[{a_idx}]"
                })

    # 5. Logical & Semantic Validation
    primary_keys = {}
    for t_idx, table in enumerate(db_tables):
        t_name = table.get('name')
        if t_name:
            p_keys = [f.get('name') for f in table.get('fields', []) if f.get('is_primary')]
            primary_keys[t_name] = p_keys
            if not p_keys:
                errors.append({
                    "type": "MISSING_PRIMARY_KEY",
                    "message": f"DB table '{t_name}' does not have a primary key.",
                    "path": f"db.tables[{t_idx}].fields"
                })

    for idx, ep in enumerate(api_endpoints):
        ep_id = ep.get('id', f'unknown_{idx}')
        method = ep.get('method', '').upper()
        path = ep.get('path', '')
        related_table = ep.get('related_table')
        
        req_field_names = [f.get('name') for f in ep.get('request_body', [])]
        res_field_names = [f.get('name') for f in ep.get('response_body', [])]
        
        # A. Security Check
        sensitive_keywords = ['password', 'secret', 'hash', 'token']
        for f_idx, field in enumerate(res_field_names):
            if field and any(keyword in field.lower() for keyword in sensitive_keywords):
                errors.append({
                    "type": "SECURITY_VIOLATION",
                    "message": f"Security Risk: API endpoint '{ep_id}' exposes sensitive field '{field}'.",
                    "path": f"api.endpoints[{idx}].response_body[{f_idx}].name"
                })

        # B. Primary Key Check
        if method == 'POST' and related_table in primary_keys:
            p_keys = primary_keys[related_table]
            for f_idx, field_name in enumerate(req_field_names):
                if field_name in p_keys:
                    errors.append({
                        "type": "LOGICAL_ERROR",
                        "message": f"POST endpoint '{ep_id}' improperly requires auto-generated primary key '{field_name}'.",
                        "path": f"api.endpoints[{idx}].request_body[{f_idx}].name"
                    })

        # C. HTTP Semantics
        if method in ['GET', 'DELETE'] and len(req_field_names) > 0:
             errors.append({
                "type": "LOGICAL_ERROR",
                "message": f"{method} endpoint '{ep_id}' should not have a request_body.",
                "path": f"api.endpoints[{idx}].request_body"
            })
             
        # D. DELETE Semantics
        if method == 'DELETE':
            res_body = ep.get('response_body', [])
            if len(res_body) != 1 or res_body[0].get('name') != 'success' or res_body[0].get('type') != 'boolean':
                 errors.append({
                    "type": "LOGICAL_ERROR",
                    "message": f"DELETE endpoint '{ep_id}' must return exactly one response_body field: 'success' of type 'boolean'.",
                    "path": f"api.endpoints[{idx}].response_body"
                })

        # E. Login Semantics
        if 'login' in path.lower():
            if method != 'POST':
                 errors.append({
                    "type": "LOGICAL_ERROR",
                    "message": f"Login endpoint '{ep_id}' MUST use POST method.",
                    "path": f"api.endpoints[{idx}].method"
                })
            if 'password' not in [str(f).lower() for f in req_field_names] and 'secret' not in [str(f).lower() for f in req_field_names]:
                 errors.append({
                    "type": "LOGICAL_ERROR",
                    "message": f"Login endpoint '{ep_id}' request_body MUST contain a password or secret.",
                    "path": f"api.endpoints[{idx}].request_body"
                })

    is_valid = len(errors) == 0
    if not is_valid:
        logger.warning(f"Schema validation failed with {len(errors)} errors.")
    else:
        logger.info("Schema validation passed successfully.")

    return {
        "is_valid": is_valid,
        "errors": errors
    }
