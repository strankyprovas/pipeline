"""Obnoví Google OAuth token bez potřeby browseru v WSL."""
import os, pickle, webbrowser
from google_auth_oauthlib.flow import InstalledAppFlow

CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "credentials.json")
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "token.pickle")
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.compose",
    # gmail.compose umí jen vytvářet a odesílat. Na detekci odpovědí je potřeba
    # ČÍST poštu – bez tohohle scope vrací sync_replies 403 a follow-upy by
    # chodily i lidem, kteří už odpověděli.
    "https://www.googleapis.com/auth/gmail.readonly",
]

BACKUP_FILE = TOKEN_FILE + ".bak"

# Starý token nejdřív zazálohovat, ne rovnou smazat. Když autorizace neprojde
# (nová oprávnění vyžadují odsouhlasení), zůstaneš jinak úplně bez tokenu.
if os.path.exists(TOKEN_FILE):
    os.replace(TOKEN_FILE, BACKUP_FILE)
    print(f"ℹ️  Původní token zazálohován do {os.path.basename(BACKUP_FILE)}")
    print("   Kdyby se autorizace nepovedla, vrátíš ho zpátky:")
    print(f"   mv {BACKUP_FILE} {TOKEN_FILE}\n")

flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
# OOB (urn:ietf:wg:oauth:2.0:oob) Google zrušil → používáme loopback redirect.
flow.redirect_uri = "http://localhost"

auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")

print("\n📋 Otevři tuto URL v prohlížeči:\n")
print(auth_url)
print("\nPo přihlášení tě přesměruje na http://localhost/... (prohlížeč ukáže chybu – to nevadí).")
print("Zkopíruj CELOU URL z adresního řádku (obsahuje ?code=...) a vlož ji sem.")
pasted = input("\nSem vlož tu URL (nebo jen kód) a stiskni Enter: ").strip()
# Vytáhni kód z vložené URL, nebo použij přímo vložený kód
if "code=" in pasted:
    from urllib.parse import urlparse, parse_qs
    code = parse_qs(urlparse(pasted).query).get("code", [""])[0]
else:
    code = pasted

flow.fetch_token(code=code)
creds = flow.credentials

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
