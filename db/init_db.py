import sqlite3
import os
import random
from datetime import datetime, timedelta

# Database path
DB_DIR = os.path.dirname(os.path.abspath(__file__))
# Ensure path uses proper separators
DB_PATH = os.path.join(DB_DIR, "demo.sqlite")

def init_db():
    print(f"Initializing database at: {DB_PATH}")
    
    # Ensure directory exists
    os.makedirs(DB_DIR, exist_ok=True)
    
    # Connect
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Create Tables
    print("Creating tables...")
    cursor.execute("DROP TABLE IF EXISTS orders")
    cursor.execute("DROP TABLE IF EXISTS customers")
    
    cursor.execute("""
    CREATE TABLE customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        city TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    cursor.execute("""
    CREATE TABLE orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        amount REAL NOT NULL,
        status TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    )
    """)
    
    # 2. Seed Data
    print("Seeding data...")
    
    # Synthetic Data
    cities = ["Lahore", "Karachi", "Islamabad", "Multan", "Faisalabad", "Rawalpindi", "Peshawar", "Quetta"]
    first_names = ["Ali", "Bilal", "Zara", "Sara", "Ahmed", "Omer", "Fatima", "Ayesha", "Hassan", "Zainab", "Usman", "Hamza"]
    last_names = ["Khan", "Ahmed", "Ali", "Butt", "Sheikh", "Malik", "Raja", "Chaudhry"]
    statuses = ["Pending", "Completed", "Cancelled", "Shipped"]
    
    # Generate Customers
    customers_data = []
    for _ in range(50):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        city = random.choice(cities)
        created_at = datetime.now() - timedelta(days=random.randint(1, 1000))
        customers_data.append((name, city, created_at))
        
    cursor.executemany("INSERT INTO customers (name, city, created_at) VALUES (?, ?, ?)", customers_data)
    
    # Retrieve customer IDs to maintain foreign key integrity
    cursor.execute("SELECT id FROM customers")
    # fetchall returns tuples like (1,), (2,)
    customer_ids = [row[0] for row in cursor.fetchall()]
    
    # Generate Orders
    orders_data = []
    for _ in range(200):
        cid = random.choice(customer_ids)
        amount = round(random.uniform(100.0, 10000.0), 2)
        status = random.choice(statuses)
        created_at = datetime.now() - timedelta(days=random.randint(1, 365))
        orders_data.append((cid, amount, status, created_at))
        
    cursor.executemany("INSERT INTO orders (customer_id, amount, status, created_at) VALUES (?, ?, ?, ?)", orders_data)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_db()
