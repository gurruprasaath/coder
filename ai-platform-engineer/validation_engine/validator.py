"""
Validation + Repair Engine Module (CORE)
Detects and handles invalid JSON, missing keys, schema mismatches, and logical inconsistencies
"""

import json
import re
from typing import Dict, Any, List, Optional

class ValidationError:
    """Represents a validation error."""
    def __init__(self, error_type: str, message: str, path: str, severity: str = "error"):
        self.error_type = error_type
        self.message = message
        self.path = path
        self.severity = severity
    
    def __repr__(self):
        return f"[{self.severity.upper()}] {self.error_type} at '{self.path}': {self.message}"

def validate_and_repair(schemas: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and repair schemas.
    
    Args:
        schemas: Refined schemas from previous stage
        
    Returns:
        Validated and repaired schemas
    """
    errors = []
    warnings = []
    
    # Validate JSON structure
    json_errors = validate_json_structure(schemas)
    errors.extend(json_errors)
    
    # Validate UI schema
    ui_errors = validate_ui_schema(schemas.get("ui_schema", {}))
    errors.extend(ui_errors)
    
    # Validate API schema
    api_errors = validate_api_schema(schemas.get("api_schema", {}))
    errors.extend(api_errors)
    
    # Validate DB schema
    db_errors = validate_db_schema(schemas.get("db_schema", {}))
    errors.extend(db_errors)
    
    # Validate Auth schema
    auth_errors = validate_auth_schema(schemas.get("auth_schema", {}))
    errors.extend(auth_errors)
    
    # Cross-schema validation
    cross_errors = validate_cross_schemas(schemas)
    errors.extend(cross_errors)
    
    # Print validation results
    print(f"\n🔍 Validation Results:")
    print(f"   Errors: {len([e for e in errors if e.severity == 'error'])}")
    print(f"   Warnings: {len([e for e in errors if e.severity == 'warning'])}")
    
    # Attempt repairs for errors
    if errors:
        print(f"\n🔧 Attempting repairs...")
        schemas = repair_schemas(schemas, errors)
    
    # Add validation metadata
    schemas["validation"] = {
        "validated": True,
        "errors_found": len(errors),
        "errors_repaired": len([e for e in errors if e.severity == "error"]),
        "warnings_found": len(warnings),
        "validation_errors": [str(e) for e in errors]
    }
    
    return schemas

def validate_json_structure(data: Any, path: str = "root") -> List[ValidationError]:
    """Validate JSON structure and required fields."""
    errors = []
    
    if not isinstance(data, dict):
        errors.append(ValidationError(
            "invalid_type",
            f"Expected dict, got {type(data).__name__}",
            path,
            "error"
        ))
        return errors
    
    # Check for required top-level keys
    required_keys = ["ui_schema", "api_schema", "db_schema", "auth_schema"]
    for key in required_keys:
        if key not in data:
            errors.append(ValidationError(
                "missing_key",
                f"Missing required key: {key}",
                f"root.{key}",
                "error"
            ))
    
    return errors

def validate_ui_schema(ui_schema: Dict[str, Any]) -> List[ValidationError]:
    """Validate UI schema."""
    errors = []
    
    if not ui_schema:
        return [ValidationError("empty_schema", "UI schema is empty", "ui_schema", "warning")]
    
    # Validate pages
    if "pages" not in ui_schema:
        errors.append(ValidationError("missing_key", "Missing 'pages' in UI schema", "ui_schema.pages", "error"))
    else:
        pages = ui_schema["pages"]
        if not isinstance(pages, list):
            errors.append(ValidationError("invalid_type", "Pages must be a list", "ui_schema.pages", "error"))
        else:
            for i, page in enumerate(pages):
                page_errors = validate_page(page, f"ui_schema.pages[{i}]")
                errors.extend(page_errors)
    
    # Validate components
    if "components" not in ui_schema:
        errors.append(ValidationError("missing_key", "Missing 'components' in UI schema", "ui_schema.components", "warning"))
    
    return errors

def validate_page(page: Dict[str, Any], path: str) -> List[ValidationError]:
    """Validate a single page definition."""
    errors = []
    
    required_fields = ["name", "path"]
    for field in required_fields:
        if field not in page:
            errors.append(ValidationError(
                "missing_key",
                f"Missing required field: {field}",
                f"{path}.{field}",
                "error"
            ))
    
    # Validate path format
    if "path" in page:
        path = page["path"]
        if not path.startswith("/"):
            errors.append(ValidationError(
                "invalid_format",
                f"Path must start with /: {path}",
                f"{path}.path",
                "error"
            ))
    
    return errors

def validate_api_schema(api_schema: Dict[str, Any]) -> List[ValidationError]:
    """Validate API schema."""
    errors = []
    
    if not api_schema:
        return [ValidationError("empty_schema", "API schema is empty", "api_schema", "warning")]
    
    # Validate base_url
    if "base_url" not in api_schema:
        errors.append(ValidationError("missing_key", "Missing 'base_url'", "api_schema.base_url", "error"))
    
    # Validate endpoints
    if "endpoints" not in api_schema:
        errors.append(ValidationError("missing_key", "Missing 'endpoints'", "api_schema.endpoints", "error"))
    else:
        endpoints = api_schema["endpoints"]
        if not isinstance(endpoints, list):
            errors.append(ValidationError("invalid_type", "Endpoints must be a list", "api_schema.endpoints", "error"))
        else:
            for i, endpoint in enumerate(endpoints):
                endpoint_errors = validate_endpoint(endpoint, f"api_schema.endpoints[{i}]")
                errors.extend(endpoint_errors)
    
    return errors

def validate_endpoint(endpoint: Dict[str, Any], path: str) -> List[ValidationError]:
    """Validate a single endpoint definition."""
    errors = []
    
    required_fields = ["method", "path"]
    for field in required_fields:
        if field not in endpoint:
            errors.append(ValidationError(
                "missing_key",
                f"Missing required field: {field}",
                f"{path}.{field}",
                "error"
            ))
    
    # Validate HTTP method
    valid_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]
    if "method" in endpoint and endpoint["method"] not in valid_methods:
        errors.append(ValidationError(
            "invalid_value",
            f"Invalid HTTP method: {endpoint['method']}",
            f"{path}.method",
            "error"
        ))
    
    # Validate path format
    if "path" in endpoint:
        path = endpoint["path"]
        if not path.startswith("/"):
            errors.append(ValidationError(
                "invalid_format",
                f"Path must start with /: {path}",
                f"{path}.path",
                "error"
            ))
    
    return errors

def validate_db_schema(db_schema: Dict[str, Any]) -> List[ValidationError]:
    """Validate database schema."""
    errors = []
    
    if not db_schema:
        return [ValidationError("empty_schema", "DB schema is empty", "db_schema", "warning")]
    
    # Validate database type
    if "database" not in db_schema:
        errors.append(ValidationError("missing_key", "Missing 'database' type", "db_schema.database", "warning"))
    
    # Validate tables
    if "tables" not in db_schema:
        errors.append(ValidationError("missing_key", "Missing 'tables'", "db_schema.tables", "error"))
    else:
        tables = db_schema["tables"]
        if not isinstance(tables, list):
            errors.append(ValidationError("invalid_type", "Tables must be a list", "db_schema.tables", "error"))
        else:
            table_names = set()
            for i, table in enumerate(tables):
                table_errors = validate_table(table, f"db_schema.tables[{i}]")
                errors.extend(table_errors)
                
                # Check for duplicate table names
                table_name = table.get("name", "")
                if table_name in table_names:
                    errors.append(ValidationError(
                        "duplicate",
                        f"Duplicate table name: {table_name}",
                        f"db_schema.tables[{i}].name",
                        "error"
                    ))
                table_names.add(table_name)
    
    return errors

def validate_table(table: Dict[str, Any], path: str) -> List[ValidationError]:
    """Validate a single table definition."""
    errors = []
    
    required_fields = ["name", "columns"]
    for field in required_fields:
        if field not in table:
            errors.append(ValidationError(
                "missing_key",
                f"Missing required field: {field}",
                f"{path}.{field}",
                "error"
            ))
    
    # Validate columns
    if "columns" in table:
        columns = table["columns"]
        if not isinstance(columns, list):
            errors.append(ValidationError(
                "invalid_type",
                "Columns must be a list",
                f"{path}.columns",
                "error"
            ))
        else:
            column_names = set()
            for col in columns:
                col_name = col.get("name", "")
                if col_name in column_names:
                    errors.append(ValidationError(
                        "duplicate",
                        f"Duplicate column name: {col_name}",
                        f"{path}.columns.{col_name}",
                        "error"
                    ))
                column_names.add(col_name)
    
    return errors

def validate_auth_schema(auth_schema: Dict[str, Any]) -> List[ValidationError]:
    """Validate authentication schema."""
    errors = []
    
    if not auth_schema:
        return [ValidationError("empty_schema", "Auth schema is empty", "auth_schema", "warning")]
    
    # Validate authentication config
    if "authentication" not in auth_schema:
        errors.append(ValidationError("missing_key", "Missing 'authentication' config", "auth_schema.authentication", "error"))
    else:
        auth = auth_schema["authentication"]
        if "method" not in auth:
            errors.append(ValidationError("missing_key", "Missing authentication method", "auth_schema.authentication.method", "error"))
    
    # Validate authorization
    if "authorization" not in auth_schema:
        errors.append(ValidationError("missing_key", "Missing 'authorization' config", "auth_schema.authorization", "error"))
    else:
        authz = auth_schema["authorization"]
        
        if "roles" not in authz:
            errors.append(ValidationError("missing_key", "Missing roles", "auth_schema.authorization.roles", "error"))
        else:
            roles = authz["roles"]
            role_names = set()
            for role in roles:
                if "name" not in role:
                    errors.append(ValidationError("missing_key", "Role missing name", "auth_schema.authorization.roles", "error"))
                else:
                    name = role["name"]
                    if name in role_names:
                        errors.append(ValidationError("duplicate", f"Duplicate role: {name}", "auth_schema.authorization.roles", "error"))
                    role_names.add(name)
    
    return errors

def validate_cross_schemas(schemas: Dict[str, Any]) -> List[ValidationError]:
    """Validate consistency across different schemas."""
    errors = []
    
    ui_schema = schemas.get("ui_schema", {})
    api_schema = schemas.get("api_schema", {})
    db_schema = schemas.get("db_schema", {})
    auth_schema = schemas.get("auth_schema", {})
    
    # Extract entities from each schema
    ui_entities = extract_entities_from_ui(ui_schema)
    api_entities = extract_entities_from_api(api_schema)
    db_entities = extract_entities_from_db(db_schema)
    
    # Check for mismatches
    all_entities = ui_entities | api_entities | db_entities
    
    for entity in all_entities:
        if entity not in db_entities:
            errors.append(ValidationError(
                "entity_mismatch",
                f"Entity '{entity}' in UI/API but not in DB",
                "cross_schema",
                "error"
            ))
    
    return errors

def extract_entities_from_ui(ui_schema: Dict[str, Any]) -> set:
    """Extract entity names from UI schema."""
    entities = set()
    for page in ui_schema.get("pages", []):
        path = page.get("path", "")
        entity = extract_entity_from_path(path)
        if entity:
            entities.add(entity)
    return entities

def extract_entities_from_api(api_schema: Dict[str, Any]) -> set:
    """Extract entity names from API schema."""
    entities = set()
    for endpoint in api_schema.get("endpoints", []):
        path = endpoint.get("path", "")
        parts = path.split("/")
        if len(parts) >= 3 and parts[1] == "api":
            entity = parts[2].rstrip('s').capitalize()
            entities.add(entity)
    return entities

def extract_entities_from_db(db_schema: Dict[str, Any]) -> set:
    """Extract entity names from DB schema."""
    entities = set()
    for table in db_schema.get("tables", []):
        name = table.get("name", "").rstrip('s').capitalize()
        if name:
            entities.add(name)
    return entities

def extract_entity_from_path(path: str) -> str:
    """Extract entity name from URL path."""
    parts = path.strip("/").split("/")
    if parts:
        entity = parts[0]
        if entity.endswith('s'):
            entity = entity[:-1]
        return entity.capitalize()
    return ""

def repair_schemas(schemas: Dict[str, Any], errors: List[ValidationError]) -> Dict[str, Any]:
    """Attempt to repair schemas based on validation errors."""
    repaired = schemas.copy()
    
    for error in errors:
        if error.severity == "error":
            # Try to repair based on error type
            if error.error_type == "missing_key":
                repaired = repair_missing_key(repaired, error.path)
            elif error.error_type == "entity_mismatch":
                repaired = repair_entity_mismatch(repaired, error.message)
    
    return repaired

def repair_missing_key(schemas: Dict[str, Any], path: str) -> Dict[str, Any]:
    """Repair missing keys based on path."""
    # This is a simplified repair logic
    # In production, you'd have more sophisticated repair strategies
    
    if "ui_schema.components" in path:
        schemas.setdefault("ui_schema", {}).setdefault("components", {})
    
    if "api_schema.base_url" in path:
        schemas.setdefault("api_schema", {})["base_url"] = "/api"
    
    return schemas

def repair_entity_mismatch(schemas: Dict[str, Any], message: str) -> Dict[str, Any]:
    """Repair entity mismatches."""
    # Extract entity name from message
    match = re.search(r"Entity '(\w+)'", message)
    if match:
        entity_name = match.group(1)
        
        # Add entity to DB schema if missing
        db_schema = schemas.get("db_schema", {})
        tables = db_schema.get("tables", [])
        table_names = [t.get("name", "").rstrip('s') for t in tables]
        
        if entity_name.lower() not in table_names:
            tables.append({
                "name": entity_name.lower() + "s",
                "columns": [
                    {"name": "id", "type": "UUID", "nullable": False, "unique": True},
                    {"name": "created_at", "type": "TIMESTAMP", "nullable": False},
                    {"name": "updated_at", "type": "TIMESTAMP", "nullable": False}
                ],
                "primary_key": "id"
            })
            db_schema["tables"] = tables
            schemas["db_schema"] = db_schema
    
    return schemas

# Test function
if __name__ == "__main__":
    test_schemas = {
        "ui_schema": {
            "pages": [
                {"name": "ContactList", "path": "/contacts"}
            ]
        },
        "api_schema": {
            "endpoints": [
                {"method": "GET", "path": "/api/contacts"}
            ]
        },
        "db_schema": {
            "tables": [
                {"name": "contacts", "columns": [{"name": "id", "type": "UUID"}]}
            ]
        },
        "auth_schema": {
            "authentication": {"method": "JWT"},
            "authorization": {"roles": [{"name": "admin", "permissions": ["*"]}]}
        }
    }
    result = validate_and_repair(test_schemas)
    print(json.dumps(result, indent=2))
