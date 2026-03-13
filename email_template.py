"""
PPC Cold Email Formula
P – Pain Point (specifický problém webu)
P – Partial Solution (ukázka webu + co umíme)
C – CTA (demo link + nabídka referencí)
"""
import random
try:
    from config import PIXEL_BASE_URL
except ImportError:
    PIXEL_BASE_URL = ""
from industries import get_industry


def _tracking_pixel_html(slug: str) -> str:
    if not PIXEL_BASE_URL or not slug:
        return ""
    return f'<img src="{PIXEL_BASE_URL}?slug={slug}" width="1" height="1" style="border:0;overflow:hidden" alt="">'


def _click_tracking_url(slug: str, demo_url: str) -> str:
    """Wraps demo_url přes Apps Script redirect – loguje kliknutí spolehlivě i v Gmailu."""
    if not PIXEL_BASE_URL or not slug or not demo_url:
        return demo_url
    from urllib.parse import urlencode
    return f"{PIXEL_BASE_URL}?{urlencode({'slug': slug, 'redirect': demo_url})}"

SENDER_NAME = "Matyáš Vrba"
SENDER_COMPANY = "StránkyProVás"
SENDER_WEBSITE = "https://strankyprovas.cz"
SENDER_EMAIL = "matyas.vrbaa@gmail.com"


# Skloňování měst pro "po celé/celém [město]"
CITY_LOCATIVE = {
    "Praha":              ("po celé", "Praze"),
    "Brno":               ("po celém", "Brně"),
    "Ostrava":            ("po celé", "Ostravě"),
    "Plzeň":              ("po celé", "Plzni"),
    "Liberec":            ("po celém", "Liberci"),
    "Olomouc":            ("po celém", "Olomouci"),
    "České Budějovice":   ("po celých", "Českých Budějovicích"),
    "Hradec Králové":     ("po celém", "Hradci Králové"),
    "Pardubice":          ("po celých", "Pardubicích"),
    "Zlín":               ("po celém", "Zlíně"),
    "Kladno":             ("po celém", "Kladně"),
    "Most":               ("po celém", "Mostě"),
}

def city_phrase(city):
    """Vrátí správně skloňovanou frázi, např. 'po celém Brně'"""
    if city in CITY_LOCATIVE:
        prep, loc = CITY_LOCATIVE[city]
        return f"{prep} {loc}"
    return f"v {city}"


def get_subject(name, category):
    if category == "bez_webu":
        return f"Udělal jsem něco pro {name}"
    else:
        return f"Udělal jsem něco pro váš web"


def generate_email(restaurant, demo_url="", city="Praha"):
    name = restaurant.get("name", "")
    website = restaurant.get("website", "")
    category = restaurant.get("category", "bez_webu")
    pagespeed = int(restaurant.get("pagespeed", 0))
    industry_key = restaurant.get("industry", "restaurace")
    ind = get_industry(industry_key)
    domain = website.replace("https://", "").replace("http://", "").rstrip("/") if website else ""

    subject = get_subject(name, category)

    # Texty specifické pro odvětví
    problem_no_web = ind.get("email_problem_no_web",
        "nemáte vlastní webové stránky – přitom 70 % lidí hledá online ještě před příchodem")
    problem_bad_web = ind.get("email_problem_bad_web",
        "web by mohl lépe fungovat na mobilech – přitom 70 % lidí hledá z telefonu")

    # Řádek 1 – konkrétní pozorování
    if category == "bez_webu":
        line1 = (
            f"Dobrý den,\n\n"
            f"narazil jsem na {name} a všiml si, že {problem_no_web}."
        )
    elif pagespeed < 30:
        line1 = (
            f"Dobrý den,\n\n"
            f"narazil jsem na {domain} a všiml si, že web se na mobilech načítá velmi pomalu "
            f"– {problem_bad_web.split('–')[-1].strip() if '–' in problem_bad_web else problem_bad_web}."
        )
    else:
        line1 = (
            f"Dobrý den,\n\n"
            f"narazil jsem na {domain} a všiml si, že {problem_bad_web}."
        )

    # Řádek 2 – ukázka (partial solution)
    if demo_url:
        line2 = (
            f"Tak jsem rovnou připravil ukázku, jak by nový web mohl vypadat:\n"
            f"→ {demo_url}\n"
            f"Texty i fotografie z ukázky jsou samozřejmě vaše – klidně je použijete i na finálním webu."
        )
    else:
        line2 = (
            f"Připravili jsme pro vás bezplatnou ukázku toho, jak by nový web mohl vypadat "
            f"– moderní, rychlý a přizpůsobený pro mobily."
        )

    # Řádek 3 – CTA (odvětvově specifické)
    cta_template = ind.get("email_cta", "Pracujeme s podniky {city_phrase}.")
    cta_city = cta_template.format(city_phrase=city_phrase(city))
    line3 = (
        f"{cta_city} Pokud by Vás web zaujal, "
        f"budu moc rád za odpověď abychom mohli navrhnout další řešení. Děkuji."
    )

    # Personalizovaný pozdrav
    closing = random.choice([
        "Přeji Vám hezký zbytek dne,",
        "Přeji příjemný den,",
        "S přáním hezkého dne,",
        "Hezký den Vám přeje,",
    ])

    signature = f"{SENDER_NAME}\n{SENDER_COMPANY} | {SENDER_WEBSITE}"
    body = f"{line1}\n\n{line2}\n\n{line3}\n\n{closing}\n{SENDER_NAME}\n\n--\n{signature}"

    slug = restaurant.get("slug", "")

    # HTML verze s klikatelným odkazem (přímý link – funguje i na mobilu)
    if demo_url:
        line2_html = (
            f"Tak jsem rovnou připravil ukázku, jak by nový web mohl vypadat:<br>"
            f'→ <a href="{demo_url}">{demo_url}</a><br>'
            f"Texty i fotografie z ukázky jsou samozřejmě vaše – klidně je použijete i na finálním webu."
        )
    else:
        line2_html = line2.replace("\n", "<br>")

    pixel = _tracking_pixel_html(slug)
    html_body = f"""<div style="font-family: Arial, sans-serif; font-size: 15px; line-height: 1.6; color: #222;">
<p>{line1.replace(chr(10), '<br>')}</p>
<p>{line2_html}</p>
<p>{line3}</p>
<p>{closing}<br>{SENDER_NAME}</p>
<p style="color:#888; font-size:13px;">--<br>{SENDER_NAME}<br>{SENDER_COMPANY} | <a href="{SENDER_WEBSITE}">{SENDER_WEBSITE}</a></p>
{pixel}
</div>"""

    return {"subject": subject, "body": body, "html_body": html_body, "to_name": name}


if __name__ == "__main__":
    test = {
        "name": "Restaurace U Tellerů",
        "website": "https://utelleru.cz",
        "category": "spatny_web",
        "pagespeed": 28,
    }
    result = generate_email(test, demo_url="https://strankyprovas.github.io/restaurace/restaurace-u-telleru/")
    print("PŘEDMĚT:", result["subject"])
    print()
    print(result["body"])
