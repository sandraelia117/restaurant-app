import sqlite3

conn = sqlite3.connect("pizza.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS PIZZA_SALES (
    pizza_id INTEGER,
    order_id INTEGER,
    pizza_name_id INTEGER,
    quantity INTEGER,
    order_date TEXT,
    order_time TEXT,
    unit_price REAL,
    total_price REAL,
    pizza_size TEXT,
    pizza_category TEXT,
    pizza_ingredients TEXT,
    pizza_name TEXT
)
""")

conn.commit()
conn.close()

print("Database created successfully!")