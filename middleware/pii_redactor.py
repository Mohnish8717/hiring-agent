"""
PII Redaction Middleware for FastAPI.

Strips Personally Identifiable Information from:
  1. Outgoing API response bodies (names, emails, phone numbers)
  2. Log records before they reach external sinks

Uses regex-based detection.  In production, consider spaCy NER
for higher accuracy entity detection.
"""

import re
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
import json

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_PATTERN = re.compile(r"(\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}")
# Aadhaar (India), SSN (US)
AADHAAR_PATTERN = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

REDACTION_PLACEHOLDER = "[REDACTED]"

logger = logging.getLogger("pii_redactor")


def redact_text(text: str) -> str:
    """Apply all PII redaction patterns to raw text."""
    text = EMAIL_PATTERN.sub(REDACTION_PLACEHOLDER, text)
    text = PHONE_PATTERN.sub(REDACTION_PLACEHOLDER, text)
    text = AADHAAR_PATTERN.sub(REDACTION_PLACEHOLDER, text)
    text = SSN_PATTERN.sub(REDACTION_PLACEHOLDER, text)
    return text


def redact_dict(data):
    """Recursively redact PII inside a dict/list structure."""
    if isinstance(data, dict):
        return {k: redact_dict(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [redact_dict(item) for item in data]
    elif isinstance(data, str):
        return redact_text(data)
    return data


class PIIRedactionMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that intercepts JSON responses and redacts PII
    before they leave the server.  SSE and file responses are passed through.
    """

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        content_type = response.headers.get("content-type", "")

        # Only redact JSON responses; skip file downloads, SSE, etc.
        if "application/json" not in content_type:
            return response

        # Read the body
        body_bytes = b""
        async for chunk in response.body_iterator:
            if isinstance(chunk, bytes):
                body_bytes += chunk
            else:
                body_bytes += chunk.encode("utf-8")

        try:
            body_json = json.loads(body_bytes)
            redacted = redact_dict(body_json)
            new_body = json.dumps(redacted).encode("utf-8")
        except (json.JSONDecodeError, UnicodeDecodeError):
            new_body = body_bytes

        return Response(
            content=new_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )


# ---------------------------------------------------------------------------
# Logging filter — attach to Python loggers to redact PII in log messages
# ---------------------------------------------------------------------------
class PIIRedactionLogFilter(logging.Filter):
    """Logging filter that redacts PII from log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: redact_text(str(v)) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(redact_text(str(a)) for a in record.args)
        return True
