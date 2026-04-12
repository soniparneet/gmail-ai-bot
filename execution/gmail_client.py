from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from email.utils import parseaddr
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


PROCESSED_LABEL = "AI Processed"
VERIFY_LABEL = "AI_Verify_to_Delete"
REQUIRED_LABELS = (PROCESSED_LABEL, VERIFY_LABEL)


@dataclass
class MessageDetails:
    message_id: str
    thread_id: str
    sender: str
    sender_email: str
    subject: str
    snippet: str
    body: str
    label_ids: list[str]


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def directives_dir() -> Path:
    remote_dir = Path("/root/directives")
    if remote_dir.exists():
        return remote_dir
    return project_root() / "directives"


def load_credentials() -> Credentials:
    token_json = os.environ.get("GOOGLE_TOKEN_JSON")
    if token_json:
        token_data = json.loads(token_json)
    else:
        token_path = project_root() / "token.json"
        token_data = json.loads(token_path.read_text(encoding="utf-8"))

    creds = Credentials.from_authorized_user_info(token_data)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def gmail_service():
    return build("gmail", "v1", credentials=load_credentials())


def get_profile_email(service: Any) -> str:
    profile = service.users().getProfile(userId="me").execute()
    return profile.get("emailAddress", "").strip().lower()


def list_labels(service: Any) -> list[dict[str, Any]]:
    response = service.users().labels().list(userId="me").execute()
    return response.get("labels", [])


def ensure_labels(service: Any, md_path: Path) -> dict[str, str]:
    labels = list_labels(service)
    existing = {label["name"]: label["id"] for label in labels}
    for name in REQUIRED_LABELS:
        if name not in existing:
            created = (
                service.users()
                .labels()
                .create(
                    userId="me",
                    body={
                        "name": name,
                        "labelListVisibility": "labelShow",
                        "messageListVisibility": "show",
                    },
                )
                .execute()
            )
            existing[created["name"]] = created["id"]

    labels = list_labels(service)
    final_map = {label["name"]: label["id"] for label in labels}
    write_labels_markdown(md_path, final_map)
    return final_map


def write_labels_markdown(md_path: Path, label_map: dict[str, str]) -> None:
    lines = [
        "# Gmail Labels",
        "",
        "This file is refreshed dynamically at runtime from `users.labels.list`.",
        "",
        "Required labels:",
        "",
        "- `AI Processed`",
        "- `AI_Verify_to_Delete`",
        "",
        "## Current Mapping",
        "",
        "| Label Name | Label ID |",
        "| --- | --- |",
    ]
    for name in sorted(label_map):
        lines.append(f"| {name} | {label_map[name]} |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_label_map(md_path: Path) -> dict[str, str]:
    mapping = {}
    if not md_path.exists():
        return mapping
    for line in md_path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        parts = [part.strip() for part in line.split("|")[1:-1]]
        if len(parts) != 2 or parts[0] in {"Label Name", "---"}:
            continue
        mapping[parts[0]] = parts[1]
    return mapping


def poll_query(after_epoch: int) -> str:
    return f'label:INBOX -label:"{PROCESSED_LABEL}" after:{after_epoch}'


def historical_query(from_date: date, to_date: date) -> str:
    after_value = from_date.strftime("%Y/%m/%d")
    before_value = (to_date + timedelta(days=1)).strftime("%Y/%m/%d")
    return (
        f'label:INBOX -label:"{PROCESSED_LABEL}" '
        f"after:{after_value} before:{before_value}"
    )


def list_message_ids(service: Any, query: str, page_token: str | None = None) -> dict[str, Any]:
    return (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=100, pageToken=page_token)
        .execute()
    )


def _decode_body(data: str | None) -> str:
    if not data:
        return ""
    decoded = base64.urlsafe_b64decode(data.encode("utf-8"))
    return decoded.decode("utf-8", errors="ignore")


def _extract_body(payload: dict[str, Any]) -> str:
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")
    if mime_type == "text/plain" and body_data:
        return _decode_body(body_data)

    parts = payload.get("parts", [])
    for part in parts:
        text = _extract_body(part)
        if text:
            return text

    if body_data:
        return _decode_body(body_data)
    return ""


def get_message_details(service: Any, message_id: str) -> MessageDetails:
    data = (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )
    headers = {
        header["name"]: header["value"]
        for header in data.get("payload", {}).get("headers", [])
    }
    sender = headers.get("From", "")
    _, sender_email = parseaddr(sender)
    subject = headers.get("Subject", "")
    snippet = data.get("snippet", "")
    body = _extract_body(data.get("payload", {})) or snippet
    return MessageDetails(
        message_id=data["id"],
        thread_id=data.get("threadId", ""),
        sender=sender,
        sender_email=sender_email.lower(),
        subject=subject,
        snippet=snippet,
        body=body,
        label_ids=data.get("labelIds", []),
    )


def add_labels(service: Any, message_id: str, label_ids: list[str]) -> None:
    if not label_ids:
        return
    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={"addLabelIds": label_ids, "removeLabelIds": []},
    ).execute()


def resolve_self_emails(service: Any) -> set[str]:
    emails = set()
    primary = get_profile_email(service)
    if primary:
        emails.add(primary)

    env_value = os.environ.get("AI_BOT_SELF_EMAILS", "")
    for item in env_value.split(","):
        email = item.strip().lower()
        if email:
            emails.add(email)
    return emails


def within_last_20_minutes_epoch(now: datetime | None = None) -> int:
    current = now or datetime.now(timezone.utc)
    return int((current - timedelta(minutes=20)).timestamp())
