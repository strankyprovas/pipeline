"""
Konfigurace pipeline – vyplň po nasazení Google Apps Script.

PIXEL_BASE_URL: URL webové aplikace z Google Apps Script.
Získáš ji po nasazení pixel_tracker.gs (viz instrukce v tom souboru).
Příklad: https://script.google.com/macros/s/AKfycbx.../exec

Pokud je prázdné, tracking pixely se do emailů nepřidávají.
"""

PIXEL_BASE_URL = "https://script.google.com/macros/s/AKfycbygnUk6Q7Z3EzWA-rNXFUyzNxgeLWeDEZ41z7QMHqEuFhFOGVVM9xf71tTBAqdKBNSk/exec"

# Podniky pro které již web od StránkyProVás existuje – NESMÍ dostat outreach email
NEVER_CONTACT_NAMES = [
    "piava",
    "pad thai",
    "padthai",
    "bratrs bistro",
    "sekvent",
]
