from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path


LOW_VALUE_CATEGORY = "LowValue"
IMPORTANT_CATEGORY = "Important"
DEFAULT_MODEL = "gemini-2.5-flash"
LOW_VALUE_MATCHES = ("lowvalue", "low value", "marketing", "promotional", "clutter")
LOW_VALUE_SIGNAL_KEYWORDS = [
    "unsubscribe",
    "manage preferences",
    "view in browser",
    "newsletter",
    "promotion",
    "limited time",
    "deal",
    "offer",
    "upgrade now",
    "blog update",
    "release notes",
    "community update",
    "notification",
    "digest",
    "summary",
]

PROTECTED_KEYWORDS = {
    "financial": [
        "bank",
        "transaction",
        "credit card",
        "debit card",
        "statement",
        "invoice",
        "bill",
        "receipt",
        "payment",
        "spent",
        "withdrawal",
        "deposit",
        "otp",
        "alert",
    ],
    "legal": [
        "agreement",
        "contract",
        "compliance",
        "policy update",
        "terms of service",
        "legal notice",
        "privacy notice",
    ],
    "jobs": [
        "interview",
        "recruiter",
        "job offer",
        "application update",
        "candidate",
        "hiring",
        "role",
    ],
    "calendar": [
        "meeting invite",
        "calendar",
        "event confirmation",
        "invite.ics",
        "zoom meeting",
        "google meet",
        "scheduled",
    ],
    "security": [
        "password reset",
        "login alert",
        "verification code",
        "otp",
        "2fa",
        "fraud alert",
        "security alert",
    ],
    "personal": [
        "dad",
        "mom",
        "family",
        "friend",
        "wedding",
        "birthday",
    ],
}


@dataclass
class DirectiveBundle:
    directives_dir: Path
    instructions_text: str
    labels_text: str
    all_markdown: dict[str, str]


def load_directive_bundle(directives_dir: Path) -> DirectiveBundle:
    markdown_files = {}
    for path in sorted(directives_dir.glob("*.md")):
        markdown_files[path.name] = path.read_text(encoding="utf-8")

    return DirectiveBundle(
        directives_dir=directives_dir,
        instructions_text=markdown_files.get("gmail_instructions.md", ""),
        labels_text=markdown_files.get("gmail_labels.md", ""),
        all_markdown=markdown_files,
    )


def trim_text(value: str, limit: int = 3000) -> str:
    clean = re.sub(r"\s+", " ", value or "").strip()
    return clean[:limit]


def has_protected_keywords(subject: str, sender: str, body: str) -> bool:
    haystack = " ".join([subject or "", sender or "", body or ""]).lower()
    return any(keyword in haystack for items in PROTECTED_KEYWORDS.values() for keyword in items)


def extract_low_value_signals(sender: str, subject: str, body: str) -> list[str]:
    haystack = " ".join([sender or "", subject or "", body or ""]).lower()
    return [keyword for keyword in LOW_VALUE_SIGNAL_KEYWORDS if keyword in haystack]


def build_prompt(
    bundle: DirectiveBundle,
    sender: str,
    subject: str,
    body: str,
    low_value_signals: list[str],
) -> str:
    trimmed_body = trim_text(body, 1500)
    trimmed_instructions = trim_text(bundle.instructions_text, 2200)
    signal_text = ", ".join(low_value_signals) if low_value_signals else "none"
    return (
        "You are classifying one email.\n"
        "Follow these rules:\n"
        f"{trimmed_instructions}\n\n"
        "Return exactly one line:\n"
        "- Category: LowValue\n"
        "- Category: Important\n\n"
        f"Sender: {trim_text(sender, 200)}\n"
        f"Subject: {trim_text(subject, 300)}\n"
        f"LowValueSignals: {signal_text}\n"
        f"Body: {trimmed_body}\n"
    )


def normalize_category(response_text: str) -> str:
    normalized = re.sub(r"[^a-z]+", " ", (response_text or "").lower()).strip()
    if any(match in normalized for match in LOW_VALUE_MATCHES):
        return LOW_VALUE_CATEGORY
    return IMPORTANT_CATEGORY


def classify_email(
    *,
    bundle: DirectiveBundle,
    gemini_api_key: str,
    sender: str,
    subject: str,
    body: str,
    model_name: str = DEFAULT_MODEL,
) -> str:
    if has_protected_keywords(subject, sender, body):
        return IMPORTANT_CATEGORY

    import google.generativeai as genai

    genai.configure(api_key=gemini_api_key)
    model = genai.GenerativeModel(model_name)
    low_value_signals = extract_low_value_signals(sender, subject, body)
    prompt = build_prompt(bundle, sender, subject, body, low_value_signals)

    delay_seconds = 1.0
    for attempt in range(3):
        try:
            response = model.generate_content(prompt)
            response_text = getattr(response, "text", "") or ""
            return normalize_category(response_text)
        except Exception:
            if attempt == 2:
                return IMPORTANT_CATEGORY
            time.sleep(delay_seconds)
            delay_seconds *= 2

    return IMPORTANT_CATEGORY
