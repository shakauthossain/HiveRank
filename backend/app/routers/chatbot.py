import os
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

load_dotenv()

router = APIRouter(tags=["chatbot"])

CHATBOT_BASE_URL = os.getenv("CHATBOT_BASE_URL", "https://api.risobuddy.com").rstrip(
    "/"
)
CHATBOT_API_KEY = os.getenv("CHATBOT_API_KEY", "").strip()
CHATBOT_API_PREFIX = "/api/v1"


class ChatAskBody(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    session_id: Optional[str] = None


def _headers() -> dict[str, str]:
    if not CHATBOT_API_KEY:
        raise HTTPException(status_code=503, detail="Chat widget is not configured")
    return {
        "X-API-Key": CHATBOT_API_KEY,
        "Accept": "application/json",
    }


def _raise_upstream(resp: httpx.Response) -> None:
    detail = "Chat service is unavailable"
    try:
        payload = resp.json()
        if isinstance(payload, dict) and payload.get("error"):
            detail = str(payload["error"])
    except Exception:
        pass
    raise HTTPException(status_code=502, detail=detail)


@router.get("/chatbot/config")
async def chatbot_config():
    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            resp = await client.get(
                f"{CHATBOT_BASE_URL}{CHATBOT_API_PREFIX}/chat/public/config",
                headers=_headers(),
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
    if resp.status_code >= 400:
        _raise_upstream(resp)
    return resp.json()


@router.post("/chatbot/ask")
async def chatbot_ask(body: ChatAskBody):
    payload: dict = {"query": body.query.strip()}
    if body.session_id:
        payload["session_id"] = body.session_id
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(
                f"{CHATBOT_BASE_URL}{CHATBOT_API_PREFIX}/chat/public/ask",
                headers={**_headers(), "Content-Type": "application/json"},
                json=payload,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
    if resp.status_code >= 400:
        _raise_upstream(resp)
    return resp.json()
