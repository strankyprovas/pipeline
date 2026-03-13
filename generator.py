"""
Generátor demo stránek – používá master šablonu z template/index.html
"""
import os
import random
from urllib.parse import quote_plus
from industries import get_industry

# Skloňování měst do lokálu (pro "v [město]" ve větě)
CITY_LOCATIVE = {
    "Praha":              "Praze",
    "Brno":               "Brně",
    "Ostrava":            "Ostravě",
    "Plzeň":              "Plzni",
    "Liberec":            "Liberci",
    "Olomouc":            "Olomouci",
    "České Budějovice":   "Českých Budějovicích",
    "Hradec Králové":     "Hradci Králové",
    "Pardubice":          "Pardubicích",
    "Zlín":               "Zlíně",
    "Kladno":             "Kladně",
    "Most":               "Mostě",
}

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "template")
TEMPLATE_PATH = os.path.join(TEMPLATE_DIR, "index.html")

# Mapování odvětví → HTML šablona
INDUSTRY_TEMPLATES = {
    "restaurace":   "index.html",
    "kavarna":      "kavarna.html",
    "penzion":      "penzion.html",
    "kadernictvi":  "kadernictvi.html",
    "zubni":        "zubni.html",
    "kosmetika":    "kosmetika.html",
    "autoservis":   "autoservis.html",
    "masaze":       "masaze.html",
    "psycholog":    "psycholog.html",
}

def get_template_path(industry: str) -> str:
    filename = INDUSTRY_TEMPLATES.get(industry, "index.html")
    path = os.path.join(TEMPLATE_DIR, filename)
    # Fallback na restauraci pokud šablona ještě neexistuje
    if not os.path.exists(path):
        path = TEMPLATE_PATH
    return path

TAGLINES = [
    "Kde každé jídlo vypráví příběh",
    "Chutě, které nezapomenete",
    "Poctivá kuchyně, přátelská atmosféra",
    "Tradiční kuchyně s moderním šmrncem",
    "Vítejte u nás – jako doma",
    "Kde se snoubí chuť a atmosféra",
    "Gastronomie s duší",
    "Vaše oblíbené místo u stolu",
]

SUBTITLES = [
    "Přijďte ochutnat autentické chutě připravené s láskou a čerstvými surovinami.",
    "Čerstvé suroviny od lokálních farmářů, recepty plné vášně a péče.",
    "Každý pokrm je výsledkem let zkušeností a lásky ke gastronomii.",
    "Nabízíme víc než jen jídlo – nabízíme zážitek, na který se nezapomíná.",
]

ABOUT_TEXTS = [
    "Jsme rodinný podnik s vášní pro dobré jídlo a pohostinnost. Každý den připravujeme čerstvá jídla z lokálních surovin a věříme, že dobrý oběd nebo večeře je víc než jen jídlo – je to zážitek, který spojuje lidi.",
    "Naše restaurace vznikla z lásky k poctivé kuchyni. Používáme suroviny od lokálních farmářů a každý recept je výsledkem let zkušeností. Přijďte ochutnat, co to opravdu znamená dobré jídlo.",
    "V naší kuchyni se snoubí tradice s moderním přístupem. Každý pokrm připravujeme s maximální péčí a důrazem na kvalitu surovin. Těšíme se na vás u nás!",
    "Věříme, že nejlepší restaurace je ta, do které se hosté rádi vracejí. Proto se soustředíme na čerstvost, chuť a přátelskou atmosféru, která vás provází od vstupu až po odchod.",
]

ABOUT_SHORT = [
    "Poctivá kuchyně s důrazem na čerstvé suroviny a přátelskou atmosféru.",
    "Rodinná restaurace s láskou k dobrému jídlu.",
    "Moderní kuchyně s tradicí a duší.",
]


def generate_demo(restaurant_data, template_path=None):
    """
    Načte šablonu dle odvětví a dosadí data podniku.
    Vrátí hotový HTML string.
    """
    if template_path is None:
        industry = restaurant_data.get("industry", "restaurace")
        template_path = get_template_path(industry)
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    name        = restaurant_data.get("name", "Restaurace")
    address     = restaurant_data.get("address", "")
    phone       = restaurant_data.get("phone", "")
    email       = restaurant_data.get("email", "")
    rating      = restaurant_data.get("rating", 4.5)
    reviews     = restaurant_data.get("reviews_count", 0)
    local_photos = restaurant_data.get("local_photos", [])
    city        = restaurant_data.get("city_real", restaurant_data.get("city", "Praha"))
    city_loc    = CITY_LOCATIVE.get(city, city)  # lokál pro "v [město]"

    # Zkrácená adresa (bez PSČ a státu)
    address_short = address.split(",")[0] if address else ""

    # Zkrácený název pro navbar (max 3 slova)
    name_words = name.split()
    short_name = " ".join(name_words[:3]) if len(name_words) > 3 else name

    # Foto soubory (relativní cesty od index.html)
    photo_files = [os.path.basename(p) for p in local_photos]
    photo1 = photo_files[0] if len(photo_files) > 0 else "photo_1.jpg"
    photo2 = photo_files[1] if len(photo_files) > 1 else photo1
    photo3 = photo_files[2] if len(photo_files) > 2 else photo1
    photo4 = photo_files[3] if len(photo_files) > 3 else photo2
    photo5 = photo_files[4] if len(photo_files) > 4 else photo3

    # JS pole fotek pro marquee galerii (sdílená složka stock_photos v root repa)
    gallery_js = ",".join([f"'../stock_photos/{p}'" for p in photo_files]) if photo_files else "''"

    # Generativní texty – dle odvětví nebo fallback na restaurační texty
    industry_key = restaurant_data.get("industry", "restaurace")
    ind = get_industry(industry_key)
    tagline      = random.choice(ind.get("taglines", TAGLINES))
    subtitle     = random.choice(ind.get("subtitles", SUBTITLES))
    about        = random.choice(ind.get("about_texts", ABOUT_TEXTS))
    about_short  = random.choice(ind.get("about_short", ABOUT_SHORT))

    # Google Maps embed – zdarma, bez API klíče
    lat = restaurant_data.get("lat", 0.0)
    lon = restaurant_data.get("lon", 0.0)
    if lat and lon:
        maps_embed = f"https://maps.google.com/maps?q={lat},{lon}&output=embed"
    else:
        maps_embed = f"https://maps.google.com/maps?q={quote_plus(address)}&output=embed"

    # POZOR: delší/konkrétnější klíče musí být před kratšími (ABOUT_SHORT před ABOUT atd.)
    replacements = [
        ("RESTAURANT_SHORT_NAME",    short_name),
        ("RESTAURANT_ADDRESS_SHORT", address_short),
        ("RESTAURANT_ADDRESS",       address),
        ("RESTAURANT_ABOUT_SHORT",   about_short),
        ("RESTAURANT_ABOUT",         about),
        ("RESTAURANT_CITY_LOC",      city_loc),
        ("RESTAURANT_CITY",          city),
        ("RESTAURANT_NAME",          name),
        ("RESTAURANT_TAGLINE",       tagline),
        ("RESTAURANT_SUBTITLE",      subtitle),
        ("RESTAURANT_PHONE",         phone or "+420 000 000 000"),
        ("RESTAURANT_EMAIL",         email or "info@restaurace.cz"),
        ("RESTAURANT_RATING",        str(rating)),
        ("RESTAURANT_REVIEWS",       str(int(reviews))),
        ("PHOTO_1",                  photo1),
        ("PHOTO_2",                  photo2),
        ("PHOTO_3",                  photo3),
        ("PHOTO_4",                  photo4),
        ("PHOTO_5",                  photo5),
        ("GALLERY_PHOTOS_JS",        gallery_js),
        ("GOOGLE_MAPS_EMBED",        maps_embed),
        ("SPECIAL_IMAGE",            f"../stock_photos/{photo_files[2]}" if len(photo_files) > 2 else f"../stock_photos/{photo1}"),
    ]

    for placeholder, value in replacements:
        html = html.replace(placeholder, value)

    return html


def save_demo(restaurant_data, demos_dir):
    """Vygeneruje demo stránku a uloží ji do demos_dir/[slug]/index.html"""
    slug = restaurant_data.get("slug", "restaurace")
    demo_dir = os.path.join(demos_dir, slug)
    os.makedirs(demo_dir, exist_ok=True)

    html = generate_demo(restaurant_data)
    index_path = os.path.join(demo_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)

    return index_path
