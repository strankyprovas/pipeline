"""
Aktualizuje leads dashboard podle reality (stav k 10.5.2026).
Spuštění: venv/bin/python3 update_dashboard.py
"""
from sheets import get_or_create_sheet, update_status, HEADERS, _retry
from datetime import datetime
import time

TODAY = "10.05.2026"

# (email, status, note) — pro každý známý lead
# Statusy: zakaznik (active client), jednani (in negotiation), follow_up_odesl, odpověděl, nezájem, nový
UPDATES = [
    # ════ AKTIVNÍ KLIENTI (zákazníci) ════
    ("kavarna@duocoffee.cz", "zakaznik",
     f"[{TODAY}] Aktivní klient. Web live na kavarnaduocoffee.cz. Řeší Google indexaci (poslán draft s vysvětlením). Faktura 3000 Kč/rok."),

    ("ndprostejov@gmail.com", "zakaznik",
     f"[{TODAY}] Aktivní klient. Web live na restauracenarodnidum.cz s plně editovatelným adminem (texty, akce, menu, sociální sítě). Spravuje Aleš Buran/Martin Frána/Ludek Chmela."),

    ("buran@klenoty-buran.cz", "zakaznik",
     f"[{TODAY}] Národní dům Prostějov — provozovatel. Web live restauracenarodnidum.cz."),

    ("martin.frana@olc.cz", "zakaznik",
     f"[{TODAY}] Národní dům Prostějov — IT/web kontakt. Web live, posíláme úpravy přes admin."),

    ("restaurantkatak@gmail.com", "zakaznik",
     f"[{TODAY}] Aktivní klient. Web live + admin pro úpravu denního menu/tisku PDF. Heslo katak2026."),

    ("sekvent.d@seznam.cz", "zakaznik",
     f"[{TODAY}] Aktivní klient. Web sekventcar.cz. Faktura 25/2026 + upozornění na nezaplacenou fakturu. Mechanická práce 1150 Kč/h, prohlídka vozidla 1500 Kč. Hosting Faster.cz (web6)."),

    ("TingliN@seznam.cz", "zakaznik",
     f"[{TODAY}] PadThai Brno — aktivní klient. Týdenní menu update. Připravený admin (padthai2026) pro samosprávu menu + auto-překlad CZ→EN. Banner o rekonstrukci 5.5.–17.5."),

    # Bylinkářství Medunka — sděleno přes Krystofa, ale v sheetu může chybět; updatuju pokud existuje
    # (nemáme přímý email, jen Mirka Svozilová)

    # ════ V JEDNÁNÍ / OPEN LEADS ════
    ("karolina.zohova@gmail.com", "jednani",
     f"[{TODAY}] Madero Kralupy. Připravené 2 varianty webu (v1 dark wellness, v2 editorial magazine). Návrh polepu výlohy hotový (SVG). Doména maderokralupy.cz volná, registrujem. Smlouva 500 Kč/měs připravuje Krystof. IČO 23114291, Štefánikova 829 Kralupy n.Vlt."),

    ("h-benesova@centrum.cz", "nezajem",
     f"[24.04.2026] Odmítla — má vlastní web (masaze-melnik.webnode.cz)."),

    ("psycholog@igorstefanko.cz", "nezajem",
     f"[30.04.2026] Odmítl — neplánuje změnu, je 'ajťák', spravuje sám."),

    ("info@mholadental.cz", "nezajem",
     f"[06.05.2026] Odmítla, žádá vyřazení z databáze. Nikdy nezasílat další oslovení."),

    ("petrajurakova@centrum.cz", "jednani",
     f"[{TODAY}] Psycholožka. Hovor potvrzen Po 11.5. v 15:30 (Google Meet). 2 varianty webu připravené, řeší doménu+hosting."),

    ("chef.yuzusushi@gmail.com", "jednani",
     f"[{TODAY}] Yuzu Sushi (Filip Cibuľa). Demo připraveno. Chtěl hovor st 6.5. v poledne — zmeškán, navrženy nové termíny (Út/St/Čt 13.-15.5). Řeší doménu, fotky, Dish.co + Skubacz."),

    ("hieucon.cz@gmail.com", "follow_up_odesl",
     f"[29.04.2026] Restaurace Viet Nam. Čeká na nové menu od ní (zaneprázdněná). Nespěcháme."),

    ("auto-cont@volny.cz", "jednani",
     f"[07.05.2026] Auto-cont MIKA. Paní Kosturová — pan ředitel zatím nestihl projít ukázku. Po jarní sezóně pneuservisu se ozve."),

    ("autovit@autovit.cz", "jednani",
     f"[27.04.2026] Auto Vít — servis OPEL. Pan Vít potvrdil zájem, ale pozastavil kvůli dokončení nové dílny (potřebuje fotky atd.). Chtěl smazat: záruční opravy, karosářské/lakýrnické. Po dokončení dílny ozve sám. NEKONTAKTOVAT 2-3 týdny."),

    ("info@terapiepolacek.cz", "jednani",
     f"[07.05.2026] Mgr. Martin Poláček — psychoterapeut. Dělá textové korektury, v neděli udělá fotky. Po víkendu pošle podklady. Web připravený, čekáme jen na finalizaci textů."),

    ("karolina.zohova@gmail.com", "jednani",
     f"[{TODAY}] viz Madero Kralupy výše."),

    ("andrea.machackova@novira.com", "zakaznik",
     f"[{TODAY}] Hlinky.cz — aktivní. Karta bytu 1kk hotová. Chybí: odkaz na rozkliknutí + oprava ceny v sekci byty + karty 2+kk a obchodních prostor (čekáme na podklady)."),

    ("r.cerny@keraservis.cz", "jednani",
     f"[{TODAY}] keraservis — aktivní. Otevírá další projekt: nové stránky pro kastanova.cz a krizikova.cz. Schůzka s Andreou v kopii — až se vrátí z mimo Brna."),

    ("karolina.zohova@gmail.com", "jednani", "viz výše"),

    # ════ OUTREACH BEZ ODPOVĚDI (3+ týdny) — možná follow-up ════
    ("info@cafisco.cz", "follow_up_odesl",
     f"[{TODAY}] Cafisco — bez odpovědi po 2 emailech (20.4. + 27.4.). Možná 2. follow-up nebo telefonát."),

    # Yvett Rohrich, FA!N — emaily neumíme bez specifických adres
    # Karolína Žohová Madero — duplicate

    # Najdiwebare.cz poptávka — externí lead (info@najdiwebare.cz je platforma, ne klient)
]


def main():
    print("📊 Aktualizuji leads dashboard...")
    sheet = get_or_create_sheet()

    # Použij expected_headers protože sheet má duplicitní/prázdné hlavičky
    rows = _retry(sheet.get_all_records, expected_headers=HEADERS)
    print(f"   Sheet má {len(rows)} řádků")

    # Mapa email -> row_index (1-based, +1 protože header)
    email_col_idx = HEADERS.index("Email") + 1
    name_col_idx = HEADERS.index("Název") + 1
    email_to_row = {}
    name_to_row = {}
    for i, row in enumerate(rows, start=2):
        e = (row.get("Email") or "").strip().lower()
        n = (row.get("Název") or "").strip()
        if e:
            email_to_row[e] = i
        if n:
            name_to_row[n.lower()] = i

    updated = 0
    not_found = []
    for email, status, note in UPDATES:
        e = email.strip().lower()
        if e in email_to_row:
            row_idx = email_to_row[e]
            try:
                _retry(sheet.update_cell, row_idx, HEADERS.index("Stav") + 1, status)
                _retry(sheet.update_cell, row_idx, HEADERS.index("Poznámka") + 1, note)
                print(f"   ✅ {email} → {status}")
                updated += 1
                time.sleep(1.2)  # rate limit
            except Exception as ex:
                print(f"   ❌ {email}: {ex}")
        else:
            not_found.append(email)

    print(f"\n✅ Updated: {updated}")
    if not_found:
        print(f"⚠️  Nenalezeno v sheetu ({len(not_found)}):")
        for e in not_found:
            print(f"   – {e}")


if __name__ == "__main__":
    main()
