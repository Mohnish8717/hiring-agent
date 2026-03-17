import logging
import random
import time
import threading
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

class GroqThrottler:
    """Centralized thread-safe throttler for Groq API calls to prevent 429 TPM/RPM errors."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(GroqThrottler, cls).__new__(cls)
                # Global limits for Llama 3.3 70b (adjust if needed)
                cls._instance.tpm_limit = 12000
                cls._instance.remaining_tokens = 12000
                cls._instance.rpm_limit = 30
                cls._instance.remaining_requests = 30
                cls._instance.reset_time = time.time() + 60
                
                # Semaphore to serialize requests (especially for Free Tier)
                cls._instance._semaphore = threading.Semaphore(1)
        return cls._instance

    @property
    def semaphore(self):
        return self._instance._semaphore

    def update_limits(self, headers: Dict[str, str]):
        """Updates internal limits based on Groq API response headers."""
        with self._lock:
            try:
                # Headers are usually: x-ratelimit-remaining-tokens, x-ratelimit-reset-tokens, etc.
                self.remaining_tokens = int(headers.get("x-ratelimit-remaining-tokens", self.remaining_tokens))
                self.remaining_requests = int(headers.get("x-ratelimit-remaining-requests", self.remaining_requests))
                
                # Reset time parsing (Groq provides reset time as string like "1.2s" or "60ms")
                reset_str = headers.get("x-ratelimit-reset-tokens", "60s")
                if "ms" in reset_str:
                    delay = float(reset_str.replace("ms", "")) / 1000.0
                else:
                    delay = float(reset_str.replace("s", ""))
                
                self.reset_time = time.time() + delay
                
                logger.debug(f"📊 Groq Limits Update: {self.remaining_tokens} tokens / {self.remaining_requests} requests remaining. Reset in {delay}s")
            except (ValueError, TypeError) as e:
                logger.debug(f"⚠️ Failed to parse Groq rate limit headers: {e}")

    def wait_if_needed(self, estimated_tokens: int = 1000):
        """Pauses execution if the token or request budget is too low."""
        with self._lock:
            now = time.time()
            
            # Proactive check: if we're very low on tokens, wait for reset
            if self.remaining_tokens < estimated_tokens or self.remaining_requests < 1:
                wait_time = max(0, self.reset_time - now) + random.uniform(0.5, 1.5)
                if wait_time > 0:
                    logger.warning(f"⏳ Groq budget low ({self.remaining_tokens} tokens left). Waiting {wait_time:.2f}s for reset...")
                    # Release lock during sleep
                    self._lock.release()
                    try:
                        time.sleep(wait_time)
                    finally:
                        self._lock.acquire()
                    # Reset after sleep
                    self.remaining_tokens = self.tpm_limit
                    self.remaining_requests = self.rpm_limit

def execute_with_backoff(func: Callable, *args, **kwargs) -> Any:
    """Executes a synchronous function with exponential backoff on 429 errors."""
    max_retries = 5
    base_delay = 2.0
    
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "Too Many Requests" in error_str:
                if attempt == max_retries - 1:
                    logger.error(f"❌ Max retries reached for Groq 429 error: {error_str}")
                    raise e
                
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"⚠️ Groq Rate Limit (429) hit. Retrying in {delay:.2f}s... (Attempt {attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                raise e
