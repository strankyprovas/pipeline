import argparse
import csv
import os
import random
import subprocess
import sys
from scraper import (
    search_restaurants,
    search_businesses,
    copy_stock_photos,
    check_website,
    slugify,
    scrape_email_from_website,
    scrape_email_from_facebook,
    find_facebook_via_google,
    _is_facebook_url,
    check_mx,
    extract_city,
)
from industries import get_industry, list_industries
from generator import save_demo
from website_analyzer import assess_website
from ai_email import generate_ai_email
from gmail_draft import create_draft

# Google Sheets - načti jen pokud credentials existují
SHEETS_ENABLED = os.path.exists(os.path.join(os.path.dirname(__file__), "credentials.json"))
if SHEETS_ENABLED:
    from sheets import get_or_create_sheet, add_restaurant, is_duplicate

from config import NEVER_CONTACT_NAMES

BASE_DIR = os.path.dirname(__file__)

# Každé odvětví má vlastní demos adresář (= vlastní GitHub repo / GitHub Pages)
INDUSTRY_DEMOS_DIR = {
    "restaurace":  os.path.join(BASE_DIR, "demos"),
    "kavarna":     os.path.join(BASE_DIR, "demos-kavarny"),
    "penzion":     os.path.join(BASE_DIR, "demos-penziony"),
    "kadernictvi": os.path.join(BASE_DIR, "demos-kadernictvi"),
    "kosmetika":   os.path.join(BASE_DIR, "demos-kosmetika"),
    "autoservis":  os.path.join(BASE_DIR, "demos-autoservis"),
    "masaze":      os.path.join(BASE_DIR, "demos-masaze"),
    "zubni":       os.path.join(BASE_DIR, "demos-zubni"),
    "psycholog":   os.path.join(BASE_DIR, "demos-psycholog"),
}

INDUSTRY_PAGES_URL = {
    "restaurace":  "https://strankyprovas.github.io/restaurace",
    "kavarna":     "https://strankyprovas.github.io/kavarny",
    "penzion":     "https://strankyprovas.github.io/penzion",
    "kadernictvi": "https://strankyprovas.github.io/kadernictvi",
    "kosmetika":   "https://strankyprovas.github.io/kosmetika",
    "autoservis":  "https://strankyprovas.github.io/autoservis",
    "masaze":      "https://strankyprovas.github.io/masaze",
    "zubni":       "https://strankyprovas.github.io/zubni",
    "psycholog":   "https://strankyprovas.github.io/psycholog",
}

DEMOS_DIR = os.path.join(BASE_DIR, "demos")   # default (restaurace)
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
CSV_PATH = os.path.join(OUTPUT_DIR, "restaurants.csv")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Kolik restaurací načteme najednou (max 60 = 3 stránky Places API)
BATCH_SIZE = 60

def process_restaurants(city="Praha", target=5, used_domains: set | None = None, industry="restaurace"):
    """
    Prochází restaurace dokud nevygeneruje `target` hotových demo+draft.
    used_domains: sdílená množina domén emailů napříč voláními (pro multi-city dedup).
    """
    if used_domains is None:
        used_domains = set()

    ind = get_industry(industry)
    ind_name = ind.get("name_cs", industry)

    demos_dir = INDUSTRY_DEMOS_DIR.get(industry, DEMOS_DIR)
    pages_base = INDUSTRY_PAGES_URL.get(industry, "https://strankyprovas.github.io/restaurace")
    os.makedirs(demos_dir, exist_ok=True)

    print(f"\n🎯 Cíl: {target} hotových demo+draft v {city} (odvětví: {ind_name})")
    print(f"🔍 Načítám podniky...\n")

    # Načti velký batch najednou přes Overpass API (zdarma)
    places = search_businesses(
        city=city,
        num_results=BATCH_SIZE,
        osm_filter=ind.get("osm_filter", '["amenity"="restaurant"]'),
    )
    print(f"  Nalezeno {len(places)} podniků k prověření\n")

    # Připoj Google Sheet
    sheet = None
    sheet_emails: set = set()   # in-memory cache – čteme sheet jen jednou
    sheet_names: set = set()
    if SHEETS_ENABLED:
        print("📊 Připojuji Google Sheet...")
        sheet = get_or_create_sheet()
        # Načti existující záznamy do paměti (1 read namísto read-per-business)
        try:
            from sheets import _retry
            all_values = _retry(sheet.get_all_values)
            # Řádek 0 = hlavička, řádky 1+ = data; Název=sl.0, Email=sl.3
            for row_vals in all_values[1:]:
                if len(row_vals) > 3 and row_vals[3]:
                    sheet_emails.add(row_vals[3].lower())
                if len(row_vals) > 0 and row_vals[0]:
                    sheet_names.add(row_vals[0].lower())
            print(f"  Cache: {len(sheet_emails)} emailů, {len(sheet_names)} názvů\n")
        except Exception as e:
            print(f"  ⚠️  Cache selhala ({e}), pokračuji bez cache\n")

    results = []
    demos_done = 0
    checked = 0

    for place in places:
        if demos_done >= target:
            break

        checked += 1
        place_id = place.get("place_id")
        name = place.get("name", "Neznámá restaurace")
        print(f"[{checked}/{len(places)}] {name}  (dema: {demos_done}/{target})")

        # Vyloučené podniky (již mají web od StránkyProVás)
        name_lower = name.lower()
        if any(excl in name_lower for excl in NEVER_CONTACT_NAMES):
            print(f"  🚫 Vyloučeno (náš klient) – přeskakuji\n")
            continue

        # OSM data – vše je už v place dict (žádný druhý API call)
        website       = place.get("website", "")
        address       = place.get("address", "")
        phone         = place.get("phone", "")
        city_real     = place.get("city_real", city)
        lat           = place.get("lat", 0.0)
        lon           = place.get("lon", 0.0)
        # Generické hodnocení – demo stránka, nikdo to neověřuje
        rating        = round(random.uniform(4.6, 4.9), 1)
        reviews_count = random.randint(80, 220)
        price_level   = 0
        opening_hours = []

        # 1. Hledej email – různé zdroje podle toho co máme
        email = ""
        fb_page_url = place.get("facebook", "")  # Facebook přímo z OSM tagů

        # Email přímo z OSM tagů (nejrychlejší)
        osm_email = place.get("contact_email", "")
        if osm_email:
            print(f"  📧 Email z OSM: {osm_email}")
            email = osm_email

        if not email:
            if website and _is_facebook_url(website):
                # Web v OSM je Facebook stránka
                print(f"  📘 Facebook web: {website}")
                fb_page_url = fb_page_url or website
                email = scrape_email_from_facebook(website)
                if email:
                    print(f"  📧 Email z Facebooku: {email}")
            elif website:
                # Normální web – homepage + kontaktní podstránky
                email = scrape_email_from_website(website)
                if email:
                    print(f"  📧 Email z webu: {email}")

        # Fallback: zkus email z FB stránky (OSM tag)
        if not email and fb_page_url:
            email = scrape_email_from_facebook(fb_page_url)
            if email:
                print(f"  📧 Email z Facebooku (OSM): {email}")

        # Poslední záchrana: DuckDuckGo hledání Facebooku
        if not email and not fb_page_url:
            fb_page_url = find_facebook_via_google(name, city)
            if fb_page_url:
                print(f"  📘 Facebook nalezen přes DuckDuckGo: {fb_page_url}")
                email = scrape_email_from_facebook(fb_page_url)
                if email:
                    print(f"  📧 Email z Facebooku: {email}")

        if not email:
            # Facebook nalezen ale bez emailu – ulož do Sheetu pro manuální oslovení
            if fb_page_url:
                print(f"  📘 Email nenalezen, mám Facebook – ukládám do Sheetu pro ruční kontakt")
                slug = slugify(name)
                demo_photos_dir = os.path.join(demos_dir, slug, "photos")
                print(f"  📸 Kopíruji stock fotky...")
                local_photos = copy_stock_photos(industry, demo_photos_dir, max_photos=5)
                fb_row = {
                    "name": name, "address": address, "phone": phone,
                    "email": "", "website": fb_page_url, "rating": rating,
                    "reviews_count": reviews_count, "pagespeed": 0,
                    "category": "bez_webu", "reasons": [], "slug": slug,
                    "city": city, "city_real": city_real, "demo_path": "",
                    "local_photos": local_photos,
                    "fb_page_url": fb_page_url,
                    "status_override": "manual",
                    "note": "Bez emailu – kontaktovat přes Facebook",
                    "industry": industry,
                }
                print(f"  🎨 Generuji demo stránku...")
                demo_path = save_demo(fb_row, demos_dir)
                demo_url = f"{pages_base}/{slug}/"
                print(f"  ✅ Demo: {demo_path}")
                if sheet:
                    add_restaurant(sheet, {**fb_row, "demo_url": demo_url})
                    print(f"  📊 Uloženo do Sheetu (stav: manual – kontaktuj přes FB)\n")
            else:
                print(f"  📧 Email ani Facebook nenalezeny – přeskakuji\n")
            continue

        # 1b. MX kontrola – doména musí přijímat poštu
        if not check_mx(email):
            print(f"  ❌ Doména {email.split('@')[1]} nemá MX záznam – přeskakuji\n")
            continue

        # 1c. Deduplikace domény (v rámci celého běhu)
        email_domain = email.split("@")[1].lower()
        if email_domain in used_domains:
            print(f"  ⏭️  Doména {email_domain} již použita v tomto běhu – přeskakuji\n")
            continue
        used_domains.add(email_domain)

        # 2. Duplikát v DB? (kontrola z in-memory cache – žádné Sheets čtení)
        if email.lower() in sheet_emails or name.lower() in sheet_names:
            print(f"  ⏭️  Již v databázi – přeskakuji\n")
            continue

        # 3. Analyzuj web
        quality_score = 0
        reasons = []
        if website:
            print(f"  🌐 Web: {website}")
            alive = check_website(website)
            if alive:
                quality_score, category, reasons = assess_website(website)
                for r in reasons:
                    print(f"    {r}")
            else:
                print(f"  ❌ Web nereaguje")
                website = ""
                category = "bez_webu"
        else:
            print(f"  🚫 Bez webu")
            category = "bez_webu"

        slug = slugify(name)

        row = {
            "name": name,
            "address": address,
            "phone": phone,
            "email": email,
            "website": website,
            "rating": rating,
            "reviews_count": reviews_count,
            "pagespeed": quality_score,
            "category": category,
            "reasons": reasons,
            "slug": slug,
            "city": city,
            "city_real": city_real,
            "lat": lat,
            "lon": lon,
            "price_level": price_level,
            "opening_hours": opening_hours,
            "demo_path": "",
            "industry": industry,
        }

        # 4. Pokud špatný/bez webu → generuj demo + draft
        if category in ("bez_webu", "spatny_web"):
            print(f"  📸 Kopíruji stock fotky...")
            demo_photos_dir = os.path.join(demos_dir, slug, "photos")
            local_photos = copy_stock_photos(industry, demo_photos_dir, max_photos=5)

            print(f"  🎨 Generuji demo stránku...")
            row["local_photos"] = local_photos
            demo_path = save_demo(row, demos_dir)
            row["demo_path"] = demo_path
            demo_url = f"{pages_base}/{slug}/"
            print(f"  ✅ Demo: {demo_path}")

            # Gmail draft
            ab_variant = ""
            try:
                email_data = generate_ai_email(row, demo_url=demo_url, city=city_real)
                ab_variant = email_data.get("ab_variant", "")
                create_draft(
                    to_email=email,
                    subject=email_data["subject"],
                    body_plain=email_data["body"],
                    body_html=email_data["html_body"],
                )
                print(f"  📨 Gmail draft vytvořen (varianta: {ab_variant})")
            except Exception as e:
                print(f"  ⚠️  Draft se nepodařilo vytvořit: {e}")

            # Google Sheet
            if sheet:
                add_restaurant(sheet, {**row, "demo_url": demo_url, "ab_variant": ab_variant, "industry": industry})
            # Aktualizuj in-memory cache
            sheet_emails.add(email.lower())
            sheet_names.add(name.lower())

            demos_done += 1
            print(f"  🎯 Hotovo: {demos_done}/{target}\n")

        else:
            print(f"  ✓ Web je OK – přeskakuji\n")

        results.append(row)

    # Souhrn
    print(f"\n{'='*50}")
    if demos_done >= target:
        print(f"✅ Hotovo! Vygenerováno {demos_done} demo+draft.")
    else:
        print(f"⚠️  Dosaženo konce výsledků. Hotovo {demos_done}/{target} demo+draft.")
        print(f"   (Zkus jiné město nebo větší oblast.)")

    print(f"\n📊 Prověřeno celkem: {checked} restaurací")
    print(f"🎨 Demos+drafty:     {demos_done}")
    print(f"📁 Demo stránky:     {DEMOS_DIR}")

    # Ulož CSV
    fieldnames = ["name", "address", "phone", "email", "website", "rating",
                  "reviews_count", "pagespeed", "category", "slug", "demo_path"]
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({k: r.get(k, "") for k in fieldnames})

    # Auto push na GitHub Pages
    if demos_done > 0:
        print(f"\n🚀 Nahrávám dema na GitHub Pages...")
        try:
            subprocess.run(["git", "-C", demos_dir, "add", "."], check=True)
            subprocess.run(["git", "-C", demos_dir, "commit",
                            "-m", f"Nová dema: {city} ({demos_done} {ind_name})"], check=True)
            subprocess.run(["git", "-C", demos_dir, "push"], check=True)
            print(f"  ✅ GitHub Pages aktualizován")
        except subprocess.CalledProcessError as e:
            print(f"  ⚠️  GitHub push selhal: {e}")

    return results


if __name__ == "__main__":
    _industries_list = ", ".join(list_industries())
    parser = argparse.ArgumentParser(description="Business outreach pipeline")
    parser.add_argument("city", nargs="?", default="Praha",
                        help="Město (default: Praha)")
    parser.add_argument("target", nargs="?", type=int, default=5,
                        help="Počet hotových demo+draft (default: 5)")
    parser.add_argument("--cities", type=str, default="",
                        help="Čárkou oddělený seznam měst, např. Praha,Brno,Ostrava")
    parser.add_argument("--target", dest="target_flag", type=int, default=None,
                        help="Počet hotových demo+draft na město (override positional)")
    parser.add_argument("--industry", type=str, default="restaurace",
                        help=f"Odvětví (default: restaurace). Možnosti: {_industries_list}")
    args = parser.parse_args()

    target = args.target_flag if args.target_flag is not None else args.target
    industry = args.industry
    used_domains: set = set()

    if args.cities:
        cities = [c.strip() for c in args.cities.split(",") if c.strip()]
        for c in cities:
            process_restaurants(city=c, target=target, used_domains=used_domains, industry=industry)
    else:
        process_restaurants(city=args.city, target=target, used_domains=used_domains, industry=industry)
