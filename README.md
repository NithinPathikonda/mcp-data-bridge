# MCP Data Bridge ⚡
> Model Context Protocol (MCP) Database Gateway for Autonomous AI Agents

`MCP Data Bridge` is a lightweight, high-performance tool server built on the **Model Context Protocol (MCP)** specification. It allows autonomous LLM agents (Claude, Gemini, OpenAI Assistants) to inspect relational database schemas and execute validated, read-only SQL queries with built-in prompt-injection and mutation guardrails.

---

## 🎯 Architecture & How It Works

```
┌───────────────────────────────┐
│ Autonomous LLM Agent          │
│ (Claude / Gemini / LangGraph) │
└──────────────┬────────────────┘
               │ JSON-RPC / MCP Request
               ▼
┌────────────────────────────────────────────────────────┐
│ MCP Data Bridge Server                                 │
│                                                        │
│  1. list_tables()                                      │
│  2. describe_table(table_name)                         │
│  3. execute_query(sql)                                 │
│     ├── Pydantic Input Validation                      │
│     ├── Read-Only SQL Guardrail (Rejects DROP/MUTATE)  │
│     └── Max Row Clamping                               │
└──────────────┬─────────────────────────────────────────┘
               │ Parameterized Safe Query
               ▼
┌───────────────────────────────┐
│ Enterprise Database           │
│ (SQLite / Postgres / RDS)     │
└───────────────────────────────┘
```

---

## 🚀 Quickstart

### 1. Initialize Sample Database
```bash
python demo_db.py
```

### 2. Run Demo & Tools
```bash
python server.py
```

### 3. Run Unit Tests (100% Pass)
```bash
python test_server.py
```

---

## 🛡️ Security Guardrails
1. **Read-Only Enforcement**: Rejects any queries containing `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, or `EXEC`.
2. **Table Name Sanitization**: PRAGMA queries enforce strict alphanumeric regex to prevent injection in table inspection.
3. **Result Clamping**: Queries are hard-limited to 100 rows to prevent memory exhaustion or token blowing on the LLM client.

---

## 💼 Interview Talking Points (FAANG / Amazon SDE)

If asked about this project in an interview:
* *"I built this MCP server to solve the problem of safely giving autonomous AI agents access to enterprise databases. Instead of giving LLMs direct raw credentials, the MCP Data Bridge acts as a secure intermediary layer. It exposes schema discovery and safe read-only query execution, with Pydantic validation and regex guardrails that prevent destructive SQL operations or prompt injection attempts."*
