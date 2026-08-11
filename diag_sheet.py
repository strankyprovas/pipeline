#!/usr/bin/env python3
"""
Diagnostika zápisu do Google Sheetu.

Proč: 11. 8. 2026 začal Sheet vracet `403 The caller does not have permission`
při zápisu, zatímco čtení dál fungovalo. Maily odcházely dál, ale stav se
nezapisoval — tedy tichá porucha přesně toho druhu, který tenhle projekt
opakovaně dostal do kolen.

Hláška od gspread je useknutá na jednu větu. Tenhle skript vypíše celé tělo
odpovědi od Googlu (obsahuje `reason`, který rozliší chybějící scope od
vyčerpané kvóty nebo plného úložiště) a k tomu rozsahy uloženého tokenu.

⚠️ Pouštět přes workflow „Diagnostika Sheetu", ne lokálně (sdílený Google token).
"""
import json
import os
import pickle
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)


def main() -> int:
    token_path = os.path.join(BASE_DIR, "token.pickle")
    with open(token_path, "rb") as f:
        creds = pickle.load(f)

    print("=== TOKEN ===")
    print("scopes:", creds.scopes)
    print("platný:", creds.valid, "| vypršel:", creds.expired)
    print("má refresh token:", bool(creds.refresh_token))
    print()

    import gspread
    from sheets import SHEET_NAME

    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1

    print("=== ČTENÍ ===")
    hlavicka = sheet.row_values(1)
    print(f"OK, {len(hlavicka)} sloupců, {sheet.row_count} řádků")
    print()

    print("=== ZÁPIS (zkušební buňka daleko za daty) ===")
    zkusebni = "ZZ1"
    try:
        sheet.update_acell(zkusebni, "test")
        print("✅ Zápis prošel – problém je pryč.")
        sheet.update_acell(zkusebni, "")
        return 0
    except Exception as e:
        print(f"❌ Zápis selhal: {type(e).__name__}: {e}")
        resp = getattr(e, "response", None)
        if resp is not None:
            print(f"HTTP status: {resp.status_code}")
            print("Celé tělo odpovědi od Googlu:")
            try:
                print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
            except Exception:
                print(resp.text[:2000])
        return 1


if __name__ == "__main__":
    sys.exit(main())
