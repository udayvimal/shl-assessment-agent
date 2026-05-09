"""
SHL Assessment Advisor — FastAPI service
Endpoints: GET /health, POST /chat
"""
from __future__ import annotations

import os
import time
from collections import defaultdict
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator

load_dotenv()

import agent as shl_agent  # noqa: E402 (after dotenv)

app = FastAPI(title="SHL Assessment Advisor", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Rate limiting — 20 requests per IP per minute (in-memory sliding window)
# ---------------------------------------------------------------------------

_ip_requests: defaultdict[str, list[float]] = defaultdict(list)
_RATE_LIMIT = 20
_RATE_WINDOW = 60.0


def _check_rate_limit(ip: str) -> bool:
    now = time.time()
    _ip_requests[ip] = [t for t in _ip_requests[ip] if now - t < _RATE_WINDOW]
    if len(_ip_requests[ip]) >= _RATE_LIMIT:
        return False
    _ip_requests[ip].append(now)
    return True


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class Message(BaseModel):
    role: str
    content: str

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v: str) -> str:
        if v not in ("user", "assistant"):
            raise ValueError("role must be 'user' or 'assistant'")
        return v


class ChatRequest(BaseModel):
    messages: list[Message]

    @field_validator("messages")
    @classmethod
    def messages_not_empty(cls, v: list[Message]) -> list[Message]:
        if not v:
            raise ValueError("messages must not be empty")
        return v


class Recommendation(BaseModel):
    name: str
    url: str
    test_type: str
    test_types: list[str] = []


class ChatResponse(BaseModel):
    reply: str
    recommendations: list[Recommendation]
    suggestions: list[str] = []
    end_of_conversation: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, req: Request) -> ChatResponse:
    ip = req.client.host if req.client else "unknown"
    if not _check_rate_limit(ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded — max 20 requests per minute. Please wait.",
        )

    messages = [m.model_dump() for m in request.messages]

    # Enforce 8-turn cap (user + assistant turns combined)
    if len(messages) > 8:
        messages = messages[-8:]

    try:
        result: dict[str, Any] = shl_agent.chat(messages)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return ChatResponse(
        reply=result["reply"],
        recommendations=[
            Recommendation(**r) for r in result.get("recommendations", [])
        ],
        suggestions=result.get("suggestions", []),
        end_of_conversation=result.get("end_of_conversation", False),
    )
