"""
Odešle všechny Gmail drafty - 1 za minutu.
Použití: venv/bin/python3 send_drafts.py
         venv/bin/python3 send_drafts.py --delay 30   # 30 sekund mezi emaily
         venv/bin/python3 send_drafts.py --dry-run    # jen vypíše, nic neposílá
"""
import argparse
import time
from datetime import datetime

from gmail_draft import get_gmail_service
from sheets import get_or_create_sheet, get_existing_emails, mark_email_sent


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
    service.users().drafts().send(userId="me", body={"id": draft_id}).execute()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--delay", type=int, default=60, help="Sekund mezi emaily (default: 60)")
    parser.add_argument("--dry-run", action="store_true", help="Jen vypíše drafty, nic neposílá")
    args = parser.parse_args()

    service = get_gmail_service()
    drafts = list_all_drafts(service)

    if not drafts:
        print("Žádné drafty k odeslání.")
        return

    # Načti již oslovené emaily ze Sheetu
    print("📊 Načítám již oslovené kontakty ze Sheetu...")
    sheet = get_or_create_sheet()
    already_sent = get_existing_emails(sheet)  # všechny emaily v DB
    # Načti jen ty co jsou "osloveno" – přečteme záznamy ručně
    try:
        records = sheet.get_all_records()
        already_sent = {r["Email"].lower() for r in records if r.get("Stav") == "osloveno" and r.get("Email")}
    except Exception:
        already_sent = set()
    print(f"   Již osloveno: {len(already_sent)} kontaktů\n")

    print(f"Nalezeno {len(drafts)} draftů. {'(DRY RUN)' if args.dry_run else f'Odesílám 1 za {args.delay}s.'}\n")

    # Stálé výjimky – podniky které již mají web od StránkyProVás
    EXCLUDED_KEYWORDS = ["piava", "padthai", "pad thai", "bratrs", "sekvent"]
    EXCLUDED_EMAILS = {"sekvent.d@seznam.cz"}

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

            if i < len(drafts):
                print(f"           Čekám {args.delay}s...")
                time.sleep(args.delay)

    print(f"\nHotovo! {'(dry run)' if args.dry_run else f'Odesláno {sent_count}, přeskočeno {skipped_count}.'}")


if __name__ == "__main__":
    main()
