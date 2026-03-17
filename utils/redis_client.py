import os
import json
import redis.asyncio as redis
from typing import Dict, Any, AsyncGenerator

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# For async FastAPI operations
async_redis_client = redis.from_url(REDIS_URL, decode_responses=True)

async def set_analysis_status(request_id: str, status: str):
    await async_redis_client.hset(request_id, mapping={"status": status})

async def get_analysis_result(request_id: str) -> Dict[str, Any]:
    result = await async_redis_client.hgetall(request_id)
    if not result:
        return {}
    
    if "data" in result:
        try:
            full_data = json.loads(result["data"])
            full_data["status"] = result.get("status", "")
            if "message" in result:
                full_data["message"] = result["message"]
            return full_data
        except json.JSONDecodeError:
            pass
    return result

async def subscribe_logs(request_id: str) -> AsyncGenerator[str, None]:
    pubsub = async_redis_client.pubsub()
    await pubsub.subscribe(f"logs:{request_id}")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield str(message["data"])
    finally:
        await pubsub.unsubscribe(f"logs:{request_id}")
        await pubsub.close()
