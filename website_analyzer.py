"""
Kombinovaný analyzátor kvality webů
Krok 1: Technická analýza HTML (rychlá)
Krok 2: Screenshot + Claude Vision (přesná) – pouze pro hraniční případy
"""
import re
import os
import base64
import requests
from bs4 import BeautifulSoup

# Načti .env pokud existuje
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


# ─── KROK 1: TECHNICKÁ ANALÝZA ──────────────────────────────────────────────

def analyze_technical(url):
    """
    Stáhne HTML a ohodnotí web technickými signály.
    Vrátí score 0-100 a seznam důvodů.
    """
    try:
        resp = requests.get(
            url, timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            allow_redirects=True
        )
        html = resp.text
    except Exception as e:
        return 0, [f"Web nedostupný: {e}"]

    soup = BeautifulSoup(html, "html.parser")
    score = 50  # začínáme na 50
    reasons = []

    # 1. Viewport meta (mobilní responsivita) – klíčové
    viewport = soup.find("meta", attrs={"name": "viewport"})
    if not viewport:
        score -= 30
        reasons.append("❌ Chybí viewport meta – nefunguje na mobilu")
    else:
        score += 10
        reasons.append("✓ Mobilní responsivita OK")

    # 2. Copyright rok v patičce
    footer_text = ""
    footer = soup.find("footer")
    if footer:
        footer_text = footer.get_text()
    else:
        footer_text = html[-3000:]  # konec stránky

    years = re.findall(r"20(\d{2})", footer_text)
    if years:
        latest_year = max(int(y) for y in years)
        if latest_year < 20:  # před 2020
            score -= 25
            reasons.append(f"❌ Copyright rok 20{latest_year:02d} – starý web")
        elif latest_year >= 23:  # 2023+
            score += 15
            reasons.append(f"✓ Aktuální rok 20{latest_year:02d}")
        else:
            reasons.append(f"~ Rok 20{latest_year:02d}")

    # 3. jQuery verze
    scripts = " ".join(str(s) for s in soup.find_all("script"))
    jquery_old = re.search(r"jquery[.-](1\.\d+|2\.\d+)", scripts, re.I)
    jquery_modern = re.search(r"jquery[.-]3\.", scripts, re.I)
    if jquery_old:
        score -= 20
        reasons.append(f"❌ Starý jQuery {jquery_old.group()} – zastaralý kód")
    elif jquery_modern:
        reasons.append("~ jQuery 3.x nalezen")

    # 4. Moderní fonty (Google Fonts)
    if "fonts.googleapis.com" in html or "fonts.gstatic.com" in html:
        score += 10
        reasons.append("✓ Google Fonts – moderní typografie")
    else:
        score -= 5
        reasons.append("~ Žádné Google Fonts")

    # 5. CSS framework detekce
    if "tailwind" in html.lower():
        score += 20
        reasons.append("✓ Tailwind CSS – moderní framework")
    elif "bootstrap" in html.lower():
        bs_version = re.search(r"bootstrap[/\-](\d)", html, re.I)
        if bs_version and int(bs_version.group(1)) >= 5:
            score += 15
            reasons.append("✓ Bootstrap 5+ – moderní")
        elif bs_version and int(bs_version.group(1)) <= 3:
            score -= 15
            reasons.append(f"❌ Bootstrap {bs_version.group(1)} – zastaralý")
        else:
            reasons.append("~ Bootstrap detekován (verze neznámá)")

    # 6. CSS custom properties (moderní CSS)
    styles = " ".join(str(s) for s in soup.find_all("style"))
    if "--" in styles and "var(" in styles:
        score += 10
        reasons.append("✓ CSS proměnné (moderní CSS)")

    # 7. Tabulkový layout (velmi starý přístup)
    tables = soup.find_all("table")
    layout_tables = [t for t in tables if not t.find_parent(["article", "section"]) and len(t.find_all("td")) > 3]
    if len(layout_tables) > 2:
        score -= 20
        reasons.append(f"❌ Tabulkový layout ({len(layout_tables)} tabulek) – velmi starý web")

    # 8. Zastaralé HTML tagy
    old_tags = soup.find_all(["font", "center", "marquee", "blink", "frame", "frameset"])
    if old_tags:
        score -= 25
        reasons.append(f"❌ Zastaralé HTML tagy: {[t.name for t in old_tags[:3]]}")

    # 9. Moderní JS signály
    if any(kw in html for kw in ["async", "defer", "type=\"module\"", "type='module'"]):
        score += 5
        reasons.append("✓ Moderní JavaScript")

    # 10. Animační knihovny (signál moderního designu)
    if any(lib in html.lower() for lib in ["gsap", "aos", "framer", "lottie", "swiper"]):
        score += 10
        reasons.append("✓ Moderní animační knihovny")

    score = max(0, min(100, score))
    return score, reasons


# ─── KROK 2: SCREENSHOT + CLAUDE VISION ──────────────────────────────────────

def take_screenshot(url, save_path):
    """Pořídí screenshot pomocí Playwright"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False  # Playwright není nainstalován (např. GitHub Actions bez chromium)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(url, timeout=15000, wait_until="networkidle")
            page.screenshot(path=save_path, full_page=False)
            browser.close()
        return True
    except Exception as e:
        print(f"  Screenshot chyba: {e}")
        return False


def analyze_with_claude_vision(screenshot_path, website_url):
    """
    Pošle screenshot Claude API a získá hodnocení designu.
    Vrátí score 0-100 a popis.
    """
    if not ANTHROPIC_API_KEY:
        return None, "Chybí ANTHROPIC_API_KEY"

    with open(screenshot_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    payload = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 300,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            f"Toto je screenshot webu {website_url}. "
                            "Ohodnoť vizuální kvalitu a modernost designu jako webdesigner. "
                            "Odpoviš POUZE ve formátu:\n"
                            "SCORE: [číslo 0-100]\n"
                            "VERDICT: [stary/hranicni/moderni]\n"
                            "REASON: [1 věta česky proč]\n"
                            "Kde 0=velmi starý ošklivý web, 100=moderní profesionální design."
                        ),
                    },
                ],
            }
        ],
    }

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers, json=payload, timeout=30
        )
        text = resp.json()["content"][0]["text"]
        score_match = re.search(r"SCORE:\s*(\d+)", text)
        verdict_match = re.search(r"VERDICT:\s*(\w+)", text)
        reason_match = re.search(r"REASON:\s*(.+)", text)

        score = int(score_match.group(1)) if score_match else 50
        verdict = verdict_match.group(1) if verdict_match else "hranicni"
        reason = reason_match.group(1) if reason_match else ""
        return score, f"{verdict} – {reason}"
    except Exception as e:
        return None, f"Claude API chyba: {e}"


# ─── HLAVNÍ FUNKCE ───────────────────────────────────────────────────────────

def assess_website(url, screenshots_dir="output/screenshots"):
    """
    Kompletní hodnocení webu.
    Vrátí: (final_score, verdict, details)
    verdict: 'bez_webu' / 'spatny_web' / 'ok_web'
    """
    if not url:
        return 0, "bez_webu", ["Nemá webové stránky"]

    print(f"  🔍 Technická analýza...")
    tech_score, tech_reasons = analyze_technical(url)
    print(f"  📊 Technické skóre: {tech_score}/100")

    # Hraniční pásmo 35-65 → použij Claude Vision
    final_score = tech_score
    vision_info = ""

    if 35 <= tech_score <= 65 and ANTHROPIC_API_KEY:
        print(f"  📸 Hraniční případ – pořizuji screenshot pro Claude Vision...")
        os.makedirs(screenshots_dir, exist_ok=True)
        slug = re.sub(r"[^a-z0-9]", "-", url.lower())[:40]
        screenshot_path = os.path.join(screenshots_dir, f"{slug}.png")

        if take_screenshot(url, screenshot_path):
            vision_score, vision_desc = analyze_with_claude_vision(screenshot_path, url)
            if vision_score is not None:
                # Váhovaný průměr: 40% technika, 60% vizuál
                final_score = int(tech_score * 0.4 + vision_score * 0.6)
                vision_info = f"👁️  Claude Vision: {vision_score}/100 – {vision_desc}"
                print(f"  {vision_info}")
                print(f"  🎯 Finální skóre: {final_score}/100")

    # Klasifikace
    # Bez Claude Vision (API klíč chybí) bereme vše pod 65 jako špatný web,
    # protože hraniční pásmo 35-65 nemáme jak vizuálně posoudit.
    threshold = 50 if ANTHROPIC_API_KEY else 65
    if final_score < threshold:
        verdict = "spatny_web"
    else:
        verdict = "ok_web"

    details = tech_reasons
    if vision_info:
        details.append(vision_info)

    return final_score, verdict, details


if __name__ == "__main__":
    # Test na konkrétních webech
    test_urls = [
        ("Apelace21", "http://www.apelace21.cz/"),
        ("Mlýnec", "https://www.mlynec.cz/"),
        ("Bílá kráva", "http://www.bilakrava.cz/"),
    ]

    for name, url in test_urls:
        print(f"\n{'='*50}")
        print(f"🌐 {name}: {url}")
        score, verdict, details = assess_website(url)
        print(f"  Výsledek: {verdict} (skóre {score}/100)")
        for d in details:
            print(f"    {d}")
