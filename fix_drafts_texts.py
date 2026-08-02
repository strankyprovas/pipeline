#!/usr/bin/env python3
"""Přepíše těla existujících Gmail draftů opravenými šablonami.

Vzniklo 2. 8. 2026: drafty z přechodového období mají špatný obor
("weby pro podniky" místo "pro pekárny") nebo rozbitý pád u města
("v Benátky nad Jizerou"). Smazat je nelze – podnik už je zapsaný
v Google Sheetu a dedup by ho podruhé nenabídl, takže by lead zmizel.

Použití:
    venv/bin/python3 fix_drafts_texts.py            # jen vypíše, co by změnil
    venv/bin/python3 fix_drafts_texts.py --apply    # skutečně přepíše
"""
import base64
import re
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from email_template import CITY_LOCATIVE, generate_email
from gmail_draft import SENDER_EMAIL, get_gmail_service

APPLY = "--apply" in sys.argv

# Odpovídá INDUSTRY_PAGES_URL v main.py. Nekopírujeme importem, protože main.py
# používá anotace `X | None`, které systémový Python 3.9 na Macu neumí spustit.
PATH_TO_INDUSTRY = {
    "restaurace": "restaurace",
    "kavarny": "kavarna",
    "pekarna": "pekarna",
    "kvetinarstvi": "kvetinarstvi",
    "penzion": "penzion",
    "kadernictvi": "kadernictvi",
    "kosmetika": "kosmetika",
    "autoservis": "autoservis",
    "masaze": "masaze",
    "zubni": "zubni",
    "psycholog": "psycholog",
}
# lokál -> nominativ, pro zpětné dohledání města z textu
LOCATIVE_TO_CITY = {v: k for k, v in CITY_LOCATIVE.items()}


def decode_part(payload):
    """Vytáhne text/plain tělo z Gmail payloadu."""
    if payload.get("body", {}).get("data"):
        if payload.get("mimeType") == "text/plain":
            return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", "replace")
    for part in payload.get("parts", []) or []:
        found = decode_part(part)
        if found:
            return found
    return ""


def parse_draft(body: str):
    """Z těla draftu zrekonstruuje vstupy pro generate_email()."""
    m = re.search(r"→ (https://strankyprovas\.github\.io/\S+)", body)
    if not m:
        return None
    demo_url = m.group(1).rstrip("/") + "/"
    parts = demo_url.rstrip("/").split("/")
    slug, repo_dir = parts[-1], parts[-2]
    industry = PATH_TO_INDUSTRY.get(repo_dir)
    if not industry:
        return None

    m = re.search(r"jak by nový web (.+?) mohl vypadat", body)
    name = m.group(1).strip() if m else ""

    # Má podnik starý web, nebo žádný?
    m = re.search(r"Díval jsem se na váš web (\S+?) a napadlo", body)
    if m:
        website, category, city = "https://" + m.group(1), "spatny_web", ""
    else:
        website, category = "", "bez_webu"
        m = re.search(r"Díval jsem se na .+? v (.+?) a napadlo", body)
        raw = m.group(1).strip() if m else ""
        # text obsahuje buď správný lokál ("Brně"), nebo u starých draftů
        # rovnou nominativ ("Benátky nad Jizerou") – zvládneme obojí
        city = LOCATIVE_TO_CITY.get(raw, raw)

    return {
        "restaurant": {"name": name, "website": website, "category": category,
                       "industry": industry, "slug": slug},
        "demo_url": demo_url,
        "city": city,
    }


def main():
    service = get_gmail_service()
    drafts = service.users().drafts().list(userId="me", maxResults=100).execute().get("drafts", [])
    print(f"Nalezeno {len(drafts)} draftů.\n")

    changed = skipped = 0
    for d in drafts:
        full = service.users().drafts().get(userId="me", id=d["id"], format="full").execute()
        msg = full["message"]
        headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
        to, subject = headers.get("to", ""), headers.get("subject", "")
        old_body = decode_part(msg["payload"])

        parsed = parse_draft(old_body)
        if not parsed:
            print(f"  ⏭️  {to} – nerozpoznán formát, nechávám být")
            skipped += 1
            continue

        fresh = generate_email(parsed["restaurant"], demo_url=parsed["demo_url"], city=parsed["city"])
        new_body = fresh["body"]

        if new_body.strip() == old_body.strip():
            print(f"  ✓  {to} – už je aktuální")
            skipped += 1
            continue

        def intro(t):
            m = re.search(r"vytváříme moderní weby (pro [^.]+?)\.", t)
            return m.group(1) if m else "?"

        print(f"  ✏️  {to}  [{parsed['restaurant']['industry']}]")
        print(f"       před: ...{intro(old_body)}...")
        print(f"       po:   ...{intro(new_body)}...")

        if APPLY:
            m = MIMEMultipart("alternative")
            m["To"], m["From"], m["Subject"] = to, SENDER_EMAIL, subject
            m.attach(MIMEText(new_body, "plain", "utf-8"))
            m.attach(MIMEText(fresh["html_body"], "html", "utf-8"))
            raw = base64.urlsafe_b64encode(m.as_bytes()).decode()
            service.users().drafts().update(
                userId="me", id=d["id"], body={"message": {"raw": raw}}
            ).execute()
        changed += 1

    print(f"\n{'Přepsáno' if APPLY else 'K přepsání'}: {changed}, beze změny: {skipped}")
    if not APPLY and changed:
        print("Spusť znovu s --apply pro skutečný zápis.")


if __name__ == "__main__":
    main()
