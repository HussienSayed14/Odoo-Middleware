from fastapi import FastAPI, HTTPException
from app.data_source.google_sheets import GoogleSheetsDataSource
from app.services import processor

app = FastAPI(title="Odoo Middleware", version="0.1.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/process")
def process_sheet():
    """
    Read all pending rows from the Google Sheet,
    execute their actions against Odoo, and write results back.
    """
    try:
        source = GoogleSheetsDataSource()
        results = processor.process(source)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))