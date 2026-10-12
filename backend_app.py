import os
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI(title="Justitia Law Firm - Integrated Professional Version")

# تفعيل الـ CORS لتأمين الاتصالات من أي شبكة
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
    # جدول الحسابات النظيف بدون اشتراكات
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lawyers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)
    # جدول الموكلين والقضايا والحسابات المالية
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

# نماذج البيانات (Pydantic Models)
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

# --- بوابات النظام البرمجية (API Endpoints) ---

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

# --- تشغيل واجهة الموقع المباشرة من السيرفر لتخطي الحظر وتغيير الـ IP ---
@app.get("/", response_class=HTMLResponse)
def serve_home_page():
    return """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Justitia Law Firm SaaS - اليمن</title>
        <script src="https://jsdelivr.net"></script>
    </head>
    <body class="bg-gray-100 font-sans min-h-screen pb-10">

        <!-- شاشة الدخول وإنشاء الحساب -->
        <div id="auth-screen" class="max-w-md mx-auto mt-10 p-6 bg-white rounded-xl shadow-lg border border-gray-200">
            <div class="text-center mb-6">
                <h1 class="text-2xl font-bold text-blue-900">Justitia Pro v4.0 💼</h1>
                <p class="text-emerald-600 text-sm mt-1 font-bold">منصة المحاماة اليمنية الذكية - نظام التخزين السحابي الدائم</p>
            </div>
            <div class="space-y-4">
                <input id="username" type="text" placeholder="اسم المستخدم للمكتب" class="w-full p-3 border rounded-lg text-right focus:outline-blue-900">
                <input id="password" type="password" placeholder="كلمة مرور الحساب" class="w-full p-3 border rounded-lg text-right focus:outline-blue-900">
                <button onclick="handleAuth('login')" class="w-full bg-blue-900 hover:bg-blue-950 text-white p-3 rounded-lg font-bold transition cursor-pointer">تسجيل الدخول</button>
                <button onclick="handleAuth('register')" class="w-full bg-emerald-600 hover:bg-emerald-700 text-white p-3 rounded-lg font-bold transition cursor-pointer">إنشاء حساب جديد للمكتب (مجاناً)</button>
            </div>
        </div>

        <!-- لوحة التحكم الرئيسية المتجاوبة -->
        <div id="main-app" class="hidden max-w-xl mx-auto px-4 mt-6">
            <div id="app-content" class="space-y-6">
                <div class="flex justify-between items-center bg-blue-900 text-white p-4 rounded-xl shadow-md">
                    <span id="welcome-msg" class="font-bold text-sm">مكتب المحاماة الرقمي ⚖️</span>
                    <button onclick="logout()" class="text-xs bg-red-600 hover:bg-red-700 px-3 py-1 rounded transition cursor-pointer">خروج</button>
                </div>

                <!-- نموذج إضافة قضية وموكل -->
                <div class="bg-white p-5 rounded-xl shadow border space-y-3 text-right">
                    <h3 class="font-bold text-blue-900 border-b pb-2">➕ تسجيل موكل وقضية جديدة</h3>
                    <input id="c-name" type="text" placeholder="اسم الموكل كاملاً" class="w-full p-2 border rounded-lg text-sm">
                    <input id="c-phone" type="text" placeholder="رقم هاتف الموكل" class="w-full p-2 border rounded-lg text-sm">
                    <input id="c-id" type="text" placeholder="رقم الهوية الوطنية / جواز السفر" class="w-full p-2 border rounded-lg text-sm">
                    <textarea id="c-case" placeholder="تفاصيل ومعطيات النزاع القانوني..." class="w-full p-2 border rounded-lg h-20 text-sm"></textarea>
                    <div class="grid grid-cols-3 gap-2">
                        <input id="c-date" type="text" placeholder="تاريخ الجلسة القادمة" class="p-2 border rounded-lg text-xs">
                        <input id="c-total" type="number" placeholder="إجمالي الأتعاب" class="p-2 border rounded-lg text-xs">
                        <input id="c-paid" type="number" placeholder="المبلغ المقدم" class="p-2 border rounded-lg text-xs">
                    </div>
                    <button onclick="addNewClient()" class="w-full bg-blue-800 hover:bg-blue-900 text-white font-bold p-2.5 rounded-lg text-sm transition cursor-pointer">حفظ السجل الشامل في قاعدة البيانات</button>
                </div>

                <!-- أرشيف المكتب المالي والقانوني -->
                <div class="bg-white p-5 rounded-xl shadow border text-right">
                    <h3 class="font-bold text-blue-900 mb-3 border-b pb-2">📁 أرشيف القضايا والحسابات والذمم المالية</h3>
                    <div id="clients-list" class="space-y-3"></div>
                </div>
            </div>
        </div>

        <script>
            // بما أن الواجهة تعمل من نفس السيرفر، فإن الرابط يتم تحديده ديناميكياً وتلقائياً ليتوافق مع أي مكان أونلاين
            const API_URL = window.location.origin;

            let currentLawyerId = localStorage.getItem("lawyer_id");
            let loggedInUser = localStorage.getItem("current_user");

            if (currentLawyerId && loggedInUser) {
                showApp();
                fetchClientsArchive();
            }

            async function handleAuth(type) {
                const user = document.getElementById("username").value.trim();
                const pass = document.getElementById("password").value.trim();
                if(!user || !pass) return alert("فضلاً املأ كافة الحقول!");

                const endpoint = type === 'register' ? '/api/register' : '/api/login';

                try {
                    const response = await fetch(`${API_URL}${endpoint}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ username: user, password: pass })
                    });

                    const data = await response.json();
                    if (!response.ok) return alert(data.detail || "بيانات الدخول غير صحيحة");

                    if (type === 'register') {
                        alert(data.message);
                    }

                    localStorage.setItem("lawyer_id", data.lawyer_id);
                    localStorage.setItem("current_user", user);
                    currentLawyerId = data.lawyer_id;
                    loggedInUser = user;

                    showApp();
