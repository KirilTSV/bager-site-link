"""Isolated, deny-by-default MCP HTTP service for BAGER SITE LINK.

This is a separate ASGI application. It is NOT imported or mounted by app/main.py.
Production deployment is intentionally out of scope until OAuth and staging checks pass.
"""
import json
import logging
import os
import time
import uuid
from contextvars import ContextVar

import jwt
from jwt import PyJWKClient
from mcp.server.fastmcp import FastMCP
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import Participant
from .chatgpt_connector_readonly import (
    ConnectorAccessDenied, project_summary, recent_trips, monitoring_alerts,
)

_log = logging.getLogger("bager.mcp.audit")
_actor_id: ContextVar[str | None] = ContextVar("bager_mcp_actor", default=None)
_mcp = FastMCP("BAGER SITE LINK", stateless_http=True, json_response=True)


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing mandatory MCP configuration: {name}")
    return value


class TokenVerifier:
    """Validate JWT signature, issuer, audience, expiry and required scope."""
    def __init__(self, issuer: str, audience: str, jwks_url: str):
        if not issuer.startswith("https://") or not jwks_url.startswith("https://"):
            raise ValueError("OAuth issuer and JWKS URL must use HTTPS")
        self.issuer = issuer
        self.audience = audience
        self.keys = PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=300)

    def verify(self, token: str) -> str:
        if not token or len(token) > 8192:
            raise ValueError("Invalid token length")
        key = self.keys.get_signing_key_from_jwt(token).key
        claims = jwt.decode(token, key, algorithms=["RS256"], issuer=self.issuer,
                            audience=self.audience, options={"require": ["exp", "iat", "sub"]},
                            leeway=30)
        scopes = claims.get("scope", "").split()
        if "bager:read" not in scopes:
            raise ValueError("Missing bager:read scope")
        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject:
            raise ValueError("Missing subject")
        return subject


def _subject_map() -> dict[str, str]:
    raw = _required_env("BAGER_MCP_SUBJECT_MAP_JSON")
    mapping = json.loads(raw)
    if not isinstance(mapping, dict) or not mapping or not all(
        isinstance(k, str) and k and isinstance(v, str) and v
        for k, v in mapping.items()
    ):
        raise RuntimeError("Subject map must be a nonempty object of subject -> participant ID")
    return mapping


def _actor(db: Session):
    participant_id = _actor_id.get()
    if not participant_id:
        raise ConnectorAccessDenied("No authenticated MCP actor")
    actor = db.get(Participant, participant_id)
    if actor is None or actor.status != "active":
        raise ConnectorAccessDenied("Actor is missing or inactive")
    return actor


def _run_tool(tool_name: str, callback):
    request_id = str(uuid.uuid4())
    started = time.monotonic()
    status = "error"
    actor_id = _actor_id.get()
    try:
        with SessionLocal() as db:
            result = callback(db, _actor(db))
        status = "ok"
        return result
    finally:
        # Log metadata only. Never log bearer tokens, coordinates or raw payloads.
        _log.info(json.dumps({
            "request_id": request_id, "tool": tool_name, "actor_id": actor_id,
            "status": status, "duration_ms": int((time.monotonic()-started)*1000),
        }))


@_mcp.tool()
def get_project_summary() -> dict:
    """Read verified operational totals for the authenticated user's own project."""
    return _run_tool("get_project_summary", project_summary)


@_mcp.tool()
def get_recent_trips(limit: int = 20) -> dict:
    """Read recent trip statuses for the authenticated user's own project."""
    return _run_tool("get_recent_trips", lambda db, actor: recent_trips(db, actor, limit))


@_mcp.tool()
def get_monitoring_alerts(limit: int = 20) -> dict:
    """Read existing operational alerts. Does not trigger a scan."""
    return _run_tool("get_monitoring_alerts",
                     lambda db, actor: monitoring_alerts(db, actor, limit))


class OAuthBoundary:
    """ASGI authentication boundary, applied before the MCP protocol handler."""
    def __init__(self, inner, verifier, subject_map):
        self.inner = inner
        self.verifier = verifier
        self.subject_map = subject_map

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            # No websocket transport supported.
            await send({"type": "websocket.close", "code": 1008}) if scope["type"] == "websocket" else None
            return
        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        auth = headers.get(b"authorization", b"").decode("latin1")
        actor_id = None
        if auth.startswith("Bearer "):
            try:
                subject = self.verifier.verify(auth[7:])
                actor_id = self.subject_map.get(subject)
            except (jwt.PyJWTError, ValueError, KeyError):
                pass
        if not actor_id:
            body = b'{"error":"unauthorized"}'
            await send({"type": "http.response.start", "status": 401,
                        "headers": [(b"content-type", b"application/json"),
                                    (b"cache-control", b"no-store"),
                                    (b"www-authenticate", b'Bearer realm="bager-mcp"')]})
            await send({"type": "http.response.body", "body": body})
            return
        marker = _actor_id.set(actor_id)
        try:
            await self.inner(scope, receive, send)
        finally:
            _actor_id.reset(marker)


def create_app():
    """Fail closed at startup if any mandatory OAuth configuration is missing."""
    issuer = _required_env("BAGER_MCP_OAUTH_ISSUER")
    audience = _required_env("BAGER_MCP_OAUTH_AUDIENCE")
    jwks_url = _required_env("BAGER_MCP_OAUTH_JWKS_URL")
    mapping = _subject_map()
    return OAuthBoundary(_mcp.streamable_http_app(),
                         TokenVerifier(issuer, audience, jwks_url), mapping)


# Run via: uvicorn app.mcp_server:app --factory --host 127.0.0.1 --port 8765
def app():
    return create_app()
