# Odoo Middleware

A FastAPI-based middleware that provides a multi-step onboarding interface to provision Odoo workspaces. It automates the creation of Odoo databases, companies, branches, and users through a clean web UI — and optionally through a Google Sheets integration for bulk operations.

---

## How It Works

The middleware sits between your users and Odoo, exposing two main interfaces:

**1. Web Onboarding UI** — A 3-step form that guides you through:
- Company details + industry + database name (with real-time availability check)
- Branches (optional)
- Users and their roles

On submission, it creates the Odoo database, company, branches, and users in the background and shows a live progress page. When done, it returns the workspace URL, database name, and user credentials.

**2. Google Sheets Processor** — A `/process` endpoint that reads pending rows from a Google Sheet, executes the actions (create company, branch, or user) against Odoo, and writes the result (success/failed + record ID or error) back to the sheet.

```
┌─────────────────────────────────────────────────────┐
│                  FastAPI Middleware                  │
│                                                     │
│  Web UI (3-step form)     Google Sheets Processor   │
│         │                          │                │
│         └──────────┬───────────────┘                │
│                    │                                │
│            Odoo XML-RPC API                         │
└─────────────────────────────────────────────────────┘
                     │
              Odoo Instance
         (self-hosted or cloud)
```

---

## Project Structure

```
.
├── app/
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Environment variable loading
│   ├── data_source/
│   │   ├── base.py                # Abstract data source interface
│   │   ├── models.py              # Pydantic models (Row, ActionType, etc.)
│   │   └── google_sheets.py       # Google Sheets implementation
│   ├── odoo/
│   │   ├── client.py              # Odoo XML-RPC client + DB management
│   │   └── actions/
│   │       ├── base.py            # Abstract action base class
│   │       ├── create_company.py  # Create Odoo company
│   │       ├── create_branch.py   # Create Odoo branch (child company)
│   │       └── create_user.py     # Create Odoo user with role
│   ├── routers/
│   │   └── onboarding.py          # All onboarding routes + background jobs
│   ├── services/
│   │   └── processor.py           # Google Sheets batch processor
│   └── templates/                 # Jinja2 HTML templates
│       ├── base.html
│       ├── step1_company.html
│       ├── step2_branches.html
│       ├── step3_users.html
│       ├── processing.html
│       └── success.html
├── Dockerfile
├── deploy.sh
├── requirements.txt
└── .env.example
```

---

## Prerequisites

- Python 3.10+
- A running Odoo instance (self-hosted or Odoo cloud)
- Docker (optional, for containerized deployment)
- A Google Cloud service account (optional, for Google Sheets integration)

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable | Description | Example |
|---|---|---|
| `ODOO_URL` | Your Odoo instance URL | `http://1.2.3.4:8069` |
| `ODOO_MASTER_PASSWORD` | Odoo master password (for DB creation) | `my_master_pass` |
| `ODOO_ADMIN_USER` | Admin login for your main DB | `admin@company.com` |
| `ODOO_ADMIN_PASSWORD` | Admin password | `admin_pass` |
| `ODOO_NEW_DB_ADMIN_USER` | Admin login for newly created DBs | `admin` |
| `ODOO_NEW_DB_ADMIN_PASSWORD` | Admin password for new DBs | `admin_pass` |
| `SECRET_KEY` | Secret key for session encryption | `any-long-random-string` |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Path to Google service account JSON | `service_account.json` |
| `SPREADSHEET_ID` | Google Sheet ID from the URL | `1BxiM...` |
| `SHEET_NAME` | Tab name in the spreadsheet | `Sheet1` |

> **Note:** `ODOO_NEW_DB_ADMIN_USER` is typically `admin` because newly created Odoo databases always use `admin` as the default login, regardless of what you use for your main database.

---

## Running Without Docker

### 1. Clone the repo

```bash
git clone git@github.com:your-username/Odoo-Middleware.git
cd Odoo-Middleware
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate      # Linux / macOS
# or
.venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up your `.env` file

```bash
cp .env.example .env
nano .env   # fill in your values
```

### 5. Run the app

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open `http://localhost:8000` — you'll see the onboarding form.

> Use `--reload` for development (auto-restarts on file changes). Remove it in production.

---

## Running With Docker

### 1. Build the image

```bash
docker build -t odoo-middleware .
```

### 2. Run the container

```bash
docker run -d \
  --name odoo-middleware \
  --restart unless-stopped \
  --network host \
  --env-file .env \
  odoo-middleware
```

> `--network host` is used so the container can reach Odoo on the same server without DNS issues. If Odoo is on a different server, you can remove it and use `-p 8000:8000` instead.

### 3. Check logs

```bash
docker logs odoo-middleware -f
```

---

## Deploying to a Linux Server (Recommended)

Use the included `deploy.sh` script. It builds the Docker image, stops any existing container, and starts a fresh one.

### First-time setup

```bash
# 1. Install Docker on the server
apt update
apt install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
tee /etc/apt/sources.list.d/docker.list > /dev/null
apt update
apt install -y docker-ce docker-ce-cli containerd.io

# 2. Open the port
ufw allow 8000/tcp
ufw reload

# 3. Clone the repo
cd /root
git clone git@github.com:your-username/Odoo-Middleware.git
cd Odoo-Middleware

# 4. Create your .env
cp .env.example .env
nano .env

# 5. Deploy
bash deploy.sh
```

### Updating after a code change

```bash
cd /root/Odoo-Middleware
git pull
bash deploy.sh
```

That's it — the script handles stopping the old container, rebuilding the image, and starting the new one.

### Useful commands

```bash
docker ps                           # check container is running
docker logs odoo-middleware -f      # live logs
docker restart odoo-middleware      # restart
docker stop odoo-middleware         # stop
```

---

## Setting Up Odoo with Docker

If you don't have Odoo yet, you can run it alongside this middleware:

```bash
# Create a shared network
docker network create odoo-network

# Run Postgres
docker run -d \
  --name odoo-db \
  --network odoo-network \
  -e POSTGRES_USER=odoo \
  -e POSTGRES_PASSWORD=odoo123 \
  -e POSTGRES_DB=postgres \
  -v odoo-db-data:/var/lib/postgresql/data \
  --restart unless-stopped \
  postgres:15

# Run Odoo 19
docker run -d \
  --name odoo \
  --network odoo-network \
  -p 8069:8069 \
  -e HOST=odoo-db \
  -e USER=odoo \
  -e PASSWORD=odoo123 \
  -v odoo-data:/var/lib/odoo \
  --restart unless-stopped \
  odoo:19
```

Open `http://YOUR_SERVER_IP:8069` to set up your first database. Then set `ODOO_URL=http://YOUR_SERVER_IP:8069` in your `.env`.

---

## Google Sheets Integration (Optional)

The `/process` endpoint reads pending rows from a Google Sheet and executes them against Odoo.

### Sheet structure

| customer_name | odoo_db | action | name | parent_company | email | phone | country | status | record_id | error |
|---|---|---|---|---|---|---|---|---|---|---|
| Acme Corp | | create_company | Acme Egypt | | info@acme.com | | EG | pending | | |
| Acme Corp | acme_db | create_branch | Acme KSA | Acme Egypt | | | SA | pending | | |
| Acme Corp | acme_db | create_user | John Doe | | john@acme.com | | | pending | | |

**Supported actions:** `create_company`, `create_branch`, `create_user`

**Status flow:** `pending` → `success` or `failed`

### Setting up Google Sheets API

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project → Enable **Google Sheets API**
3. Create a **Service Account** → Download the JSON key
4. Place the JSON file in the project root as `service_account.json`
5. Share your Google Sheet with the service account email (editor access)
6. Set `SPREADSHEET_ID` in your `.env` to the sheet ID from the URL

### Triggering the processor

```bash
curl -X POST http://localhost:8000/process
```

---

## Adding a New Action

The codebase is designed to make adding new actions easy:

1. Create `app/odoo/actions/your_action.py` extending `BaseAction`
2. Implement `validate()` and `execute()`
3. Add the action to `ActionType` enum in `app/data_source/models.py`
4. Register it in `ACTION_MAP` in `app/services/processor.py`

---

## Switching the Data Source

The `DataSource` abstract class in `app/data_source/base.py` defines just two methods: `get_pending_rows()` and `update_row()`. To replace Google Sheets with a database or REST API:

1. Create a new class in `app/data_source/` implementing those two methods
2. Swap the import in `app/main.py`

Nothing else in the codebase needs to change.