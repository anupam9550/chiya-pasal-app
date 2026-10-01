import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# DB_FILE define गरिएको छ
DB_FILE = "chiya_pasal.db"

app = FastAPI(title="AnupamChiya Pasal API")

# CORS Setup (Vercel Frontend को लागि)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def init_user_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pin TEXT UNIQUE,
            name TEXT,
            role TEXT
        )
    ''')
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO users (pin, name, role) VALUES (?, ?, ?)", [
            ("9999", "Admin", "admin"),
            ("1111", "Ram", "staff"),
            ("2222", "Sita", "staff")
        ])
    conn.commit()
    conn.close()

init_user_db()

class LoginRequest(BaseModel):
    pin: str

@app.get("/")
def home():
    return {"message": "Welcome to Chiya Pasal ☕"}

@app.post("/login")
@app.post("/api/login")
def login(req: LoginRequest):
    users = {
        "9999": {"name": "Admin", "role": "admin"},
        "1111": {"name": "Ram", "role": "staff"},
        "2222": {"name": "Sita", "role": "staff"},
    }
    if req.pin in users:
        return {"status": "success", "user": users[req.pin]}
    raise HTTPException(status_code=400, detail="Invalid PIN")