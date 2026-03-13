"""
Projde Gmail Odesláno a označí v Sheetu kontakty, kterým byl email odeslán.
Opraví stav z 'nový' na 'osloveno' + zapíše datum odeslání.

Použití:
    venv/bin/python3 sync_sent.py
    venv/bin/python3 sync_sent.py --dry-run   # jen výpis, nic neměnit
"""
import argparse
import re
from datetime import datetime

from gmail_draft import get_gmail_service
from sheets import get_or_create_sheet, HEADERS, mark_email_sent, _colorize_row


def get_sent_date(service, email: str) -> str | None:
    """Vrátí datum prvního odeslaného emailu na tuto adresu, nebo None."""
    try:
        result = service.users().messages().list(
            userId="me",
            q=f"to:{email} in:sent",
            maxResults=1,
        ).execute()
        msgs = result.get("messages", [])
        if not msgs:
            return None
        # Načti detaily zprávy pro datum
        msg = service.users().messages().get(
            userId="me", id=msgs[0]["id"], format="metadata",
            metadataHeaders=["Date"]
        ).execute()
        headers = msg.get("payload", {}).get("headers", [])
        for h in headers:
            if h["name"] == "Date":
                # Převeď na náš formát dd.mm.yyyy HH:MM
                raw = h["value"]
                # Zkus různé formáty
                for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%d %b %Y %H:%M:%S %z"):
                    try:
                        dt = datetime.strptime(raw[:31].strip(), fmt)
                        return dt.strftime("%d.%m.%Y %H:%M")
                    except ValueError:
                        continue
                return raw[:16]  # fallback – první znaky
        return None
    except Exception:
        return None


def sync_sent(dry_run: bool = False):
    print("📊 Připojuji Google Sheet...")
    sheet = get_or_create_sheet()
    all_values = sheet.get_all_values()
    headers = all_values[0]
    records = []
    for row in all_values[1:]:
        padded = row + [""] * (len(headers) - len(row))
        records.append({headers[i]: padded[i] for i in range(len(headers)) if headers[i]})

    # Pouze řádky kde Stav = 'nový' a mají email
    candidates = [
        (i + 2, r)  # +2 = header row + 0-index
        for i, r in enumerate(records)
        if r.get("Stav", "").strip() == "nový" and r.get("Email", "").strip()
    ]
    print(f"🔍 Nalezeno {len(candidates)} kontaktů se stavem 'nový' k prověření\n")

    if not candidates:
        print("✅ Nic k opravě.")
        return

    print("📬 Připojuji Gmail API...")
    service = get_gmail_service()

    datum_col = HEADERS.index("Datum emailu") + 1
    stav_col = HEADERS.index("Stav") + 1

    updated = 0
    for idx, (row_idx, record) in enumerate(candidates):
        email = record["Email"].strip()
        name = record["Název"]
        print(f"[{idx+1}/{len(candidates)}] {name} <{email}>", end=" ... ", flush=True)

        sent_date = get_sent_date(service, email)
        if sent_date:
            print(f"✅ odesláno {sent_date}", end="")
            if not dry_run:
                sheet.update_cell(row_idx, stav_col, "osloveno")
                sheet.update_cell(row_idx, datum_col, sent_date)
                _colorize_row(sheet, row_idx, "osloveno")
            updated += 1
            print()
        else:
            print("– nenalezeno v Odesláno")

    print(f"\n{'[DRY RUN] ' if dry_run else ''}✅ Hotovo: {updated}/{len(candidates)} označeno jako 'osloveno'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Jen výpis, nic neměnit v Sheetu")
    args = parser.parse_args()
    sync_sent(dry_run=args.dry_run)
