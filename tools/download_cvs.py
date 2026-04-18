# tools/download_cvs.py
# Purpose: Download CVs from Google Drive to .tmp/cvs/ using Drive API
# Outputs: list of cv dicts with local path

import os
import sys
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import io

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DIR = os.path.join(BASE_DIR, ".tmp", "cvs")
CREDS_DIR = os.path.join(BASE_DIR, "credentials")
CLIENT_SECRET_PATH = os.path.join(
    BASE_DIR, "google CLI",
    "client_secret_746931370436-l52j2fjjbfqsndjc2u0n0o8k9nj0dp70.apps.googleusercontent.com.json"
)
TOKEN_PATH = os.path.join(CREDS_DIR, "drive_token.pickle")

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

CV_FILES = [
    {
        "key": "operations",
        "drive_id": "1-aY7EYKN9wPfSSL4-izoiQ5DyMD2PvN8",
        "filename": "Omar_Shawada_Operations_CV_ATS.pdf",
        "name": "Operations CV",
        "keywords": ["operations", "supply chain", "logistics", "warehouse", "inventory",
                     "procurement", "distribution", "sourcing", "purchasing"],
    },
    {
        "key": "planning",
        "drive_id": "1yuoaq2jNsvftZwDldHBK-ZhC88HVq9lC",
        "filename": "Omar_Shawada_Planning_CV_ATS.pdf",
        "name": "Planning CV",
        "keywords": ["planning", "scheduling", "forecasting", "demand", "capacity",
                     "strategic", "analyst", "coordinator", "s&op", "mrp", "erp"],
    },
    {
        "key": "production",
        "drive_id": "1DoRzFFPVk8IHectMfzQxvqVA680gUrH4",
        "filename": "Omar_Shawada_ProductionPlanning_CV_ATS.pdf",
        "name": "Production Planning CV",
        "keywords": ["production", "manufacturing", "factory", "lean", "bom",
                     "quality", "industrial", "engineering", "automotive", "plant"],
    },
]


def get_drive_service():
    os.makedirs(CREDS_DIR, exist_ok=True)
    creds = None

    # On Railway (no local token file): load from env variable
    if not os.path.exists(TOKEN_PATH):
        token_b64 = os.environ.get("GOOGLE_OAUTH_TOKEN_B64")
        if token_b64:
            import base64
            with open(TOKEN_PATH, "wb") as f:
                f.write(base64.b64decode(token_b64))

    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_PATH, "wb") as f:
                pickle.dump(creds, f)
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
            with open(TOKEN_PATH, "wb") as f:
                pickle.dump(creds, f)

    return build("drive", "v3", credentials=creds), creds


def download_cv(cv: dict, service) -> str:
    os.makedirs(TMP_DIR, exist_ok=True)
    local_path = os.path.join(TMP_DIR, cv["filename"])

    request = service.files().get_media(fileId=cv["drive_id"])
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    with open(local_path, "wb") as f:
        f.write(buffer.getvalue())

    return local_path


def get_all_cvs(force_download: bool = False) -> list[dict]:
    result = []
    needs_download = force_download or any(
        not os.path.exists(os.path.join(TMP_DIR, cv["filename"])) for cv in CV_FILES
    )

    service = None
    if needs_download:
        service, _ = get_drive_service()

    for cv in CV_FILES:
        local_path = os.path.join(TMP_DIR, cv["filename"])
        if needs_download or not os.path.exists(local_path):
            download_cv(cv, service)
        result.append({**cv, "path": local_path})

    return result


# Also export creds for Gmail reuse
def get_gmail_creds():
    _, creds = get_drive_service()
    return creds


if __name__ == "__main__":
    print("Downloading CVs from Google Drive...")
    cvs = get_all_cvs(force_download=True)
    for cv in cvs:
        size = os.path.getsize(cv["path"])
        print(f"  {cv['name']}: {cv['path']} ({size:,} bytes)")
