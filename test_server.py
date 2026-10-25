"""
Comprehensive Unit Test Suite for MCP Data Bridge Enterprise Edition.
Tests schema discovery, read-only SQL, execution latency, audit logging,
and multi-vector injection guardrails.
Run with: python test_server.py
"""

import unittest
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from server import bridge

class TestMCPDataBridgeEnterprise(unittest.TestCase):
    def test_list_tables(self):
        res = bridge.list_tables()
        self.assertIn("tables", res)
        self.assertIn("customers", res["tables"])
        self.assertIn("orders", res["tables"])
        self.assertIn("products", res["tables"])

    def test_describe_table(self):
        res = bridge.describe_table("customers")
        self.assertEqual(res.get("table"), "customers")
        column_names = [c["name"] for c in res["columns"]]
        self.assertIn("email", column_names)
        self.assertIn("name", column_names)

    def test_execute_valid_query_and_latency(self):
        res = bridge.execute_query("SELECT id, name, email FROM customers WHERE tier = 'Enterprise'")
        self.assertTrue(res.get("success"))
        self.assertGreaterEqual(res.get("row_count"), 1)
        self.assertIn("execution_time_ms", res)
        self.assertIsInstance(res["execution_time_ms"], float)
        self.assertTrue(any(c["name"] == "Alice Smith" for c in res["data"]))

    def test_guardrail_blocks_drop(self):
        res = bridge.execute_query("DROP TABLE orders;")
        self.assertFalse(res.get("success"))
        self.assertIn("Security Guardrail", res.get("error", ""))

    def test_guardrail_blocks_delete(self):
        res = bridge.execute_query("DELETE FROM customers WHERE id = 1;")
        self.assertFalse(res.get("success"))
        self.assertIn("Security Guardrail", res.get("error", ""))

    def test_guardrail_blocks_multi_statement_stacked_injection(self):
        res = bridge.execute_query("SELECT 1; DROP TABLE customers;")
        self.assertFalse(res.get("success"))
        self.assertIn("Multi-statement", res.get("error", ""))

    def test_system_health_and_audit(self):
        health = bridge.get_system_health()
        self.assertEqual(health.get("status"), "HEALTHY")
        self.assertTrue(health["security_guardrails"]["read_only_enforced"])
        self.assertTrue(health["security_guardrails"]["multi_statement_blocking"])
        self.assertGreaterEqual(health["audit_events_recorded"], 1)

if __name__ == "__main__":
    unittest.main(verbosity=2)
