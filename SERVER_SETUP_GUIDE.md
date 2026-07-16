# Hind Agro Products ERP — Network Setup Guide

## Architecture

```
┌─────────────────────────────────┐        LAN / Network
│   SERVER MACHINE (Main PC)      │◄──────────────────────►
│   • PostgreSQL running here     │
│   • IP e.g. 192.168.1.100       │      ┌──────────────────┐
│   • App set to "localhost"       │      │  CLIENT MACHINE 1 │
└─────────────────────────────────┘      │  (Admin PC)       │
                                         │  IP → 192.168.1.100│
                                         └──────────────────┘
                                         ┌──────────────────┐
                                         │  CLIENT MACHINE 2 │
                                         │  (Dispatch PC)    │
                                         │  IP → 192.168.1.100│
                                         └──────────────────┘
```

---

## STEP 1 — Server Machine Setup

### 1A. Install PostgreSQL (if not installed)
Download from: https://www.postgresql.org/download/windows/

### 1B. Create the database
Open pgAdmin or psql and run:
```sql
CREATE DATABASE nursery_erp;
```

### 1C. Allow remote connections

**Edit postgresql.conf:**
Find file at: `C:\Program Files\PostgreSQL\15\data\postgresql.conf`
Change:
```
listen_addresses = 'localhost'
```
to:
```
listen_addresses = '*'
```

**Edit pg_hba.conf:**
Find file at: `C:\Program Files\PostgreSQL\15\data\pg_hba.conf`
Add this line at the bottom:
```
host    all    all    0.0.0.0/0    md5
```

**Restart PostgreSQL service:**
- Open Services (Win+R → services.msc)
- Find "postgresql-x64-15" → Right click → Restart

### 1D. Open Windows Firewall for port 5432
Run this in PowerShell as Administrator:
```powershell
New-NetFirewallRule -DisplayName "PostgreSQL" -Direction Inbound -Protocol TCP -LocalPort 5432 -Action Allow
```

### 1E. Find your Server IP address
Run in Command Prompt:
```
ipconfig
```
Look for "IPv4 Address" under your network adapter.
Example: `192.168.1.100`
**Write this down — all client machines need this number.**

### 1F. Run the app on the server
When the app starts for the first time, select:
**"🖥️ Server Machine"** → it uses localhost automatically.

---

## STEP 2 — Client Machine Setup

### 2A. Copy the project folder
Copy the entire `my_pyqt_project` folder to the client machine.

### 2B. Install Python dependencies
```bash
pip install PyQt6 psycopg2-binary reportlab matplotlib flask requests twilio
```

### 2C. Run the app
```bash
python main.py
```

### 2D. Connection Setup screen
On first run the Connection Setup screen appears automatically.
- Select: **"💻 Client Machine"**
- Enter Server IP: `192.168.1.100` (the IP from Step 1E)
- Port: `5432`
- Database: `nursery_erp`
- Username: `postgres`
- Password: (your PostgreSQL password)
- Click **"🔌 Test Connection"** → should show ✅
- Click **"Save & Connect"**

Done! The client is now connected to the server database in real time.

---

## Changing the Server IP Later

From the **Login screen** → click **"Change Server"** button at the bottom.
This opens the Connection Setup dialog again.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| "Connection refused" | PostgreSQL not running, or firewall blocking port 5432 |
| "Timeout" | Wrong IP address, or not on same network |
| "Password authentication failed" | Wrong password |
| "Database does not exist" | Run `CREATE DATABASE nursery_erp;` on server |
| Client can't reach server | Make sure all machines are on same WiFi/LAN |

---

## db_config.json (auto-created, do not share)

Each machine creates its own `db_config.json` in the project root:

**Server machine:**
```json
{
  "host": "localhost",
  "port": 5432,
  "database": "nursery_erp",
  "user": "postgres",
  "password": "yourpassword"
}
```

**Client machine:**
```json
{
  "host": "192.168.1.100",
  "port": 5432,
  "database": "nursery_erp",
  "user": "postgres",
  "password": "yourpassword"
}
```

⚠️ Never commit db_config.json to git — it contains your password.
