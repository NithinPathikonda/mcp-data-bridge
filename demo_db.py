"""
Sample database initializer for MCP Data Bridge.
Creates a realistic enterprise SQLite database with customers, orders, and products.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "enterprise.db"

def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        tier TEXT DEFAULT 'Standard',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL,
        stock INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        total_amount REAL NOT NULL,
        status TEXT DEFAULT 'Completed',
        order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    );
    """)

    # Populate seed data if empty
    cursor.execute("SELECT COUNT(*) FROM customers")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("""
            INSERT INTO customers (name, email, tier) VALUES (?, ?, ?)
        """, [
            ("Alice Smith", "alice@enterprise.com", "Enterprise"),
            ("Bob Jones", "bob@startup.io", "Premium"),
            ("Charlie Brown", "charlie@tech.dev", "Standard"),
            ("Diana Prince", "diana@global.org", "Enterprise")
        ])

        cursor.executemany("""
            INSERT INTO products (name, category, price, stock) VALUES (?, ?, ?, ?)
        """, [
            ("Cloud Compute Instance", "Infrastructure", 120.00, 500),
            ("Managed Vector Database", "AI Services", 250.00, 100),
            ("Distributed Storage Tier", "Storage", 45.00, 1000),
            ("API Gateway Access", "Networking", 80.00, 250)
        ])

        cursor.executemany("""
            INSERT INTO orders (customer_id, product_id, quantity, total_amount, status) VALUES (?, ?, ?, ?, ?)
        """, [
            (1, 1, 2, 240.00, "Completed"),
            (1, 2, 1, 250.00, "Completed"),
            (2, 3, 5, 225.00, "Completed"),
            (3, 4, 1, 80.00, "Processing"),
            (4, 1, 10, 1200.00, "Completed")
        ])

        conn.commit()
        print(f"✅ Sample enterprise database initialized at: {DB_PATH}")
    else:
        print(f"ℹ️ Database already exists with data at: {DB_PATH}")

    conn.close()

if __name__ == "__main__":
    init_database()
