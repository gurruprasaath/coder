"""
Refinement Layer Module
Resolves inconsistencies across layers and ensures cross-layer coherence
"""

from typing import Dict, Any, List

def refine_schemas(schemas: Dict[str, Any]) -> Dict[str, Any]:
    """
    Refine and validate schemas across all layers.
    
    Args:
        schemas: Raw schemas from generation stage
        
    Returns:
        Refined and consistency-checked schemas
    """
    ui_schema = schemas.get("ui_schema", {})
    api_schema = schemas.get("api_schema", {})
    db_schema = schemas.get("db_schema", {})
    auth_schema = schemas.get("auth_schema", {})
    
    # Refine each layer
    refined_ui = refine_ui_schema(ui_schema, api_schema, db_schema)
    refined_api = refine_api_schema(api_schema, db_schema)
    refined_db = refine_db_schema(db_schema, api_schema)
    refined_auth = refine_auth_schema(auth_schema, api_schema)
    
    # Cross-layer validation
    cross_layer_issues = check_cross_layer_consistency(
        refined_ui, refined_api, refined_db, refined_auth
    )
    
    # Apply cross-layer fixes
    if cross_layer_issues:
        refined_ui, refined_api, refined_db, refined_auth = apply_fixes(
            refined_ui, refined_api, refined_db, refined_auth, cross_layer_issues
        )
    
    return {
        "ui_schema": refined_ui,
        "api_schema": refined_api,
        "db_schema": refined_db,
        "auth_schema": refined_auth,
        "metadata": {
            "refinement_applied": True,
            "issues_resolved": len(cross_layer_issues),
            "cross_layer_checks": ["entity_coverage", "api_coverage", "auth_coverage"]
        }
    }

def refine_ui_schema(ui_schema: Dict[str, Any], api_schema: Dict[str, Any], db_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Refine UI schema for consistency."""
    refined = ui_schema.copy()
    
    # Ensure all entity pages have corresponding API endpoints
    api_paths = [ep["path"] for ep in api_schema.get("endpoints", [])]
    
    for page in refined.get("pages", []):
        page_path = page.get("path", "")
        
        # Check if page has corresponding API
        entity_name = extract_entity_from_path(page_path)
        if entity_name:
            expected_api = f"/api/{entity_name.lower()}s"
            if expected_api not in api_paths and f"/api/{entity_name.lower()}" not in str(api_paths):
                # Add warning metadata
                if "warnings" not in refined:
                    refined["warnings"] = []
                refined["warnings"].append(f"Page {page['name']} has no corresponding API endpoint")
    
    return refined

def refine_api_schema(api_schema: Dict[str, Any], db_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Refine API schema for consistency."""
    refined = api_schema.copy()
    
    # Ensure CRUD endpoints are complete
    table_names = [t["name"] for t in db_schema.get("tables", [])]
    
    for table_name in table_names:
        entity_name = table_name.rstrip('s')
        base_path = f"/api/{table_name}"
        
        # Check for required CRUD endpoints
        required_methods = {
            f"{base_path}": "GET",  # List
            f"{base_path}": "POST",  # Create
            f"{base_path}/:id": "GET",  # Read
            f"{base_path}/:id": "PUT",  # Update
            f"{base_path}/:id": "DELETE"  # Delete
        }
        
        existing_paths = {(ep["path"], ep["method"]) for ep in refined.get("endpoints", [])}
        
        for path, method in required_methods.items():
            if (path, method) not in existing_paths:
                # Add missing endpoint
                refined["endpoints"].append({
                    "method": method,
                    "path": path,
                    "description": f"{method} {entity_name}",
                    "auth_required": True,
                    "auto_generated": True,
                    "request": {},
                    "responses": {
                        "200": {"description": "Success"},
                        "400": {"description": "Bad Request"},
                        "401": {"description": "Unauthorized"},
                        "404": {"description": "Not Found"},
                        "500": {"description": "Internal Server Error"}
                    }
                })
    
    return refined

def refine_db_schema(db_schema: Dict[str, Any], api_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Refine database schema for consistency."""
    refined = db_schema.copy()
    
    # Ensure users table exists for auth
    table_names = [t["name"] for t in refined.get("tables", [])]
    
    if "users" not in table_names:
        # Add users table
        refined["tables"].insert(0, {
            "name": "users",
            "columns": [
                {"name": "id", "type": "UUID", "nullable": False, "unique": True},
                {"name": "email", "type": "VARCHAR(255)", "nullable": False, "unique": True},
                {"name": "password_hash", "type": "VARCHAR(255)", "nullable": False},
                {"name": "name", "type": "VARCHAR(255)", "nullable": False},
                {"name": "role", "type": "VARCHAR(50)", "nullable": False, "default": "user"},
                {"name": "created_at", "type": "TIMESTAMP", "nullable": False},
                {"name": "updated_at", "type": "TIMESTAMP", "nullable": False}
            ],
            "primary_key": "id"
        })
        
        refined["indexes"].append({
            "table": "users",
            "columns": ["email"],
            "type": "unique"
        })
    
    # Ensure foreign key constraints are valid
    for constraint in refined.get("constraints", []):
        from_table = constraint.get("from_table")
        to_table = constraint.get("to_table")
        
        if from_table not in table_names:
            refined["warnings"] = refined.get("warnings", [])
            refined["warnings"].append(f"Foreign key references non-existent table: {from_table}")
        
        if to_table not in table_names:
            refined["warnings"] = refined.get("warnings", [])
            refined["warnings"].append(f"Foreign key references non-existent table: {to_table}")
    
    return refined

def refine_auth_schema(auth_schema: Dict[str, Any], api_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Refine auth schema for consistency."""
    refined = auth_schema.copy()
    
    # Ensure all API endpoints have auth rules
    endpoints = api_schema.get("endpoints", [])
    auth_config = refined.get("authorization", {})
    roles = auth_config.get("roles", [])
    role_names = [r["name"] for r in roles]
    
    # Ensure required roles exist
    required_roles = ["admin", "user"]
    for role in required_roles:
        if role not in role_names:
            refined["authorization"]["roles"].append({
                "name": role,
                "description": f"Default {role} role",
                "permissions": ["read_own", "create_own"] if role == "user" else ["*"]
            })
    
    # Add auth middleware to endpoints if missing
    for endpoint in endpoints:
        if "auth_required" not in endpoint:
            # Auth endpoints should not require auth
            if "/auth/login" in endpoint.get("path", "") or "/auth/register" in endpoint.get("path", ""):
                endpoint["auth_required"] = False
            else:
                endpoint["auth_required"] = True
    
    return refined

def check_cross_layer_consistency(ui_schema: Dict, api_schema: Dict, db_schema: Dict, auth_schema: Dict) -> List[Dict[str, Any]]:
    """Check for inconsistencies across layers."""
    issues = []
    
    # Issue 1: Entity coverage
    # Check if all UI pages have corresponding API endpoints
    ui_paths = [p.get("path", "") for p in ui_schema.get("pages", [])]
    api_paths = [e.get("path", "") for e in api_schema.get("endpoints", [])]
    
    for ui_path in ui_paths:
        if ui_path.startswith("/api"):
            continue
        entity = extract_entity_from_path(ui_path)
        if entity:
            expected_api = f"/api/{entity.lower()}s"
            if expected_api not in api_paths and f"/api/{entity.lower()}" not in str(api_paths):
                issues.append({
                    "type": "missing_api_endpoint",
                    "severity": "error",
                    "message": f"UI page {ui_path} has no corresponding API endpoint",
                    "fix": "auto_generate_crud"
                })
    
    # Issue 2: DB table coverage
    # Check if all API endpoints have corresponding DB tables
    for endpoint in api_schema.get("endpoints", []):
        path = endpoint.get("path", "")
        if "/auth/" in path:
            continue
        
        # Extract entity from path
        parts = path.split("/")
        if len(parts) >= 3 and parts[1] == "api":
            table_name = parts[2].rstrip('s')
            db_tables = [t.get("name", "") for t in db_schema.get("tables", [])]
            
            if table_name not in db_tables and f"{table_name}s" not in db_tables:
                issues.append({
                    "type": "missing_db_table",
                    "severity": "error",
                    "message": f"API endpoint {path} has no corresponding database table",
                    "fix": "auto_generate_table"
                })
    
    # Issue 3: Auth coverage
    # Check if protected endpoints have role definitions
    protected_endpoints = [e for e in api_schema.get("endpoints", []) if e.get("auth_required", True)]
    roles = auth_schema.get("authorization", {}).get("roles", [])
    
    if not roles:
        issues.append({
            "type": "missing_roles",
            "severity": "error",
            "message": "No roles defined in auth schema",
            "fix": "add_default_roles"
        })
    
    return issues

def apply_fixes(ui_schema: Dict, api_schema: Dict, db_schema: Dict, auth_schema: Dict, issues: List[Dict]) -> tuple:
    """Apply fixes for identified issues."""
    for issue in issues:
        fix_type = issue.get("fix")
        
        if fix_type == "auto_generate_crud":
            # Already handled in refine functions
            pass
        elif fix_type == "add_default_roles":
            if not auth_schema.get("authorization", {}).get("roles"):
                auth_schema.setdefault("authorization", {}).setdefault("roles", []).extend([
                    {"name": "admin", "description": "Administrator", "permissions": ["*"]},
                    {"name": "user", "description": "Regular user", "permissions": ["read_own", "create_own", "update_own"]}
                ])
    
    return ui_schema, api_schema, db_schema, auth_schema

def extract_entity_from_path(path: str) -> str:
    """Extract entity name from a URL path."""
    parts = path.strip("/").split("/")
    if len(parts) >= 1:
        entity = parts[0]
        # Remove plural 's' if present
        if entity.endswith('s') and len(entity) > 1:
            entity = entity[:-1]
        return entity.capitalize()
    return ""

# Test function
if __name__ == "__main__":
    test_schemas = {
        "ui_schema": {
            "pages": [
                {"name": "ContactList", "path": "/contacts"},
                {"name": "ContactCreate", "path": "/contacts/new"}
            ]
        },
        "api_schema": {
            "endpoints": [
                {"method": "POST", "path": "/api/auth/register", "auth_required": False},
                {"method": "GET", "path": "/api/contacts", "auth_required": True}
            ]
        },
        "db_schema": {
            "tables": [{"name": "contacts", "columns": []}],
            "constraints": []
        },
        "auth_schema": {
            "authorization": {
                "roles": [
                    {"name": "admin", "permissions": ["*"]}
                ]
            }
        }
    }
    import json
    result = refine_schemas(test_schemas)
    print(json.dumps(result, indent=2))
