# gmail-ai-bot

Version: `0.1.0`

Production-oriented Gmail AI bot for real-time polling and historical inbox cleanup using Modal, Gmail API, and Gemini.

## Repository Layout

Canonical repository structure:

```text
src/
  core/
  services/
  integrations/
utils/
config/
tests/
.env.example
README.md
CHANGELOG.md
```

Project-specific runtime structure preserved from earlier requirements:

```text
execution/   # executable Python entrypoints and operational scripts
directives/  # runtime instructions, mappings, and rules
```

## Current Components

- `execution/gmail_bot.py`: Modal app with 60-second polling and historical classification API.
- `execution/gmail_client.py`: Gmail label management, message fetch, and query helpers.
- `execution/classifier.py`: Gemini-backed LOW_VALUE vs IMPORTANT classifier with conservative fallbacks.
- `execution/api_server.py`: FastAPI surface for health and historical processing.
- `execution/google_auth.py`: Local OAuth bootstrap for Gmail/Drive scopes.
- `execution/google_check.py`: Local connectivity verification.
- `execution/upload_file_to_drive.py`: Utility to publish files into Google Drive.
- `directives/gmail_instructions.md`: Runtime classification policy.
- `directives/gmail_labels.md`: Dynamic Gmail label mapping refreshed at runtime.
- `directives/agents.md`: DOE operating rules.

## Setup

1. Create a virtual environment and activate it.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a local env file from `.env.example`.
4. Authenticate Google locally:

```bash
python execution/google_auth.py --client-secrets /path/to/client_secret.json --output token.json
```

5. Deploy to Modal:

```bash
python -m modal deploy execution/gmail_bot.py
```

## Runtime Notes

- The bot re-reads `directives/` at the start of every cycle and before each email classification.
- The bot never removes `INBOX` and never deletes emails automatically.
- Gmail and Gemini credentials must be provided through Modal secrets or local secure environment variables, never hardcoded.

## Testing

```bash
pytest
```
