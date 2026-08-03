"""Obnoví Google OAuth token.

Spusť a v prohlížeči odsouhlas oprávnění – kód se zachytí sám:

    venv/bin/python3 reauth.py

Skript si otevře lokální server na http://localhost:8765, tam ho Google
po přihlášení přesměruje a autorizační kód převezme automaticky. Dřív se
kód vkládal ručně přes input(), což nefunguje, když skript neběží
v opravdovém terminálu (např. přes `!` v Claude Code → EOFError).

Když by lokální server nešel spustit, přepni se na ruční režim:

    venv/bin/python3 reauth.py --manual
"""
import os
import pickle
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "credentials.json")
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "token.pickle")
BACKUP_FILE = TOKEN_FILE + ".bak"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.compose",
    # gmail.compose umí jen vytvářet a odesílat. Na detekci odpovědí je potřeba
    # ČÍST poštu – bez tohohle scope vrací sync_replies 403 a follow-upy by
    # chodily i lidem, kteří už odpověděli.
    "https://www.googleapis.com/auth/gmail.readonly",
]

MANUAL = "--manual" in sys.argv


def main():
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)

    if MANUAL:
        flow.redirect_uri = "http://localhost"
        auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")
        print("\n📋 Otevři tuto URL v prohlížeči:\n")
        print(auth_url)
        print("\nPo přihlášení skončíš na http://localhost/... a prohlížeč ukáže chybu – to nevadí.")
        pasted = input("\nVlož sem CELOU URL z adresního řádku: ").strip()
        if "code=" in pasted:
            from urllib.parse import parse_qs, urlparse
            code = parse_qs(urlparse(pasted).query).get("code", [""])[0]
        else:
            code = pasted
        flow.fetch_token(code=code)
        return flow.credentials

    print("\n🌐 Otevírám prohlížeč. Přihlas se jako matyas.vrbaa@gmail.com a povol oprávnění.")
    print("   (Kdyby Google hlásil neověřenou aplikaci: Rozšířené → Přejít na …)\n")
    return flow.run_local_server(
        port=8765,
        prompt="consent",
        access_type="offline",
        authorization_prompt_message="Pokud se prohlížeč neotevřel sám, jdi na:\n{url}\n",
        success_message="Hotovo, tohle okno můžeš zavřít a vrátit se do terminálu.",
        open_browser=True,
    )


# Starý token nejdřív zazálohovat, ne rovnou smazat – kdyby autorizace
# neprošla, zůstal bys úplně bez tokenu.
if os.path.exists(TOKEN_FILE):
    os.replace(TOKEN_FILE, BACKUP_FILE)
    print(f"ℹ️  Původní token zazálohován do {os.path.basename(BACKUP_FILE)}")

try:
    creds = main()
except Exception as e:
    print(f"\n❌ Autorizace se nepovedla: {e}")
    if os.path.exists(BACKUP_FILE):
        os.replace(BACKUP_FILE, TOKEN_FILE)
        print("↩️  Původní token vrácen zpátky, nic se nerozbilo.")
    raise SystemExit(1)

with open(TOKEN_FILE, "wb") as f:
    pickle.dump(creds, f)

print("\n✅ Token uložen! Spouštím testy...\n")

import gspread
gspread.authorize(creds)
print("  ✅ Google Sheets OK")

# Tohle je ten důvod, proč se reauth dělá – ověř, že čtení pošty opravdu projde.
from googleapiclient.discovery import build

try:
    svc = build("gmail", "v1", credentials=creds, cache_discovery=False)
    svc.users().messages().list(userId="me", q="in:inbox", maxResults=1).execute()
    print("  ✅ Čtení Gmailu OK – detekce odpovědí bude fungovat, follow-upy lze zapnout")
except Exception as e:
    print(f"  ❌ Čtení Gmailu stále nejde: {e}")
    print("     Follow-upy NEZAPÍNAT – posílaly by i lidem, kteří už odpověděli.")

print("\nHotovo. Řekni Claudovi, ať nahraje nový token do GitHub secrets.")
