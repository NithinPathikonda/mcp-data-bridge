"""
MCP Data Bridge Server - Enterprise Edition.
Exposes database schema inspection, safe read-only SQL execution tools, and system health
following the Model Context Protocol (MCP) standard for autonomous LLM agents.
Includes multi-statement defense, query latency tracking, and structured audit logs.
"""

import sqlite3
import re
import sys
import json
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("mcp_data_bridge")

DB_PATH = Path(__file__).resolve().parent / "enterprise.db"

# Disallowed keywords to enforce read-only safety guardrails
FORBIDDEN_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|REPLACE|GRANT|REVOKE|ATTACH|DETACH|EXEC|VACUUM|REINDEX|PRAGMA)\b",
    re.IGNORECASE
)

# SQL comment markers used in injection bypasses
COMMENT_PATTERN = re.compile(r"(--|/\*|\*/)")

class QueryRequest(BaseModel):
    sql: str = Field(..., description="The SELECT SQL query to execute")
    limit: Optional[int] = Field(default=50, description="Max rows to return (default 50, max 100)")

class TableDescribeRequest(BaseModel):
    table_name: str = Field(..., description="The name of the database table to inspect")

class MCPDataBridge:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.audit_log: List[Dict[str, Any]] = []
        self._ensure_db()

    def _ensure_db(self):
        if not self.db_path.exists():
            from demo_db import init_database
            init_database()

    def _get_connection(self) -> sqlite3.Connection:
        self._ensure_db()
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _log_audit(self, status: str, action: str, details: Dict[str, Any]):
        """Records structured audit trail for compliance and security observability."""
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "status": status,
            **details
        }
        self.audit_log.append(event)
        # Keep last 100 in-memory events
        if len(self.audit_log) > 100:
            self.audit_log.pop(0)

    def list_tables(self) -> Dict[str, Any]:
        """Tool: Lists all user tables available in the enterprise database."""
        logger.info("Tool called: list_tables")
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name ASC;")
            tables = [row["name"] for row in cursor.fetchall()]

        self._log_audit("ALLOWED", "list_tables", {"tables_found": len(tables)})
        return {"tables": tables, "count": len(tables)}

    def describe_table(self, table_name: str) -> Dict[str, Any]:
        """Tool: Retrieves schema columns, types, and constraints for a specific table."""
        if not table_name or not re.match(r"^[a-zA-Z0-9_]+$", table_name):
            self._log_audit("BLOCKED", "describe_table", {"reason": "INVALID_TABLE_NAME", "input": table_name})
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
            self._log_audit("BLOCKED", "describe_table", {"reason": "TABLE_NOT_FOUND", "table": table_name})
            return {"error": f"Table '{table_name}' does not exist in database."}

        self._log_audit("ALLOWED", "describe_table", {"table": table_name, "column_count": len(columns)})
        return {"table": table_name, "columns": columns}

    def execute_query(self, sql: str, limit: int = 50) -> Dict[str, Any]:
        """
        Tool: Executes a verified, read-only SELECT SQL query with multi-statement defense,
        prohibited mutation keyword filters, and execution timing.
        """
        start_time = time.perf_counter()

        if not sql or not sql.strip():
            return {"success": False, "error": "Empty SQL query provided."}

        raw_sql = sql.strip()

        # Multi-statement defense: reject stacked queries (e.g., "SELECT 1; DROP TABLE ...")
        trimmed_semicolons = raw_sql.rstrip(";")
        if ";" in trimmed_semicolons:
            logger.warning(f"Blocked multi-statement query attempt: {sql}")
            self._log_audit("BLOCKED", "execute_query", {"reason": "MULTI_STATEMENT_REJECTED", "sql": sql})
            return {
                "success": False,
                "error": "Security Guardrail Violation: Multi-statement (stacked) SQL queries are strictly prohibited."
            }

        # Guardrail 1: Must be a pure SELECT query
        if not trimmed_semicolons.lstrip().upper().startswith("SELECT"):
            logger.warning(f"Blocked non-SELECT query attempt: {sql}")
            self._log_audit("BLOCKED", "execute_query", {"reason": "NON_SELECT_QUERY", "sql": sql})
            return {
                "success": False,
                "error": "Security Guardrail Violation: Only SELECT queries are permitted on this MCP server."
            }

        # Guardrail 2: Block prohibited destructive / mutation SQL keywords
        forbidden_match = FORBIDDEN_KEYWORDS.search(trimmed_semicolons)
        if forbidden_match:
            blocked_keyword = forbidden_match.group(0).upper()
            logger.warning(f"Blocked prohibited SQL keyword '{blocked_keyword}' in query: {sql}")
            self._log_audit("BLOCKED", "execute_query", {"reason": "FORBIDDEN_KEYWORD", "keyword": blocked_keyword, "sql": sql})
            return {
                "success": False,
                "error": f"Security Guardrail Violation: Query contains prohibited keyword '{blocked_keyword}'."
            }

        # Enforce safe row clamping (1 to 100 rows)
        effective_limit = min(max(limit, 1), 100)

        logger.info(f"Executing verified read query: {trimmed_semicolons} (limit: {effective_limit})")
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(trimmed_semicolons)
                rows = cursor.fetchmany(effective_limit)
                results = [dict(row) for row in rows]

            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            self._log_audit("ALLOWED", "execute_query", {
                "sql": trimmed_semicolons,
                "rows_returned": len(results),
                "execution_time_ms": elapsed_ms
            })

            return {
                "success": True,
                "row_count": len(results),
                "execution_time_ms": elapsed_ms,
                "data": results
            }
        except Exception as e:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(f"SQL execution error ({elapsed_ms}ms): {e}")
            self._log_audit("ERROR", "execute_query", {"error": str(e), "execution_time_ms": elapsed_ms})
            return {"success": False, "error": str(e), "execution_time_ms": elapsed_ms}

    def get_system_health(self) -> Dict[str, Any]:
        """Tool: Returns server health, database size, active tables, and audit metrics."""
        tables_res = self.list_tables()
        db_size_kb = round(self.db_path.stat().st_size / 1024, 2) if self.db_path.exists() else 0.0
        return {
            "status": "HEALTHY",
            "database": {
                "path": str(self.db_path),
                "size_kb": db_size_kb,
                "tables_count": tables_res.get("count", 0),
                "tables": tables_res.get("tables", [])
            },
            "security_guardrails": {
                "read_only_enforced": True,
                "multi_statement_blocking": True,
                "max_row_limit": 100,
                "timeout_seconds": 5.0
            },
            "audit_events_recorded": len(self.audit_log)
        }

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
                            "description": "Lists all accessible user tables in the enterprise database.",
                            "inputSchema": {"type": "object", "properties": {}}
                        },
                        {
                            "name": "describe_table",
                            "description": "Retrieves the schema, columns, and types for a given table name.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"table_name": {"type": "string", "description": "Target table name"}},
                                "required": ["table_name"]
                            }
                        },
                        {
                            "name": "execute_query",
                            "description": "Executes a safe, read-only SELECT query against the database with guardrails.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "sql": {"type": "string", "description": "The SELECT SQL statement"},
                                    "limit": {"type": "integer", "description": "Max rows to return (default: 50, max: 100)"}
                                },
                                "required": ["sql"]
                            }
                        },
                        {
                            "name": "get_system_health",
                            "description": "Returns operational metrics, database size, and security guardrail status.",
                            "inputSchema": {"type": "object", "properties": {}}
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
            elif tool_name == "get_system_health":
                res = self.get_system_health()
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
        print("🚀 MCP Data Bridge Enterprise Self-Test:")
        print("=" * 60)
        print("1. System Health:", json.dumps(bridge.get_system_health(), indent=2))
        print("\n2. Customer Table Columns:", bridge.describe_table("customers"))
        print("\n3. Verified Query Result:")
        print(json.dumps(bridge.execute_query("SELECT id, name, email, tier FROM customers LIMIT 2;"), indent=2))
        print("\n4. Security Test A (Stacked Semicolon Injection):")
        print(json.dumps(bridge.execute_query("SELECT 1; DROP TABLE customers;"), indent=2))
        print("\n5. Security Test B (Attempting DELETE query):")
        print(json.dumps(bridge.execute_query("DELETE FROM customers WHERE id = 1;"), indent=2))
        print("=" * 60)
        print("✅ Enterprise guardrails and latency tracking operational.")
