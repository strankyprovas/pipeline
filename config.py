"""
Konfigurace pipeline – vyplň po nasazení Google Apps Script.

PIXEL_BASE_URL: URL webové aplikace z Google Apps Script.
Získáš ji po nasazení pixel_tracker.gs (viz instrukce v tom souboru).
Příklad: https://script.google.com/macros/s/AKfycbx.../exec

Pokud je prázdné, tracking pixely se do emailů nepřidávají.
"""

# Odesílací adresa všech draftů (outreach i klientská pošta).
# ⚠️ Musí být v Gmailu ověřená jako „Odesílat jako", jinak ji Gmail při odeslání
# tiše přepíše zpět na primární adresu účtu. Ověřit: workflow „Test odesilatele".
# Dřív byla natvrdo na třech místech (gmail_draft.py, email_template.py,
# read_replies.py) a rozcházely se.
SENDER_EMAIL = "strankyprovas@strankyprovas.cz"

PIXEL_BASE_URL = "https://script.google.com/macros/s/AKfycbygnUk6Q7Z3EzWA-rNXFUyzNxgeLWeDEZ41z7QMHqEuFhFOGVVM9xf71tTBAqdKBNSk/exec"

# Podniky pro které již web od StránkyProVás existuje – NESMÍ dostat outreach email
NEVER_CONTACT_NAMES = [
    "piava",
    "pad thai",
    "padthai",
    "bratrs bistro",
    "sekvent",
]
