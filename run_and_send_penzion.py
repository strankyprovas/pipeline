"""
Spustí pipeline pro penziony přes česká města a pak odešle všechny pension drafty.
Použití: venv/bin/python3 run_and_send_penzion.py
"""
import time
import base64
import email as email_lib
from datetime import datetime
from main import process_restaurants
from gmail_draft import get_gmail_service
from run_all_cities import DEFAULT_CITIES

INDUSTRY = "penzion"
TARGET_PER_CITY = 2   # 2 × 80 měst = max 160 draftů
SEND_DELAY = 45        # sekund mezi emaily
FILTER_URL = "strankyprovas.github.io/penzion"  # jen pension emaily


def list_pension_drafts(service):
    """Vrátí jen drafty s pension demo URL."""
    all_drafts = []
    page_token = None
    while True:
        resp = service.users().drafts().list(userId="me", pageToken=page_token).execute()
        all_drafts.extend(resp.get("drafts", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    pension_drafts = []
    for d in all_drafts:
        detail = service.users().drafts().get(userId="me", id=d["id"], format="raw").execute()
        raw = base64.urlsafe_b64decode(detail["message"]["raw"])
        msg = email_lib.message_from_bytes(raw)
        text = ""
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    text = payload.decode("utf-8", errors="replace")
                    break
        if FILTER_URL in text:
            to = msg.get("To", "?")
            subject = msg.get("Subject", "?")
            pension_drafts.append({"id": d["id"], "to": to, "subject": subject})

    return pension_drafts


def send_pension_drafts(service, drafts):
    print(f"\n{'='*50}")
    print(f"📤 Odesílám {len(drafts)} pension emailů (1 za {SEND_DELAY}s)")
    print(f"   Odhadovaný čas: ~{len(drafts) * SEND_DELAY // 60} minut\n")

    for i, d in enumerate(drafts, 1):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [{i}/{len(drafts)}] → {d['to']}")
        try:
            service.users().drafts().send(userId="me", body={"id": d["id"]}).execute()
            print(f"           ✓ Odesláno")
        except Exception as e:
            print(f"           ❌ Chyba: {e}")

        if i < len(drafts):
            time.sleep(SEND_DELAY)

    print(f"\n✅ Hotovo! Odesláno {len(drafts)} emailů.")


def main():
    print("=" * 60)
    print(f"🏨 PENZION OUTREACH – {len(DEFAULT_CITIES)} měst, cíl {TARGET_PER_CITY}/město")
    print("=" * 60)

    # 1. Spusť pipeline
    used_domains: set = set()
    total_generated = 0

    for city in DEFAULT_CITIES:
        results = process_restaurants(
            city=city,
            target=TARGET_PER_CITY,
            used_domains=used_domains,
            industry=INDUSTRY,
        )
        total_generated += sum(1 for r in results if r.get("demo_path"))

    print(f"\n{'='*60}")
    print(f"🎉 Pipeline hotov – celkem vygenerováno: {total_generated} demo+draft")

    # 2. Odešli pension drafty
    print(f"\n🔍 Hledám pension drafty v Gmailu...")
    service = get_gmail_service()
    drafts = list_pension_drafts(service)
    print(f"   Nalezeno {len(drafts)} pension draftů k odeslání")

    if not drafts:
        print("⚠️  Žádné drafty k odeslání.")
        return

    send_pension_drafts(service, drafts)


if __name__ == "__main__":
    main()
