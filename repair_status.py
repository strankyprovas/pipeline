#!/usr/bin/env python3
"""
Doplní do Sheetu stav „osloveno" kontaktům, kterým mail prokazatelně odešel,
ale zápis stavu selhal.

Proč: 11. 8. 2026 Sheets několik hodin odmítal zápisy (403). Maily odcházely
dál, ale stav se nezapsal. Takový kontakt nemá „osloveno", takže se mu
nesleduje odpověď, nedostane follow-up a hrozí, že ho pipeline osloví znovu.

Zdrojem pravdy je odeslaná pošta v Gmailu, ne logy z Actions — ta v Gmailu
zůstane, i když log dávno vyprší.

Použití (přes workflow „Oprava evidence"):
    python3 repair_status.py --dny 3 --dry-run
    python3 repair_status.py --dny 3
"""
import argparse
import os
import re
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from config import NEVER_CONTACT_NAMES, SENDER_EMAIL
from gmail_draft import get_gmail_service
from sheets import HEADERS, _retry, get_or_create_sheet

# Vlastní a klientské adresy sem nepatří. Do odeslané pošty se dostane i běžná
# komunikace s klienty (fakturace, domluvy) a kdyby takový kontakt dostal stav
# „osloveno", poslal by mu follow-up automatickou upomínku na ukázku webu.
VLASTNI = {
    "matyas.vrbaa@gmail.com", "matyas@strankyprovas.cz",
    "strankyprovas@strankyprovas.cz", "krystofholec@strankyprovas.cz",
}

EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")


def odeslane_adresy(service, dny: int) -> set:
    """Adresy, kterým za posledních `dny` dní odešel mail."""
    adresy, page = set(), None
    while True:
        resp = service.users().messages().list(
            userId="me", q=f"in:sent newer_than:{dny}d", maxResults=500,
            pageToken=page,
        ).execute()
        for m in resp.get("messages", []):
            det = service.users().messages().get(
                userId="me", id=m["id"], format="metadata",
                metadataHeaders=["To"],
            ).execute()
            for h in det.get("payload", {}).get("headers", []):
                if h.get("name", "").lower() == "to":
                    nalezene = EMAIL_RE.search(h.get("value", ""))
                    if nalezene:
                        adresy.add(nalezene.group(0).lower())
        page = resp.get("nextPageToken")
        if not page:
            break
    return adresy


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dny", type=int, default=3, help="Jak daleko zpět brát odeslanou poštu")
    p.add_argument("--dry-run", action="store_true", help="Jen vypsat, nic nezapisovat")
    args = p.parse_args()

    service = get_gmail_service()
    print(f"Načítám odeslanou poštu za posledních {args.dny} dní…")
    odeslane = odeslane_adresy(service, args.dny)
    print(f"  {len(odeslane)} adres v odeslané poště\n")

    sheet = get_or_create_sheet()
    hodnoty = _retry(sheet.get_all_values)
    hlavicka = hodnoty[0]
    i_email = hlavicka.index("Email")
    i_stav = hlavicka.index("Stav")
    i_datum = hlavicka.index("Datum emailu")

    i_nazev = hlavicka.index("Název")
    i_demo = hlavicka.index("Demo URL")

    k_oprave = []
    preskoceno_klient = 0
    for cislo_radku, radek in enumerate(hodnoty[1:], start=2):
        def bunka(i):
            return radek[i].strip() if i < len(radek) else ""
        email = bunka(i_email).lower()
        if not email or email not in odeslane:
            continue
        if email in VLASTNI or email == SENDER_EMAIL.lower():
            continue
        # Náš klient – nikdy neoznačovat jako oslovený lead.
        nazev = bunka(i_nazev).lower()
        if any(kw in nazev or kw in email for kw in NEVER_CONTACT_NAMES):
            preskoceno_klient += 1
            continue
        # Bez vygenerované ukázky to nebyl outreachový mail, ale běžná pošta.
        if not bunka(i_demo):
            preskoceno_klient += 1
            continue
        # Mail odešel, ale v databázi to není vidět.
        if bunka(i_stav).lower() in ("", "nový", "novy") or not bunka(i_datum):
            k_oprave.append((cislo_radku, email))

    if preskoceno_klient:
        print(f"(přeskočeno {preskoceno_klient} kontaktů bez ukázky nebo z klientské pošty)")
    print(f"Kontaktů k opravě: {len(k_oprave)}")
    for _, e in k_oprave[:15]:
        print(f"  {e}")
    if len(k_oprave) > 15:
        print(f"  … a dalších {len(k_oprave) - 15}")

    if args.dry_run:
        print("\n(dry-run, nic se nezapsalo)")
        return 0

    ted = datetime.now().strftime("%d.%m.%Y %H:%M")
    opraveno = 0
    for cislo_radku, email in k_oprave:
        try:
            _retry(sheet.update_cell, cislo_radku, i_datum + 1, ted)
            _retry(sheet.update_cell, cislo_radku, i_stav + 1, "osloveno")
            opraveno += 1
        except Exception as e:
            print(f"  ⚠️  {email}: {e}")
    print(f"\n✅ Doplněno u {opraveno} kontaktů.")
    return 0 if opraveno == len(k_oprave) else 1


if __name__ == "__main__":
    sys.exit(main())
