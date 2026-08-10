"""
Konfigurace pipeline – vyplň po nasazení Google Apps Script.

PIXEL_BASE_URL: URL webové aplikace z Google Apps Script.
Získáš ji po nasazení pixel_tracker.gs (viz instrukce v tom souboru).
Příklad: https://script.google.com/macros/s/AKfycbx.../exec

Pokud je prázdné, tracking pixely se do emailů nepřidávají.
"""

# Odesílací adresa všech draftů. Jediný zdroj pravdy – dřív byla natvrdo na
# třech místech (gmail_draft.py, email_template.py, read_replies.py) a rozcházely se.
#
# ⚠️ Tady musí být adresa, kterou Gmail SKUTEČNĚ pustí, ne ta, kterou chceme.
# Ověřuje se workflow „Test odesilatele" – ten založí draft, přečte skutečnou
# hlavičku From a zase ho smaže. Neověřenou adresu Gmail tiše přepíše zpět na
# primární adresu účtu a v draftu to není poznat.
#
# 9. 8. 2026 ověřeno zeleně: matyas@strankyprovas.cz projde. Cesta tam vedla
# přes povolení „Authenticated SMTP" u schránky a vypnutí security defaults
# v Entra (ty blokovaly přihlášení heslem přes SMTP: chyba 535 5.7.139).
# Doména má SPF, DKIM i DMARC (DNS u Wedosu, MX na M365).
SENDER_EMAIL = "matyas@strankyprovas.cz"

# Jméno, které příjemce vidí v seznamu pošty dřív než cokoli jiného.
# Dřív se nenastavovalo vůbec a Gmail doplňoval jméno účtu – chodilo to jako
# „Matyas Vrba" bez diakritiky. Českému příjemci to nesedí.
SENDER_NAME = "Matyáš Vrba"

# Kam mají chodit odpovědi. Odesílá se z matyas@strankyprovas.cz, jenže odpovědi
# na tu adresu končí v Outlooku a `sync_replies` čte Gmail – měření odezvy by
# tím osleplo a follow-up by mohl přijít i tomu, kdo už odpověděl.
# Správné řešení je přeposílání M365 → Gmail, jenže to blokuje politika
# „Automatic forwarding rules" v Defenderu (chyba 550 5.7.520). Do doby, než se
# povolí, míří odpovědi rovnou do Gmailu přes Reply-To.
# ⚠️ Až přeposílání pojede, tuhle konstantu vyprázdnit ("") – odesílatel a adresa
# pro odpověď by se v ideálním případě lišit neměly.
REPLY_TO = "matyas.vrbaa@gmail.com"

PIXEL_BASE_URL = "https://script.google.com/macros/s/AKfycbygnUk6Q7Z3EzWA-rNXFUyzNxgeLWeDEZ41z7QMHqEuFhFOGVVM9xf71tTBAqdKBNSk/exec"

# Podniky pro které již web od StránkyProVás existuje – NESMÍ dostat outreach email
NEVER_CONTACT_NAMES = [
    "piava",
    "pad thai",
    "padthai",
    "bratrs bistro",
    "sekvent",
]
