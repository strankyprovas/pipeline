"""
AI personalizovaný cold email generátor.
Používá Claude Haiku k vytvoření unikátního emailu pro každou restauraci
na základě konkrétních technických problémů webu.
Fallback na email_template.generate_email() pokud API selže.
"""
import os
import random
import anthropic
from email_template import generate_email, SENDER_NAME, SENDER_COMPANY, SENDER_WEBSITE
from config import PIXEL_BASE_URL
from industries import get_industry

# A/B varianty předmětů – testujeme různé přístupy
# A = zvědavost, B = hodnota, C = problém
SUBJECT_VARIANTS = {
    "bez_webu": {
        "A": lambda name, domain: f"Udělal jsem něco pro {name}",
        "B": lambda name, domain: f"Připravil jsem web pro {name} – podívejte se",
        "C": lambda name, domain: f"Proč {name} přichází o hosty?",
    },
    "spatny_web": {
        "A": lambda name, domain: f"Udělal jsem něco pro váš web",
        "B": lambda name, domain: f"Modernizace {domain} – ukázka zdarma",
        "C": lambda name, domain: f"Váš web ztrácí hosty na mobilech",
    },
}


def pick_subject_variant(category: str, name: str, domain: str) -> tuple[str, str]:
    """Vrátí (subject, varianta) – náhodně vybere A/B/C."""
    variants = SUBJECT_VARIANTS.get(category, SUBJECT_VARIANTS["spatny_web"])
    variant_key = random.choice(list(variants.keys()))
    subject = variants[variant_key](name, domain)
    return subject, variant_key


def _tracking_pixel_html(slug: str) -> str:
    """Vrátí HTML tracking pixelu (funguje pro Outlook/Apple Mail, ne pro Gmail)."""
    if not PIXEL_BASE_URL or not slug:
        return ""
    return f'<img src="{PIXEL_BASE_URL}?slug={slug}" width="1" height="1" style="border:0;overflow:hidden" alt="">'


def _click_tracking_url(slug: str, demo_url: str) -> str:
    """Wraps demo_url přes Apps Script redirect – spolehlivě loguje kliknutí i v Gmailu."""
    if not PIXEL_BASE_URL or not slug or not demo_url:
        return demo_url
    from urllib.parse import urlencode
    return f"{PIXEL_BASE_URL}?{urlencode({'slug': slug, 'redirect': demo_url})}"

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Problémy webu → čitelný popis pro prompt
def _format_reasons(reasons: list[str]) -> str:
    """Přeloží seznam technických reasons do čitelné češtiny pro prompt."""
    cleaned = []
    for r in reasons:
        # Odstraň emoji ikony ze začátku
        r = r.lstrip("❌✓~👁️ ").strip()
        if r:
            cleaned.append(r)
    if not cleaned:
        return "web má technické problémy"
    return ", ".join(cleaned[:3])  # max 3 problémy, aby prompt nebyl moc dlouhý


def generate_ai_email(restaurant: dict, demo_url: str = "", city: str = "Praha") -> dict:
    """
    Vygeneruje personalizovaný cold email pomocí Claude Haiku.
    Při selhání API vrátí fallback z email_template.generate_email().
    """
    if not ANTHROPIC_API_KEY:
        return generate_email(restaurant, demo_url=demo_url, city=city)

    name = restaurant.get("name", "")
    website = restaurant.get("website", "")
    category = restaurant.get("category", "bez_webu")
    rating = restaurant.get("rating", 0)
    reviews_count = restaurant.get("reviews_count", 0)
    reasons = restaurant.get("reasons", [])
    price_level = restaurant.get("price_level", 0)
    opening_hours = restaurant.get("opening_hours", [])
    industry_key = restaurant.get("industry", "restaurace")
    ind = get_industry(industry_key)
    ind_name = ind.get("name_cs", "restaurace")  # "kavárny", "penziony"...

    domain = website.replace("https://", "").replace("http://", "").rstrip("/") if website else ""
    problems_text = _format_reasons(reasons)

    # A/B výběr předmětu
    subject, ab_variant = pick_subject_variant(category, name, domain)

    # Doplňkový kontext z Google Maps
    extra_context_parts = []
    if reviews_count >= 100:
        extra_context_parts.append(f"aktivní zákaznická základna ({reviews_count} recenzí)")
    if price_level:
        price_map = {1: "nízká (€)", 2: "střední (€€)", 3: "vyšší (€€€)", 4: "prémiová (€€€€)"}
        extra_context_parts.append(f"cenová kategorie: {price_map.get(price_level, '')}")
    if opening_hours:
        # Zjisti jestli mají sobotu/neděli
        weekend = any("Sobota" in h or "Neděle" in h for h in opening_hours
                      if "Zavřeno" not in h)
        if weekend:
            extra_context_parts.append("otevřeno i o víkendech")
    extra_context = ". ".join(extra_context_parts) + "." if extra_context_parts else ""

    # Prompt pro Claude Haiku – odvětvově specifické texty
    if category == "bez_webu":
        problem_hint = ind.get("email_problem_no_web",
                               "žádné webové stránky přitom 70 % zákazníků hledá online")
        web_context = f"Podnik {name} ({ind_name}) v {city} nemá žádný web."
        if extra_context:
            web_context += f" {extra_context}"
    else:
        problem_hint = ind.get("email_problem_bad_web", problems_text) if not problems_text else problems_text
        web_context = (
            f"Web podniku {name} ({ind_name}, {domain}) má problémy: {problems_text}. "
            f"Podnik má {rating}/5 hvězd a {reviews_count} recenzí na Google."
        )
        if extra_context:
            web_context += f" {extra_context}"

    demo_line = f"\nUkázka nového webu: {demo_url}" if demo_url else ""
    extra_line = f"\n- Zajímavé detaily o podniku k zmínění: {extra_context}" if extra_context else ""

    cta_phrase = ind.get("email_cta", "Pracujeme s podniky v regionu.").format(
        city_phrase=f"v {city}"
    )
    prompt = f"""Napiš krátký cold email (max 5 vět) v češtině.

Kontext:
- Jsi Matyáš Vrba z firmy StránkyProVás (webdesign pro místní podniky)
- {web_context}
- Píšeš majiteli/provozovateli poprvé
{demo_line}

Požadavky:
- Email musí být v ich-formě jako Matyáš Vrba
- Zmíň konkrétní problém: {problem_hint}{extra_line}
- Pokud je demo_url, přilož ho jako odkaz s šipkou →
- NIKDY nepiš "s vašimi fotkami" – jsou to ukázkové fotografie připravené pro demo
- CTA: {cta_phrase} Požádej o odpověď jestli by je demo zaujalo.
- Max 5 vět, bez formálního nadpisu "Dobrý den,"
- Začni slovem "Dobrý den," na prvním řádku, pak prázdný řádek, pak tělo
- Podpis NEVKLÁDEJ, bude přidán automaticky
- Emailová adresa odesílatele: matyas.vrbaa@gmail.com

Napiš jen tělo emailu, žádné instrukce ani komentáře."""

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        ai_body = message.content[0].text.strip()

        # Vždy přidej větu o textech a fotkách hned za demo odkazem
        PHOTO_NOTE = "Texty i fotografie z ukázky jsou samozřejmě vaše – klidně je použijete i na finálním webu."
        if demo_url and demo_url in ai_body and PHOTO_NOTE not in ai_body:
            ai_body = ai_body.replace(demo_url, demo_url + "\n" + PHOTO_NOTE)
        elif demo_url and PHOTO_NOTE not in ai_body:
            # Demo odkaz je jinak formátovaný – přidej za poslední řádek s demo_url
            lines = ai_body.split("\n")
            new_lines = []
            for line in lines:
                new_lines.append(line)
                if demo_url in line:
                    new_lines.append(PHOTO_NOTE)
            ai_body = "\n".join(new_lines)

        # Přidej podpis
        signature_plain = f"\nS pozdravem,\n{SENDER_NAME}\n\n--\n{SENDER_NAME}\n{SENDER_COMPANY} | {SENDER_WEBSITE}"
        body = ai_body + signature_plain

        # HTML verze
        slug = restaurant.get("slug", "")
        ai_body_html = ai_body.replace("\n", "<br>")
        if demo_url:
            ai_body_html = ai_body_html.replace(
                demo_url,
                f'<a href="{demo_url}">{demo_url}</a>'
            )
        pixel = _tracking_pixel_html(slug)
        html_body = f"""<div style="font-family: Arial, sans-serif; font-size: 15px; line-height: 1.6; color: #222;">
<p>{ai_body_html}</p>
<p style="color:#888; font-size:13px;">--<br>{SENDER_NAME}<br>{SENDER_COMPANY} | <a href="{SENDER_WEBSITE}">{SENDER_WEBSITE}</a></p>
{pixel}
</div>"""

        return {
            "subject": subject,
            "body": body,
            "html_body": html_body,
            "to_name": name,
            "ab_variant": ab_variant,
        }

    except Exception as e:
        print(f"  ⚠️  AI email selhal ({e}), používám fallback šablonu")
        fallback = generate_email(restaurant, demo_url=demo_url, city=city)
        fallback["ab_variant"] = "fallback"
        return fallback


if __name__ == "__main__":
    test = {
        "name": "Restaurace U Tellerů",
        "website": "https://utelleru.cz",
        "category": "spatny_web",
        "rating": 4.2,
        "reviews_count": 187,
        "reasons": [
            "❌ Chybí viewport meta – nefunguje na mobilu",
            "❌ Bootstrap 3.x – zastaralý",
            "❌ Tabulkový layout (5 tabulek) – velmi starý web",
        ],
    }
    result = generate_ai_email(
        test,
        demo_url="https://strankyprovas.github.io/restaurace/restaurace-u-telleru/",
        city="Praha"
    )
    print("PŘEDMĚT:", result["subject"])
    print()
    print(result["body"])
