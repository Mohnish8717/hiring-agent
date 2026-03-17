import os
import json
import asyncio
import logging
from celery import Celery
import redis
from agents.orchestrator import ATSOrchestrator

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery("iksha_tasks", broker=REDIS_URL, backend=REDIS_URL)
sync_redis = redis.from_url(REDIS_URL, decode_responses=True)

logger = logging.getLogger("celery_worker")
logging.basicConfig(level=logging.INFO)

# Initialize orchestrator at worker startup to keep it warm
orchestrator = ATSOrchestrator()

@celery_app.task(bind=True, name="process_resume")
def process_resume_task(self, request_id: str, file_path: str, job_description: str, tenant_id: str = None):
    logger.info(f"Starting Celery task for request_id: {request_id}, tenant_id: {tenant_id}")
    
    # Define a sync callback that publishes logs to Redis
    def on_log_sync(msg: str):
        sync_redis.publish(f"logs:{request_id}", msg)

    async def run_async():
        try:
            # Set status to processing
            sync_redis.hset(request_id, mapping={"status": "processing"})
            
            results = await orchestrator.run_pipeline(
                pdf_path=file_path,
                job_description=job_description,
                on_log=on_log_sync,
                request_id=request_id,
                tenant_id=tenant_id
            )
            
            # Save results back to redis
            sync_redis.hset(request_id, mapping={
                "status": "complete",
                "data": json.dumps(results)
            })
            
            # Publish DONE event
            sync_redis.publish(f"logs:{request_id}", "__DONE__")
            return results
        except Exception as e:
            logger.error(f"Error in orchestrator task: {str(e)}")
            sync_redis.publish(f"logs:{request_id}", f"ERROR: {str(e)}")
            sync_redis.hset(request_id, mapping={
                "status": "error",
                "message": str(e)
            })
            # Publish DONE even on error so client disconnects
            sync_redis.publish(f"logs:{request_id}", "__DONE__")

    asyncio.run(run_async())
