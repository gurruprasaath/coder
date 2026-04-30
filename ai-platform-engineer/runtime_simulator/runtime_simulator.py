"""
Runtime Simulator Module
Simulates execution and validates that the generated schemas can produce a working application
"""

import json
from typing import Dict, Any, List, Optional

def simulate_execution(schemas: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate execution of the generated application.
    
    Args:
        schemas: Validated schemas ready for execution
        
    Returns:
        Execution simulation results
    """
    print("\n🔄 Simulating application execution...")
    
    results = {
        "status": "success",
        "checks": [],
        "code_generation": {},
        "issues": []
    }
    
    # Check 1: Validate schema completeness
    check_result = check_schema_completeness(schemas)
    results["checks"].append(check_result)
    
    # Check 2: Generate code structure
    code_structure = generate_code_structure(schemas)
    results["code_generation"] = code_structure
    
    # Check 3: Validate entity relationships
    relationship_result = validate_relationships(schemas)
    results["checks"].append(relationship_result)
    
    # Check 4: Verify API coverage
    api_coverage = verify_api_coverage(schemas)
    results["checks"].append(api_coverage)
    
    # Check 5: Validate auth flow
    auth_flow = validate_auth_flow(schemas)
    results["checks"].append(auth_flow)
    
    # Determine overall status
    failed_checks = [c for c in results["checks"] if not c["passed"]]
    if failed_checks:
        results["status"] = "partial"
        results["issues"] = [c["message"] for c in failed_checks]
    
    # Print summary
    print(f"\n📊 Execution Simulation Results:")
    print(f"   Status: {results['status']}")
    print(f"   Checks passed: {len(results['checks']) - len(failed_checks)}/{len(results['checks'])}")
    
    for check in results["checks"]:
        status = "✅" if check["passed"] else "❌"
        print(f"   {status} {check['name']}: {check['message']}")
    
    return results

def check_schema_completeness(schemas: Dict[str, Any]) -> Dict[str, Any]:
    """Check if all required schema components are present."""
    required = ["ui_schema", "api_schema", "db_schema", "auth_schema"]
    missing = [r for r in required if r not in schemas or not schemas[r]]
    
    if missing:
        return {
            "name": "Schema Completeness",
            "passed": False,
            "message": f"Missing schemas: {', '.join(missing)}"
        }
    
    return {
        "name": "Schema Completeness",
        "passed": True,
        "message": "All required schemas present"
    }

def generate_code_structure(schemas: Dict[str, Any]) -> Dict[str, Any]:
    """Generate the code structure that would be created."""
    structure = {
        "backend": {
            "files": [],
            "directories": ["controllers", "models", "routes", "middleware", "config"]
        },
        "frontend": {
            "files": [],
            "directories": ["components", "pages", "services", "hooks", "utils"]
        }
    }
    
    # Generate backend files
    api_schema = schemas.get("api_schema", {})
    db_schema = schemas.get("db_schema", {})
    
    # Server file
    structure["backend"]["files"].append({
        "path": "server.js",
        "description": "Main Express server entry point"
    })
    
    # Database models
    for table in db_schema.get("tables", []):
        model_name = table["name"].rstrip('s').capitalize()
        structure["backend"]["files"].append({
            "path": f"models/{model_name}.js",
            "description": f"Mongoose model for {model_name}"
        })
    
    # Routes
    for endpoint in api_schema.get("endpoints", []):
        path = endpoint.get("path", "")
        if "/auth/" in path:
            continue
        
        parts = path.split("/")
        if len(parts) >= 3:
            entity = parts[2].rstrip('s')
            if f"routes/{entity}.js" not in [f["path"] for f in structure["backend"]["files"]]:
                structure["backend"]["files"].append({
                    "path": f"routes/{entity}.js",
                    "description": f"Express router for {entity} endpoints"
                })
    
    # Auth middleware
    structure["backend"]["files"].append({
        "path": "middleware/auth.js",
        "description": "JWT authentication middleware"
    })
    
    # Generate frontend files
    ui_schema = schemas.get("ui_schema", {})
    
    for page in ui_schema.get("pages", []):
        page_name = page.get("name", "Page")
        structure["frontend"]["files"].append({
            "path": f"pages/{page_name}.jsx",
            "description": f"React component for {page_name}"
        })
    
    # API service
    structure["frontend"]["files"].append({
        "path": "services/api.js",
        "description": "Axios API service with interceptors"
    })
    
    # Auth context
    structure["frontend"]["files"].append({
        "path": "contexts/AuthContext.jsx",
        "description": "React context for authentication"
    })
    
    return structure

def validate_relationships(schemas: Dict[str, Any]) -> Dict[str, Any]:
    """Validate entity relationships."""
    db_schema = schemas.get("db_schema", {})
    tables = {t["name"]: t for t in db_schema.get("tables", [])}
    
    issues = []
    
    # Check foreign key references
    for constraint in db_schema.get("constraints", []):
        from_table = constraint.get("from_table")
        to_table = constraint.get("to_table")
        
        if from_table not in tables:
            issues.append(f"Table {from_table} referenced in constraint not found")
        
        if to_table not in tables:
            issues.append(f"Table {to_table} referenced in constraint not found")
    
    # Check that primary keys exist
    for table in db_schema.get("tables", []):
        if "primary_key" not in table:
            issues.append(f"Table {table['name']} has no primary key defined")
        
        columns = {c["name"] for c in table.get("columns", [])}
        pk = table.get("primary_key", "id")
        if pk not in columns:
            issues.append(f"Primary key '{pk}' not found in table {table['name']}")
    
    if issues:
        return {
            "name": "Entity Relationships",
            "passed": False,
            "message": "; ".join(issues)
        }
    
    return {
        "name": "Entity Relationships",
        "passed": True,
        "message": "All relationships valid"
    }

def verify_api_coverage(schemas: Dict[str, Any]) -> Dict[str, Any]:
    """Verify that API endpoints cover all CRUD operations."""
    api_schema = schemas.get("api_schema", {})
    endpoints = api_schema.get("endpoints", [])
    
    # Group endpoints by entity
    entity_endpoints = {}
    for ep in endpoints:
        path = ep.get("path", "")
        if "/auth/" in path:
            continue
        
        parts = path.split("/")
        if len(parts) >= 3:
            entity = parts[2].rstrip('s')
            if entity not in entity_endpoints:
                entity_endpoints[entity] = []
            entity_endpoints[entity].append(ep.get("method"))
    
    # Check for CRUD coverage
    issues = []
    for entity, methods in entity_endpoints.items():
        required_methods = ["GET", "POST", "PUT", "DELETE"]
        missing = [m for m in required_methods if m not in methods]
        
        if missing:
            issues.append(f"{entity}: missing {', '.join(missing)}")
    
    if issues:
        return {
            "name": "API Coverage",
            "passed": False,
            "message": "; ".join(issues)
        }
    
    return {
        "name": "API Coverage",
        "passed": True,
        "message": "All CRUD operations covered"
    }

def validate_auth_flow(schemas: Dict[str, Any]) -> Dict[str, Any]:
    """Validate authentication flow."""
    auth_schema = schemas.get("auth_schema", {})
    api_schema = schemas.get("api_schema", {})
    
    # Check auth config
    if not auth_schema.get("authentication"):
        return {
            "name": "Auth Flow",
            "passed": False,
            "message": "No authentication configuration"
        }
    
    # Check for auth endpoints
    auth_endpoints = [ep for ep in api_schema.get("endpoints", []) 
                     if "/auth/login" in ep.get("path", "") or "/auth/register" in ep.get("path", "")]
    
    if not auth_endpoints:
        return {
            "name": "Auth Flow",
            "passed": False,
            "message": "No authentication endpoints found"
        }
    
    # Check for protected endpoints
    protected = [ep for ep in api_schema.get("endpoints", []) 
                if ep.get("auth_required", True) and "/auth/" not in ep.get("path", "")]
    
    if not protected:
        return {
            "name": "Auth Flow",
            "passed": False,
            "message": "No protected endpoints found"
        }
    
    # Check for role definitions
    roles = auth_schema.get("authorization", {}).get("roles", [])
    if not roles:
        return {
            "name": "Auth Flow",
            "passed": False,
            "message": "No roles defined"
        }
    
    return {
        "name": "Auth Flow",
        "passed": True,
        "message": "Authentication flow complete"
    }

# Test function
if __name__ == "__main__":
    test_schemas = {
        "ui_schema": {
            "pages": [
                {"name": "Login", "path": "/login"},
                {"name": "Dashboard", "path": "/dashboard"}
            ]
        },
        "api_schema": {
            "base_url": "/api",
            "endpoints": [
                {"method": "POST", "path": "/api/auth/register", "auth_required": False},
                {"method": "POST", "path": "/api/auth/login", "auth_required": False},
                {"method": "GET", "path": "/api/contacts", "auth_required": True},
                {"method": "POST", "path": "/api/contacts", "auth_required": True},
                {"method": "PUT", "path": "/api/contacts/:id", "auth_required": True},
                {"method": "DELETE", "path": "/api/contacts/:id", "auth_required": True}
            ]
        },
        "db_schema": {
            "tables": [
                {
                    "name": "users",
                    "columns": [
                        {"name": "id", "type": "UUID"},
                        {"name": "email", "type": "VARCHAR(255)", "unique": True}
                    ],
                    "primary_key": "id"
                },
                {
                    "name": "contacts",
                    "columns": [
                        {"name": "id", "type": "UUID"},
                        {"name": "name", "type": "VARCHAR(255)"},
                        {"name": "user_id", "type": "UUID"}
                    ],
                    "primary_key": "id"
                }
            ],
            "constraints": [
                {
                    "type": "foreign_key",
                    "from_table": "contacts",
                    "from_column": "user_id",
                    "to_table": "users",
                    "to_column": "id"
                }
            ]
        },
        "auth_schema": {
            "authentication": {"method": "JWT"},
            "authorization": {
                "roles": [
                    {"name": "admin", "permissions": ["*"]},
                    {"name": "user", "permissions": ["read_own", "create_own"]}
                ]
            }
        }
    }
    result = simulate_execution(test_schemas)
    print(json.dumps(result, indent=2))
