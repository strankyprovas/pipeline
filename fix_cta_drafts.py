"""
Opraví poslední odstavec (CTA) ve všech Gmail draftech.
Nahradí starý text o "zdarma návrh + cenová nabídka" za jednodušší CTA.
"""
import base64
import email
import email.header
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from gmail_draft import get_gmail_service

OLD_PATTERN = (
    r"Můžu vám zdarma připravit stručný návrh, jak by mohl vypadat nový web .+?"
    r"můžeme si pak dát krátký 10[–\-]15\s?min hovor a projít návrh společně\. 🙂"
)

NEW_TEXT = "Pokud vás ukázka zaujme, klidně se můžeme spojit na krátký 10–15min hovor a projít návrh společně. 🙂"

SEARCH_STRING = "Můžu vám zdarma připravit"


def fix_drafts():
    service = get_gmail_service()

    # Načti všechny drafty
    drafts = []
    page_token = None
    while True:
        resp = service.users().drafts().list(userId="me", maxResults=100, pageToken=page_token).execute()
        drafts.extend(resp.get("drafts", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    print(f"Celkem {len(drafts)} draftů v Gmailu")

    fixed = 0
    skipped = 0
    errors = 0

    for d in drafts:
        draft_id = d["id"]
        try:
            full = service.users().drafts().get(userId="me", id=draft_id, format="raw").execute()
        except Exception as e:
            errors += 1
            continue

        raw_data = full["message"].get("raw", "")
        if not raw_data:
            skipped += 1
            continue

        raw_bytes = base64.urlsafe_b64decode(raw_data)
        msg = email.message_from_bytes(raw_bytes)

        # Zkontroluj jestli draft obsahuje starý text
        has_old = False
        for part in msg.walk():
            if part.get_content_type() in ("text/plain", "text/html"):
                payload = part.get_payload(decode=True)
                if payload and SEARCH_STRING in payload.decode("utf-8", errors="replace"):
                    has_old = True
                    break

        if not has_old:
            skipped += 1
            continue

        # Extrahuj hlavičky
        to_email = msg.get("To", "")
        subject = msg.get("Subject", "")
        # Decode encoded subject
        decoded_subj = email.header.decode_header(subject)
        subj_parts = []
        for part_val, charset in decoded_subj:
            if isinstance(part_val, bytes):
                subj_parts.append(part_val.decode(charset or "utf-8", errors="replace"))
            else:
                subj_parts.append(part_val)
        subject_str = "".join(subj_parts)

        # Extrahuj a oprav plain text a HTML
        plain_body = ""
        html_body = ""
        for part in msg.walk():
            ct = part.get_content_type()
            payload = part.get_payload(decode=True)
            if not payload:
                continue
            text = payload.decode("utf-8", errors="replace")
            if ct == "text/plain":
                plain_body = re.sub(OLD_PATTERN, NEW_TEXT, text, flags=re.DOTALL)
            elif ct == "text/html":
                html_body = re.sub(OLD_PATTERN, NEW_TEXT, text, flags=re.DOTALL)

        if not plain_body and not html_body:
            skipped += 1
            continue

        # Sestav nový MIME message
        new_msg = MIMEMultipart("alternative")
        new_msg["To"] = to_email
        new_msg["From"] = msg.get("From", "matyas.vrbaa@gmail.com")
        new_msg["Subject"] = subject  # Keep original encoded subject

        if plain_body:
            new_msg.attach(MIMEText(plain_body, "plain", "utf-8"))
        if html_body:
            new_msg.attach(MIMEText(html_body, "html", "utf-8"))

        new_raw = base64.urlsafe_b64encode(new_msg.as_bytes()).decode("ascii")

        try:
            service.users().drafts().update(
                userId="me",
                id=draft_id,
                body={"message": {"raw": new_raw}},
            ).execute()
            fixed += 1
            print(f"  ✅ [{fixed}] {subject_str[:70]}")
        except Exception as e:
            errors += 1
            print(f"  ❌ {subject_str[:50]}: {e}")

    print(f"\n✅ Hotovo: {fixed} opraveno, {skipped} přeskočeno, {errors} chyb")


if __name__ == "__main__":
    fix_drafts()
