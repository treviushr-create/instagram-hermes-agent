"""Thin client for the Instagram Graph API (Instagram Login for Business).

Standard library only (urllib), on purpose — matches the convention Plow's
own agent tooling follows (agent-index-client, plow-agents) and avoids
adding a pip dependency the minimal Hermes base image doesn't already carry.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from .engine.domain import Signal, SignalKind
from .engine.ports import DeliveryError, DeliveryReceipt

GRAPH = "https://graph.instagram.com/v24.0"


def _access_token() -> str:
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "").strip()
    if not token:
        raise DeliveryError("INSTAGRAM_ACCESS_TOKEN não configurado", retryable=False)
    return token


def _account_id() -> str:
    account_id = os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID", "").strip()
    if not account_id:
        raise DeliveryError("INSTAGRAM_BUSINESS_ACCOUNT_ID não configurado", retryable=False)
    return account_id


def _request(method: str, path: str, *, params: dict[str, str] | None = None, body: dict | None = None) -> dict:
    query = dict(params or {})
    query["access_token"] = _access_token()
    url = f"{GRAPH}/{path}?{urllib.parse.urlencode(query)}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data else {},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        payload = json.loads(error.read().decode("utf-8") or "{}")
        message = payload.get("error", {}).get("message", str(error))
        retryable = error.code in {429, 500, 502, 503, 504}
        raise DeliveryError(message, retryable=retryable, status_code=error.code) from error
    except urllib.error.URLError as error:
        raise DeliveryError(str(error.reason), retryable=True) from error


def fetch_new_conversations(*, account_id: str | None = None) -> list[Signal]:
    """Poll GET /me/conversations for DMs. No webhook here on purpose — a

    Hermes agent has no inbound port (it only connects to Plow outbound), so
    polling is the only option.
    """
    account = account_id or _account_id()
    result = _request(
        "GET",
        f"{account}/conversations",
        params={"platform": "instagram", "fields": "participants,messages{message,from,created_time,id}"},
    )
    signals: list[Signal] = []
    for conversation in result.get("data", []):
        for message in conversation.get("messages", {}).get("data", []):
            sender = message.get("from", {})
            if sender.get("id") == account:
                continue  # our own outbound message, echoed back
            created_time = message.get("created_time")
            occurred_at = (
                datetime.fromisoformat(created_time.replace("Z", "+00:00"))
                if created_time
                else datetime.now(timezone.utc)
            )
            signals.append(
                Signal(
                    external_event_id=message["id"],
                    account_id=account,
                    platform_user_id=sender.get("id", ""),
                    kind=SignalKind.DIRECT_MESSAGE,
                    occurred_at=occurred_at,
                    sender_username=sender.get("username"),
                    text=message.get("message", ""),
                )
            )
    return signals


def fetch_new_tags(*, account_id: str | None = None) -> list[Signal]:
    """Poll GET /{account}/tags for posts where someone tagged this account.

    This is a different feed from mentions-in-a-comment (Meta only pushes
    those through a webhook, which a Hermes agent has no inbound port to
    receive) — tags on someone else's own post/reel are a plain, pollable
    list, so that's the one this agent can actually watch reliably.
    """
    account = account_id or _account_id()
    result = _request(
        "GET",
        f"{account}/tags",
        params={"fields": "id,caption,media_type,permalink,timestamp,username"},
    )
    signals: list[Signal] = []
    for media in result.get("data", []):
        timestamp = media.get("timestamp")
        occurred_at = (
            datetime.fromisoformat(timestamp.replace("Z", "+00:00")) if timestamp else datetime.now(timezone.utc)
        )
        signals.append(
            Signal(
                external_event_id=media["id"],
                account_id=account,
                platform_user_id=media.get("username", ""),
                kind=SignalKind.TAG,
                occurred_at=occurred_at,
                sender_username=media.get("username"),
                text=media.get("caption", ""),
                payload={"permalink": media.get("permalink", ""), "media_type": media.get("media_type", "")},
            )
        )
    return signals


def fetch_new_comments(*, account_id: str | None = None, recent_media_limit: int = 10) -> list[Signal]:
    """Poll comments on the account's own recent posts.

    Only checks the most recent `recent_media_limit` posts, not the whole
    history — a comment on a six-month-old post is not a "new signal" worth
    re-scanning every cycle, and scanning everything would make this call
    grow without bound as the account posts more.
    """
    account = account_id or _account_id()
    media_result = _request(
        "GET",
        f"{account}/media",
        params={"fields": "id", "limit": str(recent_media_limit)},
    )
    signals: list[Signal] = []
    for media in media_result.get("data", []):
        media_id = media["id"]
        comments_result = _request(
            "GET",
            f"{media_id}/comments",
            params={"fields": "id,text,username,timestamp"},
        )
        for comment in comments_result.get("data", []):
            timestamp = comment.get("timestamp")
            occurred_at = (
                datetime.fromisoformat(timestamp.replace("Z", "+00:00")) if timestamp else datetime.now(timezone.utc)
            )
            signals.append(
                Signal(
                    external_event_id=comment["id"],
                    account_id=account,
                    platform_user_id=comment.get("username", ""),
                    kind=SignalKind.COMMENT,
                    occurred_at=occurred_at,
                    sender_username=comment.get("username"),
                    text=comment.get("text", ""),
                    payload={"media_id": media_id},
                )
            )
    return signals


def send_text_message(*, recipient_id: str, text: str) -> DeliveryReceipt:
    result = _request(
        "POST",
        "me/messages",
        body={"recipient": {"id": recipient_id}, "message": {"text": text}},
    )
    message_id = result.get("message_id") or result.get("id")
    if not message_id:
        raise DeliveryError(f"resposta sem message_id: {result}", retryable=False)
    return DeliveryReceipt(message_id=message_id)


def reply_to_comment(*, comment_id: str, text: str) -> DeliveryReceipt:
    result = _request("POST", f"{comment_id}/replies", body={"message": text})
    comment_reply_id = result.get("id")
    if not comment_reply_id:
        raise DeliveryError(f"resposta sem id: {result}", retryable=False)
    return DeliveryReceipt(message_id=comment_reply_id)
