from __future__ import annotations

import argparse
import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/drive.file",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Authenticate this project with Gmail and Google Drive."
    )
    parser.add_argument(
        "--client-secrets",
        required=True,
        help="Path to the Google OAuth client secrets JSON file.",
    )
    parser.add_argument(
        "--output",
        default="token.json",
        help="Path where the authorized user token JSON should be written.",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    flow = InstalledAppFlow.from_client_secrets_file(args.client_secrets, SCOPES)
    creds = flow.run_local_server(port=0)

    output_path.write_text(creds.to_json() + "\n", encoding="utf-8")

    token_data = json.loads(output_path.read_text(encoding="utf-8"))
    print(f"Saved token with scopes: {', '.join(token_data.get('scopes', []))}")
    print(f"Token written to {output_path.resolve()}")


if __name__ == "__main__":
    main()
