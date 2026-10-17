# PulseNotify - Flight Price Monitor & Alert System ✈️🔔

PulseNotify is an asynchronous backend service built with **Django REST Framework (DRF)**, **Celery**, **Celery Beat**, and **Redis**. It allows travelers to register price alerts for flight routes (e.g. `DEL-BOM`, `BLR-HYD`). On a background schedule (every 60 seconds), Celery Beat wakes up, checks live flight prices against internal mock feeds, and asynchronously dispatches notifications whenever prices drop below user thresholds.

---

## 🌟 Key Highlights & Architecture

- **Instant Non-Blocking API**: User requests never wait for external price checking or notification delivery.
- **Celery Beat Scheduling**: Recurring background scheduler runs every 60 seconds without manual invocation.
- **Async Task Offloading**: `send_notification.delay()` ensures tasks run asynchronously without blocking the beat scheduler.
- **Internal Backend-to-Backend Mock Feed**: Direct mock price feed endpoint (`/api/flights/price/`) consumed via Python `requests`.
- **JWT Authentication & RBAC**: Scoped user access with SimpleJWT and custom role-based permissions (`ADMIN` vs `USER`).
- **Clean Configuration Architecture**: Split settings (`base.py`, `local.py`, `production.py`) reading secrets and configurations from `.env`.
- **Full Dockerized Infrastructure**: Single `docker-compose.yml` for PostgreSQL 16 and Redis 7.

---

## 📁 Repository Structure

```text
├── pulsenotify/                 # Django Project Root
│   ├── __init__.py              # Celery app export
│   ├── celery.py                # Celery application configuration
│   ├── urls.py                  # Main project URL routing
│   ├── wsgi.py                  # WSGI entrypoint
│   ├── asgi.py                  # ASGI entrypoint
│   └── settings/                # Split Settings Directory
│       ├── __init__.py          # Default DJANGO_SETTINGS_MODULE
│       ├── base.py              # Shared settings (Apps, Celery, JWT, REST)
│       ├── local.py             # Development settings & local DB config
│       └── production.py        # Production hardening & credentials
├── pulse/                       # Core Application
│   ├── apps.py                  # AppConfig wiring signals on ready()
│   ├── models.py                # UserProfile, PriceAlert, NotificationLog
│   ├── signals.py               # post_save signal auto-creating UserProfile
│   ├── serializers.py           # DRF Serializers for Auth, Alerts & Logs
│   ├── views.py                 # 7 REST API endpoints + Notification views
│   ├── urls.py                  # App URL routing (/api/...)
│   ├── permissions.py           # Custom IsAdminUser BasePermission
│   ├── tasks.py                 # check_prices & send_notification Celery tasks
│   ├── tests.py                 # 3 required unit tests + 18 integration tests
│   └── management/commands/     # Custom Django commands
│       └── setup_demo.py        # One-click demo seed script
├── docker-compose.yml           # PostgreSQL + Redis services
├── requirements.txt             # Pinned Python dependencies
├── .env.example                 # Environment variables template
├── .env                         # Active local environment variables
├── .gitignore                   # Ignore .env, db.sqlite3, caches, venv
├── PulseNotify.postman_collection.json # 13 scenarios automated test collection
└── README.md                    # Project documentation
```

---

## ⚙️ Installation & Setup

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Docker & Docker Desktop (for PostgreSQL & Redis)

### 2. Virtual Environment & Dependencies
```bash
# Clone the repository and enter the directory
cd "PulseNotify - Flight Price Monitor & Alert System"

# Create a virtual environment
python -m venv .venv

# Activate the virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (CMD):
.venv\Scripts\activate.bat
# Linux/macOS:
source .venv/bin/activate

# Install pinned dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```
Ensure `.env` contains:
```env
DJANGO_SETTINGS_MODULE=pulsenotify.settings.local
SECRET_KEY=your-secure-secret-key-here
DEBUG=True

# Database (PostgreSQL via Docker or fallback SQLite)
DB_NAME=pulsenotify_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
USE_SQLITE=True  # Set to False to connect to Docker PostgreSQL

# Redis & Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Internal Mock Price Feed Endpoint
INTERNAL_FLIGHT_API_URL=http://localhost:8000/api/flights/price/

JWT_ACCESS_MINUTES=60
JWT_REFRESH_DAYS=7
```

### 4. Start Infrastructure (Docker Compose)
Start PostgreSQL and Redis in the background:
```bash
docker compose up -d
```
Verify the containers are healthy:
```bash
docker compose ps
```

### 5. Run Database Migrations & Seed Demo Data
```bash
# Apply database migrations
python manage.py migrate

# Seed sample users and alerts (Optional but recommended)
python manage.py setup_demo
```
Default seeded Indian accounts:
- **Admin**: `username="admin"`, `password="adminpass123"` (Rajesh Sharma, `admin@pulsenotify.in`, role = `admin`)
- **Indian Users** (password for all: `password123`):
  - `username="aarav"` (Aarav Patel) — Alerts: `DEL-BOM` (₹4,500), `DEL-BLR` (₹5,200)
  - `username="priya"` (Priya Sharma) — Alerts: `BLR-HYD` (₹2,200), `BOM-GOA` (₹2,800)
  - `username="rohit"` (Rohit Verma) — Alerts: `DEL-BOM` (₹4,200), `CCU-DEL` (₹4,600)
  - `username="ananya"` (Ananya Iyer) — Alerts: `MAA-BLR` (₹2,000), `PNQ-DEL` (₹3,500)
- **Default Brief User**: `username="alice"`, `password="securepass"` (Alice Mehta, role = `user`)

Seeded Indian domestic corridors:
- `DEL-BOM` (New Delhi - Mumbai)
- `BLR-HYD` (Bengaluru - Hyderabad)
- `DEL-BLR` (New Delhi - Bengaluru)
- `BOM-GOA` (Mumbai - Goa)
- `CCU-DEL` (Kolkata - New Delhi)
- `MAA-BLR` (Chennai - Bengaluru)
- `PNQ-DEL` (Pune - New Delhi)

---

## 🚀 Running the System (3 Simultaneous Processes)

To run the complete PulseNotify platform with automated background monitoring, open three terminal windows:

### Terminal 1: Django API Server
```bash
python manage.py runserver
```
Runs at `http://localhost:8000/`.

### Terminal 2: Celery Worker
```bash
celery -A pulsenotify worker --loglevel=info
```
> **Tip for Windows users**: If encountering billiard pool limitations on Windows, run with `--pool=solo`:
> ```bash
> celery -A pulsenotify worker --loglevel=info --pool=solo
> ```
*Watch this terminal for incoming `send_notification` asynchronous tasks.*

### Terminal 3: Celery Beat Scheduler
```bash
celery -A pulsenotify beat --loglevel=info
```
*Watch this terminal fire `pulse.tasks.check_prices` every 60 seconds.*

---

## 📡 API Endpoints Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/auth/register/` | Public | Register new user. Auto-assigns `role='user'` via post-save signal. Returns 201 + JWT. |
| `POST` | `/api/auth/login/` | Public | Authenticate credentials. Returns 200 + JWT access and refresh tokens. |
| `POST` | `/api/alerts/` | JWT (User) | Create new flight price alert for logged-in user. |
| `GET` | `/api/alerts/` | JWT (User) | List alerts belonging strictly to the authenticated user. |
| `DELETE` | `/api/alerts/<id>/` | JWT (User) | Deactivate alert (soft delete to `inactive`). Returns 404 if not found or unauthorized. |
| `GET` | `/api/flights/price/?route=<route>` | Public | Mock price feed returning simulated price for route. |
| `GET` | `/api/admin/summary/` | JWT (Admin) | Platform statistics (total alerts, active, triggered, top routes). Regular users receive 403. |
| `GET` | `/api/notifications/` | JWT | Inspect created notification logs. |

---

## 🧪 Running Unit Tests

All 3 required unit tests specified in the brief plus additional integration test suites are implemented in `pulse/tests.py`:

1. **`PriceThresholdTest`**: Verifies price comparison logic (`<`, `>`, `==`).
2. **`NotificationLogTest`**: Verifies `NotificationLog` creation, attributes, and messages.
3. **`AlertScopingTest`**: Verifies strict user data scoping (users cannot see other users' alerts).
4. **`AuthAPITests`**: Tests registration, duplicate username handling (400), login (200), and invalid credentials (401).
5. **`AlertAPITests`**: Tests alert creation, listing, soft deactivation, and isolation.
6. **`FlightPriceFeedAPITests`**: Tests mock price feed valid ranges and 404 responses.
7. **`AdminSummaryAPITests`**: Tests role enforcement (403 for user, 200 for admin) and aggregations.
8. **`CeleryTasksTest`**: Tests Celery async scheduling and task execution.

Run the test suite with:
```bash
python manage.py test
```

Expected Output:
```text
Creating test database for alias 'default'...
.....................
----------------------------------------------------------------------
Ran 21 tests in 0.263s

OK
Destroying test database for alias 'default'...
```

---

## 📮 Postman Collection (13 Scenarios)

The file `PulseNotify.postman_collection.json` contains all 13 test scenarios requested in the brief:

| # | Scenario | Endpoint | Expected |
|---|---|---|---|
| 1 | Register a new user | `POST /api/auth/register/` | 201 + JWT token |
| 2 | Register with duplicate username | `POST /api/auth/register/` | 400 Bad Request |
| 3 | Login with valid credentials | `POST /api/auth/login/` | 200 + JWT token |
| 4 | Login with wrong password | `POST /api/auth/login/` | 401 Unauthorized |
| 5 | Create a price alert - no token | `POST /api/alerts/` | 401 Unauthorized |
| 6 | Create a price alert - valid token | `POST /api/alerts/` | 201 Created |
| 7 | List own alerts | `GET /api/alerts/` | 200 + list |
| 8 | Deactivate an alert | `DELETE /api/alerts/<id>/` | 200 + inactive status |
| 9 | Mock price feed - valid route | `GET /api/flights/price/?route=DEL-BOM` | 200 + simulated price |
| 10 | Mock price feed - invalid route | `GET /api/flights/price/?route=XYZ-ABC` | 404 Route not found |
| 11 | Admin summary - regular user token | `GET /api/admin/summary/` | 403 Forbidden |
| 12 | Admin summary - admin token | `GET /api/admin/summary/` | 200 + platform stats |
| 13 | Verify NotificationLog | `GET /api/notifications/` / PGAdmin | Row exists in `notification_logs` |

### How to Import & Run in Postman:
1. Open Postman.
2. Click **Import** and select `PulseNotify.postman_collection.json`.
3. Set the collection variable `baseUrl` to `http://localhost:8000` (default).
4. Run the collection using Postman Runner — all tests will execute sequentially and pass automatically.

---

## 🔍 Database Inspection (PGAdmin / SQLite)

- **PostgreSQL**: Connect PGAdmin or DBeaver to `localhost:5432` with database `pulsenotify_db`, username `postgres`, password `postgres`.
- Inspect tables:
  - `pulse_userprofile`: Check user roles (`admin` / `user`).
  - `pulse_pricealert`: Check alert routes, threshold prices, and status changes (`active` -> `triggered` / `inactive`).
  - `pulse_notificationlog`: Check rows created automatically when the Celery worker triggers.

---

## 🛡️ Best Practices & Architecture Highlights

- **ORM Aggregations**: The `/api/admin/summary/` endpoint performs all counting and grouping directly inside the SQL database via Django's `aggregate()` and `annotate()`, without using inefficient Python loops.
- **Signals**: Auto-creation of user profiles is cleanly isolated in `pulse/signals.py` and registered during Django startup in `PulseConfig.ready()`.
- **Security**: Sensitive keys are loaded exclusively from `.env`, with `.env` added to `.gitignore`.
