"""
Unit test suite for MCP Data Bridge tools and security guardrails.
Uses standard library unittest - 0 extra dependencies required.
Run with: python test_server.py
"""

import unittest
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from server import bridge

class TestMCPDataBridge(unittest.TestCase):
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

    def test_execute_valid_query(self):
        res = bridge.execute_query("SELECT id, name, email FROM customers WHERE tier = 'Enterprise'")
        self.assertTrue(res.get("success"))
        self.assertGreaterEqual(res.get("row_count"), 1)
        self.assertTrue(any(c["name"] == "Alice Smith" for c in res["data"]))

    def test_guardrail_blocks_drop(self):
        res = bridge.execute_query("DROP TABLE orders;")
        self.assertFalse(res.get("success"))
        self.assertIn("Security Guardrail", res.get("error", ""))

    def test_guardrail_blocks_delete(self):
        res = bridge.execute_query("DELETE FROM customers WHERE id = 1;")
        self.assertFalse(res.get("success"))
        self.assertIn("Security Guardrail", res.get("error", ""))

if __name__ == "__main__":
    unittest.main(verbosity=2)
