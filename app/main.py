from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

# from app.data_source.google_sheets import GoogleSheetsDataSource
from app.services import processor
from app.routers import onboarding
from app.config import SECRET_KEY

app = FastAPI(title="Odoo Middleware", version="0.1.0")

# ── Middleware ─────────────────────────────────────────
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# ── Static files ───────────────────────────────────────
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ── Routers ────────────────────────────────────────────
app.include_router(onboarding.router)

# ── Redirect root to onboarding ────────────────────────
@app.get("/")
def root():
    return RedirectResponse("/onboarding/step1")

# ── Sheet processor endpoint ───────────────────────────
@app.get("/health")
def health():
    return {"status": "ok"}

# @app.post("/process")
# def process_sheet():
#     try:
#         # source = GoogleSheetsDataSource()
#         results = processor.process(source)
#         return results
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))