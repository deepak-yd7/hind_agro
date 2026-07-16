# Hind Agro Products ERP

A desktop ERP system built with PyQt6 and PostgreSQL.

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Create PostgreSQL database
```sql
CREATE DATABASE nursery_erp;
```

### 3. Configure database credentials
Edit `backend/database.py` and update `DB_CONFIG`:
```python
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "nursery_erp",
    "user": "postgres",
    "password": "your_actual_password",
}
```

### 4. Run the app
```bash
python main.py
```
Tables are created automatically on first run.

## Modules
- **Dashboard** – Overview cards (live when DB connected)
- **Inventory** – Add/edit/delete plants with stock tracking & low-stock alerts
- **Customers** – Manage your customer list with search
- **Orders** – Place orders, update status, auto-deducts stock
- **Invoices** – Auto-generated on order, mark as paid

## Project Structure
```
my_pyqt_project/
├── main.py                  # Entry point
├── requirements.txt
├── backend/
│   └── database.py          # PostgreSQL pool & schema creation
├── models/
│   └── user_model.py        # Dataclasses: Customer, Plant, Order, Invoice
├── services/
│   └── user_service.py      # CRUD operations for all entities
└── frontend/
    ├── main_window.py        # Sidebar navigation shell
    └── pages/
        ├── dashboard_page.py
        ├── inventory_page.py
        ├── customers_page.py
        ├── orders_page.py
        └── invoices_page.py
```
