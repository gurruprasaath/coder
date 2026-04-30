"""
Intent Extraction Module
Parses user intent into structured intermediate form
"""

import re
from typing import Dict, Any, List

def extract_intent(user_input: str) -> Dict[str, Any]:
    """
    Extract structured intent from natural language input.
    
    Args:
        user_input: Natural language description
        
    Returns:
        Structured intent dictionary
    """
    intent = {
        "raw_input": user_input,
        "features": [],
        "entities": [],
        "roles": [],
        "constraints": [],
        "business_rules": []
    }
    
    # Convert to lowercase for easier matching
    text = user_input.lower()
    
    # Extract features (verbs/nouns indicating functionality)
    feature_patterns = [
        r'login', r'logout', r'register', r'sign up', r'sign in',
        r'contacts?', r'address book', r'people',
        r'dashboard', r'overview', r'analytics?', r'reports?',
        r'role.based.access|rbac|permissions?',
        r'premium\s+plan', r'subscription', r'payments?', r'billing',
        r'search', r'filter', r'sort',
        r'create|add|new', r'read|view|list', r'update|edit', r'delete|remove',
        r'notifications?', r'alerts?',
        r'file\s+upload|document\s+management',
        r'chat|messaging|communication',
        r'calendar|schedule|events?',
        r'tasks?|todo',
        r'settings?|preferences?',
        r'profile|account',
        r'search',
        r'export|import',
        r'notifications?',
        r'search',
        r'audit|logs?|history'
    ]
    
    for pattern in feature_patterns:
        if re.search(pattern, text):
            # Extract the actual matched text
            matches = re.findall(pattern, user_input, re.IGNORECASE)
            for match in matches:
                if match not in intent["features"]:
                    intent["features"].append(match)
    
    # Extract entities (nouns that could be data models)
    entity_keywords = [
        'user', 'users', 'customer', 'customers', 'client', 'clients',
        'contact', 'contacts', 'lead', 'leads', 'prospect', 'prospects',
        'product', 'products', 'item', 'items', 'inventory',
        'order', 'orders', 'purchase', 'transaction', 'transactions',
        'invoice', 'invoices', 'bill', 'bills',
        'task', 'tasks', 'todo', 'todos',
        'event', 'events', 'calendar', 'appointment', 'appointments',
        'document', 'documents', 'file', 'files',
        'message', 'messages', 'chat', 'chats', 'notification', 'notifications',
        'role', 'roles', 'permission', 'permissions',
        'plan', 'plans', 'subscription', 'subscriptions',
        'analytics', 'report', 'reports', 'metric', 'metrics',
        'settings', 'preferences', 'profile', 'profiles'
    ]
    
    for entity in entity_keywords:
        if entity in text:
            # Get singular form
            singular = entity.rstrip('s') if entity.endswith('s') and not entity.endswith('ss') else entity
            if singular not in intent["entities"]:
                intent["entities"].append(singular)
    
    # Extract roles
    role_patterns = [
        r'admin|administrator',
        r'user|member|customer|client',
        r'guest|visitor',
        r'moderator|mod',
        r'editor|contributor',
        r'manager|supervisor',
        r'owner|proprietor',
        r'support|agent',
        r'premium|paid|subscriber',
        r'basic|free|standard'
    ]
    
    for pattern in role_patterns:
        if re.search(pattern, text):
            matches = re.findall(pattern, user_input, re.IGNORECASE)
            for match in matches:
                if match not in intent["roles"]:
                    intent["roles"].append(match)
    
    # Extract constraints and business rules
    constraint_indicators = [
        'must', 'should', 'required', 'mandatory', 'only', 'except',
        'if', 'when', 'unless', 'provided that', 'as long as',
        'premium', 'paid', 'free', 'limit', 'maximum', 'minimum',
        'role.based', 'permission', 'access control',
        'validation', 'verify', 'confirm'
    ]
    
    for indicator in constraint_indicators:
        if indicator in text:
            # Extract the sentence containing the constraint
            sentences = re.split(r'[.!?]+', user_input)
            for sentence in sentences:
                if indicator in sentence.lower():
                    constraint = sentence.strip()
                    if constraint and constraint not in intent["constraints"]:
                        intent["constraints"].append(constraint)
    
    # Special handling for premium/gating logic
    if 'premium' in text and ('payment' in text or 'pay' in text):
        intent["business_rules"].append("Premium features require payment/subscription")
    
    if 'admin' in text and ('analytics' in text or 'see analytics' in text):
        intent["business_rules"].append("Only admins can access analytics")
    
    # Ensure we have at least some basic entities
    if not intent["entities"]:
        intent["entities"] = ["user"]  # Default fallback
    
    # Ensure we have basic roles
    if not intent["roles"]:
        intent["roles"] = ["user", "admin"]  # Default fallback
    
    # Remove duplicates
    intent["features"] = list(dict.fromkeys(intent["features"]))
    intent["entities"] = list(dict.fromkeys(intent["entities"]))
    intent["roles"] = list(dict.fromkeys(intent["roles"]))
    intent["constraints"] = list(dict.fromkeys(intent["constraints"]))
    intent["business_rules"] = list(dict.fromkeys(intent["business_rules"]))
    
    return intent

# Test function
if __name__ == "__main__":
    test_input = "Build a CRM with login, contacts, dashboard, role-based access, and premium plan with payments. Admins can see analytics."
    result = extract_intent(test_input)
    print(json.dumps(result, indent=2))