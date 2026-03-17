import os
import uuid
import json
import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from sse_starlette.sse import EventSourceResponse
from pythonjsonlogger import json as jsonlogger

from utils.redis_client import (
    async_redis_client,
    set_analysis_status,
    get_analysis_result,
    subscribe_logs,
)
from celery_worker import process_resume_task

from middleware.pii_redactor import PIIRedactionMiddleware, PIIRedactionLogFilter
from middleware.auth import KeycloakAuthMiddleware
from db.database import init_db

# Setup structured JSON logging with PII redaction
log_handler = logging.StreamHandler()
log_handler.setFormatter(jsonlogger.JsonFormatter(
    "%(asctime)s %(name)s %(levelname)s %(message)s",
    rename_fields={"asctime": "timestamp", "levelname": "level"},
))
log_handler.addFilter(PIIRedactionLogFilter())
logging.basicConfig(level=logging.INFO, handlers=[log_handler])
logger = logging.getLogger("api-bridge")

app = FastAPI(title="IKSHA AI Backend Bridge")

# Middleware stack (order matters: last added = first executed)
app.add_middleware(KeycloakAuthMiddleware)
app.add_middleware(PIIRedactionMiddleware)
app.add_middleware(CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to dashboard URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize PostgreSQL tables on application boot."""
    await init_db()
    logger.info("Database initialized")


@app.get("/")
async def root():
    return {"status": "IKSHA AI Backend Online"}


@app.post("/analyze")
async def analyze_resume(
    request: Request,
    file: UploadFile = File(...),
    job_description: Optional[str] = Form(None),
):
    request_id = str(uuid.uuid4())
    tenant_id = getattr(request.state, "tenant_id", None)

    # Save file temporarily
    temp_dir = "cache/uploads"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, f"{request_id}_{file.filename}")

    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Set initial status in Redis
    await set_analysis_status(request_id, "processing")

    # Dispatch to Celery worker
    process_resume_task.delay(request_id, file_path, job_description or "", tenant_id)

    return {"request_id": request_id}


@app.post("/demo")
async def run_demo():
    request_id = "demo_session"
    file_path = "Mohnish_Resume.pdf"

    if not os.path.exists(file_path):
        return {"error": "Demo file not found"}

    await set_analysis_status(request_id, "processing")

    process_resume_task.delay(request_id, file_path, "Full Stack Developer")

    return {"request_id": request_id}


@app.get("/status/{request_id}")
async def get_status(request_id: str):
    """SSE endpoint — streams logs from Redis Pub/Sub published by the Celery worker."""

    async def event_generator():
        async for msg in subscribe_logs(request_id):
            if msg == "__DONE__":
                result_data = await get_analysis_result(request_id)
                json_compatible_data = jsonable_encoder(result_data)
                yield {
                    "event": "complete",
                    "data": json.dumps(json_compatible_data),
                }
                break

            yield {"event": "log", "data": msg}

    return EventSourceResponse(event_generator())


@app.get("/results/{request_id}")
async def get_results(request_id: str):
    result = await get_analysis_result(request_id)
    return result if result else {"error": "Not found"}


@app.get("/reports/{filename}")
async def get_report(filename: str):
    report_path = os.path.join("cache/reports", filename)
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(report_path, media_type="application/pdf", filename=filename)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
