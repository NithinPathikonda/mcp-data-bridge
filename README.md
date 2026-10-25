# MCP Data Bridge ⚡

[![CI Test Suite](https://github.com/NithinPathikonda/mcp-data-bridge/actions/workflows/ci.yml/badge.svg)](https://github.com/NithinPathikonda/mcp-data-bridge/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Model Context Protocol](https://img.shields.io/badge/MCP-Compatible-emerald.svg)](https://modelcontextprotocol.io/)

> **Secure Model Context Protocol (MCP) Database Gateway for Autonomous AI Agents** with built-in runtime query guardrails, schema discovery, and interactive developer playground.

---

## 🎯 What is MCP Data Bridge?

Autonomous AI agents (such as **Claude, Gemini, OpenAI Assistants, or LangGraph workflows**) frequently require direct access to operational databases. However, granting LLMs direct connection credentials presents catastrophic security risks:
* **Prompt Injection Attacks**: An adversary can trick an agent into executing `DROP TABLE` or mutating financial data.
* **Token Bloat**: Large unstructured table dumps blow the model's context window.
* **Schema Hallucinations**: Agents guessing table or column names without structured discovery.

**`MCP Data Bridge` solves this** by acting as a hardened intermediary layer following Anthropic's open **Model Context Protocol (MCP)** specification.

```
┌──────────────────────────────────────────────┐
│       Autonomous AI Agents & Clients         │
│   (Claude Desktop, Cursor, Custom Agents)    │
└──────────────────────┬───────────────────────┘
                       │ JSON-RPC 2.0 (STDIO / REST)
                       ▼
┌────────────────────────────────────────────────────────┐
│                   MCP DATA BRIDGE                      │
│                                                        │
│  🔧 Tool: list_tables()                                │
│     └─ Discovers active database tables                │
│                                                        │
│  🔧 Tool: describe_table(table_name)                   │
│     └─ Schema inspection & PRAGMA regex sanitization   │
│                                                        │
│  🔧 Tool: execute_query(sql)                           │
│     ├─ Pydantic input validation                       │
│     ├─ Strict Read-Only Guardrail (SELECT only)        │
│     ├─ Prohibited Keyword Interceptor (DROP/DELETE...) │
│     └─ Hard result limit clamping (Max 100 rows)       │
└──────────────────────┬─────────────────────────────────┘
                       │ Parameterized Safe Query
                       ▼
┌──────────────────────────────────────────────┐
│             Enterprise Database              │
│       (SQLite, PostgreSQL, AWS RDS)          │
└──────────────────────────────────────────────┘
```

---

## ✨ Features

- **Standard MCP Compliant**: Implements the official Model Context Protocol JSON-RPC specification. Compatible out of the box with **Claude Desktop**, **Cursor**, and custom agents.
- **Strict Read-Only Guardrails**: Regex-powered gatekeeper blocks any mutation keywords (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `EXEC`).
- **Interactive Web Playground**: Includes a dark-mode visual explorer to inspect schemas and test query safety in real-time.
- **Autonomous Agent Simulator**: Pre-built script demonstrating an end-to-end multi-turn agent reasoning loop with prompt-injection interception.
- **Zero-Config Seed Database**: Includes automated enterprise database generator (`customers`, `products`, `orders`).
- **Production Ready**: Fully dockerized with unit test suite running on GitHub Actions.

---

## 🚀 Quickstart

### 1. Installation

```bash
git clone https://github.com/NithinPathikonda/mcp-data-bridge.git
cd mcp-data-bridge

# Install minimal dependencies
pip install -r requirements.txt
```

### 2. Run Autonomous Agent Simulation
Watch an AI agent explore the database, run multi-table analytics, and attempt a simulated prompt-injection attack that gets blocked:
```bash
python agent_demo.py
```

### 3. Launch Interactive Web Playground
Explore the database visually and test guardrails directly at **[http://localhost:8500](http://localhost:8500)**:
```bash
python web_ui.py
```

### 4. Run Unit Test Suite
```bash
python test_server.py
```

---

## 🤖 Claude Desktop & Cursor Integration

To expose this database directly to **Claude Desktop**, add this server to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "enterprise-data-bridge": {
      "command": "python",
      "args": [
        "/ABSOLUTE/PATH/TO/mcp-data-bridge/server.py",
        "--stdio"
      ]
    }
  }
}
```

Now, ask Claude: *"What tables do I have in the database?"* or *"Who are my top 3 customers by revenue?"*, and Claude will automatically call your tools!

---

## 🐳 Docker Deployment

Run the complete containerized stack:

```bash
docker compose up --build
```
The web playground will be available at `http://localhost:8500`.

---

## 💼 System Design & Interview Talking Points

If asked about this project during a technical or system design interview:

> *"At HPE and in my independent work, I recognized that giving autonomous LLMs unrestricted database access is an anti-pattern. I designed `mcp-data-bridge` using the Model Context Protocol to serve as an air-gapped proxy. It provides structured schema discovery (`list_tables`, `describe_table`) and read-only query execution (`execute_query`). It implements Pydantic runtime validation, sanitized table regexes, and a zero-trust guardrail that drops any destructive mutations or prompt-injected SQL before reaching the database engine."*

---

## 📄 License
Distributed under the [MIT License](LICENSE). Copyright © 2026 Nithin Pathikonda.
