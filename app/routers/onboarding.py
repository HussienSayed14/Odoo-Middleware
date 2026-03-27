import re
import uuid
import logging
from typing import Optional
from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.odoo.client import OdooClient
from app.odoo.actions.create_company import CreateCompanyAction
from app.odoo.actions.create_branch import CreateBranchAction
from app.odoo.actions.create_user import CreateUserAction
from app.data_source.models import Row, ActionType
from app.config import ODOO_URL

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/onboarding")
templates = Jinja2Templates(directory="app/templates")

jobs: dict = {}


def get_session(request: Request) -> dict:
    return request.session.setdefault("onboarding", {})

def clear_session(request: Request):
    request.session.pop("onboarding", None)

def validate_db_name(name: str) -> Optional[str]:
    if not name:
        return "Database name is required."
    if not re.match(r'^[a-z0-9_]+$', name):
        return "Only lowercase letters, numbers, and underscores allowed."
    if len(name) < 3:
        return "Must be at least 3 characters."
    if len(name) > 30:
        return "Must be 30 characters or less."
    if name.startswith('_') or name.endswith('_'):
        return "Cannot start or end with an underscore."
    return None

def s1(request, data, error=None):
    return {"request": request, "data": data, "error": error, "step_num": 1, "progress_pct": "33%"}

def s2(request, company_name, branches, error=None):
    return {"request": request, "company_name": company_name, "branches": branches, "error": error, "step_num": 2, "progress_pct": "66%"}

def s3(request, company_name, users, error=None):
    return {"request": request, "company_name": company_name, "users": users, "error": error, "step_num": 3, "progress_pct": "100%"}


def run_onboarding(job_id: str, company_data: dict, branches: list, users: list):
    db_name = company_data["db_name"]
    db_mode = company_data.get("db_mode", "new")
    try:
        if db_mode == "new":
            jobs[job_id]["step"] = "Checking database availability..."
            logger.info(f"[Job {job_id}] Checking if DB '{db_name}' exists")
            if OdooClient.database_exists(db_name):
                raise Exception(f"Database '{db_name}' already exists. Choose a different name or use existing database mode.")
            jobs[job_id]["step"] = f"Creating database '{db_name}' (~30-60 seconds)..."
            logger.info(f"[Job {job_id}] Creating database '{db_name}'")
            OdooClient.create_database(db_name)
            logger.info(f"[Job {job_id}] Database '{db_name}' created")
            is_new_db = True
        else:
            jobs[job_id]["step"] = f"Connecting to '{db_name}'..."
            logger.info(f"[Job {job_id}] Using existing DB '{db_name}'")
            if not OdooClient.database_exists(db_name):
                raise Exception(f"Database '{db_name}' does not exist. Check the name or create a new one.")
            is_new_db = False

        jobs[job_id]["step"] = "Connecting to workspace..."
        client = OdooClient(db=db_name, is_new_db=is_new_db)

        jobs[job_id]["step"] = f"Creating company '{company_data['name']}'..."
        logger.info(f"[Job {job_id}] Creating company '{company_data['name']}'")
        company_row = Row(
            row_index=0, customer_name=company_data["name"],
            action=ActionType.create_company, name=company_data["name"],
            email=company_data.get("email") or None,
            phone=company_data.get("phone") or None,
            country=company_data.get("country") or None,
        )
        company_id = CreateCompanyAction(client, company_row).run()
        logger.info(f"[Job {job_id}] Company created ID={company_id}")

        for i, branch in enumerate(branches):
            jobs[job_id]["step"] = f"Creating branch '{branch['name']}' ({i+1}/{len(branches)})..."
            logger.info(f"[Job {job_id}] Creating branch '{branch['name']}'")
            try:
                branch_row = Row(
                    row_index=0, customer_name=company_data["name"],
                    action=ActionType.create_branch, name=branch["name"],
                    parent_company=company_data["name"],
                    email=branch.get("email") or None,
                    phone=branch.get("phone") or None,
                    country=branch.get("country") or None,
                )
                bid = CreateBranchAction(client, branch_row).run()
                logger.info(f"[Job {job_id}] Branch created ID={bid}")
            except Exception as e:
                logger.error(f"[Job {job_id}] Branch '{branch['name']}' failed: {e}")
                raise Exception(f"Failed to create branch '{branch['name']}': {e}")

        created_users = []
        for i, user in enumerate(users):
            jobs[job_id]["step"] = f"Creating user '{user['name']}' ({i+1}/{len(users)})..."
            logger.info(f"[Job {job_id}] Creating user '{user['name']}' role={user['role']}")
            try:
                user_row = Row(
                    row_index=0, customer_name=company_data["name"],
                    action=ActionType.create_user, name=user["name"],
                    email=user["email"], role=user["role"],
                )
                uid = CreateUserAction(client, user_row).run()
                client.execute("res.users", "write", [[uid], {"password": user["password"]}])
                logger.info(f"[Job {job_id}] User '{user['name']}' created ID={uid}")
                created_users.append({**user, "id": uid})
            except Exception as e:
                logger.error(f"[Job {job_id}] User '{user['name']}' failed: {e}")
                raise Exception(f"Failed to create user '{user['name']}': {e}")

        logger.info(f"[Job {job_id}] Onboarding complete")
        jobs[job_id] = {
            "status": "done", "step": "Done!",
            "company_name": company_data["name"], "db_name": db_name,
            "odoo_url": f"{ODOO_URL}/web/login?db={db_name}",
            "users": created_users,
        }
    except Exception as e:
        logger.error(f"[Job {job_id}] Failed: {e}")
        jobs[job_id] = {"status": "error", "step": str(e)}


@router.get("/step1", response_class=HTMLResponse)
async def step1_get(request: Request):
    session = get_session(request)
    return templates.TemplateResponse("step1_company.html", s1(request, session.get("company", {})))

@router.post("/step1")
async def step1_post(request: Request):
    form = await request.form()
    session = get_session(request)
    name     = (form.get("name") or "").strip() # type: ignore
    db_mode  = (form.get("db_mode") or "new").strip() # type: ignore
    db_name  = (form.get("db_name") or "").strip().lower() # type: ignore
    existing = (form.get("existing_db_name") or "").strip().lower() # type: ignore
    email    = (form.get("email") or "").strip() # type: ignore
    phone    = (form.get("phone") or "").strip() # type: ignore
    country  = (form.get("country") or "").strip() # type: ignore
    city     = (form.get("city") or "").strip() # type: ignore
    website  = (form.get("website") or "").strip() # type: ignore
    data = {"name": name, "db_mode": db_mode, "db_name": db_name,
            "existing_db_name": existing, "email": email,
            "phone": phone, "country": country, "city": city, "website": website}

    if not name:
        return templates.TemplateResponse("step1_company.html", s1(request, data, "Company name is required."))

    if db_mode == "new":
        err = validate_db_name(db_name)
        if err:
            return templates.TemplateResponse("step1_company.html", s1(request, data, err))
        data["db_name"] = db_name
    else:
        err = validate_db_name(existing)
        if err:
            return templates.TemplateResponse("step1_company.html", s1(request, data, f"Existing database name: {err}"))
        data["db_name"] = existing

    if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return templates.TemplateResponse("step1_company.html", s1(request, data, "Please enter a valid email address."))

    logger.info(f"[Step1] company='{name}' db='{data['db_name']}' mode={db_mode}")
    session["company"] = data
    return RedirectResponse("/onboarding/step2", status_code=302)


@router.get("/step2", response_class=HTMLResponse)
async def step2_get(request: Request):
    session = get_session(request)
    if "company" not in session:
        return RedirectResponse("/onboarding/step1", status_code=302)
    return templates.TemplateResponse("step2_branches.html", s2(request, session["company"]["name"], session.get("branches", [])))

@router.post("/step2")
async def step2_post(request: Request):
    form = await request.form()
    session = get_session(request)
    if "company" not in session:
        return RedirectResponse("/onboarding/step1", status_code=302)
    if form.get("skip"):
        session["branches"] = []
        return RedirectResponse("/onboarding/step3", status_code=302)

    branch_count = int(form.get("branch_count", 0)) # type: ignore
    branches = []
    errors = []
    for i in range(1, branch_count + 1):
        name = (form.get(f"branch_name_{i}") or "").strip() # type: ignore
        if not name:
            continue
        email = (form.get(f"branch_email_{i}") or "").strip() # type: ignore
        if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            errors.append(f"Branch #{i}: '{email}' is not a valid email.")
            continue
        branches.append({
            "name": name, "email": email,
            "phone": (form.get(f"branch_phone_{i}") or "").strip(), # type: ignore
            "country": (form.get(f"branch_country_{i}") or "").strip(), # type: ignore
            "city": (form.get(f"branch_city_{i}") or "").strip(), # type: ignore
        })

    if errors:
        return templates.TemplateResponse("step2_branches.html", s2(request, session["company"]["name"], branches, " | ".join(errors)))

    logger.info(f"[Step2] {len(branches)} branches")
    session["branches"] = branches
    return RedirectResponse("/onboarding/step3", status_code=302)


@router.get("/step3", response_class=HTMLResponse)
async def step3_get(request: Request):
    session = get_session(request)
    if "company" not in session:
        return RedirectResponse("/onboarding/step1", status_code=302)
    return templates.TemplateResponse("step3_users.html", s3(request, session["company"]["name"], session.get("users", [])))

@router.post("/step3")
async def step3_post(request: Request, background_tasks: BackgroundTasks):
    form = await request.form()
    session = get_session(request)
    if "company" not in session:
        return RedirectResponse("/onboarding/step1", status_code=302)

    user_count = int(form.get("user_count", 0)) # type: ignore
    users = []
    errors = []
    seen_emails: set = set()

    for i in range(1, user_count + 1):
        name     = (form.get(f"user_name_{i}") or "").strip() # type: ignore
        email    = (form.get(f"user_email_{i}") or "").strip().lower() # type: ignore
        password = (form.get(f"user_password_{i}") or "").strip() # type: ignore
        role     = (form.get(f"user_role_{i}") or "user").strip() # type: ignore
        if not name or not email or not password:
            errors.append(f"User #{i}: name, email and password are all required.")
            continue
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            errors.append(f"User #{i}: '{email}' is not a valid email.")
            continue
        if len(password) < 8:
            errors.append(f"User #{i}: password must be at least 8 characters.")
            continue
        if email in seen_emails:
            errors.append(f"User #{i}: email '{email}' is already used by another user.")
            continue
        seen_emails.add(email)
        users.append({"name": name, "email": email, "password": password, "role": role})

    if errors:
        return templates.TemplateResponse("step3_users.html", s3(request, session["company"]["name"], users, " | ".join(errors)))
    if not users:
        return templates.TemplateResponse("step3_users.html", s3(request, session["company"]["name"], [], "Please add at least one user."))

    company_data = session.get("company")
    branches     = session.get("branches", [])
    logger.info(f"[Step3] company='{company_data['name']}' db='{company_data['db_name']}' users={len(users)} branches={len(branches)}") # type: ignore

    session["users"] = users
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "running", "step": "Starting..."}
    background_tasks.add_task(run_onboarding, job_id, company_data, branches, users) # type: ignore
    clear_session(request)

    return templates.TemplateResponse("processing.html", {
        "request": request, "job_id": job_id,
        "company_name": company_data["name"], # type: ignore
        "step_num": 3, "progress_pct": "100%",
    })


@router.get("/status/{job_id}")
async def job_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        return JSONResponse({"status": "error", "step": "Job not found."})
    return JSONResponse(job)


@router.get("/success/{job_id}", response_class=HTMLResponse)
async def success_page(request: Request, job_id: str):
    job = jobs.get(job_id, {})
    return templates.TemplateResponse("success.html", {
        "request": request,
        "company_name": job.get("company_name", ""),
        "db_name": job.get("db_name", ""),
        "odoo_url": job.get("odoo_url", ODOO_URL),
        "users": job.get("users", []),
        "step_num": 3, "progress_pct": "100%",
    })