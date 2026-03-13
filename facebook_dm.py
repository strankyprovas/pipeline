"""
Facebook DM sender – posílá zprávy na Facebook stránky podniků bez emailu.
Používá Playwright (browser automation) s lidským chováním.

Použití:
    venv/bin/python3 facebook_dm.py                    # test přihlášení
    venv/bin/python3 facebook_dm.py --test-login       # ověř přihlášení
"""
import os
import re
import time
import random
import argparse
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

FB_EMAIL    = os.getenv("FB_EMAIL", "")
FB_PASSWORD = os.getenv("FB_PASSWORD", "")

# Cesta k uloženým session cookies – abychom se nepřihlašovali pokaždé znovu
SESSION_FILE = os.path.join(os.path.dirname(__file__), "fb_session.json")


def _human_delay(min_s: float = 1.5, max_s: float = 4.0):
    """Náhodné zpoždění – napodobuje lidské chování."""
    time.sleep(random.uniform(min_s, max_s))


def _login(page) -> bool:
    """Přihlásí se na Facebook. Vrátí True pokud úspěch."""
    print("  🔐 Přihlašuji se na Facebook...")
    page.goto("https://www.facebook.com/login", wait_until="domcontentloaded", timeout=30000)
    _human_delay(2, 3)

    # Odmítni/přijmi cookie banner pokud se zobrazí
    for cookie_text in [
        "Povolit všechny soubory cookie",
        "Allow all cookies",
        "Accept All",
        "Odmítnout volitelné soubory cookie",
        "Decline optional cookies",
    ]:
        try:
            btn = page.get_by_role("button", name=cookie_text, exact=False).first
            if btn and btn.is_visible():
                btn.click()
                _human_delay(1, 2)
                break
        except Exception:
            pass

    # Vyplň email
    email_input = page.wait_for_selector('input[name="email"], input#email', timeout=10000)
    email_input.fill(FB_EMAIL)
    _human_delay(0.8, 1.5)

    # Vyplň heslo
    pass_input = page.wait_for_selector('input[name="pass"], input#pass', timeout=5000)
    pass_input.fill(FB_PASSWORD)
    _human_delay(0.5, 1.0)

    # Klikni přihlásit – zkus více selektorů
    for login_sel in [
        'button[name="login"]',
        'button[type="submit"]',
        '[data-testid="royal_login_button"]',
        'input[type="submit"]',
    ]:
        try:
            btn = page.query_selector(login_sel)
            if btn:
                btn.click()
                break
        except Exception:
            continue

    page.wait_for_load_state("networkidle", timeout=20000)
    _human_delay(2, 3)

    # Zkontroluj jestli jsme přihlášeni
    url = page.url
    if "facebook.com" in url and "login" not in url and "checkpoint" not in url:
        print("  ✅ Přihlášení úspěšné")
        return True
    elif "checkpoint" in url:
        print("  ⚠️  Facebook vyžaduje verifikaci – otevři prohlížeč ručně")
        return False
    else:
        print(f"  ❌ Přihlášení selhalo (URL: {url})")
        return False


def _get_messenger_url(fb_page_url: str) -> str:
    """Vrátí přímou Messenger URL z Facebook page URL."""
    url = fb_page_url.rstrip("/")
    # profile.php?id=XXXXX → messages/t/XXXXX
    id_match = re.search(r'[?&]id=(\d+)', url)
    if id_match:
        return f"https://www.facebook.com/messages/t/{id_match.group(1)}"
    # /pagename → messages/t/pagename
    handle = url.rstrip("/").split("/")[-1].split("?")[0]
    if handle:
        return f"https://www.facebook.com/messages/t/{handle}"
    return "https://www.facebook.com/messages"


def send_facebook_dm(fb_page_url: str, message: str, headless: bool = True) -> bool:
    """
    Pošle zprávu na Facebook stránku podniku přes Messenger.
    Vrátí True pokud úspěch.
    """
    from playwright.sync_api import sync_playwright

    if not FB_EMAIL or not FB_PASSWORD:
        print("  ❌ Chybí FB_EMAIL nebo FB_PASSWORD v .env")
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="cs-CZ",
        )

        # Načti uloženou session pokud existuje
        if os.path.exists(SESSION_FILE):
            context.add_cookies(_load_session())

        page = context.new_page()

        try:
            # Zkontroluj jestli jsme přihlášeni
            page.goto("https://www.facebook.com", wait_until="domcontentloaded", timeout=20000)
            _human_delay(2, 3)

            if "login" in page.url or page.query_selector('input[name="email"]'):
                if not _login(page):
                    return False
                _save_session(context.cookies())

            # Normalizuj m.facebook.com → www.facebook.com
            fb_page_url = fb_page_url.replace("m.facebook.com", "www.facebook.com")

            # Extrahuj page handle / ID pro přímou Messenger URL
            messenger_url = _get_messenger_url(fb_page_url)
            print(f"  💬 Otevírám Messenger: {messenger_url}")
            page.goto(messenger_url, wait_until="domcontentloaded", timeout=20000)
            _human_delay(3, 5)

            # FB může zobrazit PIN dialog pro obnovení historie – zavři ho
            page.keyboard.press("Escape")
            _human_delay(1, 2)
            for dont_restore_label in ["Don't restore messages", "Nepřepínat", "Continue without restoring"]:
                try:
                    btn = page.get_by_role("button", name=dont_restore_label)
                    if btn and btn.is_visible():
                        btn.click()
                        _human_delay(1, 2)
                        break
                except Exception:
                    pass

            # Najdi textové pole zprávy
            msg_box = None
            for selector in [
                '[aria-label="Message"][role="textbox"]',
                '[aria-label="Aa"][role="textbox"]',
                '[role="textbox"]',
                'textarea',
            ]:
                try:
                    msg_box = page.wait_for_selector(selector, timeout=8000)
                    if msg_box and msg_box.is_visible():
                        break
                    msg_box = None
                except Exception:
                    continue

            if not msg_box:
                try:
                    ss_path = os.path.join(os.path.dirname(__file__), "fb_debug.png")
                    page.screenshot(path=ss_path, full_page=False)
                    print(f"  📸 Screenshot: {ss_path} | URL: {page.url}")
                except Exception:
                    pass
                print("  ⚠️  Textové pole zprávy nenalezeno")
                return False

            # Piš zprávu pomalu jako člověk
            msg_box.click()
            _human_delay(0.5, 1)
            for char in message:
                msg_box.type(char, delay=random.randint(30, 120))

            _human_delay(1, 2)

            # Odešli – Enter
            msg_box.press("Enter")
            _human_delay(2, 3)

            print("  ✅ Zpráva odeslána")
            return True

        except Exception as e:
            print(f"  ❌ Chyba při odesílání: {e}")
            return False
        finally:
            browser.close()


def _save_session(cookies: list):
    import json
    with open(SESSION_FILE, "w") as f:
        json.dump(cookies, f)


def _load_session() -> list:
    """Načte cookies a převede formát Cookie-Editor → Playwright."""
    import json
    with open(SESSION_FILE) as f:
        raw = json.load(f)
    samesite_map = {"no_restriction": "None", "lax": "Lax", "strict": "Strict", None: "None"}
    cookies = []
    for c in raw:
        cookies.append({
            "name": c["name"],
            "value": c["value"],
            "domain": c["domain"],
            "path": c.get("path", "/"),
            "secure": c.get("secure", False),
            "httpOnly": c.get("httpOnly", False),
            "sameSite": samesite_map.get(c.get("sameSite"), "None"),
        })
    return cookies


def test_login(headless: bool = True) -> bool:
    """Otestuje přihlášení přes session cookies."""
    from playwright.sync_api import sync_playwright

    if not os.path.exists(SESSION_FILE):
        print(f"  ❌ Chybí {SESSION_FILE} – exportuj cookies z prohlížeče")
        return False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(locale="cs-CZ", viewport={"width": 1280, "height": 800})
        context.add_cookies(_load_session())
        page = context.new_page()

        page.goto("https://www.facebook.com", wait_until="domcontentloaded", timeout=20000)
        _human_delay(2, 3)

        url = page.url
        logged_in = "facebook.com" in url and "login" not in url
        if logged_in:
            print("  ✅ Session funguje – jsme přihlášeni")
        else:
            print(f"  ❌ Session nefunguje (URL: {url})")

        browser.close()
        return logged_in


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-login", action="store_true",
                        help="Otestuj přihlášení (otevře prohlížeč)")
    parser.add_argument("--headful", action="store_true",
                        help="Zobraz prohlížeč (ne headless)")
    args = parser.parse_args()

    if args.test_login:
        print("🔐 Testuji přihlášení na Facebook...")
        ok = test_login(headless=not args.headful)
        if ok:
            print("✅ Přihlášení funguje – session uložena")
        else:
            print("❌ Přihlášení selhalo")
