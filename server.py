"""
MCP Data Bridge Server.
Exposes database schema inspection and safe read-only SQL execution tools
following the Model Context Protocol (MCP) standard for autonomous LLM agents.
"""

import sqlite3
import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("mcp_data_bridge")

DB_PATH = Path(__file__).resolve().parent / "enterprise.db"

# Disallowed keywords to enforce read-only safety guardrails
FORBIDDEN_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|REPLACE|GRANT|REVOKE|ATTACH|DETACH|EXEC)\b",
    re.IGNORECASE
)

class QueryRequest(BaseModel):
    sql: str = Field(..., description="The SELECT SQL query to execute")
    limit: Optional[int] = Field(default=50, description="Max rows to return (default 50)")

class TableDescribeRequest(BaseModel):
    table_name: str = Field(..., description="The name of the database table to inspect")

class MCPDataBridge:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        if not self.db_path.exists():
            from demo_db import init_database
            init_database()
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def list_tables(self) -> Dict[str, Any]:
        """Tool: Lists all user tables available in the enterprise database."""
        logger.info("Executing tool: list_tables")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = [row["name"] for row in cursor.fetchall()]
        return {"tables": tables, "count": len(tables)}

    def describe_table(self, table_name: str) -> Dict[str, Any]:
        """Tool: Retrieves schema columns, types, and constraints for a specific table."""
        # Sanitize table name to prevent SQL injection in pragma
        if not re.match(r"^[a-zA-Z0-9_]+$", table_name):
            return {"error": "Invalid table name. Only alphanumeric characters and underscores allowed."}

        logger.info(f"Executing tool: describe_table for '{table_name}'")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = [
                {
                    "column_id": row["cid"],
                    "name": row["name"],
                    "type": row["type"],
                    "not_null": bool(row["notnull"]),
                    "primary_key": bool(row["pk"])
                }
                for row in cursor.fetchall()
            ]

        if not columns:
            return {"error": f"Table '{table_name}' does not exist."}

        return {"table": table_name, "columns": columns}

    def execute_query(self, sql: str, limit: int = 50) -> Dict[str, Any]:
        """Tool: Executes a safe, read-only SELECT SQL query with guardrails and limit clamping."""
        cleaned_sql = sql.strip().rstrip(";")

        # Safety Guardrail: Only SELECT queries permitted
        if not cleaned_sql.upper().startswith("SELECT"):
            logger.warning(f"Blocked non-SELECT query attempt: {sql}")
            return {
                "success": False,
                "error": "Security Guardrail Violation: Only SELECT queries are permitted on this MCP server."
            }

        # Check for mutation/destructive SQL keywords
        if FORBIDDEN_KEYWORDS.search(cleaned_sql):
            logger.warning(f"Blocked prohibited SQL keywords in query: {sql}")
            return {
                "success": False,
                "error": "Security Guardrail Violation: Query contains prohibited modification keywords."
            }

        logger.info(f"Executing verified read query: {cleaned_sql}")
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(cleaned_sql)
                rows = cursor.fetchmany(min(limit, 100))
                results = [dict(row) for row in rows]

            return {
                "success": True,
                "row_count": len(results),
                "data": results
            }
        except Exception as e:
            logger.error(f"SQL execution error: {e}")
            return {"success": False, "error": str(e)}

# Export singleton bridge
bridge = MCPDataBridge()

if __name__ == "__main__":
    print("🚀 Initializing MCP Data Bridge demo run...")
    print("1. Available Tables:", bridge.list_tables())
    print("\n2. Customer Table Schema:", bridge.describe_table("customers"))
    print("\n3. Top Customers Query:", bridge.execute_query(
        "SELECT c.name, c.tier, SUM(o.total_amount) as total_spent "
        "FROM customers c JOIN orders o ON c.id = o.customer_id "
        "GROUP BY c.id ORDER BY total_spent DESC;"
    ))
    print("\n4. Security Guardrail Test (Trying to DROP table):", bridge.execute_query("DROP TABLE customers;"))
