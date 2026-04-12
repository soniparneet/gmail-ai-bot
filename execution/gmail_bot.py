from __future__ import annotations

import os
import time
from datetime import date
from pathlib import Path
from typing import Any

import modal

from execution.classifier import (
    IMPORTANT_CATEGORY,
    LOW_VALUE_CATEGORY,
    load_directive_bundle,
    classify_email,
)
from execution.gmail_client import (
    PROCESSED_LABEL,
    VERIFY_LABEL,
    add_labels,
    directives_dir,
    ensure_labels,
    get_message_details,
    gmail_service,
    historical_query,
    list_message_ids,
    poll_query,
    read_label_map,
    resolve_self_emails,
    within_last_20_minutes_epoch,
)


DIRECTIVES_REMOTE_PATH = "/root/directives"
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
APP_NAME = "ai-email-bot-phase2"

image = (
    modal.Image.debian_slim()
    .pip_install(
        "fastapi",
        "uvicorn",
        "google-api-python-client",
        "google-auth-oauthlib",
        "google-auth-httplib2",
        "google-generativeai",
    )
    .add_local_dir("directives", remote_path=DIRECTIVES_REMOTE_PATH)
    .add_local_python_source("execution")
)

app = modal.App(APP_NAME)
google_secret = modal.Secret.from_name("google-integration-secrets")
gemini_secret = modal.Secret.from_name("gemini-api-secret")


def _directive_paths() -> tuple[Path, Path]:
    root = directives_dir()
    return root, root / "gmail_labels.md"


def _reload_directives() -> tuple[Any, dict[str, str]]:
    root, labels_path = _directive_paths()
    bundle = load_directive_bundle(root)
    label_map = read_label_map(labels_path)
    return bundle, label_map


def _refresh_labels(service: Any) -> dict[str, str]:
    _, labels_path = _directive_paths()
    return ensure_labels(service, labels_path)


def _classify_and_apply(service: Any, message_id: str) -> dict[str, Any]:
    _refresh_labels(service)
    bundle, label_map = _reload_directives()
    details = get_message_details(service, message_id)
    self_emails = resolve_self_emails(service)

    labels_to_add = [label_map[PROCESSED_LABEL]]
    category = IMPORTANT_CATEGORY
    ignored = False

    if details.sender_email in self_emails:
        ignored = True
    else:
        category = classify_email(
            bundle=bundle,
            gemini_api_key=os.environ["GEMINI_API_KEY"],
            sender=details.sender,
            subject=details.subject,
            body=f"{details.snippet}\n\n{details.body}",
            model_name=MODEL_NAME,
        )
        if category == LOW_VALUE_CATEGORY:
            labels_to_add.append(label_map[VERIFY_LABEL])

    add_labels(service, details.message_id, labels_to_add)
    return {
        "message_id": details.message_id,
        "subject": details.subject,
        "sender": details.sender,
        "category": category,
        "ignored_self_email": ignored,
        "applied_labels": labels_to_add,
    }


def run_poll_cycle() -> dict[str, Any]:
    service = gmail_service()
    _refresh_labels(service)
    _reload_directives()

    query = poll_query(within_last_20_minutes_epoch())
    response = list_message_ids(service, query)
    messages = response.get("messages", [])
    print(f"Starting poll cycle with {len(messages)} candidate messages.")

    processed = []
    for message in messages:
        processed.append(_classify_and_apply(service, message["id"]))
        print(f"Processed poll message {message['id']}")
        time.sleep(0.25)

    return {
        "status": "ok",
        "mode": "poll",
        "query": query,
        "processed_count": len(processed),
        "processed": processed,
    }


def run_historical_backfill(from_date: date, to_date: date) -> dict[str, Any]:
    service = gmail_service()
    _refresh_labels(service)
    _reload_directives()

    query = historical_query(from_date, to_date)
    processed = []
    page_token = None
    batch_number = 0

    while True:
        response = list_message_ids(service, query, page_token=page_token)
        batch_messages = response.get("messages", [])
        batch_number += 1
        print(
            f"Historical batch {batch_number}: processing {len(batch_messages)} messages "
            f"for range {from_date.isoformat()} to {to_date.isoformat()}."
        )
        for message in batch_messages:
            processed.append(_classify_and_apply(service, message["id"]))
            print(f"Processed historical message {message['id']}")
            if len(processed) % 10 == 0:
                time.sleep(1.0)
            else:
                time.sleep(0.2)

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    low_value_count = sum(1 for item in processed if item["category"] == LOW_VALUE_CATEGORY)
    important_count = sum(1 for item in processed if item["category"] == IMPORTANT_CATEGORY)

    return {
        "status": "ok",
        "mode": "historical",
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "processed_count": len(processed),
        "low_value_count": low_value_count,
        "important_count": important_count,
        "processed": processed,
    }


def status_payload() -> dict[str, Any]:
    bundle, label_map = _reload_directives()
    return {
        "status": "ok",
        "app": APP_NAME,
        "model": MODEL_NAME,
        "directives_loaded": sorted(bundle.all_markdown.keys()),
        "labels_known": sorted(label_map.keys()),
    }


@app.function(
    image=image,
    secrets=[google_secret, gemini_secret],
    schedule=modal.Period(seconds=60),
    timeout=900,
)
def poll_gmail() -> dict[str, Any]:
    return run_poll_cycle()


@app.function(image=image, secrets=[google_secret, gemini_secret], timeout=3600)
@modal.asgi_app()
def api():
    from execution.api_server import create_app

    return create_app(
        run_historical=run_historical_backfill,
        get_status=status_payload,
    )
