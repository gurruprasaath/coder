import json
import time
from dotenv import load_dotenv
from pipeline.orchestrator import run_pipeline

load_dotenv()

# Evaluation Dataset — 10 Real Prompts, 10 Edge Cases
DATASET = {
    "real": [
        "Create a CRM with login, contacts, dashboard, and role-based access. Admins can see analytics.",
        "Build a Todo application with user accounts, projects, and tasks. Each project can have multiple tasks.",
        "Create an e-commerce backend with Products, Categories, Shopping Cart, and Orders.",
        "A blog system where users can write Posts, and visitors can leave Comments.",
        "Event booking app with Venues, Events, and Tickets. Users can purchase tickets.",
        "Inventory management system. Items have SKU, quantity, warehouse location.",
        "Employee directory with Departments, Employees, and performance reviews.",
        "Support ticketing system. Users submit tickets, Agents reply to tickets.",
        "Fitness tracker app. Users log workouts, exercises, and track weight over time.",
        "Recipe sharing app. Recipes have ingredients, instructions, and user ratings."
    ],
    "edge_cases": [
        # Vague
        "Make an app.",
        "Build a system that does stuff with data.",
        "I need a website for my business.",
        # Conflicting
        "Create a private app where all data is public to everyone but requires admin login.",
        "Make a system with no database that stores millions of records permanently.",
        "A to-do list where tasks cannot be created or deleted, only updated.",
        # Incomplete
        "Create a user table. That's it.",
        "A login screen.",
        "Just make an API endpoint for /data.",
        # Hallucination trap
        "Build a time machine control panel with flux capacitor integration and quantum routing."
    ]
}

def run_benchmark():
    print("🚀 Starting Pre-Execution Evaluation Benchmark...\n")
    results = []

    total_prompts = len(DATASET["real"]) + len(DATASET["edge_cases"])
    completed = 0

    for category, prompts in DATASET.items():
        for prompt in prompts:
            print(f"[{completed+1}/{total_prompts}] Testing ({category}): {prompt[:50]}...")
            
            start_time = time.time()
            try:
                res = run_pipeline(prompt)
                latency = round((time.time() - start_time) * 1000, 2)

                if res.get("needs_clarification"):
                    print("  → 🛑 VAGUE PROMPT DETECTED (Graceful Halt)")
                    results.append({
                        "category": category,
                        "prompt": prompt,
                        "status": "VAGUE_HALT",
                        "latency_ms": latency
                    })
                elif res.get("evaluation"):
                    score = res["evaluation"]["score"]
                    eval_status = res["evaluation"]["status"]
                    print(f"  → ✅ SUCCESS. Score: {score}/100. Status: {eval_status}")
                    results.append({
                        "category": category,
                        "prompt": prompt,
                        "status": "SUCCESS",
                        "eval_score": score,
                        "eval_status": eval_status,
                        "latency_ms": latency,
                        "metrics": res["evaluation"].get("metrics", {})
                    })
                else:
                    print("  → ❌ FATAL ERROR")
                    results.append({
                        "category": category,
                        "prompt": prompt,
                        "status": "FATAL",
                        "latency_ms": latency
                    })

            except Exception as e:
                print(f"  → 💥 UNHANDLED EXCEPTION: {e}")

            completed += 1
            print("-" * 60)

    # Save metrics
    with open("benchmark_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"🎉 Benchmark complete. Results saved to benchmark_results.json")

if __name__ == "__main__":
    run_benchmark()
