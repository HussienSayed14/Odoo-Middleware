from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import re

from app.odoo.client import OdooClient
from app.odoo.actions.create_company import CreateCompanyAction
from app.odoo.actions.create_branch import CreateBranchAction
from app.odoo.actions.create_user import CreateUserAction
from app.data_source.models import Row, ActionType
from app.config import ODOO_URL

router = APIRouter(prefix="/onboarding")
templates = Jinja2Templates(directory="app/templates")


# ── Helpers ───────────────────────────────────────────────────────────────

def get_session(request: Request) -> dict:
    return request.session.setdefault("onboarding", {})

def clear_session(request: Request):
    request.session.pop("onboarding", None)


# ── Step 1: Company ───────────────────────────────────────────────────────

@router.get("/step1", response_class=HTMLResponse)
async def step1_get(request: Request):
    session = get_session(request)
    return templates.TemplateResponse("step1_company.html", {
        "request": request,
        "data": session.get("company", {}),
        "error": None,
    })

@router.post("/step1")
async def step1_post(
    request: Request,
    name: str = Form(...),
    email: str = Form(""),
    phone: str = Form(""),
    country: str = Form(""),
    city: str = Form(""),
    website: str = Form(""),
):
    if not name.strip():
        return templates.TemplateResponse("step1_company.html", {
            "request": request,
            "data": {"name": name, "email": email, "phone": phone, "country": country},
            "error": "Company name is required.",
        })

    session = get_session(request)
    session["company"] = {
        "name": name.strip(),
        "email": email.strip(),
        "phone": phone.strip(),
        "country": country.strip(),
        "city": city.strip(),
        "website": website.strip(),
    }
    return RedirectResponse("/onboarding/step2", status_code=302)


# ── Step 2: Branches ──────────────────────────────────────────────────────

@router.get("/step2", response_class=HTMLResponse)
async def step2_get(request: Request):
    session = get_session(request)
    if "company" not in session:
        return RedirectResponse("/onboarding/step1", status_code=302)

    return templates.TemplateResponse("step2_branches.html", {
        "request": request,
        "company_name": session["company"]["name"],
        "branches": session.get("branches", []),
        "error": None,
    })

@router.post("/step2")
async def step2_post(request: Request):
    form = await request.form()
    session = get_session(request)

    # Skip button
    if form.get("skip"):
        session["branches"] = []
        return RedirectResponse("/onboarding/step3", status_code=302)

    branch_count = int(form.get("branch_count", 0)) # type: ignore
    branches = []
    errors = []

    for i in range(1, branch_count + 1):
        name = (form.get(f"branch_name_{i}") or "").strip() # type: ignore
        if not name:
            continue  # empty blocks are ignored
        branches.append({
            "name": name,
            "email": (form.get(f"branch_email_{i}") or "").strip(), # type: ignore
            "phone": (form.get(f"branch_phone_{i}") or "").strip(), # type: ignore
            "country": (form.get(f"branch_country_{i}") or "").strip(), # type: ignore
            "city": (form.get(f"branch_city_{i}") or "").strip(), # type: ignore
        })

    if errors:
        return templates.TemplateResponse("step2_branches.html", {
            "request": request,
            "company_name": session["company"]["name"],
            "branches": branches,
            "error": " | ".join(errors),
        })

    session["branches"] = branches
    return RedirectResponse("/onboarding/step3", status_code=302)


# ── Step 3: Users ─────────────────────────────────────────────────────────

@router.get("/step3", response_class=HTMLResponse)
async def step3_get(request: Request):
    session = get_session(request)
    if "company" not in session:
        return RedirectResponse("/onboarding/step1", status_code=302)

    return templates.TemplateResponse("step3_users.html", {
        "request": request,
        "company_name": session["company"]["name"],
        "users": session.get("users", []),
        "error": None,
    })

@router.post("/step3")
async def step3_post(request: Request):
    form = await request.form()
    session = get_session(request)

    user_count = int(form.get("user_count", 0)) # type: ignore
    users = []
    errors = []

    for i in range(1, user_count + 1):
        name     = (form.get(f"user_name_{i}") or "").strip() # type: ignore
        email    = (form.get(f"user_email_{i}") or "").strip() # type: ignore
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

        users.append({"name": name, "email": email, "password": password, "role": role})

    if errors:
        return templates.TemplateResponse("step3_users.html", {
            "request": request,
            "company_name": session["company"]["name"],
            "users": users,
            "error": " | ".join(errors),
        })

    if not users:
        return templates.TemplateResponse("step3_users.html", {
            "request": request,
            "company_name": session["company"]["name"],
            "users": [],
            "error": "Please add at least one user.",
        })

    session["users"] = users

    # ── Process everything ─────────────────────────────────────────────────
    try:
        company_data = session["company"]
        branches     = session.get("branches", [])

        # 1. Create DB
        db_name = company_data["name"].lower().strip().replace(" ", "_") + "_db"
        if not OdooClient.database_exists(db_name):
            OdooClient.create_database(db_name)

        client = OdooClient(db=db_name)

        # 2. Create company
        company_row = Row(
            row_index=0,
            customer_name=company_data["name"],
            action=ActionType.create_company,
            name=company_data["name"],
            email=company_data["email"] or None,
            phone=company_data["phone"] or None,
            country=company_data["country"] or None,
        )
        company_id = CreateCompanyAction(client, company_row).run()

        # 3. Create branches
        for branch in branches:
            branch_row = Row(
                row_index=0,
                customer_name=company_data["name"],
                action=ActionType.create_branch,
                name=branch["name"],
                parent_company=company_data["name"],
                email=branch["email"] or None,
                phone=branch["phone"] or None,
                country=branch["country"] or None,
            )
            CreateBranchAction(client, branch_row).run()

        # 4. Create users
        created_users = []
        for user in users:
            user_row = Row(
                row_index=0,
                customer_name=company_data["name"],
                action=ActionType.create_user,
                name=user["name"],
                email=user["email"],
            )
            user_id = CreateUserAction(client, user_row).run()

            # Set password
            client.execute("res.users", "write", [[user_id], {"password": user["password"]}])
            created_users.append({**user, "id": user_id})

        clear_session(request)
        return templates.TemplateResponse("success.html", {
            "request": request,
            "company_name": company_data["name"],
            "odoo_url": f"{ODOO_URL}/web/login?db={db_name}",
            "users": created_users,
        })

    except Exception as e:
        return templates.TemplateResponse("step3_users.html", {
            "request": request,
            "company_name": session["company"]["name"],
            "users": users,
            "error": f"Something went wrong: {str(e)}",
        })