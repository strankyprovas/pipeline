"""
Opraví personalizaci v existujících Gmail draftech:
1. Předmět "Udělal jsem něco pro váš web" → extrahuje název firmy z těla a doplní
2. Špatné portfolio (restaurační pro non-restaurační odvětví) → opraví
3. "v {město}" bez správného pádu → opraví pomocí CITY_LOCATIVE
4. "Udělal jsem něco pro {name}" → přejmenuje na "Web pro {name} – připravil jsem ukázku zdarma"

Spuštění:
    venv/bin/python3 fix_drafts_personalization.py [--dry-run]
"""

import base64
import re
import sys
import time
from email import message_from_bytes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from gmail_draft import get_gmail_service, SENDER_EMAIL
from email_template import CITY_LOCATIVE, PORTFOLIO_BY_INDUSTRY

DRY_RUN = "--dry-run" in sys.argv

# Restaurační portfolio řetězce – pokud je v draftu jeden z těchto, je "špatné"
RESTAURANT_PORTFOLIO_STRINGS = [
    "piavarestaurace.cz a padthairestaurace.cz",
    "padthairestaurace.cz, aktuálně připravujeme web pro grasehaus.cz",
]

# Odvětvové slug z demo URL → industry key
DEMO_URL_TO_INDUSTRY = {
    "/restaurace/":  "restaurace",
    "/kavarny/":     "kavarna",
    "/kadernictvi/": "kadernictvi",
    "/kosmetika/":   "kosmetika",
    "/autoservis/":  "autoservis",
    "/masaze/":      "masaze",
    "/zubni/":       "zubni",
    "/psycholog/":   "psycholog",
    "/penzion/":     "penzion",
}


def get_industry_from_demo_url(body: str) -> str | None:
    """Zjistí odvětví z demo URL v těle emailu."""
    for slug, industry in DEMO_URL_TO_INDUSTRY.items():
        if slug in body:
            return industry
    return None


def extract_business_name_from_body(body: str) -> str:
    """Extrahuje název firmy z těla emailu – z 'nový web {name} mohl vypadat'."""
    m = re.search(r"nový web (.+?) mohl vypadat", body)
    if m:
        return m.group(1).strip()
    # Fallback: z "web {domain}" v intro
    m = re.search(r"web ([a-zA-Z0-9.-]+\.[a-z]{2,})", body)
    if m:
        return m.group(1)
    return ""


def fix_city_case(body: str) -> tuple[str, int]:
    """Opraví 'v {město}' → správný lokál. Vrátí (nové_tělo, počet_oprav)."""
    fixes = 0
    for city, locative in CITY_LOCATIVE.items():
        wrong = f"v {city}"
        correct = f"v {locative}"
        if wrong in body and correct not in body:
            body = body.replace(wrong, correct)
            fixes += 1
    return body, fixes


def fix_portfolio(body: str, industry: str) -> tuple[str, bool]:
    """Opraví špatné (restaurační) portfolio → správné pro dané odvětví."""
    correct_portfolio = PORTFOLIO_BY_INDUSTRY.get(industry, "")
    if not correct_portfolio:
        return body, False

    for old_str in RESTAURANT_PORTFOLIO_STRINGS:
        if old_str in body:
            # Nahraď celou větu portfolia
            body = re.sub(
                r"Naše poslední projekty jsou například [^.]+\.",
                f"Naše poslední projekty jsou například {correct_portfolio}.",
                body
            )
            return body, True
    return body, False


def decode_draft(raw_data: str) -> tuple[str, str, str, str]:
    """Dekóduje raw draft → (subject, to, body_plain, body_html)."""
    msg_bytes = base64.urlsafe_b64decode(raw_data + "==")
    msg = message_from_bytes(msg_bytes)

    subject = msg.get("Subject", "")
    to = msg.get("To", "")
    body_plain = ""
    body_html = ""

    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain" and not body_plain:
                body_plain = part.get_payload(decode=True).decode("utf-8", errors="replace")
            elif ct == "text/html" and not body_html:
                body_html = part.get_payload(decode=True).decode("utf-8", errors="replace")
    else:
        ct = msg.get_content_type()
        payload = msg.get_payload(decode=True).decode("utf-8", errors="replace")
        if ct == "text/html":
            body_html = payload
        else:
            body_plain = payload

    return subject, to, body_plain, body_html


def create_updated_draft(service, draft_id: str, to: str, subject: str,
                          body_plain: str, body_html: str) -> bool:
    """Smaže starý draft a vytvoří nový s opravenými daty."""
    try:
        # Vytvoř novou zprávu
        mime = MIMEMultipart("alternative")
        mime["From"] = SENDER_EMAIL
        mime["To"] = to
        mime["Subject"] = subject
        mime.attach(MIMEText(body_plain, "plain", "utf-8"))
        if body_html:
            mime.attach(MIMEText(body_html, "html", "utf-8"))

        raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()

        if DRY_RUN:
            print(f"    [DRY-RUN] Nový draft: To={to} | Subject={subject[:60]}")
            return True

        # Smaž starý
        service.users().drafts().delete(userId="me", id=draft_id).execute()
        time.sleep(0.3)

        # Vytvoř nový
        service.users().drafts().create(
            userId="me",
            body={"message": {"raw": raw}}
        ).execute()
        return True

    except Exception as e:
        print(f"    ❌ Chyba při update draftu {draft_id}: {e}")
        return False


def main():
    print(f"{'[DRY-RUN] ' if DRY_RUN else ''}Kontroluji drafty v Gmailu...\n")
    service = get_gmail_service()

    # Načti všechny drafty
    drafts = []
    page_token = None
    while True:
        result = service.users().drafts().list(
            userId="me",
            maxResults=500,
            pageToken=page_token
        ).execute()
        drafts.extend(result.get("drafts", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            break

    print(f"Nalezeno {len(drafts)} draftů celkem.\n")

    fixed_subject = 0
    fixed_portfolio = 0
    fixed_city = 0
    skipped = 0
    errors = 0

    for i, draft in enumerate(drafts):
        draft_id = draft["id"]
        try:
            full = service.users().drafts().get(
                userId="me", id=draft_id, format="raw"
            ).execute()
            raw = full["message"]["raw"]
            subject, to, body_plain, body_html = decode_draft(raw)

            if not to or "@" not in to:
                skipped += 1
                continue

            # Detekuj odvětví z demo URL
            industry = get_industry_from_demo_url(body_plain or body_html or "")
            needs_update = False
            new_subject = subject
            new_body_plain = body_plain
            new_body_html = body_html

            # ── FIX 1: Předmět "Udělal jsem něco pro váš web" ──
            if "váš web" in subject and "pro váš web" in subject:
                name = extract_business_name_from_body(body_plain or "")
                if name:
                    new_subject = f"Web pro {name} – ukázka modernizace zdarma"
                    print(f"[{i+1}] FIX subject (váš web→název): {subject[:50]} → {new_subject[:60]}")
                    fixed_subject += 1
                    needs_update = True
                else:
                    print(f"[{i+1}] WARN: Nelze extrahovat název z draftu {draft_id} (To: {to})")

            # ── FIX 2: Předmět "Udělal jsem něco pro {name}" → lepší subject ──
            elif subject.startswith("Udělal jsem něco pro ") and "váš web" not in subject:
                name = subject.replace("Udělal jsem něco pro ", "").strip()
                if name:
                    cat = "spatny_web" if industry and (body_plain or "").find("váš web") > 0 else "bez_webu"
                    new_subject = f"Web pro {name} – připravil jsem ukázku zdarma"
                    print(f"[{i+1}] FIX subject (Udělal→Web): {subject[:50]} → {new_subject[:60]}")
                    fixed_subject += 1
                    needs_update = True

            # ── FIX 3: Špatné (restaurační) portfolio pro non-restaurační odvětví ──
            if industry and industry != "restaurace":
                body_to_check = body_plain or body_html or ""
                if any(s in body_to_check for s in RESTAURANT_PORTFOLIO_STRINGS):
                    new_body_plain, changed_p = fix_portfolio(new_body_plain, industry)
                    new_body_html, changed_h = fix_portfolio(new_body_html, industry)
                    if changed_p or changed_h:
                        print(f"[{i+1}] FIX portfolio ({industry}): {to}")
                        fixed_portfolio += 1
                        needs_update = True

            # ── FIX 4: Špatný pád města ("v Ostrava" → "v Ostravě") ──
            if new_body_plain:
                fixed_plain, n = fix_city_case(new_body_plain)
                if n > 0:
                    new_body_plain = fixed_plain
                    fixed_city += n
                    needs_update = True
            if new_body_html:
                fixed_html, n = fix_city_case(new_body_html)
                if n > 0:
                    new_body_html = fixed_html
                    needs_update = True

            # ── Ulož opravený draft ──
            if needs_update:
                ok = create_updated_draft(
                    service, draft_id, to, new_subject, new_body_plain, new_body_html
                )
                if not ok:
                    errors += 1
                time.sleep(0.5)
            else:
                skipped += 1

        except Exception as e:
            print(f"[{i+1}] ERR draft {draft_id}: {e}")
            errors += 1
            continue

    print(f"""
══════════════════════════════════════
Výsledky opravy draftů:
  Opraveno předmětů:   {fixed_subject}
  Opraveno portfolia:  {fixed_portfolio}
  Opraveno pádů měst:  {fixed_city}
  Přeskočeno (OK):     {skipped}
  Chyby:               {errors}
══════════════════════════════════════
""")


if __name__ == "__main__":
    main()
