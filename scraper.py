import requests
import os
import re
import shutil
import time

# Adresář se stock fotkami (stažit jednou přes setup_stock_photos.py)
STOCK_PHOTOS_DIR = os.path.join(os.path.dirname(__file__), "stock_photos")

# User-Agent pro Nominatim (povinný dle ToS)
_OSM_HEADERS = {"User-Agent": "StrankyProVas/1.0 outreach-pipeline"}


def _get_city_bbox(city: str) -> tuple[float, float, float, float] | None:
    """Nominatim → bounding box pro město v ČR. Vrátí (south, west, north, east)."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": f"{city}, Czech Republic", "format": "json", "limit": 1}
    try:
        resp = requests.get(url, params=params, headers=_OSM_HEADERS, timeout=10)
        data = resp.json()
        if data:
            bb = data[0]["boundingbox"]  # [south, north, west, east]
            return float(bb[0]), float(bb[2]), float(bb[1]), float(bb[3])
    except Exception as e:
        print(f"  ⚠️  Nominatim error pro '{city}': {e}")
    return None


def search_businesses(city="Praha", num_results=10, osm_filter='["amenity"="restaurant"]', **kwargs) -> list[dict]:
    """
    Hledá podniky přes Overpass API (OpenStreetMap). Zdarma, bez API klíče.
    osm_filter: OSM tag filter, např. '["amenity"="restaurant"]' nebo '["shop"="hairdresser"]'
    """
    bbox = _get_city_bbox(city)
    if not bbox:
        print(f"  ⚠️  Nepodařilo se najít bbox pro město '{city}'")
        return []

    s, w, n, e = bbox
    # Požadujeme 2× více než chceme – po deduplikaci jich bude méně
    limit = max(num_results * 2, 120)

    query = f"""
[out:json][timeout:40];
(
  node{osm_filter}({s},{w},{n},{e});
  way{osm_filter}({s},{w},{n},{e});
);
out body center {limit};
"""
    # Záložní Overpass servery – zkusíme postupně.
    # ⚠️ User-Agent je POVINNÝ: bez něj vrací overpass-api.de 406 Not Acceptable.
    overpass_servers = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.openstreetmap.fr/api/interpreter",
        "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
        "https://overpass.osm.ch/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
    ]
    data = None
    empty_ok = False  # server odpověděl korektně, jen tam nic není (řídké obory/malé obce)
    # 2 kola – přetížené servery (504/429) často projdou na druhý pokus
    for attempt in range(2):
        for server in overpass_servers:
            try:
                resp = requests.post(server, data=query,
                                     headers=_OSM_HEADERS, timeout=90)
                if resp.status_code == 200 and resp.content:
                    candidate = resp.json()
                    if candidate.get("elements"):
                        data = candidate
                        break
                    empty_ok = True
                    continue
                print(f"  ⚠️  Overpass {server.split('/')[2]}: {resp.status_code}")
            except Exception as e:
                print(f"  ⚠️  Overpass {server.split('/')[2]}: {str(e)[:60]}")
        if data is not None or empty_ok:
            break
        if attempt == 0:
            time.sleep(5)
    if data is None:
        if not empty_ok:
            print("  ❌ Všechny Overpass servery selhaly")
        return []

    results = []
    seen_names: set[str] = set()

    for el in data.get("elements", []):
        tags = el.get("tags", {})
        name = tags.get("name", "").strip()
        if not name or name.lower() in seen_names:
            continue
        seen_names.add(name.lower())

        # Souřadnice
        if el["type"] == "node":
            lat, lon = el.get("lat", 0.0), el.get("lon", 0.0)
        else:
            center = el.get("center", {})
            lat, lon = center.get("lat", 0.0), center.get("lon", 0.0)

        # Adresa
        street      = tags.get("addr:street", "")
        housenumber = tags.get("addr:housenumber", "")
        city_tag    = tags.get("addr:city", city)
        postcode    = tags.get("addr:postcode", "")

        addr_parts = []
        if street and housenumber:
            addr_parts.append(f"{street} {housenumber}")
        elif street:
            addr_parts.append(street)
        if postcode and city_tag:
            addr_parts.append(f"{postcode} {city_tag}")
        elif city_tag:
            addr_parts.append(city_tag)
        addr_parts.append("Česká republika")
        address = ", ".join(filter(None, addr_parts))

        # Telefon
        phone = (
            tags.get("phone") or tags.get("contact:phone") or
            tags.get("contact:mobile") or tags.get("mobile") or ""
        )
        if phone:
            phone = phone.split(";")[0].strip()

        # Web
        website = (
            tags.get("website") or tags.get("contact:website") or tags.get("url") or ""
        )
        if website and not website.startswith("http"):
            website = "https://" + website

        # Facebook a email přímo z OSM
        facebook = tags.get("contact:facebook") or tags.get("facebook") or ""
        contact_email = tags.get("email") or tags.get("contact:email") or ""

        results.append({
            "name": name,
            "address": address,
            "phone": phone,
            "website": website,
            "facebook": facebook,
            "contact_email": contact_email,
            "lat": lat,
            "lon": lon,
            "city_real": city_tag or city,
        })

        if len(results) >= num_results:
            break

    return results


def search_restaurants(city="Praha", num_results=10):
    """Zpětná kompatibilita – volá search_businesses pro restaurace."""
    return search_businesses(city=city, num_results=num_results, osm_filter='["amenity"="restaurant"]')


def extract_city(data: dict) -> str:
    """Extrahuje město z OSM dat (city_real) nebo z adresy jako fallback."""
    if isinstance(data, dict):
        if "city_real" in data:
            return data["city_real"]
        address = data.get("address", "") or data.get("formatted_address", "")
        parts = [p.strip() for p in address.split(",")]
        if len(parts) >= 2:
            city_part = parts[-2]
            city_part = re.sub(r"^\d{3}\s?\d{2}\s*", "", city_part).split("-")[0].strip()
            if city_part:
                return city_part
    return ""


def copy_stock_photos(industry: str, save_dir: str, max_photos: int = 5) -> list[str]:
    """
    Zkopíruje generické stock fotky pro odvětví do adresáře dema.
    Stock fotky musí být předem staženy přes setup_stock_photos.py.
    """
    ind_dir = os.path.join(STOCK_PHOTOS_DIR, industry)
    # Fallback na restaurace pokud odvětví nemá vlastní fotky
    if not os.path.isdir(ind_dir):
        ind_dir = os.path.join(STOCK_PHOTOS_DIR, "restaurace")
    if not os.path.isdir(ind_dir):
        print(f"  ⚠️  Stock fotky nenalezeny – spusť setup_stock_photos.py")
        return []

    os.makedirs(save_dir, exist_ok=True)
    paths = []
    for i in range(1, max_photos + 1):
        src = os.path.join(ind_dir, f"photo_{i}.jpg")
        if os.path.exists(src):
            dst = os.path.join(save_dir, f"photo_{i}.jpg")
            shutil.copy2(src, dst)
            paths.append(dst)
    return paths


# Alias pro zpětnou kompatibilitu (voláno z main.py)
def download_photos(photo_references, save_dir, max_photos=5, industry="restaurace"):
    """Zpětná kompatibilita – ignoruje photo_references, kopíruje stock fotky."""
    return copy_stock_photos(industry, save_dir, max_photos)


def check_website(url):
    if not url:
        return False
    try:
        resp = requests.get(
            url,
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0"},
            allow_redirects=True,
        )
        return resp.status_code < 400
    except:
        return False


def get_pagespeed_score(url):
    # PageSpeed Insights API – zdarma i bez klíče (nižší rate limit)
    api_url = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    params = {"url": url, "strategy": "mobile"}
    try:
        resp = requests.get(api_url, params=params, timeout=30)
        data = resp.json()
        score = (
            data.get("lighthouseResult", {})
            .get("categories", {})
            .get("performance", {})
            .get("score", 0)
        )
        return int(score * 100)
    except Exception as e:
        print(f"  PageSpeed error: {e}")
        return 0


def download_photos(photo_references, save_dir, max_photos=5):
    os.makedirs(save_dir, exist_ok=True)
    paths = []
    for i, ref in enumerate(photo_references[:max_photos]):
        url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=1400&photo_reference={ref}&key={API_KEY}"
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                path = os.path.join(save_dir, f"photo_{i+1}.jpg")
                with open(path, "wb") as f:
                    f.write(resp.content)
                paths.append(path)
                print(f"  Fotka {i+1} stažena")
        except Exception as e:
            print(f"  Chyba stahování fotky {i+1}: {e}")
    return paths


# Facebook User-Agent – napodobuje běžný prohlížeč
_FB_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "cs-CZ,cs;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _is_facebook_url(url: str) -> bool:
    return bool(url and "facebook.com" in url.lower())


def scrape_email_from_facebook(fb_url: str) -> str:
    """
    Hledá email na Facebook stránce podniku.
    Zkouší mobilní verzi (m.facebook.com) – jednodušší HTML, méně blokování.
    """
    if not fb_url:
        return ""

    # Převeď na mobilní verzi Facebook
    mobile_url = re.sub(r'https?://(www\.)?facebook\.com', 'https://m.facebook.com', fb_url)
    mobile_url = mobile_url.split("?")[0].rstrip("/")

    urls_to_try = [
        mobile_url + "/about",
        mobile_url,
        fb_url.split("?")[0].rstrip("/") + "/about",
    ]

    fb_junk = ["facebook.com", "fb.com", "tfbnw.net", "meta.com",
               "sentry", "example", "domain", "fbcdn.net"]

    for url in urls_to_try:
        try:
            resp = requests.get(url, timeout=10, headers=_FB_HEADERS, allow_redirects=True)
            if resp.status_code >= 400:
                continue
            html = resp.text

            # 1. JSON data – Facebook vkládá kontaktní info jako "email":"..."
            json_emails = re.findall(
                r'"email"\s*:\s*"([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})"',
                html
            )
            for e in json_emails:
                if not any(j in e.lower() for j in fb_junk):
                    return e

            # 2. Obecný regex
            all_emails = re.findall(
                r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}',
                html
            )
            for e in all_emails:
                if not any(j in e.lower() for j in fb_junk):
                    return e

        except Exception:
            continue

    return ""


def find_facebook_via_google(name: str, city: str) -> str:
    """
    Hledá Facebook stránku restaurace přes DuckDuckGo.
    Vrátí URL Facebook stránky nebo prázdný string.
    """
    query = f'site:facebook.com "{name}" {city}'
    search_url = f"https://duckduckgo.com/html/?q={requests.utils.quote(query)}"
    try:
        resp = requests.get(
            search_url, timeout=10,
            headers={**_FB_HEADERS, "Accept-Language": "cs-CZ,cs;q=0.9"},
        )
        fb_urls = re.findall(
            r'https://(?:www\.)?facebook\.com/(?:pages/)?[a-zA-Z0-9._/\-]{3,}',
            resp.text
        )
        junk = ["/search", "/share", "/login", "/help", "/policies",
                "/groups", "/events", "/marketplace", "/watch"]
        for url in fb_urls:
            url = url.split("?")[0].rstrip("/")
            if not any(j in url for j in junk) and len(url) > 28:
                return url
    except Exception:
        pass
    return ""


# Domény restauračních skupin – info@ zde neposílat
GROUP_DOMAINS = {
    "zatisigroup.cz", "ambi.cz", "kolkovna.cz", "pytloun-restaurants.cz",
    "ambiente.cz", "cresci.cz", "mujrestaurant.cz",
}

# Domény volných emailových poskytovatelů
FREE_MAIL_DOMAINS = {
    "gmail.com", "seznam.cz", "centrum.cz", "email.cz", "volny.cz",
    "yahoo.com", "outlook.com", "hotmail.com", "atlas.cz", "post.cz",
}

# Generické local party – negativní signál pro skupinové/hotelové weby
GENERIC_LOCALS = {"info", "kontakt", "recepce", "rezervace", "office",
                  "contact", "reception", "booking", "hello", "mail"}


def _score_email(email: str, website_domain: str, is_mailto: bool, html: str) -> int:
    """Vrátí skóre emailu. Vyšší = lepší kandidát pro oslovení."""
    email_l = email.lower()
    local, _, domain = email_l.partition("@")
    score = 0

    # Filtr – technické false-positive a template domény
    junk = ["example", "domain", "sentry", "wix", "schema",
            ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".ico",
            ".pdf", ".mp4", ".mp3", ".woff", ".ttf", ".eot",
            "mysite.com", "wixsite.com", "squarespace.com", "weebly.com",
            "webnode.cz", "webnode.com", "strikingly.com"]
    if any(j in email_l for j in junk):
        return -999

    # Doména emailu odpovídá doméně webu → velmi dobrý signál
    if website_domain and (domain == website_domain or domain.endswith("." + website_domain)):
        score += 30

    # Volný emailový poskytovatel → špatný signál (cizí osoba / soukromý kontakt)
    if domain in FREE_MAIL_DOMAINS:
        score -= 50

    # Generický local part u skupinové nebo velké domény → špatný signál
    if local in GENERIC_LOCALS and (domain in GROUP_DOMAINS or website_domain in GROUP_DOMAINS):
        score -= 30

    # Local part vypadá jako jméno (obsahuje tečku jako jan.novak) → dobrý signál
    if "." in local and local.replace(".", "").isalpha():
        score += 20

    # Email je viditelný jako mailto: link → dobrý signál
    if is_mailto:
        score += 10

    return score


# Klíčová slova v URL která naznačují kontaktní stránku
_CONTACT_KEYWORDS = [
    "kontakt", "contact", "kontakty", "contacts",
    "o-nas", "o-nás", "about", "reach", "napiste",
    "napište", "write", "kde-jsme", "kde-najdete",
]


def _fetch_html(url: str, timeout: int = 8) -> str:
    """Stáhne HTML stránky, vrátí prázdný string při chybě."""
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0"},
            allow_redirects=True,
        )
        return resp.text if resp.status_code < 400 else ""
    except Exception:
        return ""


def _extract_emails(html: str, website_domain: str) -> tuple[set, set]:
    """Vrátí (všechny emaily, emaily z mailto: linků) z HTML."""
    mailto = set(re.findall(
        r'mailto:([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})',
        html, re.IGNORECASE
    ))
    all_emails = set(re.findall(
        r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}',
        html
    ))
    return all_emails, mailto


def _find_contact_urls(html: str, base_url: str, website_domain: str) -> list[str]:
    """Najde URL kontaktních podstránek na webu (max 3)."""
    # Nejdřív zkus standardní cesty
    standard_paths = [
        "/kontakt", "/contact", "/kontakty", "/contacts",
        "/o-nas", "/about", "/kde-jsme",
    ]
    base = base_url.rstrip("/")
    candidates = [base + path for path in standard_paths]

    # Pak hledej v odkazech na stránce
    hrefs = re.findall(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE)
    for href in hrefs:
        href_l = href.lower()
        if any(kw in href_l for kw in _CONTACT_KEYWORDS):
            # Absolutní nebo relativní URL
            if href.startswith("http"):
                if website_domain in href:
                    candidates.append(href)
            elif href.startswith("/"):
                candidates.append(base + href)

    # Deduplikuj, zachovej pořadí, max 3
    seen = set()
    result = []
    for c in candidates:
        c = c.split("?")[0].split("#")[0]  # odstraň query string a fragment
        if c not in seen:
            seen.add(c)
            result.append(c)
        if len(result) >= 3:
            break
    return result


def scrape_email_from_website(url: str) -> str:
    """
    Vybere nejlepší kontaktní email z webu pomocí scoringu.
    Prochází homepage + až 3 kontaktní podstránky.
    """
    if not url:
        return ""

    website_domain = re.sub(r"^https?://(www\.)?", "", url).split("/")[0].lower()

    # 1. Načti homepage
    homepage_html = _fetch_html(url)
    if not homepage_html:
        return ""

    all_emails: set = set()
    mailto_emails: set = set()

    emails, mailtos = _extract_emails(homepage_html, website_domain)
    all_emails |= emails
    mailto_emails |= mailtos

    # 2. Najdi a načti kontaktní podstránky (jen pokud homepage nemá dobrý email)
    homepage_best = _best_email(all_emails, mailto_emails, website_domain)
    if not homepage_best or homepage_best[1] < 30:
        contact_urls = _find_contact_urls(homepage_html, url, website_domain)
        for contact_url in contact_urls:
            html = _fetch_html(contact_url, timeout=6)
            if html:
                e, m = _extract_emails(html, website_domain)
                all_emails |= e
                mailto_emails |= m

    # 3. Vyber nejlepší email ze všech stránek
    best_email, best_score = _best_email(all_emails, mailto_emails, website_domain)
    return best_email if best_score >= 0 else ""


def _best_email(all_emails: set, mailto_emails: set, website_domain: str) -> tuple[str, int]:
    """Vrátí (nejlepší email, jeho skóre) ze sady emailů."""
    best_email = ""
    best_score = -1
    mailto_lower = {e.lower() for e in mailto_emails}
    for email in all_emails:
        is_mailto = email.lower() in mailto_lower
        score = _score_email(email, website_domain, is_mailto, "")
        if score > best_score:
            best_score = score
            best_email = email
    return best_email, best_score


def check_mx(email: str) -> bool:
    """Ověří, že doména emailu má MX záznam (přijímá poštu)."""
    if not email or "@" not in email:
        return False
    domain = email.split("@")[1]
    try:
        import dns.resolver
        dns.resolver.resolve(domain, "MX")
        return True
    except Exception:
        return False


def slugify(name):
    slug = name.lower()
    replacements = {
        "č": "c", "š": "s", "ž": "z", "ě": "e", "ř": "r",
        "ů": "u", "ú": "u", "á": "a", "í": "i", "ý": "y",
        "ó": "o", "ď": "d", "ť": "t", "ň": "n",
    }
    for k, v in replacements.items():
        slug = slug.replace(k, v)
    slug = re.sub(r"[^a-z0-9]", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug
