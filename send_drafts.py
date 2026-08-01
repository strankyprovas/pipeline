"""
Odešle všechny Gmail drafty - 1 za minutu.
Použití: venv/bin/python3 send_drafts.py
         venv/bin/python3 send_drafts.py --delay 30   # 30 sekund mezi emaily
         venv/bin/python3 send_drafts.py --dry-run    # jen vypíše, nic neposílá
"""
import argparse
import base64
import re
import time
from datetime import datetime

import requests

from gmail_draft import get_gmail_service
from sheets import get_or_create_sheet, get_existing_emails, mark_email_sent

DEMO_URL_RE = re.compile(r"https://strankyprovas\.github\.io/[A-Za-z0-9._~\-/]+")


def _walk_parts(payload):
    """Rekurzivně projde části zprávy a vrátí dekódovaný text."""
    texts = []
    data = payload.get("body", {}).get("data")
    if data:
        try:
            texts.append(base64.urlsafe_b64decode(data).decode("utf-8", "ignore"))
        except Exception:
            pass
    for part in payload.get("parts", []) or []:
        texts.extend(_walk_parts(part))
    return texts


def get_draft_demo_url(service, draft_id):
    """Vytáhne z těla draftu odkaz na demo (nebo None)."""
    try:
        draft = service.users().drafts().get(
            userId="me", id=draft_id, format="full").execute()
        body = "\n".join(_walk_parts(draft["message"].get("payload", {})))
        m = DEMO_URL_RE.search(body)
        return m.group(0).rstrip("/") + "/" if m else None
    except Exception:
        return None


def demo_is_live(url, tries=2):
    """True, pokud demo odpovídá 200 (aby mail neodkazoval na 404)."""
    for attempt in range(tries):
        try:
            r = requests.get(url, timeout=12, allow_redirects=True)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        if attempt + 1 < tries:
            time.sleep(3)
    return False


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


def get_draft_info(service, draft_id):
    draft = service.users().drafts().get(userId="me", id=draft_id, format="metadata").execute()
    headers = draft["message"].get("payload", {}).get("headers", [])
    info = {h["name"]: h["value"] for h in headers if h["name"] in ("To", "Subject")}
    return info.get("To", "?"), info.get("Subject", "?")


def send_draft(service, draft_id):
    import re
    for attempt in range(10):
        try:
            service.users().drafts().send(userId="me", body={"id": draft_id}).execute()
            return
        except Exception as e:
            if "429" in str(e) or "rateLimitExceeded" in str(e):
                # Zjisti retry-after z chybové zprávy
                m = re.search(r'Retry after (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})', str(e))
                if m:
                    from datetime import datetime, timezone
                    retry_at = datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                    wait = max(10, (retry_at - datetime.now(timezone.utc)).total_seconds() + 5)
                else:
                    wait = 60 * (attempt + 1)
                print(f"           ⏳ Rate limit – čekám {int(wait)}s (pokus {attempt+1}/10)...")
                time.sleep(wait)
            elif "404" in str(e) or "notFound" in str(e):
                print(f"           ⚠️  Draft nenalezen (smazán/změněn), přeskakuji.")
                return
            elif "400" in str(e) or "invalidArgument" in str(e):
                print(f"           ⚠️  Neplatný draft (chybí příjemce?), přeskakuji.")
                return
            else:
                raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--delay", type=int, default=60, help="Sekund mezi emaily (default: 60)")
    parser.add_argument("--dry-run", action="store_true", help="Jen vypíše drafty, nic neposílá")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max. počet odeslaných e-mailů za běh (0 = bez omezení)")
    args = parser.parse_args()

    service = get_gmail_service()
    drafts = list_all_drafts(service)

    if not drafts:
        print("Žádné drafty k odeslání.")
        return

    # Načti již oslovené emaily ze Sheetu
    print("📊 Načítám již oslovené kontakty ze Sheetu...")
    sheet = get_or_create_sheet()
    already_sent = set()
    try:
        all_values = sheet.get_all_values()
        if len(all_values) > 1:
            header = all_values[0]
            email_col = header.index("Email") if "Email" in header else 3
            stav_col = header.index("Stav") if "Stav" in header else 10
            for row in all_values[1:]:
                email_val = row[email_col].lower().strip() if len(row) > email_col else ""
                stav_val = row[stav_col].strip() if len(row) > stav_col else ""
                if email_val and stav_val == "osloveno":
                    already_sent.add(email_val)
    except Exception as e:
        print(f"   ⚠️  Nepodařilo se načíst Sheet: {e}")
    print(f"   Již osloveno: {len(already_sent)} kontaktů\n")

    print(f"Nalezeno {len(drafts)} draftů. {'(DRY RUN)' if args.dry_run else f'Odesílám 1 za {args.delay}s.'}\n")

    # Stálé výjimky – podniky které již mají web od StránkyProVás
    EXCLUDED_KEYWORDS = ["piava", "padthai", "pad thai", "bratrs", "sekvent"]
    EXCLUDED_EMAILS = {
        "sekvent.d@seznam.cz",
        "kavarna@duocoffee.cz",
        "restaurantkatak@gmail.com",
        "kadernictvi.zohan@gmail.com",
        "axonlife1@gmail.com",
        "principal@zapletalove.cz",
        "sylviarampova@gmail.com",
        "auto-cont@volny.cz",
        "radekzraly@tiscali.cz",
        "jakoubkovapetra@gmail.com",
        "chef.yuzusushi@gmail.com",
        "hieucon.cz@gmail.com",
        "lennytalianova@gmail.com",
        "info@labellezza.cz",
        "libuse.prochazkova@pojdtedal.cz",
        "lucie.vrtisova@vinnykost.cz",
        "ales.buran@gmail.com",
        "buran@klenoty-buran.cz",
        "ndprostejov@gmail.com",
        "yvet.rohrich@gmail.com",
        "hovtvacake@gmail.com",
        "kubesova@masazecb.cz",
        "rezervace@muslov.cz",
        "mauritz.stozec@mybox.cz",
        "kentorirestaurace25@gmail.com",
        "mmoravek00@volny.cz",
        "info@studiozeny.cz",
        "santiagoarteagajesus@gmail.com",
        "holicstvi.mischell@gmail.com",
        "info@cafisco.eu",
        "ln.novacek@gmail.com",
        "hello@pizzabolka.cz",
        "info@terapiepolacek.cz",
        "marta.csontosova@mojegenerace.cz",
        "lukydv1114@gmail.com",
        "karolina.zohova@gmail.com",
        "petrajurakova@centrum.cz",
        "legierskym@gmail.com",
        "horackova-kristyna@seznam.cz",
        "autovit@autovit.cz",
    }

    sent_this_run = set()  # deduplikace v rámci tohoto běhu
    sent_count = 0
    skipped_count = 0

    for i, draft in enumerate(drafts, 1):
        draft_id = draft["id"]
        try:
            to, subject = get_draft_info(service, draft_id)
        except Exception:
            continue

        to_email = to.lower().strip()
        ts = datetime.now().strftime("%H:%M:%S")

        # Přeskoč chráněné podniky (již mají web od nás)
        if to_email in EXCLUDED_EMAILS or any(kw in to_email for kw in EXCLUDED_KEYWORDS):
            print(f"[{ts}] [{i}/{len(drafts)}] 🚫 Vyloučeno (náš klient) → {to}")
            skipped_count += 1
            continue

        # Přeskoč pokud již osloveno nebo duplicitní v tomto běhu
        if to_email in already_sent:
            print(f"[{ts}] [{i}/{len(drafts)}] ⏭️  Přeskočeno (již osloveno) → {to}")
            skipped_count += 1
            continue
        if to_email in sent_this_run:
            print(f"[{ts}] [{i}/{len(drafts)}] ⏭️  Přeskočeno (duplicitní email v draftech) → {to}")
            skipped_count += 1
            continue

        # ⚠️ Neodesílat, dokud demo není živé – jinak příjemce klikne na 404.
        # (GitHub Pages build zaostává za pushem; draft zůstane a pošle se příště.)
        demo_url = get_draft_demo_url(service, draft_id)
        if demo_url and not demo_is_live(demo_url):
            print(f"[{ts}] [{i}/{len(drafts)}] ⏳ Demo ještě nenaběhlo (404) → {to} | {demo_url}")
            skipped_count += 1
            continue

        if args.dry_run:
            print(f"[{ts}] [{i}/{len(drafts)}] {to} | {subject}")
        else:
            print(f"[{ts}] [{i}/{len(drafts)}] Odesílám → {to} | {subject}")
            send_draft(service, draft_id)
            sent_this_run.add(to_email)
            sent_count += 1
            # Označ jako osloveno v Sheetu
            try:
                mark_email_sent(sheet, to)
            except Exception as e:
                print(f"           ⚠️  Sheet update selhal: {e}")
            print(f"           ✓ Odesláno")

            if args.limit and sent_count >= args.limit:
                print(f"\n📭 Dosažen limit {args.limit} e-mailů pro tento běh, končím.")
                break

            if i < len(drafts):
                print(f"           Čekám {args.delay}s...")
                time.sleep(args.delay)

    print(f"\nHotovo! {'(dry run)' if args.dry_run else f'Odesláno {sent_count}, přeskočeno {skipped_count}.'}")


if __name__ == "__main__":
    main()
