#!/usr/bin/env python3
"""
Ověří, z jaké adresy se drafty opravdu zakládají.

Proč: `gmail_draft.create_draft()` si hlavičku From nastavuje sám podle
SENDER_EMAIL, jenže Gmail ji uzná jen tehdy, je-li adresa v účtu ověřená jako
„Odesílat jako". Když ověřená není, Gmail ji při odeslání tiše přepíše zpět na
primární adresu – draft přitom vypadá správně, takže se na to nepřijde.

Skript proto draft založí, načte zpátky přes Gmail API a vypíše, co v hlavičce
skutečně zůstalo. Testovací draft na konci zase smaže.

⚠️ Pouštět přes workflow „Test odesilatele", ne lokálně – sahá to na týž Google
   token jako pipeline a sender.
"""
import argparse
import sys

import gmail_draft
from gmail_draft import SENDER_EMAIL, create_draft, get_gmail_service

PRIJEMCE = "matyas.vrbaa@gmail.com"
PREDMET = "Kontrola odesílací adresy (automatický test)"


def _hlavicka(payload: dict, jmeno: str) -> str:
    for h in payload.get("headers", []):
        if h.get("name", "").lower() == jmeno.lower():
            return h.get("value", "")
    return "(chybí)"


def main() -> int:
    p = argparse.ArgumentParser(description="Ověří, kterou odesílací adresu Gmail pustí")
    p.add_argument("--adresa", default="",
                   help="Zkusit jinou adresu než tu v config.py (nic se nepřepisuje, "
                        "jen se ověří, jestli ji Gmail uzná)")
    args = p.parse_args()

    # Zkoušená adresa se podstrčí do modulu, ať projde stejnou cestou jako
    # ostrý provoz – včetně kódování jména v hlavičce From.
    global SENDER_EMAIL
    if args.adresa:
        SENDER_EMAIL = args.adresa
        gmail_draft.SENDER_EMAIL = args.adresa

    service = get_gmail_service()

    print(f"Zkouším odesílací adresu: {SENDER_EMAIL}")
    print(f"Zakládám testovací draft na {PRIJEMCE} …\n")

    create_draft(
        to_email=PRIJEMCE,
        subject=PREDMET,
        body_plain="Automatický test odesílací adresy. Tento draft se sám smaže.",
        body_html="<p>Automatický test odesílací adresy. Tento draft se sám smaže.</p>",
    )

    # Najdi ho zpátky a přečti, co Gmail v hlavičce nechal.
    drafts = service.users().drafts().list(userId="me", maxResults=25).execute()
    nalezen = None
    for d in drafts.get("drafts", []):
        detail = service.users().drafts().get(
            userId="me", id=d["id"], format="metadata",
        ).execute()
        payload = detail.get("message", {}).get("payload", {})
        if _hlavicka(payload, "Subject") == PREDMET:
            nalezen = (d["id"], payload)
            break

    # Ukliď i případné starší testovací drafty (ručně založené přes Gmail MCP
    # apod.) – sender je jinak vezme jako běžný outreach.
    for d in drafts.get("drafts", []):
        detail = service.users().drafts().get(
            userId="me", id=d["id"], format="metadata",
        ).execute()
        predmet = _hlavicka(detail.get("message", {}).get("payload", {}), "Subject")
        if predmet.lower().startswith("test odesílací adresy"):
            service.users().drafts().delete(userId="me", id=d["id"]).execute()
            print(f"Uklizen starý testovací draft: {predmet}")

    if not nalezen:
        print("❌ Testovací draft se nepodařilo najít zpátky.")
        return 1

    draft_id, payload = nalezen
    from_header = _hlavicka(payload, "From")
    print(f"From v založeném draftu: {from_header}")

    # Úklid, ať v Gmailu nezůstává smetí, které by sender omylem rozeslal.
    service.users().drafts().delete(userId="me", id=draft_id).execute()
    print("Testovací draft smazán.\n")

    if SENDER_EMAIL.lower() in from_header.lower():
        print(f"✅ Gmail hlavičku přijal – drafty se zakládají jako {SENDER_EMAIL}.")
        print("   Pozor: definitivní potvrzení dá až reálné odeslání, Gmail "
              "neověřený alias přepisuje až v tu chvíli.")
        return 0

    print(f"❌ Gmail hlavičku NEPŘIJAL. Očekáváno {SENDER_EMAIL}, je tam {from_header}.")
    print("   Adresu je potřeba v Gmailu přidat v Nastavení → Účty a import → "
          "„Odesílat jako“ a potvrdit ověřovací e-mail.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
