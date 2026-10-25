"""
Autonomous AI Agent End-to-End Simulation.
Simulates a multi-turn LLM reasoning loop that queries the MCP Data Bridge
to answer business questions and demonstrates runtime security guardrails.
"""

import json
import time
from typing import Any
from server import bridge

def print_step(title: str, content: Any):
    print("\n" + "=" * 65)
    print(f"🤖 AGENT STEP: {title}")
    print("=" * 65)
    if isinstance(content, (dict, list)):
        print(json.dumps(content, indent=2))
    else:
        print(content)
    time.sleep(0.5)

def run_agent_workflow():
    print("\n🚀 Starting Autonomous Agent Session via MCP Data Bridge...")
    print("Goal: 'Identify our top enterprise customers and their total spend.'")

    # Step 1: Agent inspects schema
    print_step("Discovering Available Enterprise Tables", bridge.list_tables())

    # Step 2: Agent describes schema for relevant tables
    print_step("Inspecting 'customers' Schema", bridge.describe_table("customers"))
    print_step("Inspecting 'orders' Schema", bridge.describe_table("orders"))

    # Step 3: Agent formulates SQL query and calls execute_query tool
    top_spenders_sql = """
    SELECT 
        c.name AS customer_name,
        c.tier AS subscription_tier,
        COUNT(o.id) AS total_orders,
        ROUND(SUM(o.total_amount), 2) AS total_revenue
    FROM customers c
    JOIN orders o ON c.id = o.customer_id
    GROUP BY c.id
    ORDER BY total_revenue DESC
    """
    print_step("Executing Analytical Query (Customer Revenue Breakdown)", bridge.execute_query(top_spenders_sql))

    # Step 4: Simulated Prompt Injection / Malicious Tool Execution
    print("\n⚠️  Simulating Unsafe LLM Behavior (e.g. Prompt Injection Attack):")
    malicious_sql = "DROP TABLE customers; -- bye bye data"
    print_step("Attempting Malicious Query (DROP TABLE)", bridge.execute_query(malicious_sql))

    # Step 5: Summary of Execution
    print("\n" + "#" * 65)
    print("🎉 WORKFLOW COMPLETE: All safe queries succeeded; unsafe mutation blocked.")
    print("#" * 65)

if __name__ == "__main__":
    run_agent_workflow()
