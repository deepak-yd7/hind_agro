# 🌿 Hind Agro Products ERP — Complete Folder Structure

```
my_pyqt_project/
│
├── main.py                          ← Entry point. Shows connection setup → login → main app
├── requirements.txt                 ← pip install -r requirements.txt
├── db_config.json                   ← AUTO-CREATED on first run (your DB connection settings)
│                                      Do NOT share — contains your password
│
├── SERVER_SETUP_GUIDE.md            ← Step-by-step guide for network/multi-PC setup
├── README.md                        ← Project overview
│
│
├── backend/                         ── Database layer
│   ├── __init__.py
│   ├── database.py                  ← PostgreSQL connection pool + creates all tables on startup
│   └── db_config.py                 ← Loads/saves db_config.json (server IP, port, password)
│
│
├── models/                          ── Data models (dataclasses)
│   ├── __init__.py
│   └── user_model.py                ← AppUser, Customer, Plant, Seed, Container,
│                                      Order, OrderItem, Invoice
│
│
├── services/                        ── Business logic layer
│   ├── __init__.py
│   ├── auth_service.py              ← Login, logout, session, user management (CRUD)
│   ├── user_service.py              ← CustomerService, PlantService, SeedService,
│   │                                  ContainerService, OrderService, InvoiceService
│   ├── otp_service.py               ← OTP generation, DB storage, Twilio SMS sending
│   ├── pdf_service.py               ← Customer invoice PDF + dispatch slip PDF
│   └── invoice_pdf.py               ← Alternative invoice PDF generator
│
│
├── frontend/                        ── All UI screens
│   ├── __init__.py
│   │
│   ├── connection_setup.py          ← First-run DB connection wizard
│   │                                  (Server vs Client, IP entry, Test Connection)
│   ├── login_window.py              ← Login screen with role badges + Forgot Password link
│   ├── main_window.py               ← Main shell: sidebar nav, role-based page visibility,
│   │                                  Change Password, Logout, server IP indicator
│   └── forgot_password.py          ← 3-step OTP password reset + Change Password dialog
│
│   ├── pages/                       ── One file per page (loaded by main_window based on role)
│   │   ├── __init__.py
│   │   ├── dashboard_page.py        ← Live stats + 4 charts with full date filter bar
│   │   ├── inventory_page.py        ← 3 tabs: Plants (tray/bucket), Seeds, Containers
│   │   ├── customers_page.py        ← Customer list — Add, Edit, Delete
│   │   ├── orders_page.py           ← Place orders, update status, generate PDF invoice
│   │   ├── invoices_page.py         ← Invoice list, Mark Paid, overdue highlighting
│   │   ├── users_page.py            ← User accounts — Add, Disable, Delete (Owner only)
│   │   └── dispatch_page.py         ← Delivery updates with staff names + WhatsApp invoice
│   │
│   └── [legacy widgets — NOT used, safe to delete]
│       ├── customers_widget.py
│       ├── dashboard_widget.py
│       ├── inventory_widget.py
│       ├── invoices_widget.py
│       └── orders_widget.py
│
│
└── ivr_whatsapp/                    ── IVR + WhatsApp server (runs separately from the app)
    ├── __init__.py
    ├── SETUP_GUIDE.md               ← How to configure Exotel + MSG91 + ngrok
    ├── requirements_ivr_wa.txt      ← pip install flask requests psycopg2-binary
    │
    ├── server.py                    ← Flask webhook server (python ivr_whatsapp/server.py)
    ├── config.py                    ← YOUR API KEYS go here (Exotel, MSG91, Business info)
    │                                  Set EXOTEL_ENABLED=True / MSG91_ENABLED=True when ready
    ├── ivr_handler.py               ← Handles Exotel IVR call logic (digit press → action)
    ├── wa_handler.py                ← Handles inbound WhatsApp messages (multi-turn chat bot)
    ├── wa_sender.py                 ← Sends WhatsApp messages OUT via MSG91
    └── db_bridge.py                 ← Direct DB access for Flask server (same PostgreSQL DB)
```

---

## 👤 Role → Pages Access

| Page            | 🌿 Owner | 🛠 Admin | 🚚 Dispatch |
|-----------------|:--------:|:--------:|:-----------:|
| Dashboard       | ✅       | ✅       | ❌          |
| Inventory       | ✅       | ✅       | ❌          |
| Customers       | ✅       | ❌       | ❌          |
| Orders          | ✅       | ❌       | ❌          |
| Invoices        | ✅       | ❌       | ❌          |
| Users           | ✅       | ❌       | ❌          |
| Dispatch Board  | ✅       | ❌       | ✅          |

---

## 🗄️ Database Tables (auto-created on first run)

| Table           | Purpose                                              |
|-----------------|------------------------------------------------------|
| app_users       | Login accounts — username, hashed password, role, phone |
| customers       | Customer contact details                             |
| plants          | Plant catalogue with tray/bucket container support   |
| seeds           | Seed inventory in grams + packets                    |
| containers      | Tray, bucket, pot stock                              |
| orders          | Orders with full delivery + staff tracking           |
| order_items     | Line items per order                                 |
| invoices        | Invoice records linked to orders                     |
| otp_sessions    | OTP codes for password reset (expires in 10 min)     |
| ivr_wa_sessions | WhatsApp chat session state per customer             |

---

## ▶️ How to Run

### Desktop App
```bash
# 1. Install dependencies
pip install PyQt6 psycopg2-binary reportlab matplotlib twilio

# 2. Run
python main.py
# → First run shows Connection Setup screen
# → Select Server (localhost) or Client (enter server IP)
# → Then Login: owner / owner123
```

### IVR + WhatsApp Server (optional, separate)
```bash
pip install flask requests psycopg2-binary

# Fill in API keys in ivr_whatsapp/config.py first
python ivr_whatsapp/server.py

# Expose publicly for testing:
ngrok http 5000
```

---

## 🔐 Default Login
| Username | Password  | Role  |
|----------|-----------|-------|
| `owner`  | `owner123`| Owner |

> Change after first login via: Sidebar → 🔑 Change Password

---

## 🌐 Multi-PC Network Setup
Read **SERVER_SETUP_GUIDE.md** for the full guide.
Quick summary:
- **Server PC**: Run app → select "Server Machine" → uses localhost
- **Client PCs**: Copy project folder → run app → select "Client Machine" → enter server IP
- All machines share the same PostgreSQL database in real time
