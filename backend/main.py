from fastapi import FastAPI, HTTPException, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
import csv
import io
from datetime import datetime

app = FastAPI(title="Anupam Chiya Pasal API")

# フロントエンドからのリクエストを許可するCORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_NAME = "chiya_pasal.db"

# --- データベース初期化 ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 商品テーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT NOT NULL,
            is_available INTEGER DEFAULT 1
        )
    ''')
    
    # 注文テーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            customer_phone TEXT,
            customer_address TEXT,
            order_type TEXT,
            table_number TEXT,
            payment_method TEXT,
            payment_status TEXT,
            notes TEXT,
            discount REAL DEFAULT 0,
            staff_name TEXT,
            subtotal REAL DEFAULT 0,
            total_price REAL DEFAULT 0,
            status TEXT DEFAULT 'Pending',
            created_at TEXT
        )
    ''')
    
    # 注文明細テーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product_id INTEGER,
            product_name TEXT,
            quantity INTEGER,
            price REAL,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    ''')
    
    # 原材料在庫テーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ingredients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            min_threshold REAL DEFAULT 2.0
        )
    ''')
    
    # 経費テーブル
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            created_at TEXT
        )
    ''')
    
    # 初期データ（サンプルメニュー）の挿入
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        sample_products = [
            ("Milk Tea", 25.0, "Tea", 1),
            ("Black Tea", 15.0, "Tea", 1),
            ("Masala Tea", 30.0, "Tea", 1),
            ("Coffee", 50.0, "Beverage", 1),
            ("Samosa", 25.0, "Snacks", 1),
            ("Pakoda", 40.0, "Snacks", 1)
        ]
        cursor.executemany("INSERT INTO products (name, price, category, is_available) VALUES (?, ?, ?, ?)", sample_products)

    # 初期データ（サンプル原材料）の挿入
    cursor.execute("SELECT COUNT(*) FROM ingredients")
    if cursor.fetchone()[0] == 0:
        sample_ingredients = [
            ("Milk", 10.0, "Liter", 3.0),
            ("Tea Powder", 5.0, "KG", 1.0),
            ("Sugar", 8.0, "KG", 2.0)
        ]
        cursor.executemany("INSERT INTO ingredients (name, quantity, unit, min_threshold) VALUES (?, ?, ?, ?)", sample_ingredients)

    conn.commit()
    conn.close()

init_db()

# --- リクエスト/レスポンス用 Pydantic モデル ---
class LoginReq(BaseModel):
    pin: str

class OrderItemInput(BaseModel):
    product_id: int
    quantity: int

class CreateOrderReq(BaseModel):
    customer_name: str
    customer_phone: str
    customer_address: Optional[str] = ""
    order_type: str
    table_number: Optional[str] = ""
    payment_method: str
    payment_status: str
    notes: Optional[str] = ""
    discount: Optional[float] = 0.0
    staff_name: Optional[str] = "Admin"
    items: List[OrderItemInput]

class StatusUpdateReq(BaseModel):
    status: str

class PaymentUpdateReq(BaseModel):
    payment_status: str

class IngredientReq(BaseModel):
    name: str
    quantity: float
    unit: str
    min_threshold: float

class ExpenseReq(BaseModel):
    title: str
    amount: float

# --- エンドポイント実装 ---

# 1. ログイン認証
@app.post("/login")
def login(req: LoginReq):
    pins = {
        "9999": {"name": "Admin", "role": "Admin"},
        "1111": {"name": "Ram", "role": "Staff"},
        "2222": {"name": "Sita", "role": "Staff"}
    }
    if req.pin in pins:
        return {"status": "success", **pins[req.pin]}
    raise HTTPException(status_code=400, detail="無効なPINコードです")

# 2. ダッシュボード統計
@app.get("/stats")
def get_stats():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("SELECT COUNT(*) FROM orders WHERE created_at LIKE ?", (f"{today}%",))
    today_orders = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(total_price) FROM orders WHERE created_at LIKE ? AND payment_status = 'Paid'", (f"{today}%",))
    today_revenue = cursor.fetchone()[0] or 0.0

    cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'Pending'")
    pending_orders = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(total_price) FROM orders WHERE payment_status = 'Paid'")
    total_revenue = cursor.fetchone()[0] or 0.0

    cursor.execute('''
        SELECT product_name, SUM(quantity) as total_qty 
        FROM order_items 
        GROUP BY product_name 
        ORDER BY total_qty DESC LIMIT 1
    ''')
    top_product = cursor.fetchone()
    top_selling_product = top_product[0] if top_product else "N/A"

    conn.close()
    return {
        "today_orders": today_orders,
        "today_revenue": today_revenue,
        "pending_orders": pending_orders,
        "total_revenue": total_revenue,
        "top_selling_product": top_selling_product
    }

# 3. 商品一覧・在庫切替
@app.get("/products")
def get_products():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price, category, is_available FROM products")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "price": r[2], "category": r[3], "is_available": bool(r[4])} for r in rows]

@app.put("/products/{product_id}/toggle")
def toggle_product(product_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET is_available = CASE WHEN is_available = 1 THEN 0 ELSE 1 END WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return {"message": "Toggled"}

# 4. 注文管理 (一覧・新規作成・詳細・状態更新)
@app.get("/orders")
def get_orders():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, customer_name, customer_phone, customer_address, order_type, table_number, payment_method, payment_status, notes, discount, staff_name, subtotal, total_price, status, created_at FROM orders ORDER BY id DESC")
    orders = cursor.fetchall()
    
    result = []
    for o in orders:
        order_id = o[0]
        cursor.execute("SELECT product_id, product_name, quantity, price FROM order_items WHERE order_id = ?", (order_id,))
        items = [{"product_id": i[0], "product_name": i[1], "quantity": i[2], "price": i[3]} for i in cursor.fetchall()]
        result.append({
            "id": o[0], "customer_name": o[1], "customer_phone": o[2], "customer_address": o[3],
            "order_type": o[4], "table_number": o[5], "payment_method": o[6], "payment_status": o[7],
            "notes": o[8], "discount": o[9], "staff_name": o[10], "subtotal": o[11],
            "total_price": o[12], "status": o[13], "created_at": o[14], "items": items
        })
    conn.close()
    return result

@app.get("/orders/{order_id}")
def get_order_by_id(order_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, customer_name, customer_phone, customer_address, order_type, table_number, payment_method, payment_status, notes, discount, staff_name, subtotal, total_price, status, created_at FROM orders WHERE id = ?", (order_id,))
    o = cursor.fetchone()
    if not o:
        conn.close()
        raise HTTPException(status_code=404, detail="Order not found")
    
    cursor.execute("SELECT product_id, product_name, quantity, price FROM order_items WHERE order_id = ?", (order_id,))
    items = [{"product_id": i[0], "product_name": i[1], "quantity": i[2], "price": i[3]} for i in cursor.fetchall()]
    conn.close()
    return {
        "id": o[0], "customer_name": o[1], "customer_phone": o[2], "customer_address": o[3],
        "order_type": o[4], "table_number": o[5], "payment_method": o[6], "payment_status": o[7],
        "notes": o[8], "discount": o[9], "staff_name": o[10], "subtotal": o[11],
        "total_price": o[12], "status": o[13], "created_at": o[14], "items": items
    }

@app.post("/orders")
def create_order(req: CreateOrderReq):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    subtotal = 0.0
    items_to_insert = []
    
    for item in req.items:
        cursor.execute("SELECT name, price FROM products WHERE id = ?", (item.product_id,))
        prod = cursor.fetchone()
        if prod:
            p_name, p_price = prod[0], prod[1]
            subtotal += p_price * item.quantity
            items_to_insert.append((item.product_id, p_name, item.quantity, p_price))

    total_price = max(0.0, subtotal - req.discount)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute('''
        INSERT INTO orders (customer_name, customer_phone, customer_address, order_type, table_number, payment_method, payment_status, notes, discount, staff_name, subtotal, total_price, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?)
    ''', (req.customer_name, req.customer_phone, req.customer_address, req.order_type, req.table_number, req.payment_method, req.payment_status, req.notes, req.discount, req.staff_name, subtotal, total_price, created_at))
    
    order_id = cursor.lastrowid

    for item in items_to_insert:
        cursor.execute('''
            INSERT INTO order_items (order_id, product_id, product_name, quantity, price)
            VALUES (?, ?, ?, ?, ?)
        ''', (order_id, item[0], item[1], item[2], item[3]))

    conn.commit()
    conn.close()
    return {"message": "Order created successfully", "order_id": order_id}

@app.put("/orders/{order_id}/status")
def update_order_status(order_id: int, req: StatusUpdateReq):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (req.status, order_id))
    conn.commit()
    conn.close()
    return {"message": "Status updated"}

@app.put("/orders/{order_id}/payment")
def update_payment_status(order_id: int, req: PaymentUpdateReq):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET payment_status = ? WHERE id = ?", (req.payment_status, order_id))
    conn.commit()
    conn.close()
    return {"message": "Payment status updated"}

# 5. 原材料（Raw Inventory）管理
@app.get("/ingredients")
def get_ingredients():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, quantity, unit, min_threshold FROM ingredients")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "quantity": r[2], "unit": r[3], "min_threshold": r[4]} for r in rows]

@app.post("/ingredients")
def add_ingredient(req: IngredientReq):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO ingredients (name, quantity, unit, min_threshold) VALUES (?, ?, ?, ?)",
                   (req.name, req.quantity, req.unit, req.min_threshold))
    conn.commit()
    conn.close()
    return {"message": "Ingredient added"}

@app.put("/ingredients/{ingredient_id}/restock")
def restock_ingredient(ingredient_id: int, added_qty: float = Query(...)):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE ingredients SET quantity = quantity + ? WHERE id = ?", (added_qty, ingredient_id))
    conn.commit()
    conn.close()
    return {"message": "Restocked"}

# 6. 経費（Expense Tracker）管理
@app.get("/expenses")
def get_expenses():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, amount, created_at FROM expenses ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "amount": r[2], "created_at": r[3]} for r in rows]

@app.post("/expenses")
def add_expense(req: ExpenseReq):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO expenses (title, amount, created_at) VALUES (?, ?, ?)", (req.title, req.amount, created_at))
    conn.commit()
    conn.close()
    return {"message": "Expense added"}

@app.delete("/expenses/{expense_id}")
def delete_expense(expense_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()
    return {"message": "Expense deleted"}

# 7. ロイヤリティチェック (Loyalty Badge)
@app.get("/customers/{phone}")
def check_loyalty(phone: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM orders WHERE customer_phone = ?", (phone,))
    count = cursor.fetchone()[0]
    conn.close()

    if count >= 5:
        return {"message": f"👑 VIP顧客 (訪問回数: {count}回) - 10% OFF対象!", "discount_percent": 10, "order_count": count}
    elif count >= 2:
        return {"message": f"🌟 常連様 (訪問回数: {count}回)", "discount_percent": 0, "order_count": count}
    else:
        return {"message": "🆕 ご新規様", "discount_percent": 0, "order_count": count}

# 8. カテゴリ別売上グラフデータ
@app.get("/stats/category-sales")
def get_category_sales():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.category, SUM(oi.quantity * oi.price) as total_sales
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        JOIN orders o ON oi.order_id = o.id
        WHERE o.payment_status = 'Paid'
        GROUP BY p.category
    ''')
    rows = cursor.fetchall()
    conn.close()
    return [{"category": r[0], "total_sales": r[1]} for r in rows]

# 9. ツケ払い（Khata System）管理
@app.get("/khata")
def get_khata():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT customer_name, customer_phone, COUNT(*) as pending_bills, SUM(total_price) as total_due
        FROM orders
        WHERE payment_status = 'Unpaid'
        GROUP BY customer_phone
    ''')
    rows = cursor.fetchall()
    conn.close()
    return [{"customer_name": r[0], "customer_phone": r[1], "pending_bills": r[2], "total_due": r[3]} for r in rows]

@app.put("/khata/{phone}/clear")
def clear_khata(phone: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET payment_status = 'Paid' WHERE customer_phone = ? AND payment_status = 'Unpaid'", (phone,))
    conn.commit()
    conn.close()
    return {"message": "Khata cleared"}

# 10. Excel / CSV エクスポート
@app.get("/export/orders-csv")
def export_csv():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, customer_name, customer_phone, order_type, table_number, total_price, payment_method, payment_status, status, created_at FROM orders")
    rows = cursor.fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Order ID", "Customer Name", "Phone", "Order Type", "Table", "Total Price", "Payment Method", "Payment Status", "Order Status", "Created At"])
    writer.writerows(rows)

    return Response(content=output.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=orders.csv"})