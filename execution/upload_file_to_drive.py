from __future__ import annotations

import argparse
import json
import mimetypes
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def load_credentials(token_path: Path) -> Credentials:
    token_data = json.loads(token_path.read_text(encoding="utf-8"))
    return Credentials.from_authorized_user_info(token_data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload a local file to Google Drive.")
    parser.add_argument("--file", required=True, help="Path to the local file to upload.")
    parser.add_argument(
        "--token",
        default="token.json",
        help="Path to the Google authorized user token JSON.",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Optional target file name in Google Drive.",
    )
    args = parser.parse_args()

    file_path = Path(args.file).resolve()
    token_path = Path(args.token).resolve()
    creds = load_credentials(token_path)
    service = build("drive", "v3", credentials=creds)

    mime_type = mimetypes.guess_type(file_path.name)[0] or "text/markdown"
    metadata = {"name": args.name or file_path.name}
    media = MediaFileUpload(str(file_path), mimetype=mime_type, resumable=False)
    created = service.files().create(
        body=metadata,
        media_body=media,
        fields="id,name,mimeType,webViewLink",
    ).execute()

    print(json.dumps(created, ensure_ascii=True))


if __name__ == "__main__":
    main()
