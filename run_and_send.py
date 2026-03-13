"""
Spustí pipeline přes česká města a pak odešle drafty daného odvětví.
Použití:
    venv/bin/python3 run_and_send.py --industry kadernictvi
    venv/bin/python3 run_and_send.py --industry penzion --target 3
    venv/bin/python3 run_and_send.py --industry restaurace --delay 30
"""
import argparse
import time
import base64
import email as email_lib
from datetime import datetime
from main import process_restaurants
from gmail_draft import get_gmail_service
from run_all_cities import DEFAULT_CITIES
from main import INDUSTRY_PAGES_URL


def list_industry_drafts(service, filter_url):
    """Vrátí jen drafty patřící danému odvětví (filtr podle URL v těle)."""
    all_drafts = []
    page_token = None
    while True:
        resp = service.users().drafts().list(userId="me", pageToken=page_token).execute()
        all_drafts.extend(resp.get("drafts", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    result = []
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
        if filter_url in text:
            result.append({
                "id": d["id"],
                "to": msg.get("To", "?"),
                "subject": msg.get("Subject", "?"),
            })
    return result


def send_drafts(service, drafts, delay):
    print(f"\n{'='*60}")
    print(f"📤 Odesílám {len(drafts)} emailů (1 za {delay}s)")
    print(f"   Odhadovaný čas: ~{len(drafts) * delay // 60} minut\n")

    sent = 0
    for i, d in enumerate(drafts, 1):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [{i}/{len(drafts)}] → {d['to']}")
        try:
            service.users().drafts().send(userId="me", body={"id": d["id"]}).execute()
            print(f"           ✓ Odesláno")
            sent += 1
        except Exception as e:
            print(f"           ❌ Chyba: {e}")
        if i < len(drafts):
            time.sleep(delay)

    print(f"\n✅ Hotovo! Odesláno {sent}/{len(drafts)} emailů.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--industry", type=str, default="restaurace")
    parser.add_argument("--target", type=int, default=2,
                        help="Počet demo+draft na město (default: 2)")
    parser.add_argument("--delay", type=int, default=60,
                        help="Sekund mezi emaily při odesílání (default: 60)")
    args = parser.parse_args()

    filter_url = INDUSTRY_PAGES_URL.get(args.industry, "strankyprovas.github.io")
    # Vezmi jen hostname+path část
    filter_url = filter_url.replace("https://", "")

    print("=" * 60)
    print(f"🚀 PIPELINE: {args.industry.upper()} | {len(DEFAULT_CITIES)} měst | cíl {args.target}/město")
    print(f"   Filter URL pro odesílání: {filter_url}")
    print("=" * 60)

    # 1. Pipeline přes všechna města
    used_domains: set = set()
    total = 0
    for city in DEFAULT_CITIES:
        results = process_restaurants(
            city=city,
            target=args.target,
            used_domains=used_domains,
            industry=args.industry,
        )
        total += sum(1 for r in results if r.get("demo_path"))

    print(f"\n{'='*60}")
    print(f"🎉 Pipeline hotov – vygenerováno: {total} demo+draft")

    # 2. Odešli jen drafty tohoto odvětví
    print(f"\n🔍 Hledám {args.industry} drafty v Gmailu...")
    service = get_gmail_service()
    drafts = list_industry_drafts(service, filter_url)
    print(f"   Nalezeno {len(drafts)} draftů k odeslání")

    if drafts:
        send_drafts(service, drafts, args.delay)
    else:
        print("⚠️  Žádné drafty k odeslání.")


if __name__ == "__main__":
    main()
