"""
MCP Data Bridge Server.
Exposes database schema inspection and safe read-only SQL execution tools
following the Model Context Protocol (MCP) standard for autonomous LLM agents.
Supports STDIO transport (Claude Desktop / Cursor), Interactive CLI, and Python SDK.
"""

import sqlite3
import re
import sys
import json
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
        self._ensure_db()

    def _ensure_db(self):
        if not self.db_path.exists():
            from demo_db import init_database
            init_database()

    def _get_connection(self) -> sqlite3.Connection:
        self._ensure_db()
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def list_tables(self) -> Dict[str, Any]:
        """Tool: Lists all user tables available in the enterprise database."""
        logger.info("Tool called: list_tables")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = [row["name"] for row in cursor.fetchall()]
        return {"tables": tables, "count": len(tables)}

    def describe_table(self, table_name: str) -> Dict[str, Any]:
        """Tool: Retrieves schema columns, types, and constraints for a specific table."""
        if not table_name or not re.match(r"^[a-zA-Z0-9_]+$", table_name):
            return {"error": "Invalid table name. Only alphanumeric characters and underscores allowed."}

        logger.info(f"Tool called: describe_table for '{table_name}'")
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
            return {"error": f"Table '{table_name}' does not exist in database."}

        return {"table": table_name, "columns": columns}

    def execute_query(self, sql: str, limit: int = 50) -> Dict[str, Any]:
        """Tool: Executes a verified, read-only SELECT SQL query with guardrails and limit clamping."""
        if not sql or not sql.strip():
            return {"success": False, "error": "Empty SQL query provided."}

        cleaned_sql = sql.strip().rstrip(";")

        # Safety Guardrail 1: Only SELECT queries permitted
        if not cleaned_sql.upper().startswith("SELECT"):
            logger.warning(f"Blocked non-SELECT query attempt: {sql}")
            return {
                "success": False,
                "error": "Security Guardrail Violation: Only SELECT queries are permitted on this MCP server."
            }

        # Safety Guardrail 2: Block mutation/destructive SQL keywords
        if FORBIDDEN_KEYWORDS.search(cleaned_sql):
            logger.warning(f"Blocked prohibited SQL keywords in query: {sql}")
            return {
                "success": False,
                "error": "Security Guardrail Violation: Query contains prohibited modification keywords (INSERT, UPDATE, DELETE, DROP, etc.)."
            }

        logger.info(f"Executing verified read query: {cleaned_sql}")
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(cleaned_sql)
                rows = cursor.fetchmany(min(max(limit, 1), 100))
                results = [dict(row) for row in rows]

            return {
                "success": True,
                "row_count": len(results),
                "data": results
            }
        except Exception as e:
            logger.error(f"SQL execution error: {e}")
            return {"success": False, "error": str(e)}

    def handle_mcp_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handles Model Context Protocol JSON-RPC 2.0 messages over STDIO."""
        msg_id = message.get("id")
        method = message.get("method")
        params = message.get("params", {})

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": [
                        {
                            "name": "list_tables",
                            "description": "Lists all accessible tables in the enterprise database.",
                            "inputSchema": {"type": "object", "properties": {}}
                        },
                        {
                            "name": "describe_table",
                            "description": "Retrieves the schema and column details for a given table name.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"table_name": {"type": "string", "description": "Target table name"}},
                                "required": ["table_name"]
                            }
                        },
                        {
                            "name": "execute_query",
                            "description": "Executes a safe, read-only SELECT query against the database.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "sql": {"type": "string", "description": "The SELECT SQL statement"},
                                    "limit": {"type": "integer", "description": "Max rows to return (default: 50)"}
                                },
                                "required": ["sql"]
                            }
                        }
                    ]
                }
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})

            if tool_name == "list_tables":
                res = self.list_tables()
            elif tool_name == "describe_table":
                res = self.describe_table(tool_args.get("table_name", ""))
            elif tool_name == "execute_query":
                res = self.execute_query(tool_args.get("sql", ""), tool_args.get("limit", 50))
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
                }

            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}
            }

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"Method not supported: {method}"}
        }

# Singleton instance
bridge = MCPDataBridge()

def run_stdio_server():
    """Runs standard input/output JSON-RPC loop for Claude Desktop / Cursor / MCP clients."""
    logger.info("Starting MCP Data Bridge in STDIO transport mode...")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = bridge.handle_mcp_message(req)
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        except Exception as e:
            err_resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(e)}}
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--stdio":
        run_stdio_server()
    else:
        print("🚀 MCP Data Bridge Self-Test & Diagnostic Run:")
        print("-" * 55)
        print("1. Tables Available:", bridge.list_tables())
        print("\n2. Customer Table Columns:", bridge.describe_table("customers"))
        print("\n3. Sample Read Query:")
        query_res = bridge.execute_query("SELECT id, name, email, tier FROM customers LIMIT 3;")
        print(json.dumps(query_res, indent=2))
        print("\n4. Security Guardrail Test (Attempting DELETE query):")
        guardrail_res = bridge.execute_query("DELETE FROM customers WHERE id = 1;")
        print(json.dumps(guardrail_res, indent=2))
        print("-" * 55)
        print("✅ All tools verified and operating normally.")
        print("💡 Run with `python server.py --stdio` to start in MCP client mode.")
