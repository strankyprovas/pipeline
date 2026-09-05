"""
Projde všechny Gmail drafty a přepíše starou cenu na novou (500 Kč měsíčně).
Použití: venv/bin/python3 fix_draft_price.py
         venv/bin/python3 fix_draft_price.py --dry-run
"""
import argparse
import base64
import re
import time
from gmail_draft import get_gmail_service


OLD_PRICES = [
    "1 000 Kč měsíčně",
    "1000 Kč měsíčně",
    "2 000 Kč ročně",
    "2000 Kč ročně",
    "1 000 Kč/měsíc",
    "2 000 Kč/rok",
]
NEW_PRICE = "500 Kč měsíčně"


def list_all_drafts(service):
    drafts = []
    page_token = None
    while True:
        resp = service.users().drafts().list(userId="me", pageToken=page_token).execute()
        drafts.extend(resp.get("drafts", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return drafts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    service = get_gmail_service()
    drafts = list_all_drafts(service)
    print(f"Nalezeno {len(drafts)} draftů.\n")

    fixed = 0
    skipped = 0

    for i, draft in enumerate(drafts, 1):
        draft_id = draft["id"]
        try:
            full = service.users().drafts().get(userId="me", id=draft_id, format="full").execute()
        except Exception as e:
            print(f"[{i}] Chyba při čtení draftu: {e}")
            continue

        message = full.get("message", {})
        payload = message.get("payload", {})

        # Get headers
        headers = {h["name"]: h["value"] for h in payload.get("headers", [])}
        subject = headers.get("Subject", "?")
        to = headers.get("To", "?")

        # Find and decode body
        body_data = None
        body_part = None

        # Check direct body
        if payload.get("body", {}).get("data"):
            body_data = payload["body"]["data"]
            body_part = payload["body"]
        # Check parts (multipart)
        for part in payload.get("parts", []):
            if part.get("mimeType") in ("text/plain", "text/html"):
                if part.get("body", {}).get("data"):
                    body_data = part["body"]["data"]
                    body_part = part["body"]
                    break
            # Nested parts
            for sub in part.get("parts", []):
                if sub.get("mimeType") in ("text/plain", "text/html"):
                    if sub.get("body", {}).get("data"):
                        body_data = sub["body"]["data"]
                        body_part = sub["body"]
                        break

        if not body_data:
            skipped += 1
            continue

        decoded = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")

        # Check if any old price is present
        needs_fix = False
        new_body = decoded
        for old in OLD_PRICES:
            if old in new_body:
                needs_fix = True
                new_body = new_body.replace(old, NEW_PRICE)

        if not needs_fix:
            skipped += 1
            continue

        if args.dry_run:
            print(f"[{i}/{len(drafts)}] OPRAVIT → {to} | {subject}")
            fixed += 1
            continue

        # Re-encode
        encoded = base64.urlsafe_b64encode(new_body.encode("utf-8")).decode("ascii")

        # Rebuild the message raw from the full message
        # Easier: update draft with new raw message
        # Build raw email from headers + new body
        raw_headers = ""
        for h in payload.get("headers", []):
            if h["name"] in ("From", "To", "Subject", "Content-Type", "MIME-Version",
                             "References", "In-Reply-To", "Thread-Id"):
                raw_headers += f"{h['name']}: {h['value']}\r\n"

        if "Content-Type" not in raw_headers:
            raw_headers += "Content-Type: text/html; charset=utf-8\r\n"
        if "MIME-Version" not in raw_headers:
            raw_headers += "MIME-Version: 1.0\r\n"

        raw_message = raw_headers + "\r\n" + new_body
        raw_b64 = base64.urlsafe_b64encode(raw_message.encode("utf-8")).decode("ascii")

        try:
            service.users().drafts().update(
                userId="me",
                id=draft_id,
                body={
                    "message": {
                        "raw": raw_b64,
                        "threadId": message.get("threadId"),
                    }
                }
            ).execute()
            print(f"[{i}/{len(drafts)}] ✓ Opraveno → {to} | {subject}")
            fixed += 1
        except Exception as e:
            print(f"[{i}/{len(drafts)}] ✗ Chyba: {e}")

        time.sleep(0.5)  # rate limit

    print(f"\nHotovo! Opraveno: {fixed}, přeskočeno: {skipped}")


if __name__ == "__main__":
    main()
