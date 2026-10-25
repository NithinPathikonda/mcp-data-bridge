"""
MCP Data Bridge Interactive Web Playground.
Provides a local visual dashboard to explore database schemas, execute read queries,
and test runtime security guardrails against destructive SQL operations.
"""

import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn
from server import bridge

app = FastAPI(title="MCP Data Bridge Explorer", version="1.0.0")

class QueryBody(BaseModel):
    sql: str
    limit: int = 50

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MCP Data Bridge | Explorer & Guardrail Playground</title>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #090d16;
      --surface: #111827;
      --card: #162032;
      --border: #1f293d;
      --primary: #3b82f6;
      --accent: #10b981;
      --danger: #ef4444;
      --text: #f8fafc;
      --muted: #94a3b8;
    }
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Plus Jakarta Sans', sans-serif; background: var(--bg); color: var(--text); padding: 30px; }
    .container { max-width: 1100px; margin: 0 auto; }
    header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 20px; margin-bottom: 25px; }
    h1 { font-size: 24px; font-weight: 700; color: var(--text); }
    .badge { background: rgba(59, 130, 246, 0.15); color: var(--primary); padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; border: 1px solid rgba(59, 130, 246, 0.3); }
    .grid { display: grid; grid-template-columns: 320px 1fr; gap: 20px; }
    .panel { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 20px; }
    .panel-title { font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; color: var(--muted); margin-bottom: 15px; }
    .table-item { background: var(--card); border: 1px solid var(--border); border-radius: 6px; padding: 10px 14px; margin-bottom: 8px; cursor: pointer; transition: all 0.2s; }
    .table-item:hover { border-color: var(--primary); transform: translateX(3px); }
    .table-name { font-weight: 600; font-size: 14px; }
    textarea { width: 100%; height: 120px; background: #06090e; border: 1px solid var(--border); border-radius: 6px; padding: 12px; color: #a5f3fc; font-family: 'JetBrains Mono', monospace; font-size: 13px; resize: none; margin-bottom: 12px; }
    textarea:focus { outline: none; border-color: var(--primary); }
    .buttons { display: flex; gap: 10px; margin-bottom: 15px; }
    button { background: var(--primary); color: white; border: none; padding: 9px 16px; border-radius: 6px; font-weight: 600; font-size: 13px; cursor: pointer; transition: background 0.2s; }
    button:hover { background: #2563eb; }
    button.danger-btn { background: rgba(239, 68, 68, 0.15); color: var(--danger); border: 1px solid rgba(239, 68, 68, 0.4); }
    button.danger-btn:hover { background: var(--danger); color: white; }
    pre { background: #06090e; border: 1px solid var(--border); border-radius: 6px; padding: 14px; color: #e2e8f0; font-family: 'JetBrains Mono', monospace; font-size: 12px; overflow-x: auto; max-height: 380px; }
    .schema-view { background: #06090e; border: 1px solid var(--border); border-radius: 6px; padding: 10px; margin-top: 10px; font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--muted); display: none; }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <h1>MCP Data Bridge</h1>
        <p style="color: var(--muted); font-size: 13px; margin-top: 4px;">Model Context Protocol Tool Server with Safety Guardrails</p>
      </div>
      <span class="badge">STDIO & REST Protocol Ready</span>
    </header>

    <div class="grid">
      <div class="panel">
        <div class="panel-title">Available Tables</div>
        <div id="table-list">Loading tables...</div>
        <div id="schema-box" class="schema-view"></div>
      </div>

      <div class="panel">
        <div class="panel-title">Query Execution & Guardrail Playground</div>
        <textarea id="sql-input">SELECT c.name, c.tier, SUM(o.total_amount) as total_spent
FROM customers c
JOIN orders o ON c.id = o.customer_id
GROUP BY c.id
ORDER BY total_spent DESC;</textarea>
        
        <div class="buttons">
          <button onclick="runQuery()">▶ Execute Safe Query</button>
          <button class="danger-btn" onclick="testAttack()">⚠️ Test Guardrail (DROP TABLE)</button>
        </div>

        <div class="panel-title" style="margin-top: 20px;">Tool Result</div>
        <pre id="output-box">// Results will appear here...</pre>
      </div>
    </div>
  </div>

  <script>
    async function loadTables() {
      const res = await fetch('/api/tables');
      const data = await res.json();
      const listEl = document.getElementById('table-list');
      listEl.innerHTML = '';
      data.tables.forEach(t => {
        const item = document.createElement('div');
        item.className = 'table-item';
        item.innerHTML = `<div class="table-name">📄 ${t}</div><div style="font-size: 11px; color: var(--muted); margin-top: 2px;">Click to inspect schema</div>`;
        item.onclick = () => loadSchema(t);
        listEl.appendChild(item);
      });
    }

    async function loadSchema(table) {
      const res = await fetch(`/api/schema/${table}`);
      const data = await res.json();
      const box = document.getElementById('schema-box');
      box.style.display = 'block';
      box.innerHTML = `<strong style="color: var(--primary);">Table: ${table}</strong><br>` + 
        data.columns.map(c => `• ${c.name} (${c.type}) ${c.primary_key ? '[PK]' : ''}`).join('<br>');
    }

    async function runQuery() {
      const sql = document.getElementById('sql-input').value;
      const box = document.getElementById('output-box');
      box.textContent = 'Executing query via MCP Data Bridge...';
      const res = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sql })
      });
      const data = await res.json();
      box.textContent = JSON.stringify(data, null, 2);
    }

    function testAttack() {
      document.getElementById('sql-input').value = 'DROP TABLE customers; -- Attempting malicious schema deletion';
      runQuery();
    }

    loadTables();
  </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE

@app.get("/api/tables")
async def get_tables():
    return bridge.list_tables()

@app.get("/api/schema/{table_name}")
async def get_schema(table_name: str):
    return bridge.describe_table(table_name)

@app.get("/api/health")
async def get_health():
    return bridge.get_system_health()

@app.post("/api/query")
async def execute_query_endpoint(body: QueryBody):
    return bridge.execute_query(body.sql, body.limit)

if __name__ == "__main__":
    print("🚀 Starting MCP Data Bridge Playground on http://127.0.0.1:8500")
    uvicorn.run(app, host="127.0.0.1", port=8500)
