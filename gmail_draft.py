"""
Automatické vytváření Gmail draftů přes Gmail API
"""
import base64
import os
import pickle
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "credentials.json")
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "token.pickle")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.compose",
]

from config import SENDER_EMAIL, SENDER_NAME  # jediný zdroj pravdy


def get_gmail_service():
    import fcntl
    import time as _time

    def _load():
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "rb") as f:
                return pickle.load(f)
        return None

    creds = _load()
    if creds and creds.valid:
        return build("gmail", "v1", credentials=creds)

    # Obnova tokenu pod zámkem – jen jeden proces naráz (zabrání revokaci při souběhu)
    lock_path = TOKEN_FILE + ".lock"
    with open(lock_path, "w") as lockf:
        fcntl.flock(lockf, fcntl.LOCK_EX)
        try:
            creds = _load()
            if creds and creds.valid:
                return build("gmail", "v1", credentials=creds)
            if creds and creds.expired and creds.refresh_token:
                for attempt in range(3):
                    try:
                        creds.refresh(Request())
                        break
                    except Exception:
                        if attempt == 2:
                            raise
                        _time.sleep(2)
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            tmp = TOKEN_FILE + ".tmp"
            with open(tmp, "wb") as f:
                pickle.dump(creds, f)
            os.replace(tmp, TOKEN_FILE)
        finally:
            fcntl.flock(lockf, fcntl.LOCK_UN)

    return build("gmail", "v1", credentials=creds)


def create_draft(to_email, subject, body_plain, body_html):
    """Vytvoří Gmail draft s HTML i plain text verzí."""
    service = get_gmail_service()

    msg = MIMEMultipart("alternative")
    msg["To"] = to_email
    # Jméno se musí zakódovat podle RFC 2047, jinak diakritika v hlavičce
    # skončí jako mojibake. formataddr + Header to udělá správně.
    msg["From"] = formataddr((str(Header(SENDER_NAME, "utf-8")), SENDER_EMAIL))
    msg["Subject"] = subject

    msg.attach(MIMEText(body_plain, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = service.users().drafts().create(
        userId="me",
        body={"message": {"raw": raw}}
    ).execute()

    return draft["id"]
