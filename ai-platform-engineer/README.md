# AI Platform Engineer - Multi-Stage Generation Pipeline

A compiler-like system that converts natural language to executable applications.

## Overview

This system implements a multi-stage generation pipeline for building software applications from natural language descriptions:

1. **Intent Extraction** - Parse user intent into structured intermediate form
2. **System Design Layer** - Convert intent to app architecture
3. **Schema Generation** - Generate UI, API, DB, and Auth schemas
4. **Refinement Layer** - Resolve inconsistencies across layers
5. **Validation + Repair Engine** - Detect and fix errors
6. **Execution Simulation** - Validate correctness

## Usage

```bash
# Run with default example
python main.py

# Run with custom prompt
python main.py "Build an e-commerce platform with products, cart, and checkout"
```

## Pipeline Stages

### 1. Intent Extraction
Parses natural language input to extract:
- Features (login, dashboard, etc.)
- Entities (User, Product, Order, etc.)
- Roles (admin, user, guest, etc.)
- Business rules and constraints

### 2. System Design
Converts intent into:
- Application type determination
- Entity definitions with fields
- Entity relationships
- API flows
- Role-based access control

### 3. Schema Generation
Generates complete schemas:
- **UI Schema**: Pages, components, layouts
- **API Schema**: Endpoints, methods, validators
- **DB Schema**: Tables, columns, indexes, constraints
- **Auth Schema**: JWT config, roles, permissions

### 4. Refinement Layer
Ensures cross-layer consistency:
- UI page to API endpoint mapping
- API to DB table mapping
- Auth role coverage

### 5. Validation + Repair Engine
Validates:
- Valid JSON structure
- Required fields present
- Type safety
- Cross-layer consistency
- Entity relationships

### 6. Execution Simulation
Validates that output can produce a working app:
- Schema completeness check
- Code structure generation
- Relationship validation
- API coverage verification
- Auth flow validation

## Example Output

Input:
```
Build a CRM with login, contacts, dashboard, role-based access, 
and premium plan with payments. Admins can see analytics.
```

The system generates:
- Complete database schema with Users, Contacts tables
- REST API endpoints for all CRUD operations
- React components for all pages
- JWT authentication with RBAC
- Premium gating business logic

## Evaluation Framework

The system includes built-in evaluation capabilities:
- 20 test prompts (10 real products, 10 edge cases)
- Success rate tracking
- Retry count monitoring
- Failure type classification
- Latency measurement

## Architecture

```
├── intent_extraction/
│   └── intent_extractor.py
├── system_design/
│   └── system_designer.py
├── schema_generation/
│   └── schema_generator.py
├── refinement_layer/
│   └── refiner.py
├── validation_engine/
│   └── validator.py
├── runtime_simulator/
│   └── runtime_simulator.py
└── main.py
```

## Requirements

- Python 3.7+
- No external dependencies (pure Python)

## License

MIT
