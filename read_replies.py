"""
Přečte odpovědi na outreach emaily z posledního týdne a připraví drafty.
"""
import base64
import os
import pickle
import re
import json
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

import anthropic
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "credentials.json")
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "token_replies.pickle")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.modify",
]

from config import SENDER_EMAIL  # jediný zdroj pravdy
SENDER_NAME = "Matyáš Vrba"
FIRMA = "StránkyProVás"


def get_gmail_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Zkusí použít existující token z gmail_draft.py s rozšířenými scopes
            old_token = os.path.join(os.path.dirname(__file__), "token.pickle")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=58135, open_browser=False)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
    return build("gmail", "v1", credentials=creds)


def decode_body(part):
    """Dekóduje tělo emailu."""
    data = part.get("body", {}).get("data", "")
    if data:
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    return ""


def get_email_text(payload):
    """Extrahuje plain text z emailu."""
    mime_type = payload.get("mimeType", "")
    if mime_type == "text/plain":
        return decode_body(payload)
    if mime_type in ("multipart/alternative", "multipart/mixed", "multipart/related"):
        for part in payload.get("parts", []):
            text = get_email_text(part)
            if text:
                return text
    return ""


def get_header(headers, name):
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def fetch_replies_last_week(service):
    """Načte všechny odpovědi z posledního týdne."""
    since = (datetime.now() - timedelta(days=7)).strftime("%Y/%m/%d")

    # Hledáme emaily v inboxu od externích odesílatelů (ne od nás)
    query = f"after:{since} -from:{SENDER_EMAIL} in:inbox"

    results = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=50
    ).execute()

    messages = results.get("messages", [])
    replies = []

    for msg_ref in messages:
        msg = service.users().messages().get(
            userId="me",
            id=msg_ref["id"],
            format="full"
        ).execute()

        headers = msg["payload"].get("headers", [])
        subject = get_header(headers, "Subject")
        sender = get_header(headers, "From")
        reply_to_header = get_header(headers, "In-Reply-To")
        message_id = get_header(headers, "Message-ID")
        thread_id = msg.get("threadId", "")

        # Filtrujeme pouze odpovědi (mají In-Reply-To nebo Re: v subject)
        is_reply = bool(reply_to_header) or subject.lower().startswith("re:")
        if not is_reply:
            continue

        body = get_email_text(msg["payload"])

        # Extrahujeme email odesílatele
        sender_email_match = re.search(r'<(.+?)>', sender)
        sender_email = sender_email_match.group(1) if sender_email_match else sender
        sender_name = re.sub(r'<.+?>', '', sender).strip().strip('"')

        replies.append({
            "id": msg_ref["id"],
            "thread_id": thread_id,
            "subject": subject,
            "sender": sender,
            "sender_email": sender_email,
            "sender_name": sender_name,
            "message_id": message_id,
            "body": body.strip()[:3000],  # Max 3000 znaků
            "date": datetime.fromtimestamp(int(msg["internalDate"]) / 1000).strftime("%d.%m.%Y %H:%M")
        })

    return replies


def classify_and_reply(reply):
    """Použije Claude k zhodnocení zájmu a přípravě odpovědi."""
    client = anthropic.Anthropic()

    prompt = f"""Jsi Matyáš Vrba ze StránkyProVás – vytváříš profesionální weby pro restaurace a malé firmy.

Dostal jsi tuto odpověď na svůj outreach email:

Od: {reply['sender_name']} ({reply['sender_email']})
Předmět: {reply['subject']}
Datum: {reply['date']}

Obsah emailu:
---
{reply['body']}
---

Úkol:
1. Urči, zda jde o ZÁJEM o web (pozitivní reakce, otázky k ceně/procesu/demo) nebo NEZÁJEM/SPAM/jiné.
2. Pokud jde o ZÁJEM: napiš zdvořilou, přirozenou českou odpověď, která:
   - Odpovídá na konkrétní otázky z emailu
   - Navrhuje krátký hovor nebo schůzku
   - Je stručná (max 150 slov)
   - Nepůsobí jako šablona
   - Podepiš: Matyáš Vrba, StránkyProVás
3. Pokud jde o NEZÁJEM: napiš jen "NEZÁJEM"

Odpověz ve formátu JSON:
{{
  "zajem": true/false,
  "duvod": "krátké vysvětlení",
  "odpoved_text": "text odpovědi nebo NEZÁJEM"
}}"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )

    try:
        result = json.loads(response.content[0].text)
        return result
    except:
        return {"zajem": False, "duvod": "Chyba parsování", "odpoved_text": "NEZÁJEM"}


def create_draft(service, reply, odpoved_text):
    """Vytvoří Gmail draft jako odpověď na email."""
    msg = MIMEMultipart("alternative")
    msg["To"] = reply["sender_email"]
    msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
    msg["Subject"] = f"Re: {reply['subject'].replace('Re: ', '').replace('RE: ', '')}"
    msg["In-Reply-To"] = reply["message_id"]
    msg["References"] = reply["message_id"]

    # Plain text
    msg.attach(MIMEText(odpoved_text, "plain", "utf-8"))

    # HTML verze
    html = odpoved_text.replace('\n', '<br>')
    html_body = f"""<div style="font-family: Arial, sans-serif; font-size: 14px; color: #333;">
{html}
</div>"""
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    draft = service.users().drafts().create(
        userId="me",
        body={
            "message": {
                "raw": raw,
                "threadId": reply["thread_id"]
            }
        }
    ).execute()

    return draft["id"]


def main():
    print("Připojuji se k Gmail API...")
    service = get_gmail_service()

    print("Načítám odpovědi z posledního týdne...")
    replies = fetch_replies_last_week(service)

    if not replies:
        print("Žádné odpovědi z posledního týdne nenalezeny.")
        return

    print(f"\nNalezeno {len(replies)} odpovědí. Analyzuji...\n")

    drafted = 0
    skipped = 0

    for i, reply in enumerate(replies, 1):
        print(f"[{i}/{len(replies)}] {reply['sender_name']} ({reply['sender_email']}) – {reply['subject'][:50]}")

        result = classify_and_reply(reply)

        if result.get("zajem"):
            print(f"  ✅ ZÁJEM: {result['duvod']}")
            draft_id = create_draft(service, reply, result["odpoved_text"])
            print(f"  📧 Draft vytvořen (ID: {draft_id})")
            print(f"  Náhled odpovědi:\n{result['odpoved_text'][:200]}...\n")
            drafted += 1
        else:
            print(f"  ⏭️  PŘESKOČENO: {result['duvod']}\n")
            skipped += 1

    print(f"\n{'='*50}")
    print(f"Hotovo! Vytvořeno {drafted} draftů, přeskočeno {skipped} emailů.")
    print(f"Drafty najdeš v Gmail → Koncepty.")


if __name__ == "__main__":
    main()
