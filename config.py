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
# 8. 8. 2026 tu chvíli bylo strankyprovas@strankyprovas.cz a Gmail hlavičku tiše
# přepisoval zpět (adresa není ověřená jako „Odesílat jako"). Přepnout až potom,
# co workflow „Test odesilatele" projde zeleně – a až bude doména mít SPF, DKIM
# a DMARC, jinak 60 studených mailů denně z čerstvé domény spadne do spamu.
SENDER_EMAIL = "matyas.vrbaa@gmail.com"

PIXEL_BASE_URL = "https://script.google.com/macros/s/AKfycbygnUk6Q7Z3EzWA-rNXFUyzNxgeLWeDEZ41z7QMHqEuFhFOGVVM9xf71tTBAqdKBNSk/exec"

# Podniky pro které již web od StránkyProVás existuje – NESMÍ dostat outreach email
NEVER_CONTACT_NAMES = [
    "piava",
    "pad thai",
    "padthai",
    "bratrs bistro",
    "sekvent",
]
