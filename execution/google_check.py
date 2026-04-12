from __future__ import annotations

import json
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def main() -> None:
    token_path = Path("token.json")
    token_data = json.loads(token_path.read_text(encoding="utf-8"))
    creds = Credentials.from_authorized_user_info(token_data)

    gmail = build("gmail", "v1", credentials=creds)
    drive = build("drive", "v3", credentials=creds)

    profile = gmail.users().getProfile(userId="me").execute()
    files = (
        drive.files()
        .list(pageSize=3, orderBy="modifiedTime desc", fields="files(name,mimeType)")
        .execute()
        .get("files", [])
    )

    print(f"Gmail connected for: {profile.get('emailAddress')}")
    print("Recent Drive files:")
    for file in files:
        print(f"- {file['name']} ({file['mimeType']})")


if __name__ == "__main__":
    main()
