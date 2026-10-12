import os
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Justitia Law Firm API - Professional Free Version")

# تفعيل الـ CORS الكامل للسماح للواجهة بالاتصال بالسيرفر السحابي من أي مكان
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "lawfirm_saas.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # جدول الحسابات
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lawyers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)
    # جدول الموكلين والقضايا والبيانات المالية
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lawyer_id INTEGER,
        name TEXT,
        phone TEXT,
        id_num TEXT,
        case_text TEXT,
        session_date TEXT,
        total_fees REAL,
        paid_amount REAL,
        remaining_amount REAL,
        FOREIGN KEY(lawyer_id) REFERENCES lawyers(id)
    )
    """)
    conn.commit()
    conn.close()

init_db()

class LawyerAuth(BaseModel):
    username: str
    password: str

class ClientData(BaseModel):
    lawyer_id: int
    name: str
    phone: str
    id_num: str
    case_text: str
    session_date: str
    total_fees: float
    paid_amount: float

@app.post("/api/register")
def register_lawyer(auth: LawyerAuth):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO lawyers (username, password) VALUES (?, ?)", (auth.username, auth.password))
        conn.commit()
        lawyer_id = cursor.lastrowid
        return {"status": "success", "lawyer_id": lawyer_id, "message": "تم إنشاء حساب مكتبك بنجاح!"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="اسم المستخدم هذا مسجل مسبقاً!")
    finally:
        conn.close()

@app.post("/api/login")
def login_lawyer(auth: LawyerAuth):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM lawyers WHERE username=? AND password=?", (auth.username, auth.password))
    user = cursor.fetchone()
    conn.close()

    if not user:
        raise HTTPException(status_code=401, detail="بيانات الدخول غير صحيحة!")

    return {"status": "success", "lawyer_id": user[0]}

@app.post("/api/add-client")
def add_client(client: ClientData):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM lawyers WHERE id=?", (client.lawyer_id,))
    if not cursor.fetchone(): 
        conn.close()
        raise HTTPException(status_code=404, detail="المحامي غير مسجل")

    remaining = client.total_fees - client.paid_amount
    cursor.execute(
        "INSERT INTO clients (lawyer_id, name, phone, id_num, case_text, session_date, total_fees, paid_amount, remaining_amount) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (client.lawyer_id, client.name, client.phone, client.id_num, client.case_text, client.session_date, client.total_fees, client.paid_amount, remaining)
    )
    conn.commit()
    conn.close()
    return {"status": "success", "message": "تم حفظ بيانات الموكل وحساب الميزانية بنجاح"}

@app.get("/api/clients/{lawyer_id}")
def get_clients(lawyer_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name, phone, id_num, case_text, session_date, total_fees, paid_amount, remaining_amount FROM clients WHERE lawyer_id=?", (lawyer_id,))
    rows = cursor.fetchall()
    conn.close()

    clients = []
    for r in rows:
        clients.append({
            "name": r[0], "phone": r[1], "id_num": r[2], "case_text": r[3],
            "session_date": r[4], "total_fees": r[5], "paid_amount": r[6], "remaining_amount": r[7]
        })
    return {"status": "success", "clients": clients}
