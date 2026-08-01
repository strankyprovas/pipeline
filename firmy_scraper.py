"""
Scraper pro Firmy.cz – získá podniky s jejich kontaktními údaji a webem.

Strategie:
1. Načte listing stránky dané kategorie pro dané město (14 výsledků/stránku)
2. Sbírá: název, adresa, web (pokud v listingu), detail URL
3. Pro podniky BEZ webu v listingu → navštíví detail stránku → web, email, telefon
4. Vrátí seznam podniků (kompatibilní formát s run_all_cities.py)

Použití:
    from firmy_scraper import search_businesses_firmy
    businesses = asyncio.run(search_businesses_firmy("Praha", "restaurace", max_results=20))
"""

import asyncio
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Mapování odvětví na Firmy.cz URL slug (kategorie) nebo search query (?q=...)
# Formát: "slug/path" → URL /{slug}?locality={city}
#         "?q=term"   → URL /?q={term}&locality={city}  (pro kategorie bez funkčního slug)
FIRMY_CATEGORY_SLUGS = {
    "restaurace":   "?q=restaurace",
    "kavarna":      "?q=kavarna",
    "pekarna":      "?q=pekařství",
    "kvetinarstvi": "?q=květinářství",
    "penzion":      "?q=penzion",
    "kadernictvi":  "?q=kadernictvi",
    "kosmetika":    "?q=kosmeticky+salon",
    "autoservis":   "?q=autoservis",
    "masaze":       "?q=masaze",
    "zubni":        "?q=zubni+ordinace",
    "psycholog":    "?q=psycholog",
}

FIRMY_BASE = "https://www.firmy.cz"
CONSENT_SELECTORS = [
    '[data-testid="cw-button-agree-with-ads"]',
    'button[data-testid="cw-button-agree-with-ads"]',
    'button:has-text("Souhlasím se vším")',
    'button:has-text("Souhlasím")',
    'button:has-text("Přijmout vše")',
    'button:has-text("Přijmout")',
    'button:has-text("Agree")',
]

# Globální browser instance (sdílená v rámci procesu)
_browser = None
_context = None
_consent_done = False


async def _get_context():
    """Vrátí sdílený playwright context, inicializuje pokud potřeba."""
    global _browser, _context, _consent_done
    from playwright.async_api import async_playwright

    if _context is None:
        pw = await async_playwright().start()
        _browser = await pw.chromium.launch(headless=True)
        _context = await _browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
        _consent_done = False

    return _context


async def _accept_consent(page):
    """Přijme CMP souhlas pokud je zobrazený. Zkouší main page i CMP iframe."""
    # 1) Zkus tlačítka na hlavní stránce
    for sel in CONSENT_SELECTORS:
        try:
            await page.wait_for_selector(sel, timeout=3000)
            btn = await page.query_selector(sel)
            if btn:
                await btn.click()
                await page.wait_for_timeout(2000)
                return True
        except Exception:
            pass

    # 2) Zkus CMP iframe (h.seznam.cz/html/cmp.html)
    try:
        cmp_loc = page.frame_locator('iframe[src*="cmp"]')
        for txt in ["Přijmout vše", "Přijmout", "Souhlasím", "Accept all"]:
            try:
                btn = cmp_loc.locator(f'button:has-text("{txt}")')
                if await btn.count() > 0:
                    await btn.first.click()
                    await page.wait_for_timeout(2000)
                    return True
            except Exception:
                pass
    except Exception:
        pass

    return False


async def _scrape_detail(context, detail_url: str) -> dict:
    """Navštíví detail stránku podniku a extrahuje web, email, telefon."""
    page = await context.new_page()
    result = {"website": None, "email": None, "phone": None}

    async def _extract():
        # Web – pouze z data-dot="show-website", vyhni se social sítím
        SOCIAL_DOMAINS = ["facebook", "instagram", "linkedin", "twitter", "tiktok", "youtube"]
        web_el = await page.query_selector('[data-dot="show-website"]')
        if web_el:
            href = await web_el.get_attribute("href") or ""
            text = (await web_el.inner_text()).strip()
            url = href if href.startswith("http") else text
            # Odfiltruj social sítě a firmy.cz
            if url and not any(x in url.lower() for x in SOCIAL_DOMAINS + ["firmy.cz"]):
                if not url.startswith("http"):
                    url = "https://" + url.lstrip("/")
                result["website"] = url

        # Email
        email_el = await page.query_selector('[data-dot="e-mail"]')
        if email_el:
            result["email"] = (await email_el.inner_text()).strip()

        # Telefon
        phone_el = await page.query_selector('[data-dot="origin-phone-number"]')
        if phone_el:
            result["phone"] = (await phone_el.inner_text()).strip()

    try:
        await page.goto(detail_url, wait_until="domcontentloaded", timeout=25000)
        await _accept_consent(page)
        # Po souhlasu se stránka může reloadovat – počkej na ustálení,
        # jinak query_selector padá na "Execution context was destroyed"
        try:
            await page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        await page.wait_for_timeout(1500)

        for attempt in range(2):
            try:
                await _extract()
                break
            except Exception as e:
                if "Execution context was destroyed" in str(e) and attempt == 0:
                    await page.wait_for_timeout(2500)
                    continue
                raise

    except Exception as e:
        logger.warning(f"Detail scrape error {detail_url}: {e}")
    finally:
        await page.close()

    return result


async def search_businesses_firmy(
    city: str,
    industry: str = "restaurace",
    max_results: int = 20,
    check_details: bool = True,
) -> list[dict]:
    """
    Prohledá Firmy.cz a vrátí podniky ve formátu kompatibilním s main.py.

    Args:
        city: Název města (např. "Praha", "Brno")
        industry: Odvětví (viz FIRMY_CATEGORY_SLUGS)
        max_results: Maximální počet výsledků
        check_details: Zda navštívit detail stránku pro podniky bez webu

    Returns:
        Seznam slovníků s klíči: name, address, phone, website, email,
        facebook, lat, lon, rating, reviews_count, price_level, opening_hours
    """
    slug = FIRMY_CATEGORY_SLUGS.get(industry)
    if not slug:
        logger.warning(f"Neznámé odvětví: {industry}")
        return []

    context = await _get_context()
    page = await context.new_page()
    businesses = []

    try:
        # Načti první stránku výsledků
        # Všechny kategorie používají ?q= formát s městem přímo v query
        # např. https://www.firmy.cz/?q=restaurace+Praha
        from urllib.parse import quote_plus
        if slug.startswith("?q="):
            term = slug[3:]  # odstraň "?q="
        else:
            term = slug.replace("/", " ").replace("-", " ").lower()
        query = quote_plus(f"{term} {city}")
        url = f"{FIRMY_BASE}/?q={query}"
        await page.goto(url, wait_until="domcontentloaded", timeout=35000)
        await _accept_consent(page)
        await page.wait_for_timeout(4000)

        # Zjisti počet stránek
        pages_total = 1
        pag = await page.query_selector('[data-dot="navigation/pagination"]')
        if pag:
            pag_links = await pag.query_selector_all("a")
            nums = []
            for a in pag_links:
                t = await a.inner_text()
                if t.strip().isdigit():
                    nums.append(int(t.strip()))
            if nums:
                pages_total = max(nums)

        logger.info(f"Firmy.cz {industry}/{city}: {pages_total} stránek")

        for page_num in range(1, pages_total + 1):
            if len(businesses) >= max_results:
                break

            if page_num > 1:
                page_url = f"{FIRMY_BASE}/?q={query}&page={page_num}"
                await page.goto(page_url, wait_until="domcontentloaded", timeout=25000)
                await page.wait_for_timeout(3000)

            articles = await page.query_selector_all("article.premiseBox")
            for art in articles:
                if len(businesses) >= max_results:
                    break

                # Název
                h3 = await art.query_selector("h3")
                name = (await h3.inner_text()).strip() if h3 else ""
                if not name:
                    continue

                # Adresa
                addr_el = await art.query_selector('[data-dot="address"]')
                address = (await addr_el.inner_text()).strip() if addr_el else ""

                # Detail URL + web z listingu
                detail_url = None
                website = None
                all_links = await art.query_selector_all("a[href]")
                for a in all_links:
                    href = await a.get_attribute("href") or ""
                    if "detail" in href and "firmy.cz" in href:
                        detail_url = href.split("#")[0]  # odstraň anchor
                    elif (
                        href.startswith("http")
                        and "firmy.cz" not in href
                        and "mapy." not in href
                        and not any(s in href.lower() for s in ["facebook", "instagram", "twitter"])
                    ):
                        website = href

                biz = {
                    "name": name,
                    "address": address,
                    "phone": None,
                    "website": website,
                    "email": None,
                    "facebook": None,
                    "contact_email": None,
                    "lat": None,
                    "lon": None,
                    "rating": None,
                    "reviews_count": 0,
                    "price_level": None,
                    "opening_hours": None,
                    "_detail_url": detail_url,
                }
                businesses.append(biz)

    except Exception as e:
        logger.error(f"Chyba při scraping listingu {industry}/{city}: {e}")
    finally:
        await page.close()

    # Navštiv detail stránky pro všechny podniky bez emailu (bez webu i s webem)
    if check_details:
        detail_tasks = [
            b for b in businesses
            if not b.get("email") and b.get("_detail_url")
        ]
        logger.info(f"  Detaily: {len(detail_tasks)}/{len(businesses)} podniků")

        # Zpracuj po 3 souběžně
        batch_size = 3
        for i in range(0, len(detail_tasks), batch_size):
            batch = detail_tasks[i:i + batch_size]
            results = await asyncio.gather(
                *[_scrape_detail(context, b["_detail_url"]) for b in batch],
                return_exceptions=True,
            )
            for biz, res in zip(batch, results):
                if isinstance(res, dict):
                    biz["website"] = res.get("website")
                    biz["email"] = res.get("email")
                    biz["phone"] = res.get("phone") or biz.get("phone")
                    if biz["email"]:
                        biz["contact_email"] = biz["email"]

    # Odstraň interní pole
    for b in businesses:
        b.pop("_detail_url", None)

    return businesses


async def close():
    """Uzavře browser."""
    global _browser, _context, _consent_done
    if _browser:
        await _browser.close()
        _browser = None
        _context = None
        _consent_done = False


def search_businesses_firmy_sync(
    city: str,
    industry: str = "restaurace",
    max_results: int = 20,
    check_details: bool = True,
) -> list[dict]:
    """
    Synchronní wrapper pro search_businesses_firmy().
    Lze volat z neaktuální funkce (main.py, scraper.py atd.).
    """
    import asyncio

    async def _run():
        results = await search_businesses_firmy(city, industry, max_results, check_details)
        await close()   # explicitně zavři browser před ukončením loopu
        return results

    # Vždy vytvoř nový event loop (bezpečné pro subprocess volání)
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        # Zruš zbývající pending tasky (Playwright connection tasks) před zavřením
        try:
            pending = asyncio.all_tasks(loop)
            if pending:
                for task in pending:
                    task.cancel()
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass
        loop.close()


# ─── CLI test ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    city = sys.argv[1] if len(sys.argv) > 1 else "Praha"
    industry = sys.argv[2] if len(sys.argv) > 2 else "restaurace"
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 5

    async def main():
        results = await search_businesses_firmy(city, industry, max_results=limit)
        print(f"\n✅ Nalezeno {len(results)} podniků v {city} ({industry}):\n")
        for b in results:
            web = b.get("website") or "–"
            email = b.get("email") or "–"
            phone = b.get("phone") or "–"
            print(f"  {b['name']}")
            print(f"    Adresa: {b.get('address','')}")
            print(f"    Web:    {web}")
            print(f"    Email:  {email}")
            print(f"    Tel:    {phone}")
        await close()

    asyncio.run(main())
