"""
Keycloak OAuth2 / OIDC Authentication Middleware for FastAPI.

Validates JWT Bearer tokens issued by a self-hosted Keycloak server.
Extracts tenant_id from the token claims for multi-tenant isolation.

Environment variables:
    KEYCLOAK_URL     – Keycloak base URL (e.g. http://localhost:8180)
    KEYCLOAK_REALM   – Realm name (default: iksha)
    AUTH_ENABLED     – Set to "false" to disable auth in dev (default: true)
"""

import os
import logging
from typing import Optional
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
import httpx

logger = logging.getLogger("auth")

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:8180")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "iksha")
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "true").lower() == "true"

# Endpoints that do NOT require authentication
PUBLIC_PATHS = {"/", "/docs", "/openapi.json", "/redoc", "/favicon.ico"}

_jwks_client = None


def _get_certs_url() -> str:
    return f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"


def _get_userinfo_url() -> str:
    return f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/userinfo"


async def _validate_token_via_introspection(token: str) -> dict:
    """
    Validate JWT by calling Keycloak's userinfo endpoint.
    This avoids needing to handle JWKS/RS256 verification locally
    and works out of the box with a fresh Keycloak install.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            _get_userinfo_url(),
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return response.json()


class KeycloakAuthMiddleware(BaseHTTPMiddleware):
    """
    Intercepts requests and validates the Bearer token against Keycloak.
    Injects `request.state.user` and `request.state.tenant_id` on success.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip auth if disabled (dev mode)
        if not AUTH_ENABLED:
            request.state.user = {"sub": "dev-user", "preferred_username": "developer"}
            request.state.tenant_id = "default"
            return await call_next(request)

        # Skip public paths
        if request.url.path in PUBLIC_PATHS:
            return await call_next(request)

        # Extract token
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing Bearer token")

        token = auth_header.removeprefix("Bearer ").strip()

        try:
            user_info = await _validate_token_via_introspection(token)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise HTTPException(status_code=401, detail="Token validation failed")

        # Inject into request state
        request.state.user = user_info
        # Extract tenant from token claims (Keycloak custom claim or group)
        request.state.tenant_id = user_info.get("tenant_id", user_info.get("sub", "default"))

        return await call_next(request)
