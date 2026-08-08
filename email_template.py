"""
Nový long-form cold email template (styl Vegeranda).
Struktura: intro → problémy → řešení → přínosy → demo → CTA (cena se v mailu neuvádí)
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
    if not PIXEL_BASE_URL or not slug or not demo_url:
        return demo_url
    from urllib.parse import urlencode
    return f"{PIXEL_BASE_URL}?{urlencode({'slug': slug, 'redirect': demo_url})}"


SENDER_NAME = "Matyáš Vrba"
SENDER_COMPANY = "StránkyProVás"
SENDER_WEBSITE = "https://strankyprovas.cz"
from config import SENDER_EMAIL  # jediný zdroj pravdy

PORTFOLIO_BY_INDUSTRY = {
    # Jen reálné klientské domény – odkaz na strankyprovas.github.io/... vypadal
    # jako testovací a v cold mailu spíš ubližoval než pomáhal.
    "restaurace":   "piavarestaurace.cz a padthairestaurace.cz, aktuálně připravujeme web pro graselhaus.cz",
    "kavarna":      "piavarestaurace.cz (kavárna/bistro) a padthairestaurace.cz",
    "pekarna":      "dortycvikov.cz (cukrárna) a piavarestaurace.cz",
    "kvetinarstvi": "bylinarstvimedunka.cz a dortycvikov.cz",
    "penzion":      "piavarestaurace.cz a dortycvikov.cz",
    "kadernictvi":  "bylinarstvimedunka.cz a dortycvikov.cz",
    "kosmetika":    "bylinarstvimedunka.cz a petrakovalska.cz",
    "autoservis":   "sekventcar.cz a sojkafinance.cz",
    "masaze":       "petrakovalska.cz a bylinarstvimedunka.cz",
    "zubni":        "petrakovalska.cz a psychologiejurakova.cz",
    "psycholog":    "psychologiejurakova.cz a petrakovalska.cz",
}
# Fallback pro zpětnou kompatibilitu
PORTFOLIO = PORTFOLIO_BY_INDUSTRY["restaurace"]

CITY_LOCATIVE = {
    "Praha":                 "Praze",
    "Brno":                  "Brně",
    "Ostrava":               "Ostravě",
    "Plzeň":                 "Plzni",
    "Liberec":               "Liberci",
    "Olomouc":               "Olomouci",
    "České Budějovice":      "Českých Budějovicích",
    "Hradec Králové":        "Hradci Králové",
    "Pardubice":             "Pardubicích",
    "Zlín":                  "Zlíně",
    "Kladno":                "Kladně",
    "Most":                  "Mostě",
    "Frýdek-Místek":         "Frýdku-Místku",
    "Karviná":               "Karviné",
    "Havířov":               "Havířově",
    "Opava":                 "Opavě",
    "Jihlava":               "Jihlavě",
    "Ústí nad Labem":        "Ústí nad Labem",
    "Teplice":               "Teplicích",
    "Chomutov":              "Chomutově",
    "Děčín":                 "Děčíně",
    "Přerov":                "Přerově",
    "Třebíč":                "Třebíči",
    "Znojmo":                "Znojmě",
    "Prostějov":             "Prostějově",
    "Šumperk":               "Šumperku",
    "Kroměříž":              "Kroměříži",
    "Vsetín":                "Vsetíně",
    "Uherské Hradiště":      "Uherském Hradišti",
    "Hodonín":               "Hodoníně",
    "Vyškov":                "Vyškově",
    "Blansko":               "Blansku",
    "Bruntál":               "Bruntálu",
    "Nový Jičín":            "Novém Jičíně",
    "Kopřivnice":            "Kopřivnici",
    "Třinec":                "Třinci",
    "Orlová":                "Orlové",
    "Bohumín":               "Bohumíně",
    "Krnov":                 "Krnově",
    "Náchod":                "Náchodě",
    "Trutnov":               "Trutnově",
    "Jičín":                 "Jičíně",
    "Chrudim":               "Chrudimi",
    "Svitavy":               "Svitavách",
    "Litomyšl":              "Litomyšli",
    "Kolín":                 "Kolíně",
    "Kutná Hora":            "Kutné Hoře",
    "Mladá Boleslav":        "Mladé Boleslavi",
    "Příbram":               "Příbrami",
    "Mělník":                "Mělníku",
    "Beroun":                "Berouně",
    "Benešov":               "Benešově",
    "Rakovník":              "Rakovníku",
    "Písek":                 "Písku",
    "Tábor":                 "Táboře",
    "Strakonice":            "Strakonicích",
    "Prachatice":            "Prachaticích",
    "Klatovy":               "Klatovech",
    "Domažlice":             "Domažlicích",
    "Rokycany":              "Rokycanech",
    "Sokolov":               "Sokolově",
    "Cheb":                  "Chebu",
    "Mariánské Lázně":       "Mariánských Lázních",
    "Karlovy Vary":          "Karlových Varech",
    "Litoměřice":            "Litoměřicích",
    "Louny":                 "Lounech",
    "Česká Lípa":            "České Lípě",
    "Jablonec nad Nisou":    "Jablonci nad Nisou",
    "Turnov":                "Turnově",
    "Semily":                "Semilech",
    "Rychnov nad Kněžnou":   "Rychnově nad Kněžnou",
    "Dvůr Králové nad Labem":"Dvoře Králové nad Labem",
    "Broumov":               "Broumově",
    "Nové Město na Moravě":  "Novém Městě na Moravě",
    "Havlíčkův Brod":        "Havlíčkově Brodě",
    "Pelhřimov":             "Pelhřimově",
    "Jindřichův Hradec":     "Jindřichově Hradci",
    "Český Krumlov":         "Českém Krumlově",
    "Hustopeče":             "Hustopečích",
    "Mikulov":               "Mikulově",
    "Břeclav":               "Břeclavi",
    "Boskovice":             "Boskovicích",
    "Ivančice":              "Ivančicích",
    "Rosice":                "Rosicích",
    "Kuřim":                 "Kuřimi",
}

def city_in_locative(city: str) -> str:
    """Vrátí 'v {město v lokálu}', nebo prázdný řetězec, když pád neznáme.

    Slovník pokrývá ~90 měst, ale pipeline projíždí přes 2 000 obcí. Dřív se
    u neznámého města vracel 1. pád ("v Benátky nad Jizerou"), což je v mailu
    klientovi vidět. Skloňovat česká jména obcí heuristikou je nespolehlivé
    (Klatovy→Klatovech, Kopřivnice→Kopřivnici, Benátky→Benátkách), proto radši
    vrátíme prázdno a volající větu složí bez zmínky o městě.
    """
    loc = CITY_LOCATIVE.get(city)
    return f"v {loc}" if loc else ""


def pick_subject(name, category) -> tuple:
    """Vrátí (předmět, varianta A/B/C) – aby šlo v Sheetu vyhodnotit, co funguje.

    `get_subject()` níž vrací jen text, takže se do Sheetu zapisovala prázdná
    varianta a A/B test nešel vyhodnotit ("Gmail draft vytvořen (varianta: )").
    """
    subjects = _subject_variants(name, category)
    i = random.randrange(len(subjects))
    return subjects[i], "ABC"[i] if i < 3 else str(i)


def _rating_note(restaurant: dict, category: str) -> str:
    """Věta o hodnocení na Googlu. Data se scrapují, ale v mailu se nepoužívala.

    Přidá se jen když je hodnocení opravdu dobré a postavené na dost recenzích –
    u podniku se třemi hvězdami by to vyznělo jako výsměch.
    """
    try:
        rating = float(restaurant.get("rating") or 0)
        reviews = int(restaurant.get("reviews_count") or 0)
    except (TypeError, ValueError):
        return ""
    if rating < 4.3 or reviews < 15:
        return ""
    r = f"{rating:.1f}".replace(".", ",")
    if category == "bez_webu":
        return (f" Všiml jsem si, že na Googlu máte {r} z {reviews} hodnocení – "
                f"to je skvělá vizitka, kterou ale nemáte kde pořádně ukázat.")
    return (f" Všiml jsem si, že na Googlu máte {r} z {reviews} hodnocení – "
            f"to je skvělá vizitka, kterou by web měl mnohem víc prodávat.")


def _subject_variants(name, category):
    if category == "bez_webu":
        subjects = [
            f"{name} – připravil jsem vám ukázku webu",
            "Váš nový web je hotový – podívejte se",
            "Zákazníci vás hledají na Googlu a nenajdou vás",
        ]
    else:
        subjects = [
            f"{name} – připravil jsem vám ukázku nového webu",
            "Váš nový web je hotový – podívejte se",
            "Zákazníci vás hledají na Googlu – co najdou?",
        ]
    return subjects


def get_subject(name, category):
    """Zpětně kompatibilní obal – vrací jen text předmětu."""
    return pick_subject(name, category)[0]


# Odvětvové texty pro šablonu
INDUSTRY_TEXTS = {
    "pekarna": {
        "co_delate": "pečete a prodáváte pečivo",
        "zakaznici": "zákazníky a stálé odběratele",
        "co_web_ukaze": "nabídku pečiva, otevírací dobu a to, co pečete vlastníma rukama",
        "problemy_bez_webu": [
            "lidé hledají pekárnu v okolí online – přes Google a mapy – a bez webu na vás jednoduše nenarazí",
            "bez vlastního webu neukážete to hlavní: co pečete, z čeho a v kolik hodin je to čerstvé",
            "katalogy vás sice zobrazí, ale sortiment, otevírací dobu ani objednávky na zakázku tam nemáte pod kontrolou",
            "Google a AI vyhledávače dávají přednost pekárnám s vlastním webem před těmi jen v katalozích",
        ],
        "reseni": [
            "postavíme moderní jednoduchý web, který hned ukáže: co pečete, kdy máte čerstvo a kde vás najdou",
            "přidáme přehledné bloky: nabídka pečiva a zákusků, fotky výrobků, otevírací doba, kontakt a mapa",
            "web bude rychlý, plně funkční na mobilu a nastavíme lokální SEO, aby vás Google bral jako hlavní výsledek pro dotazy v okolí",
        ],
        "prinosy": [
            "víc zákazníků, kteří vás cíleně najdou a přijdou – ne jen ti, co jdou náhodou kolem",
            "méně opakujících se dotazů na sortiment, otevírací dobu nebo objednávky na zakázku",
            "pevný online základ pro sezónní nabídky – vánoční cukroví, velikonoční pečivo, dorty na objednávku",
        ],
    },
    "kvetinarstvi": {
        "co_delate": "vážete a prodáváte květiny",
        "zakaznici": "zákazníky a klienty",
        "co_web_ukaze": "ukázky vazeb, nabídku a otevírací dobu",
        "problemy_bez_webu": [
            "květiny se vybírají očima – bez webu s fotkami vašich vazeb nemá zákazník podle čeho se rozhodnout",
            "svatební a smuteční vazba se objednává dopředu, a lidé k tomu hledají někoho, kdo působí důvěryhodně",
            "katalogy vás sice zobrazí, ale vaši práci, styl a fotky tam neukážete",
            "Google a AI vyhledávače upřednostňují květinářství s vlastním webem",
        ],
        "reseni": [
            "postavíme moderní web, kde bude vaše práce vidět na první pohled – galerie vazeb a aranžmá",
            "přidáme přehledné bloky: nabídka a sortiment, svatební a smuteční vazba, otevírací doba, kontakt a mapa",
            "web bude rychlý, plně funkční na mobilu a nastavíme lokální SEO, aby vás Google bral jako hlavní výsledek pro dotazy v okolí",
        ],
        "prinosy": [
            "víc zákazníků, kteří si vás najdou podle vašich fotek – a přijdou rovnou s konkrétní představou",
            "víc objednávek na svatby a větší zakázky, kde se rozhoduje podle ukázek práce",
            "pevný online základ pro sezónní špičky – Valentýn, Dušičky, Den matek, svatební sezóna",
        ],
    },
    "restaurace": {
        "co_delate": "vaři a servírujete jídlo",
        "zakaznici": "hosty a strávníky",
        "co_web_ukaze": "jídelní lístek, denní menu, provozní dobu a atmosféru restaurace",
        "problemy_bez_webu": [
            "většina lidí dnes hledá restauraci online ještě před příchodem – přes Google, mapy nebo Instagram",
            "bez vlastního webu vám uniká spousta zákazníků, kteří přejdou ke konkurenci s vlastní stránkou",
            "katalogy a portály vás sice ukazují, ale na vlastní stránce máte menu, atmosféru a rezervace pod kontrolou",
            "Google a nové AI vyhledávače upřednostňují restaurace s vlastním webem před těmi, co jsou jen v katalozích",
        ],
        "reseni": [
            "postavíme moderní jednoduchý web, který za pár vteřin ukáže: co vaříte, jaká je atmosféra a jak se k vám dostat",
            "přidáme přehledné bloky: jídelní lístek / denní menu, fotky jídel a interiéru, otevírací doba, kontakt a mapa",
            "web bude rychlý, plně funkční na mobilu a nastavíme lokální SEO, aby vás Google bral jako hlavní výsledek pro dotazy v okolí",
        ],
        "prinosy": [
            "víc hostů, kteří vás cíleně vyhledají a přijdou – ne jen náhodné kolemjdoucí",
            "méně opakujících se dotazů na menu, otevírací dobu nebo parkoviště – vše bude přehledně na webu",
            "pevný online základ, na kterém se dá stavět: sezónní nabídky, akce, rezervace",
        ],
    },
    "kavarna": {
        "co_delate": "provozujete kavárnu",
        "zakaznici": "hosty a zákazníky",
        "co_web_ukaze": "nabídku kávy a dortů, otevírací dobu a atmosféru kavárny",
        "problemy_bez_webu": [
            "lidé dnes hledají kavárny online – přes Google, mapy nebo Instagram – a bez webu vás jednoduše přehlédnou",
            "bez vlastního webu neukazujete to nejdůležitější: atmosféru, nabídku a proč si vybrat právě vás",
            "katalogy vás sice zobrazují, ale na vlastním webu máte nabídku, fotky a otevírací dobu pod kontrolou",
            "Google a AI vyhledávače upřednostňují kavárny s vlastním webem před těmi bez stránek",
        ],
        "reseni": [
            "postavíme moderní web, který rychle ukáže: kavárna, co nabízíte, jaká je atmosféra a kde vás najít",
            "přidáme přehledné bloky: nabídka kávy a zákusků, fotky interiéru, otevírací doba a kontakt",
            "technicky rychlý, responzivní pro mobil, lokální SEO pro dotazy jako 'kavárna [město]'",
        ],
        "prinosy": [
            "víc zákazníků, kteří vás najdou při hledání kavárny v okolí",
            "lepší první dojem – lidé přijdou připraveni, když viděli fotky a nabídku předem",
            "pevný základ pro propagaci sezónních specialit a akcí",
        ],
    },
    "penzion": {
        "co_delate": "provozujete penzion",
        "zakaznici": "hosty a turisty",
        "co_web_ukaze": "pokoje, ceny, polohu a vybavení penzionu",
        "problemy_bez_webu": [
            "většina turistů dnes hledá ubytování online – přes Google, Booking nebo mapy",
            "bez vlastního webu závisíte výhradně na portálech jako Booking, které si berou vysoké provize",
            "vlastní web snižuje závislost na portálech a přináší přímé rezervace zdarma",
            "Google a AI vyhledávače upřednostňují ubytování s vlastní stránkou před těmi bez ní",
        ],
        "reseni": [
            "postavíme web, který za pár vteřin ukáže: penzion, pokoje, ceny a jak rezervovat přímo u vás",
            "přidáme fotogalerii pokojů a společných prostor, ceník, dostupnost a kontaktní formulář",
            "lokální SEO pro dotazy jako 'penzion [město]' nebo 'ubytování [region]'",
        ],
        "prinosy": [
            "přímé rezervace bez provizí portálům – ušetříte 15–20 % z každé rezervace",
            "víc turistů, kteří vás najdou přes Google při plánování výletu",
            "profesionální první dojem, který pomůže obsadit i zbývající termíny",
        ],
    },
    "kadernictvi": {
        "co_delate": "provozujete kadeřnictví",
        "zakaznici": "klienty",
        "co_web_ukaze": "nabídku služeb, ceník a možnost objednání",
        "problemy_bez_webu": [
            "nové klientky hledají kadeřnictví přes Google nebo mapy – bez webu vás snadno přehlédnou",
            "bez vlastního webu neukazujete ceník, práce ani jak se objednat – vše závisí na doporučeních",
            "vlastní web buduje důvěru a ukazuje vaši práci ještě před první návštěvou",
        ],
        "reseni": [
            "postavíme moderní web s ceníkem, fotkami práce a tlačítkem pro objednání",
            "přidáme přehled služeb, galerii střihů a barvení, otevírací dobu a kontakt",
            "lokální SEO pro dotazy jako 'kadeřnictví [město]'",
        ],
        "prinosy": [
            "víc nových klientek, které vás najdou přes Google",
            "méně telefonátů s dotazy na ceník a volné termíny",
            "profesionální prezentace, která přitáhne klientky s vyšším rozpočtem",
        ],
    },
    "kosmetika": {
        "co_delate": "provozujete kosmetický salon",
        "zakaznici": "klientky",
        "co_web_ukaze": "nabídku procedur, ceník a možnost objednání",
        "problemy_bez_webu": [
            "nové klientky hledají kosmetiku přes Google nebo Instagram – bez webu vás snadno přehlédnou",
            "bez vlastního webu není kde ukázat ceník, procedury ani výsledky vaší práce",
            "vlastní web buduje důvěru a ukazuje profesionalitu ještě před první návštěvou",
        ],
        "reseni": [
            "postavíme web s ceníkem procedur, fotkami výsledků a možností objednání",
            "přidáme přehled služeb, fotogalerii, otevírací dobu a kontakt",
            "lokální SEO pro dotazy jako 'kosmetika [město]' nebo 'kosmetický salon [město]'",
        ],
        "prinosy": [
            "víc nových klientek, které vás najdou při hledání kosmetiky v okolí",
            "profesionální prezentace, která odliší váš salon od konkurence",
            "méně dotazů na ceník – vše přehledně na webu",
        ],
    },
    "autoservis": {
        "co_delate": "provozujete autoservis",
        "zakaznici": "zákazníky",
        "co_web_ukaze": "nabídku služeb, ceník a kontakty pro objednání",
        "problemy_bez_webu": [
            "motoristé dnes hledají autoservis přes Google nebo mapy – bez webu vás snadno přehlédnou",
            "bez vlastního webu nevíte, že vaši zákazníci hledají konkrétní služby: STK, pneu, klima servis...",
            "vlastní web ukazuje, co všechno děláte, a přináší zákazníky z celého okolí",
        ],
        "reseni": [
            "postavíme web s přehledem služeb, ceníkem a kontaktem pro objednání termínu",
            "přidáme sekce pro hlavní služby: servis, diagnostika, STK, pneuservis, klimatizace",
            "lokální SEO pro dotazy jako 'autoservis [město]' nebo konkrétní služby",
        ],
        "prinosy": [
            "víc zákazníků z okolí, kteří hledají konkrétní service a najdou vás přes Google",
            "méně telefonátů s dotazy na ceny a dostupnost",
            "pevný základ pro propagaci sezónních akcí (přezutí, STK akce atd.)",
        ],
    },
    "masaze": {
        "co_delate": "provozujete masážní salon",
        "zakaznici": "klienty",
        "co_web_ukaze": "nabídku masáží, ceník a objednání online",
        "problemy_bez_webu": [
            "noví klienti hledají masáže přes Google nebo mapy – bez webu vás snadno přehlédnou",
            "bez vlastního webu není kde ukázat druhy masáží, ceník a proč si vybrat právě vás",
            "vlastní web buduje důvěru a přináší klienty, kteří vás aktivně hledají",
        ],
        "reseni": [
            "postavíme web s přehledem masáží, ceníkem a možností online objednání",
            "přidáme fotky prostředí, otevírací dobu a jednoduché info o vašem přístupu",
            "lokální SEO pro dotazy jako 'masáže [město]'",
        ],
        "prinosy": [
            "víc nových klientů, kteří vás najdou při hledání masáží v okolí",
            "profesionální prezentace, která odliší váš salon od konkurence",
            "méně dotazů na ceny a volné termíny – vše na webu",
        ],
    },
    "zubni": {
        "co_delate": "provozujete zubní ordinaci",
        "zakaznici": "pacienty",
        "co_web_ukaze": "nabídku zubních služeb, ceník a objednání",
        "problemy_bez_webu": [
            "noví pacienti hledají zubaře přes Google nebo mapy – bez webu vás snadno přehlédnou",
            "bez vlastního webu není kde ukázat nabídku ošetření, ceník a jak se objednat",
            "vlastní web buduje důvěru a ukazuje přístup ordinace ještě před první návštěvou",
        ],
        "reseni": [
            "postavíme web s přehledem služeb, ceníkem a kontaktem pro objednání",
            "přidáme základní info o ordinaci, ošetřeních a jak se objednat online nebo telefonicky",
            "lokální SEO pro dotazy jako 'zubař [město]' nebo 'zubní ordinace [město]'",
        ],
        "prinosy": [
            "víc nových pacientů, kteří vás najdou přes Google při hledání zubaře v okolí",
            "méně telefonátů s dotazy na přijímání nových pacientů a ceník",
            "profesionální prezentace, která buduje důvěru ještě před první návštěvou",
        ],
    },
    "psycholog": {
        "co_delate": "provozujete psychologickou poradnu",
        "zakaznici": "klienty",
        "co_web_ukaze": "nabídku služeb, přístup a jak se objednat",
        "problemy_bez_webu": [
            "noví klienti hledají psychologa přes Google nebo doporučení – bez webu vás snadno přehlédnou",
            "bez vlastního webu není kde ukázat váš přístup, specializaci a jak funguje spolupráce",
            "vlastní web buduje důvěru a ukazuje, že jste profesionálové, ještě před prvním kontaktem",
        ],
        "reseni": [
            "postavíme web s popisem vašeho přístupu, specializace a jak probíhá první sezení",
            "přidáme info o formátu spolupráce, ceníku a jak se objednat",
            "lokální SEO pro dotazy jako 'psycholog [město]' nebo 'psychologická poradna [město]'",
        ],
        "prinosy": [
            "víc klientů, kteří vás najdou přes Google při hledání psychologické pomoci",
            "profesionální první dojem, který buduje důvěru ještě před prvním telefonátem",
            "jasná prezentace přístupu a specializace, která přitáhne klienty, se kterými chcete pracovat",
        ],
    },
}


def generate_email(restaurant, demo_url="", city="Praha"):
    name = restaurant.get("name", "")
    website = restaurant.get("website", "")
    category = restaurant.get("category", "bez_webu")
    industry_key = restaurant.get("industry", "restaurace")
    slug = restaurant.get("slug", "")
    ind = get_industry(industry_key)
    ind_name_gen = ind.get("name_genitive_pl", "podniky")  # "restaurací", "kaváren"...
    domain = website.replace("https://", "").replace("http://", "").rstrip("/") if website else ""

    subject, ab_variant = pick_subject(name, category)
    rating_note = _rating_note(restaurant, category)
    texts = INDUSTRY_TEXTS.get(industry_key, INDUSTRY_TEXTS["restaurace"])
    portfolio = PORTFOLIO_BY_INDUSTRY.get(industry_key, PORTFOLIO_BY_INDUSTRY["restaurace"])
    city_loc = city_in_locative(city)

    # Intro odstavec
    if category == "bez_webu":
        intro = (
            f"Dobrý den,\n\n"
            f"jmenuju se Matyáš a s mým kamarádem Kryštofem už několik let vytváříme moderní weby "
            f"pro {ind_name_gen} v Česku. Díval jsem se na {name}{' ' + city_loc if city_loc else ''} a napadlo mě, "
            f"že byste hodně získali jednoduchým, ale moderním vlastním webem, který bude prodávat "
            f"to, co děláte skvěle – ne jen jako zápis v katalozích a na sociálních sítích, "
            f"ale jako funkční základ podnikání.{rating_note}"
        )
    else:
        intro = (
            f"Dobrý den,\n\n"
            f"jmenuju se Matyáš a s mým kamarádem Kryštofem už několik let vytváříme moderní weby "
            f"pro {ind_name_gen} v Česku. Díval jsem se na váš web {domain} a napadlo mě, "
            f"že by zasloužil modernizaci – aby lépe fungoval na mobilech, rychleji se načítal "
            f"a výš se zobrazoval ve vyhledávačích.{rating_note}"
        )

    # Sekce problémů
    problems = texts["problemy_bez_webu"] if category == "bez_webu" else [
        f"web {domain} není plně přizpůsobený pro mobily – přitom přes 70 % lidí hledá z telefonu",
        "starší design a technologie snižují pozici ve vyhledávačích Google",
        "chybí jasná prezentace toho, co nabízíte, a proč si vybrat právě vás",
        "Google a AI vyhledávače dávají přednost moderním webům s rychlým načítáním",
    ]
    problems_formatted = "\n".join(f"• {p}" for p in problems[:4])

    problems_section = f"Co je teď problém\n{problems_formatted}"

    # Sekce řešení
    reseni = texts["reseni"]
    reseni_formatted = "\n".join(f"• {r}" for r in reseni)
    reseni_section = f"Jak to vyřešíme\n{reseni_formatted}"

    # Sekce přínosů
    prinosy = texts["prinosy"]
    prinosy_formatted = "\n".join(f"• {p}" for p in prinosy)
    prinosy_section = f"Co to přinese\n{prinosy_formatted}"

    # Demo odkaz
    if demo_url:
        demo_section = (
            f"Naše poslední projekty jsou například {portfolio}.\n\n"
            f"Pro ukázku jsem rovnou připravil, jak by nový web {name} mohl vypadat:\n"
            f"→ {demo_url}\n"
            f"Texty z ukázky jsou samozřejmě vaše, fotky vyměníme za vaše vlastní."
        )
    else:
        demo_section = f"Naše poslední projekty jsou například {portfolio}."

    # CTA. Cenu do studeného mailu schválně nepíšeme (rozhodnuto 5. 8. 2026) –
    # řeší se až v odpovědi, kdy je o čem mluvit. HTML verze cta_section přebírá.
    cta_section = (
        f"Rád vám k tomu řeknu víc – hodí se vám krátký hovor v úterý nebo ve středu "
        f"dopoledne? Stačí odpovědět na tento e-mail. 🙂"
    )

    # Podpis
    signature = f"S přátelským pozdravem,\n{SENDER_NAME}\n{SENDER_COMPANY} | {SENDER_WEBSITE}"

    body = "\n\n".join([
        intro,
        problems_section,
        reseni_section,
        prinosy_section,
        demo_section,
        cta_section,
        signature,
    ])

    # HTML verze
    def to_html_block(text):
        return text.replace("•", "•").replace("\n", "<br>")

    intro_html = intro.replace("\n\n", "</p><p>").replace("\n", "<br>")

    if demo_url:
        demo_html = (
            f"Naše poslední projekty jsou například {PORTFOLIO}.<br><br>"
            f"Pro ukázku jsem rovnou připravil, jak by nový web {name} mohl vypadat:<br>"
            # Odkaz vede přes Apps Script redirect, aby se dal změřit proklik.
            # Zobrazený text zůstává čistá adresa dema. Bez tohohle obalu se
            # `_click_tracking_url()` nikdy nevolala a prokliky byly od dubna
            # 2026 nula – ne že by nikdo neklikal, jen se to nikde nezapsalo.
            f'→ <a href="{_click_tracking_url(slug, demo_url)}">{demo_url}</a><br>'
            f"Texty z ukázky jsou samozřejmě vaše, fotky vyměníme za vaše vlastní."
        )
    else:
        demo_html = f"Naše poslední projekty jsou například {PORTFOLIO}."

    pixel = _tracking_pixel_html(slug)
    html_body = f"""<div style="font-family: Arial, sans-serif; font-size: 15px; line-height: 1.7; color: #222; max-width: 680px;">
<p>{intro_html}</p>
<p><strong>Co je teď problém</strong><br>{problems_formatted.replace(chr(10), '<br>')}</p>
<p><strong>Jak to vyřešíme</strong><br>{reseni_formatted.replace(chr(10), '<br>')}</p>
<p><strong>Co to přinese</strong><br>{prinosy_formatted.replace(chr(10), '<br>')}</p>
<p>{demo_html}</p>
<p>{cta_section.replace(chr(10)+chr(10), '</p><p>').replace(chr(10), '<br>')}</p>
<p style="margin-top:24px;">S přátelským pozdravem,<br><strong>{SENDER_NAME}</strong><br>
<a href="{SENDER_WEBSITE}">{SENDER_COMPANY}</a></p>
{pixel}
</div>"""

    return {"subject": subject, "body": body, "html_body": html_body, "to_name": name, "ab_variant": ab_variant}


def generate_followup_email(name, demo_url):
    """
    Krátký follow-up email pro podniky, které neodpověděly na první email.
    """
    subject = f"Viděl/a jste ukázku webu, {name}?"

    body = (
        f"Dobrý den,\n\n"
        f"posílám jen krátké připomenutí – před pár dny jsem vám poslal ukázku webu "
        f"pro {name}: {demo_url}\n\n"
        f"Kdyby vás to zajímalo nebo měli jakýkoliv dotaz, stačí odpovědět na tento e-mail.\n"
        f"A pokud teď není vhodná doba, klidně to nechte být – ozvat se můžete kdykoliv později.\n\n"
        f"S pozdravem,\n"
        f"{SENDER_NAME}\n"
        f"{SENDER_COMPANY}"
    )

    html_body = (
        f'<div style="font-family: Arial, sans-serif; font-size: 15px; line-height: 1.7; color: #222; max-width: 680px;">'
        f"<p>Dobrý den,</p>"
        f"<p>posílám jen krátké připomenutí – před pár dny jsem vám poslal ukázku webu "
        f'pro {name}: <a href="{demo_url}">{demo_url}</a></p>'
        f"<p>Kdyby vás to zajímalo nebo měli jakýkoliv dotaz, stačí odpovědět na tento e-mail. "
        f"A pokud teď není vhodná doba, klidně to nechte být – ozvat se můžete kdykoliv později.</p>"
        f"<p>S pozdravem,<br>"
        f"<strong>{SENDER_NAME}</strong><br>"
        f'<a href="{SENDER_WEBSITE}">{SENDER_COMPANY}</a></p>'
        f"</div>"
    )

    return {"subject": subject, "body": body, "html_body": html_body}


if __name__ == "__main__":
    test = {
        "name": "Kavárna U Mostu",
        "website": "",
        "category": "bez_webu",
        "industry": "kavarna",
        "slug": "kavarna-u-mostu",
    }
    result = generate_email(test, demo_url="https://strankyprovas.github.io/restaurace/kavarna-u-mostu/", city="Brno")
    print("PŘEDMĚT:", result["subject"])
    print()
    print(result["body"])
