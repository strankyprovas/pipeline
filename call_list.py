"""
Denní „call list" — teplé leady na zavolání.

Vybírá ze Sheetu podniky, které OTEVŘELY email nebo KLIKLY na demo,
mají telefon a neodpověděly. To jsou lidé, kteří nabídku viděli a
zaujala je natolik, že se podívali — ideální kandidáti na krátký hovor
(hovory zavírají řádově líp než další mail: Němcová, Roth, Polišenská…).

Použití:  python call_list.py [N]     # N = kolik čísel vypsat, výchozí 5
Řazení:   klik na demo > otevření; novější oslovení dřív.
"""
import sys
from datetime import datetime
from sheets import get_client, SHEET_NAME, _retry

def main(limit=5):
    client = get_client()
    sheet = _retry(lambda: client.open(SHEET_NAME).sheet1)
    # get_all_records padá na duplicitních prázdných hlavičkách → ručně
    vsechna = _retry(lambda: sheet.get_all_values())
    hlavicky = vsechna[0]
    rows = [dict(zip(hlavicky, radek)) for radek in vsechna[1:]]

    kandidati = []
    for r in rows:
        telefon = str(r.get("Telefon", "")).strip()
        otevrel = str(r.get("Otevřel email", "")).strip().lower()
        odpovedel = str(r.get("Odpověděl", "")).strip().lower()
        stav = str(r.get("Stav", "")).strip().lower()
        if not telefon or not otevrel:
            continue
        if odpovedel == "ano" or stav in ("odpověděl", "nezájem"):
            continue
        skore = 2 if "klik" in otevrel else 1
        kandidati.append((skore, str(r.get("Datum emailu", "")), r))

    def cas(datum):
        for fmt in ("%d.%m.%Y %H:%M", "%d.%m.%Y", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(datum.strip(), fmt).timestamp()
            except ValueError:
                continue
        return 0.0  # bez data = stará kampaň → až na konec

    # klik > otevření; uvnitř kategorie nejčerstvější oslovení první
    kandidati.sort(key=lambda x: (-x[0], -cas(x[1])))

    if not kandidati:
        print("Žádní teplí kandidáti (nikdo s telefonem neotevřel bez odpovědi).")
        return
    print(f"📞 CALL LIST — {min(limit, len(kandidati))} nejteplejších (z {len(kandidati)}):\n")
    for skore, _, r in kandidati[:limit]:
        akce = "KLIKL NA DEMO" if skore == 2 else "otevřel email"
        print(f"• {r.get('Název','?')} ({r.get('Odvětví','?')}, {r.get('Město','?')})")
        print(f"  tel: {r.get('Telefon')} · {akce} · osloveno {r.get('Datum emailu','?')}")
        print(f"  demo: {r.get('Demo URL','')}")
        print()

if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 5)
