#!/usr/bin/env python3
"""
Main application for the AI Platform Engineer multi-stage generation pipeline.
This implements a compiler-like system that converts natural language to executable applications.
"""
import json
import sys
import os
from typing import Dict, Any, Optional

sys.path.insert(0, os.path.dirname(__file__))

try:
    from intent_extraction.intent_extractor import extract_intent
    from system_design.system_designer import design_system
    from schema_generation.schema_generator import generate_schemas
    from refinement_layer.refiner import refine_schemas
    from validation_engine.validator import validate_and_repair
    from runtime_simulator.runtime_simulator import simulate_execution
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure all module directories contain their .py files")
    sys.exit(1)

def run_pipeline(user_input: str) -> Dict[str, Any]:
    """
    Execute the multi-stage generation pipeline.
    
    Args:
        user_input: Natural language description of the desired application
        
    Returns:
        Final validated and refined schema ready for execution
    """
    print("="*60)
    print("AI Platform Engineer Pipeline - Multi-Stage Generator")
    print("="*60)
    print(f"\n📝 Input: {user_input}\n")
    
    # Stage 1: Intent Extraction
    print("─"*60)
    print("🔍 STAGE 1: INTENT EXTRACTION")
    print("─"*60)
    try:
        intent = extract_intent(user_input)
        print(f"✅ Intent extracted successfully")
        print(f"   Features: {', '.join(intent.get('features', [])[:5])}{'...' if len(intent.get('features', [])) > 5 else ''}")
        print(f"   Entities: {', '.join(intent.get('entities', []))}")
        print(f"   Roles: {', '.join(intent.get('roles', []))}")
    except Exception as e:
        print(f"❌ Intent Extraction Failed: {e}")
        return {"error": f"Intent extraction failed: {e}"}
    
    # Stage 2: System Design
    print("\n" + "─"*60)
    print("🏗️  STAGE 2: SYSTEM DESIGN")
    print("─"*60)
    try:
        system_design = design_system(intent)
        app_type = system_design.get("application_type", "Unknown")
        num_entities = len(system_design.get("entities", []))
        num_flows = len(system_design.get("api_flows", []))
        print(f"✅ System design completed")
        print(f"   Application Type: {app_type}")
        print(f"   Entities: {num_entities}")
        print(f"   API Flows: {num_flows}")
    except Exception as e:
        print(f"❌ System Design Failed: {e}")
        return {"error": f"System design failed: {e}"}
    
    # Stage 3: Schema Generation
    print("\n" + "─"*60)
    print("📋 STAGE 3: SCHEMA GENERATION")
    print("─"*60)
    try:
        schemas = generate_schemas(system_design)
        ui_pages = len(schemas.get("ui_schema", {}).get("pages", []))
        api_endpoints = len(schemas.get("api_schema", {}).get("endpoints", []))
        db_tables = len(schemas.get("db_schema", {}).get("tables", []))
        print(f"✅ Schemas generated successfully")
        print(f"   UI Pages: {ui_pages}")
        print(f"   API Endpoints: {api_endpoints}")
        print(f"   DB Tables: {db_tables}")
    except Exception as e:
        print(f"❌ Schema Generation Failed: {e}")
        return {"error": f"Schema generation failed: {e}"}
    
    # Stage 4: Refinement Layer
    print("\n" + "─"*60)
    print("⚙️  STAGE 4: REFINEMENT LAYER")
    print("─"*60)
    try:
        refined_schemas = refine_schemas(schemas)
        metadata = refined_schemas.get("metadata", {})
        issues_resolved = metadata.get("issues_resolved", 0)
        print(f"✅ Refinement completed")
        print(f"   Cross-layer issues resolved: {issues_resolved}")
    except Exception as e:
        print(f"❌ Refinement Failed: {e}")
        return {"error": f"Refinement failed: {e}"}
    
    # Stage 5: Validation + Repair Engine
    print("\n" + "─"*60)
    print("✅ STAGE 5: VALIDATION + REPAIR ENGINE")
    print("─"*60)
    try:
        validated_schemas = validate_and_repair(refined_schemas)
        validation = validated_schemas.get("validation", {})
        errors_found = validation.get("errors_found", 0)
        errors_repaired = validation.get("errors_repaired", 0)
        print(f"✅ Validation completed")
        print(f"   Errors found: {errors_found}")
        print(f"   Errors repaired: {errors_repaired}")
    except Exception as e:
        print(f"❌ Validation Failed: {e}")
        return {"error": f"Validation failed: {e}"}
    
    # Stage 6: Execution Awareness (Simulation)
    print("\n" + "─"*60)
    print("▶️  STAGE 6: EXECUTION SIMULATION")
    print("─"*60)
    try:
        execution_result = simulate_execution(validated_schemas)
        status = execution_result.get("status", "unknown")
        checks_passed = len([c for c in execution_result.get("checks", []) if c.get("passed")])
        total_checks = len(execution_result.get("checks", []))
        print(f"✅ Execution simulation completed")
        print(f"   Status: {status}")
        print(f"   Checks passed: {checks_passed}/{total_checks}")
    except Exception as e:
        print(f"⚠️  Execution Simulation Warning: {e}")
        status = "partial"
    
    print("\n" + "="*60)
    print("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
    print("="*60 + "\n")
    
    return validated_schemas

def main():
    """Main entry point for the application."""
    if len(sys.argv) > 1:
        # Use command line argument as input
        user_input = " ".join(sys.argv[1:])
    else:
        # Use example input
        user_input = "Build a CRM with login, contacts, dashboard, role-based access, and premium plan with payments. Admins can see analytics."
    
    result = run_pipeline(user_input)
    
    if "error" in result:
        print(f"\n❌ Pipeline failed: {result['error']}")
        sys.exit(1)
    
    # Output final result summary
    print("\n" + "="*60)
    print("📊 FINAL OUTPUT SUMMARY")
    print("="*60)
    print(f"\n✅ Generated Application Configuration:")
    print(f"   - Application Type: {result.get('ui_schema', {}).get('application_type', 'Web App')}")
    print(f"   - Pages: {len(result.get('ui_schema', {}).get('pages', []))}")
    print(f"   - API Endpoints: {len(result.get('api_schema', {}).get('endpoints', []))}")
    print(f"   - Database Tables: {len(result.get('db_schema', {}).get('tables', []))}")
    print(f"   - Roles: {len(result.get('auth_schema', {}).get('authorization', {}).get('roles', []))}")
    
    # Save to file
    output_dir = os.path.dirname(__file__)
    output_path = os.path.join(output_dir, 'output.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Output saved to: {output_path}")

if __name__ == "__main__":
    main()