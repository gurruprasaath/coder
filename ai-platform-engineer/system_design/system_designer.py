"""
System Design Module
Converts intent into app architecture, defines entities, flows, and roles
"""

from typing import Dict, Any, List

def design_system(intent: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert extracted intent into system architecture.
    
    Args:
        intent: Structured intent from extraction stage
        
    Returns:
        System design with entities, relationships, flows, and role definitions
    """
    entities = intent.get("entities", [])
    features = intent.get("features", [])
    roles = intent.get("roles", [])
    constraints = intent.get("constraints", [])
    business_rules = intent.get("business_rules", [])
    
    system_design = {
        "application_type": determine_app_type(intent),
        "entities": design_entities(entities, features),
        "relationships": design_relationships(entities),
        "api_flows": design_api_flows(entities, features),
        "roles": design_roles(roles, entities),
        "security": design_security(roles, business_rules),
        "data_flow": design_data_flow(entities, features)
    }
    
    return system_design

def determine_app_type(intent: Dict[str, Any]) -> str:
    """Determine the type of application based on intent."""
    text = intent.get("raw_input", "").lower()
    
    if any(word in text for word in ["crm", "customer", "client", "lead"]):
        return "CRM"
    elif any(word in text for word in ["e-commerce", "shop", "store", "cart", "product"]):
        return "E-Commerce"
    elif any(word in text for word in ["social", "community", "forum", "post"]):
        return "Social Platform"
    elif any(word in text for word in ["saas", "subscription", "billing"]):
        return "SaaS Platform"
    elif any(word in text for word in ["task", "todo", "project", "management"]):
        return "Project Management"
    elif any(word in text for word in ["blog", "content", "cms"]):
        return "CMS"
    else:
        return "Web Application"

def design_entities(entities: List[str], features: List[str]) -> List[Dict[str, Any]]:
    """Design entity definitions with fields and operations."""
    entity_definitions = []
    
    # Always include User entity for authentication
    user_entity = {
        "name": "User",
        "fields": [
            {"name": "id", "type": "uuid", "required": True, "unique": True},
            {"name": "email", "type": "string", "required": True, "unique": True},
            {"name": "password_hash", "type": "string", "required": True},
            {"name": "name", "type": "string", "required": True},
            {"name": "role", "type": "enum", "required": True},
            {"name": "created_at", "type": "timestamp", "required": True},
            {"name": "updated_at", "type": "timestamp", "required": True}
        ],
        "relationships": [],
        "operations": ["create", "read", "update", "delete"]
    }
    entity_definitions.append(user_entity)
    
    # Map extracted entities to proper definitions
    entity_mappings = {
        "contact": {
            "name": "Contact",
            "fields": [
                {"name": "id", "type": "uuid", "required": True, "unique": True},
                {"name": "name", "type": "string", "required": True},
                {"name": "email", "type": "string", "required": False},
                {"name": "phone", "type": "string", "required": False},
                {"name": "company", "type": "string", "required": False},
                {"name": "notes", "type": "text", "required": False},
                {"name": "user_id", "type": "uuid", "required": True, "foreign_key": "User.id"},
                {"name": "created_at", "type": "timestamp", "required": True},
                {"name": "updated_at", "type": "timestamp", "required": True}
            ],
            "relationships": [{"type": "belongs_to", "entity": "User"}],
            "operations": ["create", "read", "update", "delete"]
        },
        "task": {
            "name": "Task",
            "fields": [
                {"name": "id", "type": "uuid", "required": True, "unique": True},
                {"name": "title", "type": "string", "required": True},
                {"name": "description", "type": "text", "required": False},
                {"name": "status", "type": "enum", "required": True, "values": ["pending", "in_progress", "completed"]},
                {"name": "priority", "type": "enum", "required": False, "values": ["low", "medium", "high"]},
                {"name": "due_date", "type": "timestamp", "required": False},
                {"name": "user_id", "type": "uuid", "required": True, "foreign_key": "User.id"},
                {"name": "created_at", "type": "timestamp", "required": True},
                {"name": "updated_at", "type": "timestamp", "required": True}
            ],
            "relationships": [{"type": "belongs_to", "entity": "User"}],
            "operations": ["create", "read", "update", "delete"]
        },
        "product": {
            "name": "Product",
            "fields": [
                {"name": "id", "type": "uuid", "required": True, "unique": True},
                {"name": "name", "type": "string", "required": True},
                {"name": "description", "type": "text", "required": False},
                {"name": "price", "type": "decimal", "required": True},
                {"name": "category", "type": "string", "required": False},
                {"name": "stock", "type": "integer", "required": False},
                {"name": "image_url", "type": "string", "required": False},
                {"name": "created_at", "type": "timestamp", "required": True},
                {"name": "updated_at", "type": "timestamp", "required": True}
            ],
            "relationships": [],
            "operations": ["create", "read", "update", "delete"]
        },
        "order": {
            "name": "Order",
            "fields": [
                {"name": "id", "type": "uuid", "required": True, "unique": True},
                {"name": "user_id", "type": "uuid", "required": True, "foreign_key": "User.id"},
                {"name": "status", "type": "enum", "required": True, "values": ["pending", "processing", "shipped", "delivered", "cancelled"]},
                {"name": "total", "type": "decimal", "required": True},
                {"name": "shipping_address", "type": "text", "required": False},
                {"name": "created_at", "type": "timestamp", "required": True},
                {"name": "updated_at", "type": "timestamp", "required": True}
            ],
            "relationships": [{"type": "belongs_to", "entity": "User"}, {"type": "has_many", "entity": "OrderItem"}],
            "operations": ["create", "read", "update"]
        },
        "subscription": {
            "name": "Subscription",
            "fields": [
                {"name": "id", "type": "uuid", "required": True, "unique": True},
                {"name": "user_id", "type": "uuid", "required": True, "foreign_key": "User.id"},
                {"name": "plan", "type": "enum", "required": True, "values": ["free", "basic", "premium", "enterprise"]},
                {"name": "status", "type": "enum", "required": True, "values": ["active", "cancelled", "expired"]},
                {"name": "start_date", "type": "timestamp", "required": True},
                {"name": "end_date", "type": "timestamp", "required": False},
                {"name": "created_at", "type": "timestamp", "required": True},
                {"name": "updated_at", "type": "timestamp", "required": True}
            ],
            "relationships": [{"type": "belongs_to", "entity": "User"}],
            "operations": ["create", "read", "update"]
        },
        "payment": {
            "name": "Payment",
            "fields": [
                {"name": "id", "type": "uuid", "required": True, "unique": True},
                {"name": "order_id", "type": "uuid", "required": True, "foreign_key": "Order.id"},
                {"name": "amount", "type": "decimal", "required": True},
                {"name": "method", "type": "enum", "required": True, "values": ["credit_card", "paypal", "stripe"]},
                {"name": "status", "type": "enum", "required": True, "values": ["pending", "completed", "failed", "refunded"]},
                {"name": "transaction_id", "type": "string", "required": False},
                {"name": "created_at", "type": "timestamp", "required": True}
            ],
            "relationships": [{"type": "belongs_to", "entity": "Order"}],
            "operations": ["create", "read"]
        }
    }
    
    for entity in entities:
        entity_lower = entity.lower()
        if entity_lower in entity_mappings and entity_lower not in [e["name"].lower() for e in entity_definitions]:
            entity_definitions.append(entity_mappings[entity_lower])
    
    return entity_definitions

def design_relationships(entities: List[str]) -> List[Dict[str, Any]]:
    """Design entity relationships."""
    relationships = []
    
    # User is central to most applications
    for entity in entities:
        if entity.lower() not in ["user"]:
            relationships.append({
                "from": "User",
                "to": entity.capitalize(),
                "type": "one-to-many",
                "description": f"A user can have multiple {entity}s"
            })
    
    # Add specific relationships based on entity types
    if "order" in [e.lower() for e in entities] and "product" in [e.lower() for e in entities]:
        relationships.append({
            "from": "Order",
            "to": "Product",
            "type": "many-to-many",
            "description": "Orders contain multiple products via order items"
        })
    
    return relationships

def design_api_flows(entities: List[str], features: List[str]) -> List[Dict[str, Any]]:
    """Design API endpoints and flows."""
    flows = []
    
    # Auth endpoints (always needed)
    flows.extend([
        {"method": "POST", "path": "/api/auth/register", "description": "User registration", "auth": False},
        {"method": "POST", "path": "/api/auth/login", "description": "User login", "auth": False},
        {"method": "POST", "path": "/api/auth/logout", "description": "User logout", "auth": True},
        {"method": "GET", "path": "/api/auth/me", "description": "Get current user", "auth": True}
    ])
    
    # Entity CRUD endpoints
    for entity in entities:
        entity_singular = entity.rstrip('s') if entity.endswith('s') else entity
        entity_plural = entity if entity.endswith('s') else entity + 's'
        
        flows.extend([
            {"method": "GET", "path": f"/api/{entity_plural}", "description": f"List all {entity_plural}", "auth": True},
            {"method": "POST", "path": f"/api/{entity_plural}", "description": f"Create new {entity_singular}", "auth": True},
            {"method": "GET", "path": f"/api/{entity_plural}/:{{entity_singular}}_id", "description": f"Get {entity_singular} by ID", "auth": True},
            {"method": "PUT", "path": f"/api/{entity_plural}/:{{entity_singular}}_id", "description": f"Update {entity_singular}", "auth": True},
            {"method": "DELETE", "path": f"/api/{entity_plural}/:{{entity_singular}}_id", "description": f"Delete {entity_singular}", "auth": True}
        ])
    
    return flows

def design_roles(roles: List[str], entities: List[str]) -> List[Dict[str, Any]]:
    """Design role definitions with permissions."""
    role_definitions = []
    
    # Default roles
    default_roles = {
        "admin": {
            "name": "admin",
            "description": "Administrator with full access",
            "permissions": ["*"]
        },
        "user": {
            "name": "user",
            "description": "Regular authenticated user",
            "permissions": ["read_own", "create_own", "update_own", "delete_own"]
        },
        "guest": {
            "name": "guest",
            "description": "Unauthenticated visitor",
            "permissions": ["read_public"]
        }
    }
    
    for role in roles:
        role_lower = role.lower()
        if role_lower in default_roles:
            role_definitions.append(default_roles[role_lower])
        elif role_lower not in [r["name"] for r in role_definitions]:
            role_definitions.append({
                "name": role_lower,
                "description": f"Custom role: {role}",
                "permissions": ["read_own", "create_own", "update_own"]
            })
    
    # Ensure admin and user exist
    role_names = [r["name"] for r in role_definitions]
    if "admin" not in role_names:
        role_definitions.append(default_roles["admin"])
    if "user" not in role_names:
        role_definitions.append(default_roles["user"])
    
    return role_definitions

def design_security(roles: List[str], business_rules: List[str]) -> Dict[str, Any]:
    """Design security configuration."""
    security = {
        "authentication": {
            "method": "JWT",
            "token_expiry": "24h",
            "refresh_token": True
        },
        "authorization": {
            "model": "RBAC",
            "default_role": "guest"
        },
        "middleware": [
            "authenticate",
            "authorize",
            "validate_request",
            "rate_limit"
        ],
        "business_rules": business_rules
    }
    
    # Add role-based access rules
    if "admin" in [r.lower() for r in roles]:
        security["role_access"] = {
            "admin": {"resources": "*", "actions": "*"},
            "user": {"resources": ["own", "shared"], "actions": ["read", "create", "update"]},
            "guest": {"resources": ["public"], "actions": ["read"]}
        }
    
    return security

def design_data_flow(entities: List[str], features: List[str]) -> Dict[str, Any]:
    """Design data flow diagrams."""
    return {
        "entry_points": ["/api/auth/register", "/api/auth/login"],
        "data_processing": [
            {"step": 1, "action": "Authentication", "description": "Verify user credentials"},
            {"step": 2, "action": "Authorization", "description": "Check user permissions"},
            {"step": 3, "action": "Validation", "description": "Validate request data"},
            {"step": 4, "action": "Processing", "description": "Execute business logic"},
            {"step": 5, "action": "Persistence", "description": "Store/retrieve from database"},
            {"step": 6, "action": "Response", "description": "Return formatted response"}
        ],
        "error_handling": {
            "authentication_failed": 401,
            "authorization_failed": 403,
            "validation_failed": 400,
            "not_found": 404,
            "server_error": 500
        }
    }

# Test function
if __name__ == "__main__":
    test_intent = {
        "raw_input": "Build a CRM with login, contacts, dashboard, role-based access, and premium plan with payments. Admins can see analytics.",
        "features": ["login", "contacts", "dashboard", "role-based access", "premium plan", "payments"],
        "entities": ["contact", "user"],
        "roles": ["admin", "user", "premium"],
        "constraints": [],
        "business_rules": ["Premium features require payment/subscription", "Only admins can access analytics"]
    }
    result = design_system(test_intent)
    import json
    print(json.dumps(result, indent=2))
