from __future__ import annotations

import os
from typing import Any

import httpx


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def load_autoworkflow_review_config(config: dict | None = None) -> dict[str, Any]:
    cfg = config or {}
    section = cfg.get("autoworkflow_review", {}) if isinstance(cfg, dict) else {}
    if not isinstance(section, dict):
        section = {}
    return {
        "enabled": _truthy(section.get("enabled") or os.getenv("AUTOWORKFLOW_REVIEW_ENABLED")),
        "base_url": str(
            section.get("base_url")
            or os.getenv("AUTOWORKFLOW_REVIEW_BASE_URL")
            or "http://127.0.0.1:8882"
        ).rstrip("/"),
        "api_token": str(
            section.get("api_token") or os.getenv("AUTOWORKFLOW_REVIEW_API_TOKEN") or ""
        ),
        "digest_limit": int(section.get("digest_limit") or os.getenv("AUTOWORKFLOW_REVIEW_DIGEST_LIMIT") or 5),
    }


def _headers(api_token: str) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"
    return headers


async def list_review_items(base_url: str, api_token: str, limit: int = 5) -> list[dict[str, Any]]:
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            f"{base_url}/api/review-items",
            headers=_headers(api_token),
            params={"status": "awaiting_review", "limit": max(1, min(limit, 20))},
        )
        resp.raise_for_status()
        return resp.json()


async def get_review_item(base_url: str, api_token: str, review_item_id: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            f"{base_url}/api/review-items/{review_item_id}",
            headers=_headers(api_token),
        )
        resp.raise_for_status()
        return resp.json()


async def submit_review_decision(
    base_url: str,
    api_token: str,
    review_item_id: str,
    action: str,
    notes: str = "",
) -> dict[str, Any]:
    if action not in {"approve", "reject", "edit", "defer"}:
        raise ValueError(f"Unsupported review action: {action}")
    payload: dict[str, Any]
    if action == "edit":
        payload = {"instruction": notes}
    else:
        payload = {"reviewer_notes": notes}
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            f"{base_url}/api/review-items/{review_item_id}/{action}",
            headers=_headers(api_token),
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()


def render_review_cards(items: list[dict[str, Any]]) -> str:
    if not items:
        return "No review items pending."
    lines: list[str] = ["Review queue:"]
    for item in items:
        item_id = item.get("id", "")
        title = item.get("title") or item.get("summary") or "Untitled"
        summary = item.get("summary") or ""
        priority = item.get("priority")
        confidence = item.get("confidence")
        risk = item.get("risk_level") or "unknown"
        lines.append(f"#{item_id} {title}")
        if summary and summary != title:
            lines.append(f"Why: {summary}")
        meta: list[str] = []
        if priority is not None:
            meta.append(f"priority {priority}")
        if confidence is not None:
            try:
                meta.append(f"confidence {float(confidence):.0%}")
            except (TypeError, ValueError):
                pass
        meta.append(f"risk {risk}")
        lines.append("Meta: " + ", ".join(meta))
        lines.append("")
    lines.append("Reply: /approve <id>, /reject <id> why, /edit <id> instruction, /defer <id>")
    return "\n".join(lines)
