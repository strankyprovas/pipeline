"""
Opraví broken click-tracking linky ve stávajících draftech.
Nahradí script.google.com redirect přímým GitHub Pages URL.
"""
import base64
import re
import email
from urllib.parse import urlparse, parse_qs, unquote
from gmail_draft import get_gmail_service

TRACKING_DOMAIN = "script.google.com"


def get_all_drafts(service):
    drafts = []
    page_token = None
    while True:
        resp = service.users().drafts().list(userId="me", pageToken=page_token).execute()
        drafts.extend(resp.get("drafts", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return drafts


def get_draft_full(service, draft_id):
    return service.users().drafts().get(userId="me", id=draft_id, format="full").execute()


def decode_part(part):
    data = part.get("body", {}).get("data", "")
    if data:
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
    return ""


def extract_parts(payload):
    """Rekurzivně extrahuje plain a html části."""
    plain, html = "", ""
    mime = payload.get("mimeType", "")
    if mime == "text/plain":
        plain = decode_part(payload)
    elif mime == "text/html":
        html = decode_part(payload)
    for part in payload.get("parts", []):
        p, h = extract_parts(part)
        if p: plain = p
        if h: html = h
    return plain, html


def fix_tracking_urls(html):
    """Nahradí href=script.google.com/... přímým redirect URL."""
    # &amp; i & varianta (HTML entity encoding)
    pattern = re.compile(
        r'href="(https://script\.google\.com/macros/s/[^"]+?(?:&amp;|&)redirect=([^"&]+)[^"]*)"'
    )
    count = 0
    def replacer(m):
        nonlocal count
        direct_url = unquote(m.group(2))
        count += 1
        return f'href="{direct_url}"'
    fixed = pattern.sub(replacer, html)
    return fixed, count


def delete_draft(service, draft_id):
    service.users().drafts().delete(userId="me", id=draft_id).execute()


def create_draft_raw(service, to_email, subject, plain, html):
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    msg = MIMEMultipart("alternative")
    msg["To"] = to_email
    msg["From"] = "matyas.vrbaa@gmail.com"
    msg["Subject"] = subject
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = service.users().drafts().create(
        userId="me", body={"message": {"raw": raw}}
    ).execute()
    return draft["id"]


def main():
    service = get_gmail_service()
    drafts = get_all_drafts(service)
    print(f"Nalezeno {len(drafts)} draftů")

    fixed = 0
    skipped = 0

    for i, d in enumerate(drafts, 1):
        try:
            draft_full = get_draft_full(service, d["id"])
        except Exception as e:
            print(f"  [{i}/{len(drafts)}] ⚠️  Přeskočeno (chyba: {e}) – {d['id']}")
            skipped += 1
            continue
        msg = draft_full["message"]
        payload = msg["payload"]

        # Hlavičky
        headers = {h["name"]: h["value"] for h in payload.get("headers", [])}
        to_email = headers.get("To", "")
        subject = headers.get("Subject", "")

        plain, html = extract_parts(payload)

        if not html or TRACKING_DOMAIN not in html:
            print(f"  [{i}/{len(drafts)}] OK (bez tracking URL) – {to_email}")
            skipped += 1
            continue

        fixed_html, count = fix_tracking_urls(html)
        if count == 0:
            print(f"  [{i}/{len(drafts)}] OK – {to_email}")
            skipped += 1
            continue

        # Smaž starý, vytvoř nový
        delete_draft(service, d["id"])
        new_id = create_draft_raw(service, to_email, subject, plain, fixed_html)
        print(f"  [{i}/{len(drafts)}] ✅ Opraveno ({count}x) – {to_email}")
        fixed += 1

    print(f"\nHotovo: {fixed} opraveno, {skipped} přeskočeno")


if __name__ == "__main__":
    main()
