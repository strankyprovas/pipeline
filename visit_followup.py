#!/usr/bin/env python3
"""
Follow-up podle návštěv dem (beacon, 2. 10. 2026).

Beacon v každém demu zapisuje návštěvy do strankyprovas.cz/track/visits.log.
Tenhle skript si stáhne agregaci (track/visits.php), spáruje slugy s kontakty
v Sheetu přes "Demo URL" a kontaktům, kteří si demo nedávno prohlédli, ale
neodpověděli, připraví follow-up draft (odešle ho hodinový Send Drafts).

Prohlédnuté demo = nejsilnější nákupní signál, který máme — proto se tahle
připomínka posílá dřív (už po 1 dni od návštěvy) než plošný follow-up (5 dní).

⚠️ Text NIKDY nepřiznává, že o návštěvě víme (viz check_followups.py — pixel
otvírák odstraněn 18. 9., působí nepříjemně). Je to jen "vracím se k ukázce".

Stav v Sheetu se mění na 'visit_followup' → kontakt vypadne z plošných
follow-upů (ty berou jen 'osloveno') a podruhé ho tenhle skript nevezme.
"""
import argparse
import os
import sys
import time
from datetime import datetime, timedelta

import requests

from check_followups import _records
from email_template import industry_subpage
from gmail_draft import create_draft
from sheets import get_or_create_sheet
from email_template import SENDER_NAME, SENDER_COMPANY

VISITS_URL = "https://strankyprovas.cz/track/visits.php"


def fetch_visits(key: str) -> list[dict]:
    r = requests.get(VISITS_URL, params={"k": key}, timeout=30)
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError("visits.php vrátil ok=false (špatný TRACK_KEY?)")
    return data.get("visits", [])


def make_body(name: str, demo_url: str, industry: str) -> tuple[str, str, str]:
    subject = f"Jak se vám líbí ukázka pro {name}?"
    sub_url, sub_popis = industry_subpage(industry)

    plain = (
        f"Dobrý den,\n\n"
        f"před časem jsem vám posílal ukázku nového webu pro {name} a rád bych se "
        f"k ní krátce vrátil — co na ni říkáte?\n"
        f"→ {demo_url}\n\n"
        f"Pokud se vám líbí, rád ji doladím podle vašich představ (texty, fotky, "
        f"ceník…) a pomůžu se spuštěním na vlastní adrese. A pokud je teď špatná "
        f"doba, stačí krátce napsat — nebudu vás dál zdržovat.\n\n"
        f"P.S. Kromě měsíčního modelu web umíme i jednorázově od 6 000 Kč — "
        f"zaplatíte jednou a web je navždy váš.\n\n"
        f"Co všechno děláme pro {sub_popis}: {sub_url}\n\n"
        f"Hezký den,\n{SENDER_NAME}\n{SENDER_COMPANY}"
    )
    html = (
        f'<div style="font-family:Arial,sans-serif;font-size:14px;color:#222;line-height:1.55">'
        f"<p>Dobrý den,</p>"
        f"<p>před časem jsem vám posílal ukázku nového webu pro <b>{name}</b> a rád bych se "
        f"k ní krátce vrátil — co na ni říkáte?</p>"
        f'<p><a href="{demo_url}">Ukázka webu {name}</a></p>'
        f"<p>Pokud se vám líbí, rád ji doladím podle vašich představ (texty, fotky, ceník…) "
        f"a pomůžu se spuštěním na vlastní adrese. A pokud je teď špatná doba, stačí krátce "
        f"napsat — nebudu vás dál zdržovat.</p>"
        f"<p>P.S. Kromě měsíčního modelu web umíme i jednorázově od 6 000 Kč — zaplatíte "
        f"jednou a web je navždy váš.</p>"
        f'<p>Co všechno děláme pro {sub_popis}: <a href="{sub_url}">{sub_url.replace("https://", "")}</a></p>'
        f"<p>Hezký den,<br>{SENDER_NAME}<br>{SENDER_COMPANY}</p></div>"
    )
    return subject, plain, html


def main():
    ap = argparse.ArgumentParser(description="Follow-up podle návštěv dem")
    ap.add_argument("--days", type=int, default=3,
                    help="jak staré návštěvy brát (dní zpět, default 3)")
    ap.add_argument("--min-age-hours", type=int, default=12,
                    help="minimální stáří návštěvy, ať nepíšeme 10 minut po kliknutí")
    ap.add_argument("--limit", type=int, default=10, help="strop draftů za běh")
    ap.add_argument("--dry-run", action="store_true", help="jen vypsat, nic nevytvářet")
    args = ap.parse_args()

    key = os.environ.get("TRACK_KEY", "")
    if not key:
        print("❌ Chybí TRACK_KEY")
        sys.exit(1)

    visits = fetch_visits(key)
    now = datetime.now()
    recent = {}
    for v in visits:
        slug = v.get("slug", "")
        if slug.startswith("test/"):
            continue
        try:
            last = datetime.strptime(v["last"], "%Y-%m-%d %H:%M:%S")
        except (KeyError, ValueError):
            continue
        age = now - last
        if age > timedelta(days=args.days) or age < timedelta(hours=args.min_age_hours):
            continue
        recent["https://strankyprovas.github.io/" + slug + "/"] = v
    print(f"👀 Čerstvých návštěv k párování: {len(recent)}")
    if not recent:
        return

    sheet = get_or_create_sheet()
    records = _records(sheet)
    made = 0
    for idx, r in enumerate(records, start=2):  # řádek 1 = hlavička
        demo = (r.get("Demo URL") or "").strip().rstrip("/") + "/"
        if demo not in recent:
            continue
        stav = (r.get("Stav") or "").strip()
        if stav not in ("osloveno", "follow_up_odesl"):
            continue
        if (r.get("Odpověděl") or "").strip():
            continue
        email = (r.get("Email") or "").strip()
        name = (r.get("Název") or "").strip()
        if not email or not name:
            continue

        v = recent[demo]
        print(f"🔥 {name} <{email}> — demo zobrazeno {v['views']}×, naposledy {v['last']}")
        if args.dry_run:
            made += 1
            continue

        subject, plain, html = make_body(name, demo.rstrip("/") + "/",
                                         (r.get("Odvětví") or "restaurace").strip())
        try:
            create_draft(email, subject, plain, html)
        except Exception as e:
            print(f"  ⚠️ Draft selhal: {e}")
            continue
        try:
            hdr = sheet.row_values(1)
            col = hdr.index("Stav") + 1
            sheet.update_cell(idx, col, "visit_followup")
        except Exception as e:
            print(f"  ⚠️ Zápis Stavu selhal: {e}")
        made += 1
        if made >= args.limit:
            break
        time.sleep(2)

    print(f"✅ Hotovo, follow-upů: {made}")


if __name__ == "__main__":
    main()
