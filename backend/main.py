import hashlib
import csv
import io
import sqlite3
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# १. मुख्य Configuration र Database File Name
DB_FILE = "chiya_pasal.db"

# २. FastAPI App र CORS Setup
app = FastAPI(title="Anupam Chiya Pasal API")

# CORS Setup (Vercel Frontend को लागि)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------
# Helper Functions
# ----------------
def get_db():
    conn = sqlite3.connect(DB_FILE, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn

def send_sms_alert(mobile_number: str, message: str):
    print(f"📱 [SMS Sent to {mobile_number}]: {message}")

# ----------------
# Database Init
# ----------------
def init_user_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        admin_pass = hashlib.sha256("admin123".encode()).hexdigest()
        staff_pass = hashlib.sha256("staff123".encode()).hexdigest()
        cursor.execute("INSERT INTO users (username, password, role) VALUES ('admin', ?, 'Admin')", (admin_pass,))
        cursor.execute("INSERT INTO users (username, password, role) VALUES ('staff', ?, 'Staff')", (staff_pass,))
    conn.commit()
    conn.close()

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, price REAL, category TEXT, is_available INTEGER DEFAULT 1
        )''')
        
        cursor.execute("SELECT COUNT(*) FROM products")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT INTO products (name, price, category) VALUES (?, ?, ?)", [
                ("Milk Chiya", 30, "Tea"),
                ("Black Chiya", 20, "Tea"),
                ("Masala Chiya", 40, "Tea"),
                ("Samosa", 25, "Snacks"),
                ("Momo (Buff)", 120, "Snacks")
            ])

        cursor.execute('''CREATE TABLE IF NOT EXISTS ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, quantity REAL, unit TEXT, min_threshold REAL
        )''')
        cursor.execute("SELECT COUNT(*) FROM ingredients")
        if cursor.fetchone()[0] == 0:
            cursor.executemany("INSERT INTO ingredients (name, quantity, unit, min_threshold) VALUES (?, ?, ?, ?)", [
                ("Milk", 10.0, "Liter", 3.0),
                ("Tea Leaves", 2.5, "KG", 0.5),
                ("Sugar", 5.0, "KG", 1.0)
            ])

        cursor.execute('''CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT, customer_phone TEXT, customer_address TEXT,
            order_type TEXT, table_number TEXT, payment_method TEXT,
            payment_status TEXT, notes TEXT, discount REAL, subtotal REAL,
            total_price REAL, status TEXT, created_at TEXT, staff_name TEXT
        )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER, product_id INTEGER, product_name TEXT,
            price REAL, quantity INTEGER
        )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, amount REAL, created_at TEXT
        )''')

init_user_db()
init_db()

USERS = {
    "9999": {"name": "Admin Owner", "role": "Admin"},
    "1111": {"name": "Staff Ram", "role": "Staff"},
    "2222": {"name": "Staff Sita", "role": "Staff"}
}

# ----------------
# Pydantic Schemas
# ----------------
class LoginSchema(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    pin: str

class SelfOrderCreateSchema(BaseModel):
    customer_name: str
    customer_phone: str
    table_number: str
    notes: Optional[str] = ""
    items: List[dict]

class OrderItemSchema(BaseModel):
    product_id: int
    quantity: int

class OrderCreateSchema(BaseModel):
    customer_name: str
    customer_phone: str
    customer_address: Optional[str] = ""
    order_type: str
    table_number: Optional[str] = ""
    payment_method: str
    payment_status: str
    notes: Optional[str] = ""
    discount: float = 0.0
    staff_name: Optional[str] = "Admin"
    items: List[OrderItemSchema]

class StatusUpdateSchema(BaseModel):
    status: str

class PaymentUpdateSchema(BaseModel):
    payment_status: str

class IngredientCreateSchema(BaseModel):
    name: str
    quantity: float
    unit: str
    min_threshold: float

class ExpenseCreateSchema(BaseModel):
    title: str
    amount: float

# ----------------
# API Endpoints
# ----------------

@app.get("/")
def home():
    return {"message": "Welcome to Anupam Chiya Pasal API ☕"}

# Login (Username & Password)
@app.post("/login/user")
def login_user(req: LoginSchema):
    hashed_pass = hashlib.sha256(req.password.encode()).hexdigest()
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role FROM users WHERE username = ? AND password = ?", (req.username, hashed_pass))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return {"status": "success", "user": {"id": user[0], "username": user[1], "role": user[2]}}
    raise HTTPException(status_code=401, detail="गलत प्रयोगकर्ता वा पासवर्ड!")

# Login (PIN-based)
@app.post("/login")
@app.post("/api/login")
def login_pin(req: LoginRequest):
    if req.pin in USERS:
        user = USERS[req.pin]
        return {"status": "success", "name": user["name"], "role": user["role"]}
    raise HTTPException(status_code=401, detail="Invalid PIN")

@app.get("/products")
def get_products():
    with get_db() as conn:
        rows = conn.execute("SELECT id, name, price, category, is_available FROM products").fetchall()
    return [{"id": r["id"], "name": r["name"], "price": r["price"], "category": r["category"], "is_available": bool(r["is_available"])} for r in rows]

@app.put("/products/{product_id}/toggle")
def toggle_product_availability(product_id: int):
    with get_db() as conn:
        conn.execute("UPDATE products SET is_available = NOT is_available WHERE id = ?", (product_id,))
    return {"status": "success"}

@app.get("/stats")
def get_stats():
    today_str = datetime.now().strftime("%Y-%m-%d")
    with get_db() as conn:
        today_paid = conn.execute(
            "SELECT COUNT(*), SUM(total_price) FROM orders WHERE created_at LIKE ? AND payment_status = 'Paid'", 
            (f"{today_str}%",)
        ).fetchone()
        today_orders_count = today_paid[0] or 0
        today_revenue = today_paid[1] or 0.0

        pending_orders = conn.execute("SELECT COUNT(*) FROM orders WHERE status IN ('Pending', 'Preparing')").fetchone()[0] or 0
        total_revenue = conn.execute("SELECT SUM(total_price) FROM orders WHERE payment_status = 'Paid'").fetchone()[0] or 0.0

        top_item_row = conn.execute("""
            SELECT product_name, SUM(quantity) as total_qty 
            FROM order_items GROUP BY product_name ORDER BY total_qty DESC LIMIT 1
        """).fetchone()
        top_selling = top_item_row["product_name"] if top_item_row else "N/A"

    return {
        "today_orders": today_orders_count,
        "today_revenue": today_revenue,
        "pending_orders": pending_orders,
        "total_revenue": total_revenue,
        "top_selling_product": top_selling
    }

@app.post("/public/order")
def create_self_order(req: SelfOrderCreateSchema):
    subtotal = 0.0
    items_to_save = []

    with get_db() as conn:
        cursor = conn.cursor()
        for item in req.items:
            p_id = item.get("product_id")
            qty = item.get("quantity", 1)
            prod = cursor.execute("SELECT name, price FROM products WHERE id = ?", (p_id,)).fetchone()
            if prod:
                subtotal += (prod["price"] * qty)
                items_to_save.append((p_id, prod["name"], prod["price"], qty))

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO orders (customer_name, customer_phone, customer_address, order_type, table_number,
                                payment_method, payment_status, notes, discount, subtotal, total_price, status, created_at, staff_name)
            VALUES (?, ?, '', 'Dine-in', ?, 'QR/Self', 'Unpaid', ?, 0.0, ?, ?, 'Pending', ?, 'Self-QR')
        """, (req.customer_name, req.customer_phone, req.table_number, req.notes, subtotal, subtotal, created_at))
        
        order_id = cursor.lastrowid

        for item in items_to_save:
            cursor.execute("INSERT INTO order_items (order_id, product_id, product_name, price, quantity) VALUES (?, ?, ?, ?, ?)",
                           (order_id, item[0], item[1], item[2], item[3]))

    sms_msg = f"नमस्ते {req.customer_name}! चिया पसलमा तपाईंको अर्डर (Order #{order_id}) प्राप्त भयो। धन्यवाद!"
    send_sms_alert(req.customer_phone, sms_msg)

    return {"status": "success", "order_id": order_id, "message": "अर्डर सफलतापुर्वक प्राप्त भयो!"}

@app.post("/orders")
def create_order(req: OrderCreateSchema):
    subtotal = 0.0
    items_to_save = []

    with get_db() as conn:
        cursor = conn.cursor()
        for item in req.items:
            prod = cursor.execute("SELECT name, price FROM products WHERE id = ?", (item.product_id,)).fetchone()
            if prod:
                item_total = prod["price"] * item.quantity
                subtotal += item_total
                items_to_save.append((item.product_id, prod["name"], prod["price"], item.quantity))

        total_price = max(0.0, subtotal - req.discount)
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO orders (customer_name, customer_phone, customer_address, order_type, table_number,
                                payment_method, payment_status, notes, discount, subtotal, total_price, status, created_at, staff_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?, ?)
        """, (req.customer_name, req.customer_phone, req.customer_address, req.order_type, req.table_number,
              req.payment_method, req.payment_status, req.notes, req.discount, subtotal, total_price, created_at, req.staff_name))
        
        order_id = cursor.lastrowid

        for item in items_to_save:
            cursor.execute("INSERT INTO order_items (order_id, product_id, product_name, price, quantity) VALUES (?, ?, ?, ?, ?)",
                           (order_id, item[0], item[1], item[2], item[3]))

    return {"id": order_id, "status": "success"}

@app.get("/orders")
def get_orders():
    with get_db() as conn:
        orders_rows = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
        orders = []
        for r in orders_rows:
            item_rows = conn.execute("SELECT product_id, product_name, price, quantity FROM order_items WHERE order_id = ?", (r["id"],)).fetchall()
            items = [{"product_id": i["product_id"], "product_name": i["product_name"], "price": i["price"], "quantity": i["quantity"]} for i in item_rows]

            orders.append({
                "id": r["id"], "customer_name": r["customer_name"], "customer_phone": r["customer_phone"], 
                "customer_address": r["customer_address"], "order_type": r["order_type"], "table_number": r["table_number"], 
                "payment_method": r["payment_method"], "payment_status": r["payment_status"], "notes": r["notes"], 
                "discount": r["discount"], "subtotal": r["subtotal"], "total_price": r["total_price"],
                "status": r["status"], "created_at": r["created_at"], "staff_name": r["staff_name"], "items": items
            })

    return orders

@app.put("/orders/{order_id}/status")
def update_order_status(order_id: int, req: StatusUpdateSchema):
    with get_db() as conn:
        cursor = conn.cursor()
        order_data = cursor.execute("SELECT customer_name, customer_phone FROM orders WHERE id = ?", (order_id,)).fetchone()
        cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (req.status, order_id))

    if order_data and order_data["customer_phone"]:
        c_name = order_data["customer_name"]
        c_phone = order_data["customer_phone"]
        if req.status == "Preparing":
            send_sms_alert(c_phone, f"नमस्ते {c_name}, तपाईंको अर्डर (Order #{order_id}) भान्सामा तयार हुँदैछ ☕")
        elif req.status == "Completed":
            send_sms_alert(c_phone, f"नमस्ते {c_name}, तपाईंको अर्डर (Order #{order_id}) तयार भयो! कृपया लिनुहोला/आनन्द लिनुहोला 🙏")

    return {"status": "success"}

@app.put("/orders/{order_id}/payment")
def update_payment_status(order_id: int, req: PaymentUpdateSchema):
    with get_db() as conn:
        conn.execute("UPDATE orders SET payment_status = ? WHERE id = ?", (req.payment_status, order_id))
    return {"status": "success"}

@app.get("/customers/{phone}")
def check_loyalty(phone: str):
    with get_db() as conn:
        order_count = conn.execute("SELECT COUNT(*) FROM orders WHERE customer_phone = ?", (phone,)).fetchone()[0] or 0
    
    if order_count >= 5:
        return {"message": f"🏆 VIP Customer! ({order_count} अर्डर पुरा)", "discount_percent": 10}
    elif order_count > 0:
        return {"message": f"✨ Regular Customer ({order_count} अर्डर पुरा)", "discount_percent": 0}
    return {"message": "🆕 नयाँ ग्राहक", "discount_percent": 0}

@app.get("/ingredients")
def get_ingredients():
    with get_db() as conn:
        rows = conn.execute("SELECT id, name, quantity, unit, min_threshold FROM ingredients").fetchall()
    return [{"id": r["id"], "name": r["name"], "quantity": r["quantity"], "unit": r["unit"], "min_threshold": r["min_threshold"]} for r in rows]

@app.post("/ingredients")
def add_ingredient(req: IngredientCreateSchema):
    with get_db() as conn:
        conn.execute("INSERT INTO ingredients (name, quantity, unit, min_threshold) VALUES (?, ?, ?, ?)",
                     (req.name, req.quantity, req.unit, req.min_threshold))
    return {"status": "success"}

@app.put("/ingredients/{ing_id}/restock")
def restock_ingredient(ing_id: int, added_qty: float = Query(...)):
    with get_db() as conn:
        conn.execute("UPDATE ingredients SET quantity = quantity + ? WHERE id = ?", (added_qty, ing_id))
    return {"status": "success"}

@app.get("/expenses")
def get_expenses():
    with get_db() as conn:
        rows = conn.execute("SELECT id, title, amount, created_at FROM expenses ORDER BY id DESC").fetchall()
    return [{"id": r["id"], "title": r["title"], "amount": r["amount"], "created_at": r["created_at"]} for r in rows]

@app.post("/expenses")
def add_expense(req: ExpenseCreateSchema):
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        conn.execute("INSERT INTO expenses (title, amount, created_at) VALUES (?, ?, ?)", (req.title, req.amount, created_at))
    return {"status": "success"}

@app.delete("/expenses/{exp_id}")
def delete_expense(exp_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM expenses WHERE id = ?", (exp_id,))
    return {"status": "deleted"}

@app.get("/export/orders-csv")
def export_orders_csv():
    with get_db() as conn:
        rows = conn.execute("SELECT id, created_at, customer_name, customer_phone, order_type, table_number, total_price, payment_method, payment_status, status, staff_name FROM orders").fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Order ID", "Date", "Customer Name", "Phone", "Type", "Table", "Total Price", "Payment Method", "Payment Status", "Status", "Staff"])
    for r in rows:
        writer.writerow(list(r))
    
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=orders_report.csv"}
    )

@app.get("/stats/category-sales")
def get_category_sales():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT p.category, SUM(oi.quantity * oi.price) as total_sales
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            GROUP BY p.category
        """).fetchall()
    return [{"category": r["category"], "total_sales": r["total_sales"]} for r in rows]

@app.get("/khata")
def get_udharo_khata():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT customer_name, customer_phone, COUNT(id) as pending_bills, SUM(total_price) as total_due
        FROM orders 
        WHERE payment_status = 'Unpaid' AND customer_phone != ''
        GROUP BY customer_phone
        ORDER BY total_due DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [{"customer_name": r[0], "customer_phone": r[1], "pending_bills": r[2], "total_due": r[3]} for r in rows]

@app.put("/khata/{phone}/clear")
def clear_udharo(phone: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE orders 
        SET payment_status = 'Paid', payment_method = 'Cash (Khata Cleared)'
        WHERE customer_phone = ? AND payment_status = 'Unpaid'
    """, (phone,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"{phone} को सम्पूर्ण उधारो चुक्ता भयो!"}