# DeviceVault — Mobile Device Inventory Management System

DeviceVault is a full-stack, self-hosted inventory system for an organization's phones, tablets and smartwatches. It tracks every device from purchase to retirement — who has it, which project it belongs to, when it is due back, whether it is in repair, and whether it passed the last physical audit.

![stack](https://img.shields.io/badge/backend-FastAPI-009688) ![stack](https://img.shields.io/badge/frontend-React%20%2B%20Vite-61dafb) ![stack](https://img.shields.io/badge/server-nginx-269539) ![stack](https://img.shields.io/badge/db-SQLite-003b57)

---

## Features

| Area | What you get |
|------|--------------|
| **Inventory** | Phones, iPads, Android tablets and smartwatches with OS/version, serial, MAC, IMEI (enforced for cellular devices), location, division, project and notes. Search and filter by type, OS, status, company, assignee. |
| **Dashboard** | Totals, in-stock list, utilization, devices by category / project, OS freshness (latest / recent / outdated), pending requests, overdue returns, active repairs, quarterly audit progress and a "needs attention" list. |
| **Assignment history** | Every hand-over, return, extension and repair is written to a per-device timeline. |
| **Requests & approvals** | Any user can request a device; managers approve/reject and fulfil the request by allocating a specific device with a return date. |
| **Maintenance** | Repair tickets with priority, vendor and cost. Opening a ticket moves the device to *in repair*; completing it brings it back to *active*; *unrepairable* retires it. |
| **Returns** | Overdue / due-today / due-this-week views, extend a return date, process a return (with printable clearance receipt). |
| **Audits** | Record physical verification per audit cycle (e.g. `2026-Q4`); *missing* devices are flagged as lost automatically. |
| **Allocation reports** | Device distribution by division, project and location with overdue counts. |
| **CSV import** | Bulk-load devices from a spreadsheet, with per-row error reporting. |
| **Users & roles** | JWT auth with refresh-token rotation and three roles (below). |

### Roles

| Role | Capabilities |
|------|--------------|
| **Admin** | Everything, including user management and hard-deleting devices |
| **Manager** | Create / edit / assign devices, import CSV, handle requests, repairs, returns and audits |
| **Viewer** | Read-only inventory and dashboard; can submit and track their own device requests |

---

## Tech stack

- **Frontend:** React 18, React Router, Axios, Vite
- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2, Pydantic 2
- **Database:** SQLite (single file, zero setup)
- **Auth:** JWT access tokens + rotating refresh tokens, bcrypt password hashing
- **Production serving:** nginx (static frontend + reverse proxy to uvicorn)

```
            ┌────────────── nginx (:80 / :8080) ──────────────┐
 Browser ──►│  /            → frontend/dist (React SPA)        │
            │  /api/*, /health, /docs → 127.0.0.1:8000 ───────┼──► uvicorn (FastAPI) ──► SQLite
            └─────────────────────────────────────────────────┘
```

---

## Project structure

```
├── backend/
│   ├── app/
│   │   ├── api/            # Route handlers: auth, users, devices, management
│   │   ├── core/           # Settings, security (JWT / bcrypt)
│   │   ├── db/             # Engine/session, seed data, SQLite column migrations
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic request/response models
│   │   └── services/       # CSV import
│   ├── tests/              # pytest suite covering every API endpoint
│   ├── .env.example
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/               # React app (Vite)
├── deploy/
│   ├── nginx/devicevault.conf      # nginx site for Linux
│   ├── systemd/devicevault.service # backend service for Linux
│   ├── windows/nginx.conf          # standalone nginx config for Windows
│   └── install.sh                  # one-shot Ubuntu/Debian installer
├── scripts/setup.bat       # Windows first-time setup
├── samples/                # Example CSV files for import
├── start-local.bat         # Windows: development mode
├── start-production.bat    # Windows: nginx production mode
└── stop-production.bat
```

---

## Quick start

### Requirements

- Python **3.11+**
- Node.js **20.19+** (22 LTS recommended)
- nginx (only for production mode)

### Option A — Development mode (Windows, one click)

```powershell
start-local.bat
```

The script creates the Python virtualenv, installs dependencies, creates `backend\.env` with a random secret key, and starts:

- API with hot reload on http://localhost:8000 (interactive docs at http://localhost:8000/docs)
- Frontend with hot reload on **http://localhost:3000** (Vite proxies `/api` to the backend)

### Option B — Development mode (any OS, manual)

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then set SECRET_KEY
uvicorn app.main:app --reload --port 8000

# Frontend (second terminal)
cd frontend
npm install
npm run dev                        # http://localhost:3000
```

### Sign in

On first start the database is seeded with demo accounts and sample devices:

| Role    | Email               | Password    |
|---------|---------------------|-------------|
| Admin   | admin@company.com   | Admin123!   |
| Manager | manager@company.com | Manager123! |
| Viewer  | viewer@company.com  | Viewer123!  |

> **Change these passwords** (Users page) before going live, or set `SEED_ON_STARTUP=false` and create your own admin.

---

## Production deployment with nginx

In production the React app is built to static files and served by nginx, which also reverse-proxies `/api` to uvicorn on `127.0.0.1:8000`. The frontend and API share one origin, so no CORS setup is needed.

### Linux (Ubuntu / Debian) — automated

```bash
git clone https://github.com/Talhaaashraf/Mobile-Device-Inventory-Management-System.git
cd Mobile-Device-Inventory-Management-System
sudo bash deploy/install.sh
```

The installer:

1. installs nginx, Python and Node.js
2. copies the app to `/opt/devicevault` and creates a `devicevault` system user
3. creates the virtualenv and `backend/.env` with a random `SECRET_KEY`
4. builds the frontend into `/opt/devicevault/frontend/dist`
5. installs and starts the `devicevault` systemd service and the nginx site

Then open `http://<server-ip>/`.

Useful commands:

```bash
sudo systemctl status devicevault      # API status
sudo journalctl -u devicevault -f      # API logs
sudo nginx -t && sudo systemctl reload nginx
```

To serve a real domain, set `server_name` in `/etc/nginx/sites-available/devicevault` and add HTTPS, e.g. with `sudo certbot --nginx -d inventory.example.com`.

### Linux — manual

```bash
# 1. Backend
cd /opt/devicevault/backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env    # set SECRET_KEY

# 2. Frontend
cd /opt/devicevault/frontend
npm ci && npm run build

# 3. Services
sudo cp /opt/devicevault/deploy/systemd/devicevault.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now devicevault
sudo cp /opt/devicevault/deploy/nginx/devicevault.conf /etc/nginx/sites-available/devicevault
sudo ln -s /etc/nginx/sites-available/devicevault /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### Windows

1. Download nginx for Windows from https://nginx.org/en/download.html and extract it (e.g. to `C:\nginx`).
2. Either add that folder to `PATH` or set `NGINX_HOME`:

   ```powershell
   set NGINX_HOME=C:\nginx
   start-production.bat
   ```

3. Open **http://localhost:8080**. Stop everything with `stop-production.bat`.

`start-production.bat` runs the same setup as development mode, builds the frontend, starts uvicorn on `127.0.0.1:8000` and starts nginx with [deploy/windows/nginx.conf](deploy/windows/nginx.conf). nginx logs are written to `deploy\windows\runtime\`.

---

## Security

Built in:

- Passwords hashed with **bcrypt**; JWTs signed with HS256 using your `SECRET_KEY` (generated randomly by the setup scripts).
- Short-lived access tokens (30 min) and **rotating** refresh tokens. Old refresh tokens are revoked on use, on logout, on password change and when an account is deactivated.
- Role checks on every endpoint (admin / manager / viewer); admins cannot delete, deactivate or demote their own account.
- nginx adds `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy` and `Permissions-Policy`, hides its version, and rate-limits `/api/auth/login` to 10 attempts per minute per IP.
- Login takes the same time whether or not an email is registered, so accounts cannot be enumerated.
- Workflow guards: only pending/approved requests can be fulfilled, a request can be fulfilled once, and a device already allocated to someone cannot be handed out again.
- Input bounds on all numeric fields; CSV uploads are limited to 5 MB; SQLite foreign keys are enforced.
- Dependabot (weekly) and CI (tests, build, `nginx -t`) run on GitHub with read-only permissions.
- The placeholder `SECRET_KEY` is never used to sign tokens (a random key is generated instead), and the API warns at startup if a demo account still has its published password.

Production checklist:

1. Change or deactivate the three demo accounts (or start with `SEED_ON_STARTUP=false` and create your own admin).
2. Keep `backend/.env` private — it is git-ignored; never commit it.
3. Enable HTTPS (e.g. `sudo certbot --nginx`) and then uncomment the `Strict-Transport-Security` header in the nginx config.
4. Optionally remove the `/docs` and `/openapi.json` blocks from the nginx config to hide the API explorer.

---

## Configuration

All settings are read from environment variables or `backend/.env` (see [backend/.env.example](backend/.env.example)).

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./device_inventory.db` | SQLAlchemy URL of the database file |
| `SECRET_KEY` | *(auto-generated)* | Signs JWTs. Set a long random value. If it is missing or still the `.env.example` placeholder, the API generates a random key, stores it in `backend/.secret_key` (git-ignored) and logs a warning — the published placeholder is never used. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Only needed if the frontend is hosted on a different origin |
| `SEED_ON_STARTUP` | `true` | Create the demo accounts and sample data if the database is empty |

Frontend (build time, optional):

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | *(empty — same origin)* | Set only if the API lives on a different host, e.g. `https://api.example.com` |
| `API_PROXY_TARGET` | `http://127.0.0.1:8000` | Backend address used by the Vite dev server proxy |

### Backups

The whole database is one file: `backend/device_inventory.db`. Back it up by copying it while the API is stopped, or with `sqlite3 device_inventory.db ".backup backup.db"` while it is running.

---

## Importing devices from CSV

1. Sign in as **admin** or **manager** → **Devices**
2. Click **CSV template** (or use a file from [samples/](samples/))
3. Fill in your rows and click **Import CSV**

Required columns:

```
device_name, device_type, os_type, os_version, serial_number
```

Recommended: `device_nickname`, `is_cellular`, `imei_number` (required when `is_cellular` is true), `mac_address` (generated from the serial if missing), `company`.

Optional: `status`, `audit_status`, `resident_location`, `division`, `issued_to`, `project_manager`, `project_name`, `date_of_return`, `purchase_date` (YYYY-MM-DD), `assigned_user_email`, `notes`.

Allowed values: `device_type` = `phone | tablet_ipad | tablet_android | smartwatch`; `os_type` = `ios | android | watchos | wear_os`; `status` = `active | in_repair | retired | lost`.

Rows that fail validation are skipped and reported with their row number; valid rows are still imported.

---

## API reference

Interactive Swagger docs: `/docs` (e.g. http://localhost:8000/docs, or through nginx at `/docs`).

| Method | Path | Role |
|--------|------|------|
| POST | `/api/auth/login` · `/api/auth/refresh` · `/api/auth/logout` | public / any |
| GET | `/api/auth/me` | any |
| GET / POST | `/api/users` | admin |
| PATCH / DELETE | `/api/users/{id}` | admin |
| GET | `/api/users/assignees` | manager, admin |
| GET | `/api/dashboard/summary` | any |
| GET | `/api/devices` (filters: `device_type`, `os_type`, `company`, `status`, `assigned_user_id`, `unassigned`, `q`) | any |
| POST | `/api/devices` · `/api/devices/import` | manager, admin |
| GET | `/api/devices/{id}` · `/api/devices/{id}/history` | any |
| PATCH | `/api/devices/{id}` | manager, admin |
| DELETE | `/api/devices/{id}` | admin |
| GET / POST | `/api/management/requests` | any (viewers see their own) |
| POST | `/api/management/requests/{id}/review` · `/fulfill` | manager, admin |
| GET | `/api/management/maintenance` | any |
| POST / PATCH | `/api/management/maintenance[/{id}]` | manager, admin |
| GET | `/api/management/returns` | any |
| POST | `/api/management/returns/{device_id}/extend` · `/return` | manager, admin |
| GET | `/api/management/audits` · `/api/management/audits/cycles` | any |
| POST | `/api/management/audits` | manager, admin |
| GET | `/api/management/allocations` | any |
| GET | `/health` | public |

---

## Testing

The backend has a pytest suite (79 tests) that exercises every endpoint against a throwaway SQLite database: authentication and token rotation, role permissions, device validation rules (IMEI/MAC, duplicates), assignment history, CSV import, the request → approval → fulfilment workflow, maintenance, returns, audits, allocations, the dashboard, and data integrity when users or devices are deleted.

```bash
cd backend
pip install -r requirements-dev.txt
pytest -q
```

Frontend build check:

```bash
cd frontend
npm run build
```

GitHub Actions ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs the backend tests, the frontend build and `nginx -t` against the site config on every push.

---

## License

Released for free use and modification. Add a `LICENSE` file of your choice (e.g. MIT) before distributing.
