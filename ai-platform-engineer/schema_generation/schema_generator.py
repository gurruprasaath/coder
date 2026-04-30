"""
Schema Generation Module
Generates UI config, API config, DB schema, and Auth rules
"""

from typing import Dict, Any, List

def generate_schemas(system_design: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate all schema components from system design.
    
    Args:
        system_design: System architecture from design stage
        
    Returns:
        Complete schema package with UI, API, DB, and Auth configs
    """
    return {
        "ui_schema": generate_ui_schema(system_design),
        "api_schema": generate_api_schema(system_design),
        "db_schema": generate_db_schema(system_design),
        "auth_schema": generate_auth_schema(system_design)
    }

def generate_ui_schema(system_design: Dict[str, Any]) -> Dict[str, Any]:
    """Generate UI configuration schema."""
    entities = system_design.get("entities", [])
    app_type = system_design.get("application_type", "Web Application")
    
    ui_schema = {
        "pages": [],
        "components": {},
        "layouts": {}
    }
    
    # Always include auth pages
    ui_schema["pages"].extend([
        {
            "name": "Login",
            "path": "/login",
            "components": ["EmailInput", "PasswordInput", "SubmitButton", "LinkToRegister"],
            "layout": "centered"
        },
        {
            "name": "Register",
            "path": "/register",
            "components": ["NameInput", "EmailInput", "PasswordInput", "ConfirmPasswordInput", "SubmitButton", "LinkToLogin"],
            "layout": "centered"
        }
    ])
    
    # Dashboard (main page after login)
    ui_schema["pages"].append({
        "name": "Dashboard",
        "path": "/dashboard",
        "components": ["Sidebar", "Header", "StatsCard", "RecentActivity", "QuickActions"],
        "layout": "sidebar"
    })
    
    # Entity-specific pages
    for entity in entities:
        entity_name = entity["name"]
        entity_lower = entity_name.lower()
        
        # List page
        ui_schema["pages"].append({
            "name": f"{entity_name}List",
            "path": f"/{entity_lower}s",
            "components": [
                f"{entity_name}Table",
                "SearchInput",
                "FilterDropdown",
                "AddButton",
                "Pagination"
            ],
            "layout": "sidebar"
        })
        
        # Detail/Edit page
        ui_schema["pages"].append({
            "name": f"{entity_name}Detail",
            "path": f"/{entity_lower}s/:id",
            "components": [
                f"{entity_name}Form",
                "DeleteButton",
                "SaveButton",
                "CancelButton"
            ],
            "layout": "sidebar"
        })
        
        # Create page
        ui_schema["pages"].append({
            "name": f"{entity_name}Create",
            "path": f"/{entity_lower}s/new",
            "components": [f"{entity_name}Form", "SubmitButton", "CancelButton"],
            "layout": "sidebar"
        })
    
    # Settings page
    ui_schema["pages"].append({
        "name": "Settings",
        "path": "/settings",
        "components": ["ProfileForm", "PasswordChangeForm", "PreferencesForm"],
        "layout": "sidebar"
    })
    
    # Define common components
    ui_schema["components"] = {
        "Button": {"type": "button", "props": ["variant", "size", "disabled", "onClick"]},
        "Input": {"type": "input", "props": ["type", "placeholder", "value", "onChange", "error"]},
        "Select": {"type": "select", "props": ["options", "value", "onChange", "placeholder"]},
        "Table": {"type": "table", "props": ["columns", "data", "onRowClick", "pagination"]},
        "Card": {"type": "card", "props": ["title", "content", "actions"]},
        "Modal": {"type": "modal", "props": ["isOpen", "onClose", "children"]},
        "Sidebar": {"type": "layout", "props": ["items", "activeItem", "onItemClick"]},
        "Header": {"type": "layout", "props": ["title", "userMenu", "notifications"]},
        "Form": {"type": "form", "props": ["fields", "onSubmit", "initialValues"]},
        "Alert": {"type": "alert", "props": ["type", "message", "onClose"]},
        "Badge": {"type": "badge", "props": ["label", "variant"]},
        "Avatar": {"type": "avatar", "props": ["src", "alt", "size"]},
        "Dropdown": {"type": "dropdown", "props": ["trigger", "items", "onItemClick"]},
        "Tabs": {"type": "tabs", "props": ["tabs", "activeTab", "onTabChange"]}
    }
    
    # Define layouts
    ui_schema["layouts"] = {
        "centered": {
            "type": "flex",
            "direction": "column",
            "justify": "center",
            "align": "center",
            "maxWidth": "400px"
        },
        "sidebar": {
            "type": "flex",
            "direction": "row",
            "sidebar": {"width": "250px", "position": "fixed"},
            "content": {"marginLeft": "250px"}
        },
        "full": {
            "type": "flex",
            "direction": "column",
            "fullWidth": True
        }
    }
    
    return ui_schema

def generate_api_schema(system_design: Dict[str, Any]) -> Dict[str, Any]:
    """Generate API configuration schema."""
    entities = system_design.get("entities", [])
    api_flows = system_design.get("api_flows", [])
    security = system_design.get("security", {})
    
    api_schema = {
        "base_url": "/api",
        "version": "v1",
        "endpoints": [],
        "middleware": security.get("middleware", []),
        "validators": {},
        "responses": {}
    }
    
    # Generate endpoints from flows
    for flow in api_flows:
        endpoint = {
            "method": flow["method"],
            "path": flow["path"],
            "description": flow["description"],
            "auth_required": flow.get("auth", True),
            "request": {},
            "responses": {}
        }
        
        # Add request/response schemas based on method
        if flow["method"] in ["POST", "PUT", "PATCH"]:
            # Extract entity from path
            path_parts = flow["path"].split("/")
            if len(path_parts) >= 3:
                entity = path_parts[2].rstrip('s')
                endpoint["request"] = {
                    "body": {
                        "type": "object",
                        "properties": get_entity_fields(entities, entity)
                    }
                }
        
        endpoint["responses"] = {
            "200": {"description": "Success", "schema": {"type": "object"}},
            "201": {"description": "Created", "schema": {"type": "object"}},
            "400": {"description": "Bad Request", "schema": {"type": "object", "properties": {"error": {"type": "string"}}}},
            "401": {"description": "Unauthorized", "schema": {"type": "object", "properties": {"error": {"type": "string"}}}},
            "403": {"description": "Forbidden", "schema": {"type": "object", "properties": {"error": {"type": "string"}}}},
            "404": {"description": "Not Found", "schema": {"type": "object", "properties": {"error": {"type": "string"}}}},
            "500": {"description": "Internal Server Error", "schema": {"type": "object", "properties": {"error": {"type": "string"}}}}
        }
        
        api_schema["endpoints"].append(endpoint)
    
    return api_schema

def generate_db_schema(system_design: Dict[str, Any]) -> Dict[str, Any]:
    """Generate database schema."""
    entities = system_design.get("entities", [])
    relationships = system_design.get("relationships", [])
    
    db_schema = {
        "database": "postgresql",
        "tables": [],
        "indexes": [],
        "constraints": []
    }
    
    # Generate tables from entities
    for entity in entities:
        table = {
            "name": entity["name"].lower() + "s",
            "columns": [],
            "primary_key": "id"
        }
        
        for field in entity.get("fields", []):
            column = {
                "name": field["name"],
                "type": map_field_type(field["type"]),
                "nullable": not field.get("required", False),
                "default": field.get("default")
            }
            
            if field.get("unique"):
                column["unique"] = True
            
            if field.get("foreign_key"):
                column["references"] = {
                    "table": field["foreign_key"].split(".")[0].lower() + "s",
                    "column": "id"
                }
            
            table["columns"].append(column)
        
        db_schema["tables"].append(table)
    
    # Generate indexes
    for entity in entities:
        table_name = entity["name"].lower() + "s"
        for field in entity.get("fields", []):
            if field.get("unique") or field.get("index"):
                db_schema["indexes"].append({
                    "table": table_name,
                    "columns": [field["name"]],
                    "type": "btree" if not field.get("unique") else "unique"
                })
    
    # Generate constraints
    for rel in relationships:
        if rel["type"] == "one-to-many":
            db_schema["constraints"].append({
                "type": "foreign_key",
                "from_table": rel["from"].lower() + "s",
                "from_column": rel["from"].lower() + "_id",
                "to_table": rel["to"].lower() + "s",
                "to_column": "id",
                "on_delete": "CASCADE"
            })
    
    return db_schema

def generate_auth_schema(system_design: Dict[str, Any]) -> Dict[str, Any]:
    """Generate authentication and authorization schema."""
    roles = system_design.get("roles", [])
    security = system_design.get("security", {})
    
    auth_schema = {
        "authentication": {
            "method": security.get("authentication", {}).get("method", "JWT"),
            "config": {
                "secret_key_env": "JWT_SECRET",
                "token_expiry": "24h",
                "refresh_token_enabled": True,
                "refresh_token_expiry": "7d",
                "password_min_length": 8,
                "password_hashing_algorithm": "bcrypt",
                "bcrypt_rounds": 12
            }
        },
        "authorization": {
            "model": security.get("authorization", {}).get("model", "RBAC"),
            "roles": [],
            "permissions": {},
            "role_hierarchy": {}
        }
    }
    
    # Generate role permissions
    all_permissions = [
        "create", "read", "update", "delete",
        "create_own", "read_own", "update_own", "delete_own",
        "create_any", "read_any", "update_any", "delete_any",
        "manage_users", "manage_roles", "view_analytics",
        "manage_settings", "manage_billing"
    ]
    
    for role in roles:
        role_name = role["name"]
        permissions = role.get("permissions", [])
        
        if "*" in permissions:
            role_permissions = all_permissions
        else:
            role_permissions = permissions
        
        auth_schema["authorization"]["roles"].append({
            "name": role_name,
            "description": role.get("description", ""),
            "permissions": role_permissions
        })
        
        auth_schema["authorization"]["permissions"][role_name] = role_permissions
    
    # Define role hierarchy
    role_levels = {"admin": 3, "moderator": 2, "user": 1, "guest": 0}
    for role in roles:
        role_name = role["name"]
        level = role_levels.get(role_name, 1)
        auth_schema["authorization"]["role_hierarchy"][role_name] = level
    
    return auth_schema

def get_entity_fields(entities: List[Dict], entity_name: str) -> Dict[str, Any]:
    """Get field definitions for an entity."""
    for entity in entities:
        if entity["name"].lower() == entity_name.lower():
            return {field["name"]: {"type": field["type"]} for field in entity.get("fields", [])}
    return {}

def map_field_type(field_type: str) -> str:
    """Map internal field types to database types."""
    type_mapping = {
        "uuid": "UUID",
        "string": "VARCHAR(255)",
        "text": "TEXT",
        "integer": "INTEGER",
        "decimal": "DECIMAL(10, 2)",
        "boolean": "BOOLEAN",
        "timestamp": "TIMESTAMP",
        "date": "DATE",
        "enum": "VARCHAR(50)",
        "json": "JSONB",
        "email": "VARCHAR(255)",
        "password": "VARCHAR(255)"
    }
    return type_mapping.get(field_type.lower(), "VARCHAR(255)")

# Test function
if __name__ == "__main__":
    test_design = {
        "application_type": "CRM",
        "entities": [
            {"name": "User", "fields": [
                {"name": "id", "type": "uuid", "required": True},
                {"name": "email", "type": "string", "required": True},
                {"name": "password_hash", "type": "string", "required": True},
                {"name": "name", "type": "string", "required": True}
            ]},
            {"name": "Contact", "fields": [
                {"name": "id", "type": "uuid", "required": True},
                {"name": "name", "type": "string", "required": True},
                {"name": "email", "type": "string", "required": False}
            ]}
        ],
        "api_flows": [
            {"method": "POST", "path": "/api/auth/register", "description": "Register", "auth": False},
            {"method": "GET", "path": "/api/contacts", "description": "List contacts", "auth": True}
        ],
        "security": {
            "middleware": ["authenticate", "authorize"],
            "authentication": {"method": "JWT"},
            "authorization": {"model": "RBAC"}
        },
        "roles": [
            {"name": "admin", "description": "Admin", "permissions": ["*"]},
            {"name": "user", "description": "User", "permissions": ["read_own", "create_own"]}
        ],
        "relationships": []
    }
    import json
    result = generate_schemas(test_design)
    print(json.dumps(result, indent=2))
