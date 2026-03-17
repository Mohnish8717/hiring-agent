from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
import hashlib
import time
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

app = FastAPI(title="Device Fingerprinting API")
logger = logging.getLogger("fingerprint_api")

# --- Models ---

class FingerprintPayload(BaseModel):
    # Core Signals
    userAgent: str
    platform: str
    language: str
    timezone: str
    screenResolution: str
    colorDepth: int
    hardwareConcurrency: int
    deviceMemory: Optional[float] = None
    cookiesEnabled: bool
    
    # Advanced Signals
    canvasFingerprint: str
    webglVendor: str
    webglRenderer: str
    
    # Security/Bot Signals
    isHeadless: bool
    webdriver: bool
    
    # Application Context
    resume_country: Optional[str] = None

class FingerprintResponse(BaseModel):
    device_id: str
    ip_country: str
    vpn_detected: bool
    headless_browser: bool
    same_device_applications: int

# --- Fingerprint Hashing ---

def generate_device_hash(payload: Dict[str, Any]) -> str:
    """Generates a stable SHA256 hash from browser signals."""
    # Select stable signals for the hash
    stable_keys = [
        "userAgent", "platform", "language", "timezone", 
        "screenResolution", "colorDepth", "hardwareConcurrency", 
        "deviceMemory", "canvasFingerprint", "webglVendor", "webglRenderer"
    ]
    
    components = {k: payload.get(k) for k in stable_keys}
    seed = json.dumps(components, sort_keys=True).encode('utf-8')
    return hashlib.sha256(seed).hexdigest()

# --- Mock Database / Service Logic ---

# In real production, this would be a DB call
MOCK_DB: Dict[str, Dict[str, Any]] = {}

def update_device_history(device_id: str, ip: str):
    """Updates device record in DB."""
    if device_id not in MOCK_DB:
        MOCK_DB[device_id] = {
            "first_seen": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "application_count": 1,
            "ip_history": [ip]
        }
    else:
        MOCK_DB[device_id]["last_seen"] = datetime.now().isoformat()
        MOCK_DB[device_id]["application_count"] += 1
        if ip not in MOCK_DB[device_id]["ip_history"]:
            MOCK_DB[device_id]["ip_history"].append(ip)

# --- API Endpoints ---

@app.post("/api/device-fingerprint", response_model=FingerprintResponse)
async def ingest_fingerprint(payload: FingerprintPayload, request: Request, background_tasks: BackgroundTasks):
    """
    Ingests device signals, generates stable ID, and extracts security metadata.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    # 1. Normalize and Hash
    data = payload.model_dump()
    device_id = generate_device_hash(data)
    
    # 2. Fraud Signal Extraction (Mock logic for demonstration)
    # In production, use MaxMind or IPQualityScore for VPN/Proxy/Geo detection
    vpn_detected = False
    if "vpn" in client_ip.lower(): # Trivial mockup
        vpn_detected = True
        
    ip_country = "US" # Mocked GeoIP lookup
    
    # 3. Headless Detection
    is_headless = data.get("isHeadless", False) or data.get("webdriver", False)
    
    # 4. Update Database (Async)
    background_tasks.add_task(update_device_history, device_id, client_ip)
    
    # 5. Get application velocity
    app_count = MOCK_DB.get(device_id, {}).get("application_count", 0) + 1
    
    return FingerprintResponse(
        device_id=device_id,
        ip_country=ip_country,
        vpn_detected=vpn_detected,
        headless_browser=is_headless,
        same_device_applications=app_count
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
