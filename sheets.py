"""
Google Sheets databáze kontaktů
- Zabraňuje duplicitnímu oslovení stejného podniku
- Sleduje stav každého kontaktu
"""
import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import pickle
import time
import random
from datetime import datetime, timedelta


def _retry(fn, *args, max_retries=12, **kwargs):
    """Volá fn s retry + exponential backoff při 429 (Sheets rate limit)."""
    for attempt in range(max_retries):
        try:
            return fn(*args, **kwargs)
        except gspread.exceptions.APIError as e:
            if e.response.status_code == 429 and attempt < max_retries - 1:
                # Delší čekání pro paralelní GitHub Actions joby – kvóta se resetuje za ~60s
                wait = min(60, (2 ** attempt)) + random.uniform(5, 15)
                print(f"  ⏳ Sheets rate limit – čekám {wait:.1f}s (pokus {attempt+1}/{max_retries})")
                time.sleep(wait)
            else:
                raise

CREDENTIALS_FILE = os.path.join(os.path.dirname(__file__), "credentials.json")
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "token.pickle")
SHEET_NAME = "Restaurace - Kontakty"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/gmail.compose",
]

HEADERS = [
    "Název",
    "Adresa",
    "Telefon",
    "Email",
    "Web",
    "PageSpeed",
    "Kategorie",
    "Demo URL",
    "Datum přidání",
    "Datum emailu",
    "Stav",          # nový / osloveno / bez_odpovědi / odpověděl / nezájem / manual
    "Poznámka",
    "Město",         # reálné město restaurace
    "Vision skóre",  # skóre od Claude Vision (pokud bylo použito)
    "Otevřel email", # tracking (ruční/automatický)
    "Odpověděl",     # ano / ne
    "Zájem",         # ano / ne / možná
    "AB Varianta",   # A / B / C – která verze předmětu byla použita
    "Facebook URL",  # FB stránka pro manuální oslovení (když není email)
    "Odvětví",       # restaurace / kavarna / penzion / kosmetika / kadernictvi / zubni / psycholog
    "Datum follow-up",  # kdy byl odeslán follow-up email
    "Follow-up due",    # YYYY-MM-DD – kdy má být odeslán follow-up (5 dní od draftu)
]

# Barvy řádků podle stavu
ROW_COLORS = {
    "nový":          {"red": 1.0,  "green": 1.0,  "blue": 1.0},   # bílá
    "osloveno":      {"red": 1.0,  "green": 0.95, "blue": 0.6},   # žlutá
    "odpověděl":     {"red": 0.7,  "green": 0.93, "blue": 0.7},   # zelená
    "bez_odpovědi":  {"red": 0.88, "green": 0.88, "blue": 0.88},  # šedá
    "nezájem":       {"red": 0.95, "green": 0.7,  "blue": 0.7},   # červená
    "manual":           {"red": 0.8,  "green": 0.9,  "blue": 1.0},   # modrá – čeká na manuální FB oslovení
    "follow_up_odesl":  {"red": 1.0,  "green": 0.85, "blue": 0.6},   # oranžová – follow-up odeslán
}


def get_client():
    import fcntl
    import time as _time

    def _load():
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, "rb") as f:
                return pickle.load(f)
        return None

    creds = _load()

    # Pokud je token platný, rovnou ho použij (žádný zámek nepotřeba)
    if creds and creds.valid:
        return gspread.authorize(creds)

    # Token je expirovaný/neplatný → obnov POD ZÁMKEM.
    # Jen JEDEN proces obnovuje naráz; ostatní počkají a načtou už obnovený token.
    # Tím se zabrání souběžnému refresh, který Google vyhodnotí jako reuse a token revokuje.
    lock_path = TOKEN_FILE + ".lock"
    with open(lock_path, "w") as lockf:
        fcntl.flock(lockf, fcntl.LOCK_EX)  # blokující zámek
        try:
            # Re-load – mezitím možná token obnovil jiný proces
            creds = _load()
            if creds and creds.valid:
                return gspread.authorize(creds)

            if creds and creds.expired and creds.refresh_token:
                # Malá náhodná prodleva pro jistotu, pak refresh
                for attempt in range(3):
                    try:
                        creds.refresh(Request())
                        break
                    except Exception:
                        if attempt == 2:
                            raise
                        _time.sleep(2)
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)

            # Ulož token atomicky
            tmp = TOKEN_FILE + ".tmp"
            with open(tmp, "wb") as f:
                pickle.dump(creds, f)
            os.replace(tmp, TOKEN_FILE)
        finally:
            fcntl.flock(lockf, fcntl.LOCK_UN)

    return gspread.authorize(creds)


def get_or_create_sheet():
    """Otevře existující sheet nebo vytvoří nový"""
    client = get_client()
    try:
        sheet = _retry(lambda: client.open(SHEET_NAME).sheet1)
        print(f"✓ Sheet nalezen: {SHEET_NAME}")
    except gspread.SpreadsheetNotFound:
        spreadsheet = client.create(SHEET_NAME)
        sheet = spreadsheet.sheet1
        # Nastav hlavičky
        sheet.append_row(HEADERS)
        # Formátování hlavičky - tučně
        last_col = chr(ord("A") + len(HEADERS) - 1)
        sheet.format(f"A1:{last_col}1", {
            "textFormat": {"bold": True},
            "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.2},
        })
        print(f"✓ Sheet vytvořen: {SHEET_NAME}")
        print(f"  URL: {spreadsheet.url}")
        # Ulož URL do souboru
        with open(os.path.join(os.path.dirname(__file__), "sheet_url.txt"), "w") as f:
            f.write(spreadsheet.url)
    return sheet


def get_existing_emails(sheet):
    """Vrátí set všech emailů které už jsou v databázi"""
    try:
        records = _retry(sheet.get_all_records)
        return {r["Email"].lower() for r in records if r.get("Email")}
    except Exception:
        return set()


def get_existing_names(sheet):
    """Vrátí set všech názvů podniků které už jsou v databázi"""
    try:
        records = _retry(sheet.get_all_records)
        return {r["Název"].lower() for r in records if r.get("Název")}
    except Exception:
        return set()


def is_duplicate(sheet, name, email=""):
    """Zkontroluje jestli podnik už je v databázi – Název=sl.0, Email=sl.3."""
    try:
        all_values = _retry(sheet.get_all_values)
        for row_vals in all_values[1:]:
            row_email = row_vals[3].lower() if len(row_vals) > 3 else ""
            row_name  = row_vals[0].lower() if len(row_vals) > 0 else ""
            if email and row_email and email.lower() == row_email:
                return True
            if name and row_name and name.lower() == row_name:
                return True
    except Exception:
        pass
    return False


def add_restaurant(sheet, data):
    """
    Přidá restauraci do sheetu.
    data = dict s klíči: name, address, phone, email, website,
                         pagespeed, category, demo_url, city_real, vision_score
    """
    if is_duplicate(sheet, data.get("name", ""), data.get("email", "")):
        print(f"  ⚠️  Přeskakuji duplikát: {data.get('name')}")
        return False

    # Extrahuj vision skóre z reasons pokud je tam (👁️ řádek)
    vision_score = data.get("vision_score", "")
    if not vision_score:
        for r in data.get("reasons", []):
            if "Vision" in r or "vision" in r:
                import re as _re
                m = _re.search(r"(\d+)/100", r)
                if m:
                    vision_score = int(m.group(1))
                break

    row = [
        data.get("name", ""),
        data.get("address", ""),
        data.get("phone", ""),
        data.get("email", ""),
        data.get("website", ""),
        data.get("pagespeed", 0),
        data.get("category", ""),
        data.get("demo_url", ""),
        datetime.now().strftime("%d.%m.%Y"),
        "",              # datum emailu – vyplní se až po odeslání
        data.get("status_override", "nový") or "nový",
        data.get("note", ""),        # poznámka
        data.get("city_real", data.get("city", "")),  # Město
        vision_score,    # Vision skóre
        "",              # Otevřel email
        "",              # Odpověděl
        "",              # Zájem
        data.get("ab_variant", ""),  # AB Varianta
        data.get("fb_page_url", ""), # Facebook URL
        data.get("industry", "restaurace"),  # Odvětví
        "",              # Datum follow-up
        data.get("follow_up_due", ""),  # Follow-up due
    ]
    _retry(sheet.append_row, row)

    # Obarvi nový řádek podle stavu "nový"
    try:
        row_idx = len(_retry(sheet.get_all_values))  # nový řádek je poslední
        last_col = chr(ord("A") + len(HEADERS) - 1)
        color = ROW_COLORS.get("nový", {"red": 1.0, "green": 1.0, "blue": 1.0})
        sheet.format(f"A{row_idx}:{last_col}{row_idx}", {
            "backgroundColor": color
        })
    except Exception:
        pass  # formátování není kritické

    return True


def mark_email_sent(sheet, email, note=""):
    """Označí podnik jako oslovený a obarví řádek."""
    import re as _re
    # Extrahuj čistý email z formátu "Jméno <email>" nebo jen "email"
    m = _re.search(r'[\w.+-]+@[\w.-]+\.\w+', email)
    clean_email = m.group(0).lower() if m else email.lower().strip()
    try:
        cell = sheet.find(clean_email)
        sheet.update_cell(cell.row, HEADERS.index("Datum emailu") + 1,
                          datetime.now().strftime("%d.%m.%Y %H:%M"))
        sheet.update_cell(cell.row, HEADERS.index("Stav") + 1, "osloveno")
        if note:
            sheet.update_cell(cell.row, HEADERS.index("Poznámka") + 1, note)
        _colorize_row(sheet, cell.row, "osloveno")
    except Exception as e:
        print(f"  Chyba při aktualizaci stavu: {e}")


def update_status(sheet, email, status: str, note: str = ""):
    """
    Aktualizuje stav kontaktu a obarví řádek.
    status: 'nový' | 'osloveno' | 'bez_odpovědi' | 'odpověděl' | 'nezájem'
    """
    try:
        cell = sheet.find(email)
        sheet.update_cell(cell.row, HEADERS.index("Stav") + 1, status)
        if note:
            sheet.update_cell(cell.row, HEADERS.index("Poznámka") + 1, note)
        _colorize_row(sheet, cell.row, status)
    except Exception as e:
        print(f"  Chyba při aktualizaci stavu: {e}")


def _colorize_row(sheet, row_idx: int, status: str):
    """Obarví řádek podle stavu."""
    color = ROW_COLORS.get(status, {"red": 1.0, "green": 1.0, "blue": 1.0})
    last_col = chr(ord("A") + len(HEADERS) - 1)
    try:
        sheet.format(f"A{row_idx}:{last_col}{row_idx}", {
            "backgroundColor": color
        })
    except Exception:
        pass


def mark_followup_sent(sheet, email: str):
    """Označí kontakt jako 'follow_up_odesl' a zapíše datum follow-upu."""
    import re as _re
    m = _re.search(r'[\w.+-]+@[\w.-]+\.\w+', email)
    clean_email = m.group(0).lower() if m else email.lower().strip()
    try:
        cell = sheet.find(clean_email)
        sheet.update_cell(cell.row, HEADERS.index("Stav") + 1, "follow_up_odesl")
        sheet.update_cell(cell.row, HEADERS.index("Datum follow-up") + 1,
                          datetime.now().strftime("%d.%m.%Y %H:%M"))
        _colorize_row(sheet, cell.row, "follow_up_odesl")
    except Exception as e:
        print(f"  Chyba při aktualizaci follow-up stavu: {e}")


def get_sheet_url():
    url_file = os.path.join(os.path.dirname(__file__), "sheet_url.txt")
    if os.path.exists(url_file):
        with open(url_file) as f:
            return f.read().strip()
    return None


if __name__ == "__main__":
    print("Testuji připojení ke Google Sheets...")
    sheet = get_or_create_sheet()
    print("✅ Připojení funguje!")
    url = get_sheet_url()
    if url:
        print(f"📊 Sheet URL: {url}")
