"""
AI personalizovaný cold email generátor.
Používá Claude Haiku k vytvoření unikátního emailu pro každou restauraci
na základě konkrétních technických problémů webu.
Fallback na email_template.generate_email() pokud API selže.
"""
import os
import random
import hashlib
import anthropic
from email_template import generate_email, industry_subpage, SENDER_NAME, SENDER_COMPANY, SENDER_WEBSITE
from config import PIXEL_BASE_URL
from industries import get_industry

# A/B varianty předmětů – testujeme různé přístupy
# A = zvědavost, B = hodnota, C = problém
SUBJECT_VARIANTS = {
    "bez_webu": {
        "A": lambda name, domain: f"{name} – připravil jsem vám ukázku webu",
        "B": lambda name, domain: "Váš nový web je hotový – podívejte se",
        "C": lambda name, domain: "Zákazníci vás hledají na Googlu a nenajdou vás",
    },
    "spatny_web": {
        "A": lambda name, domain: f"{name} – připravil jsem vám ukázku nového webu",
        "B": lambda name, domain: "Váš nový web je hotový – podívejte se",
        "C": lambda name, domain: "Zákazníci vás hledají na Googlu – co najdou?",
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

    # A/B výběr předmětu.
    # U masáží běží od 14. 9. 2026 A/B test ŠABLON (klasik/retro/ultra,
    # viz generator.py) a do sloupce „AB Varianta" se zapisuje šablona.
    # Předmět proto fixujeme na vítěze testu předmětů (A: 4,1 % ▲,
    # report 1. 9.) — kdyby se losovaly obě dimenze naráz, 3×3 kombinace
    # rozdrobí vzorek a test nikdy nedoběhne k závěru.
    if industry_key == "masaze":
        variants = SUBJECT_VARIANTS.get(category, SUBJECT_VARIANTS["spatny_web"])
        klic = sorted(variants.keys())[0]  # varianta A
        subject, ab_variant = variants[klic](name, domain), klic
    else:
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

    demo_line = f"\n- Demo URL: {demo_url}" if demo_url else ""
    extra_line = f"\n- Zajímavé detaily o podniku k zmínění: {extra_context}" if extra_context else ""

    # Portfolio reference podle odvětví
    INDUSTRY_PORTFOLIO = {
        "restaurace":  "piavarestaurace.cz a padthairestaurace.cz, aktuálně připravujeme web pro grasehaus.cz",
        "kavarna":     "piavarestaurace.cz (kavárna/bistro) a padthairestaurace.cz, aktuálně připravujeme web pro grasehaus.cz",
        "penzion":     "jakubsojka.cz (poradenství) a piavarestaurace.cz, aktuálně připravujeme weby pro penzionyv regionu",
        "kadernictvi": "piavarestaurace.cz a strankyprovas.github.io/kadernictvi (ukázky pro kadeřnictví)",
        "kosmetika":   "piavarestaurace.cz a strankyprovas.github.io/kosmetika (ukázky pro kosmetické salony)",
        "autoservis":  "piavarestaurace.cz a strankyprovas.github.io/autoservis (ukázky pro autoservisy)",
        "masaze":      "piavarestaurace.cz a strankyprovas.github.io/masaze (ukázky pro masážní salony)",
        "zubni":       "jakubsojka.cz (zdravotnictví/poradenství) a strankyprovas.github.io/zubni (ukázky pro zubní ordinace)",
        "psycholog":   "jakubsojka.cz (zdravotnictví/poradenství) a strankyprovas.github.io/psycholog (ukázky pro psychology)",
    }
    portfolio = INDUSTRY_PORTFOLIO.get(industry_key, INDUSTRY_PORTFOLIO["restaurace"])

    # ── A/B FRAMING (50/50, stabilní podle příjemce) ──
    # osobní = "Matyáš + Kryštof" (ich-forma) · agentura = "StránkyProVás, česká
    # webová agentura" (my-forma, bez jmen). Zapisuje se do „AB Varianta".
    _seed = (restaurant.get("email") or domain or name or "").lower()
    osobni = int(hashlib.md5(_seed.encode("utf-8")).hexdigest(), 16) % 2 == 0
    framing = "osobní" if osobni else "agentura"
    signer = SENDER_NAME if osobni else "tým StránkyProVás"
    if osobni:
        odesilatel_line = "Odesílatel: Matyáš Vrba + kamarád Kryštof, firma StránkyProVás (webdesign pro místní podniky)"
        struktura_1 = f'1. Začni: "Dobrý den," → prázdný řádek → odstavec kde se představíš jako Matyáš, zmíníš kamaráda Kryštofa, napíšeš že spolu už několik let děláte moderní weby pro {ind_name} v Česku, a konkrétně zmíníš {name} v {city} + proč jim píšeš ({problem_hint})'
        demo_verb_text = "Pro ukázku jsem rovnou připravil"
        forma_rule = "- Ich-forma jako Matyáš Vrba (mluvíš za sebe a kamaráda Kryštofa)"
    else:
        odesilatel_line = "Odesílatel: StránkyProVás — česká agentura, která už několik let dělá moderní weby pro místní podniky (píše tým, NE konkrétní osoba)"
        struktura_1 = f'1. Začni: "Dobrý den," → prázdný řádek → odstavec kde se představíš jako StránkyProVás, česká agentura, která už několik let dělá moderní weby pro {ind_name} v Česku, a konkrétně zmíníš {name} v {city} + proč jim píšete ({problem_hint}). Piš v množném čísle (my), NEuváděj žádná křestní jména.'
        demo_verb_text = "Pro ukázku jsme rovnou připravili"
        forma_rule = "- My-forma (množné číslo) jménem agentury StránkyProVás; NIKDY neuváděj jména Matyáš ani Kryštof"

    prompt = f"""Napiš krátký cold email v češtině (max 5–8 vět, příjemce čte na mobilu). Drž se této struktury, ale piš stručně:

KONTEXT:
- {odesilatel_line}
- Příjemce: majitel/provozovatel podniku {name} ({ind_name}) v {city}
- {web_context}{demo_line}{extra_line}
- Portfolio: {portfolio}
- Cena: 500 Kč měsíčně – v ceně hosting, správa, úpravy na vyžádání, vše technické

STRUKTURA EMAILU (přesně dodržuj):

{struktura_1}

2. Sekce "Co je teď problém" (nadpis tučně, pak 3–4 odrážky • s konkrétními problémy pro {ind_name})

3. Sekce "Jak to vyřešíme" (nadpis tučně, pak 2–3 odrážky • co konkrétně uděláte)

4. Sekce "Co to přinese" (nadpis tučně, pak 2–3 odrážky • konkrétní přínosy pro jejich byznys)

5. Portfolio + demo odkaz:
"Naše poslední projekty jsou například {portfolio}."
Pokud je demo URL: "{demo_verb_text}, jak by nový web {name} mohl vypadat:\\n→ [demo_url]\\nTexty z ukázky jsou samozřejmě vaše, fotky vyměníme za vaše vlastní."

6. CTA odstavec: Zmíň cenu 500 Kč/měsíc se vším všudy. Nabídni konkrétní termín: "Hodí se vám krátký hovor v úterý nebo ve středu dopoledne? Stačí odpovědět na tento email." Nepiš nic o "zdarma připravit návrh" ani "cenovou nabídku" – ukázku už posíláme a cenu už zmiňujeme. Srdečný tón. 🙂

DŮLEŽITÉ PRAVIDLA:
- Piš KRÁTCE – celý email max 5–8 vět. Příjemce čte na mobilu mezi zákazníky.
{forma_rule}
- Používej správný pád města v češtině (např. "v Ostravě", "v Brně", "v Praze", "v Olomouci" – ne "v Ostrava")
- Název firmy {name} používej přesně jak je, nesklonávej
- NIKDY nepiš "s vašimi fotkami" – jsou to ukázkové fotografie
- Vždy uveď větu o 14denním limitu dema
- Konči konkrétním CTA: nabídni hovor v úterý nebo středu dopoledne
- Podpis NEVKLÁDEJ (bude přidán automaticky)
- Nepiš žádné instrukce ani komentáře
- Napiš jen tělo emailu"""

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        ai_body = message.content[0].text.strip()

        # Vždy přidej větu o textech a fotkách hned za demo odkazem
        PHOTO_NOTE = "Texty z ukázky jsou samozřejmě vaše, fotky vyměníme za vaše vlastní."
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
        sub_url, sub_label = industry_subpage(restaurant.get("industry", "restaurace"))
        signature_plain = f"\nS pozdravem,\n{signer}\n\nCo všechno děláme pro {sub_label}: {sub_url}\n\n--\n{signer}\n{SENDER_COMPANY} | {SENDER_WEBSITE}"
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
<p style="font-size:13px;color:#8a8a8a;">Co všechno děláme pro {sub_label}: <a href="{sub_url}" style="color:#8f6230;">{sub_url.replace("https://", "").rstrip("/")}</a></p>
<p style="color:#888; font-size:13px;">--<br>{signer}<br>{SENDER_COMPANY} | <a href="{SENDER_WEBSITE}">{SENDER_WEBSITE}</a></p>
{pixel}
</div>"""

        return {
            "subject": subject,
            "body": body,
            "html_body": html_body,
            "to_name": name,
            "ab_variant": framing,
            "framing": framing,
        }

    except Exception as e:
        print(f"  ⚠️  AI email selhal ({e}), používám fallback šablonu")
        fallback = generate_email(restaurant, demo_url=demo_url, city=city)
        # ab_variant zůstává = framing z template (kvůli čistému A/B vyhodnocení)
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


# ─────────────────────────────────────────────────────────────────────────────
# AI e-mailový asistent — outreach kampaň (50/50 split s webovými ukázkami)
# Statický schválený text (viz strankyprovas.cz/asistent/). Bez dema.
# ─────────────────────────────────────────────────────────────────────────────
ASSISTANT_SUBJECT = "Odpovědi na e-maily připravené za vás"

def generate_assistant_email(restaurant: dict, city: str = "Praha") -> dict:
    name = restaurant.get("name", "")
    body = (
        "Dobrý den,\n\n"
        "jmenuju se Matyáš a s kamarádem Kryštofem pomáháme menším podnikům v Česku "
        "ušetřit čas, který jim ujídají e-maily.\n\n"
        "Nastavíme vám asistenta, který hlídá vaši schránku a na zákaznické dotazy "
        "připraví odpověď v tónu vašeho podniku — rovnou do vašich Konceptů. Vy ji jen "
        "přečtete a odešlete. Nic se neodešle samo, máte to plně pod kontrolou.\n\n"
        "Postupně ho nasazujeme podnikům, kterým e-maily berou spoustu času — třeba i "
        "oční ordinaci v Brně, která to shrnula takhle:\n\n"
        "„Naprostá spokojenost. Odpovědi se mi připravují rovnou do konceptů — jen "
        "přečtu a odešlu. Ušetří mi to spoustu času a místo hodin nad e-maily se můžu "
        "věnovat práci v ordinaci. Moc doporučuji.“ — Oční ordinace Hrnčířská, Brno\n\n"
        "Rádi vám to nastavíme na měsíc zdarma a nezávazně, ať sami vidíte, jestli vám "
        "to sedne. Víc tady: https://strankyprovas.cz/asistent/\n\n"
        "Kdyby vás to zajímalo, stačí odepsat.\n\n"
        "Hezký den,\n"
        "Matyáš a Kryštof\n"
        "StránkyProVás"
    )
    html_body = (
        '<div style="font-family:Arial,sans-serif;font-size:15px;line-height:1.6;color:#222">'
        '<p>Dobrý den,</p>'
        '<p>jmenuju se Matyáš a s kamarádem Kryštofem pomáháme menším podnikům v Česku ušetřit čas, který jim ujídají e-maily.</p>'
        '<p>Nastavíme vám asistenta, který hlídá vaši schránku a na zákaznické dotazy připraví odpověď <b>v tónu vašeho podniku — rovnou do vašich Konceptů</b>. Vy ji jen přečtete a odešlete. <b>Nic se neodešle samo</b>, máte to plně pod kontrolou.</p>'
        '<p>Postupně ho nasazujeme podnikům, kterým e-maily berou spoustu času — třeba i oční ordinaci v Brně, která to shrnula takhle:</p>'
        '<blockquote style="margin:0;padding:10px 16px;border-left:3px solid #3F6E60;color:#444;font-style:italic">'
        '„Naprostá spokojenost. Odpovědi se mi připravují rovnou do konceptů — jen přečtu a odešlu. Ušetří mi to spoustu času a místo hodin nad e-maily se můžu věnovat práci v ordinaci. Moc doporučuji.“'
        '<br><span style="font-style:normal;color:#666">— Oční ordinace Hrnčířská, Brno</span></blockquote>'
        '<p>Rádi vám to nastavíme na <b>měsíc zdarma a nezávazně</b>, ať sami vidíte, jestli vám to sedne. Víc tady: <a href="https://strankyprovas.cz/asistent/">strankyprovas.cz/asistent/</a></p>'
        '<p>Kdyby vás to zajímalo, stačí odepsat.</p>'
        '<p>Hezký den,<br>Matyáš a Kryštof<br>StránkyProVás</p>'
        '</div>'
    )
    return {"subject": ASSISTANT_SUBJECT, "body": body, "html_body": html_body,
            "to_name": name, "ab_variant": "asistent", "framing": "asistent"}
