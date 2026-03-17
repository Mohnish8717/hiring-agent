import os
import uuid
import json
import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from sse_starlette.sse import EventSourceResponse
from agents.orchestrator import ATSOrchestrator

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api-bridge")

app = FastAPI(title="IKSHA AI Backend Bridge")

# Enable CORS for Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to dashboard URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for demo (use Redis/DB for production)
analysis_results = {}
analysis_logs = {}

orchestrator = ATSOrchestrator()

@app.get("/")
async def root():
    return {"status": "IKSHA AI Backend Online"}

@app.post("/analyze")
async def analyze_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    job_description: Optional[str] = Form(None)
):
    request_id = str(uuid.uuid4())
    
    # Save file temporarily
    temp_dir = "cache/uploads"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, f"{request_id}_{file.filename}")
    
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    analysis_logs[request_id] = asyncio.Queue()
    analysis_results[request_id] = {"status": "processing"}

    background_tasks.add_task(
        run_orchestrator, request_id, file_path, job_description
    )
    
    return {"request_id": request_id}

@app.post("/demo")
async def run_demo(background_tasks: BackgroundTasks):
    request_id = "demo_session"
    file_path = "Mohnish_Resume.pdf" # This exists in the root
    
    if not os.path.exists(file_path):
        return {"error": "Demo file not found"}

    analysis_logs[request_id] = asyncio.Queue()
    analysis_results[request_id] = {"status": "processing"}

    background_tasks.add_task(
        run_orchestrator, request_id, file_path, "Full Stack Developer"
    )
    
    return {"request_id": request_id}

async def run_orchestrator(request_id: str, file_path: str, job_description: str):
    try:
        async def on_log(msg: str):
            await analysis_logs[request_id].put(msg)

        results = await orchestrator.run_pipeline(file_path, job_description, on_log=on_log)
        
        # Format results for frontend consumption
        analysis_results[request_id] = {
            "status": "complete",
            "data": results
        }
        # Signal end of stream
        await analysis_logs[request_id].put("__DONE__")
        
    except Exception as e:
        logger.error(f"Error in orchestrator: {str(e)}")
        await analysis_logs[request_id].put(f"ERROR: {str(e)}")
        analysis_results[request_id] = {"status": "error", "message": str(e)}

@app.get("/status/{request_id}")
async def get_status(request_id: str):
    if request_id not in analysis_logs:
        return {"error": "Invalid request ID"}

    async def event_generator():
        while True:
            try:
                msg = await analysis_logs[request_id].get()
                
                if msg == "__DONE__":
                    # Send final result if available
                    result_data = analysis_results.get(request_id, {})
                    # Ensure all data (including Pydantic models) is JSON serializable
                    json_compatible_data = jsonable_encoder(result_data)
                    yield {
                        "event": "complete",
                        "data": json.dumps(json_compatible_data)
                    }
                    break
                
                yield {
                    "event": "log",
                    "data": msg
                }
            except Exception as e:
                logger.error(f"SSE Error: {str(e)}")
                break

    return EventSourceResponse(event_generator())

@app.get("/results/{request_id}")
async def get_results(request_id: str):
    return analysis_results.get(request_id, {"error": "Not found"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
