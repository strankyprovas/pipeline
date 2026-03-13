"""
Hromadné spuštění pipeline pro všechna česká města.
Města se stahují dynamicky z Overpass API (OSM) – žádný hardcoded list.

Použití:
    venv/bin/python3 run_all_cities.py              # všechna města, target 2
    venv/bin/python3 run_all_cities.py --target 5
    venv/bin/python3 run_all_cities.py --min-pop 5000   # jen města 5000+ obyvatel
    venv/bin/python3 run_all_cities.py --cities Praha,Brno --target 10
    venv/bin/python3 run_all_cities.py --skip 50   # přeskoč prvních 50 měst
"""
import argparse
import os
import random
import requests
import time
from main import process_restaurants


CITIES_CACHE_FILE = os.path.join(os.path.dirname(__file__), "czech_cities_cache.json")
CACHE_MAX_AGE_DAYS = 7


def fetch_czech_cities(min_population: int = 1000) -> list[str]:
    """
    Vrátí všechna česká města/obce seřazená podle počtu obyvatel.
    Výsledek se cachuje do souboru (obnovuje se jednou za 7 dní).
    """
    import json, os, time

    # Použij cache pokud existuje a není starší než 7 dní
    if os.path.exists(CITIES_CACHE_FILE):
        age_days = (time.time() - os.path.getmtime(CITIES_CACHE_FILE)) / 86400
        if age_days < CACHE_MAX_AGE_DAYS:
            with open(CITIES_CACHE_FILE, encoding="utf-8") as f:
                cached = json.load(f)
            cities = [c for c in cached if c]
            print(f"🏙️  Načteno {len(cities)} měst z cache (stáří: {age_days:.1f} dní)")
            return cities

    print(f"🌍 Stahuji seznam českých měst z Overpass API (min. {min_population} obyvatel)...")

    # Rychlejší query – jen cities a towns (vždy), villages s populačním tagem
    query = """
[out:json][timeout:60];
area["ISO3166-1"="CZ"][admin_level=2]->.czechia;
(
  node(area.czechia)["place"~"^(city|town)$"]["name"];
  node(area.czechia)["place"="village"]["name"]["population"];
  way(area.czechia)["place"~"^(city|town)$"]["name"];
  way(area.czechia)["place"="village"]["name"]["population"];
);
out tags;
"""
    try:
        resp = requests.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": query},
            timeout=90,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  ⚠️  Overpass API selhalo ({e}), používám záložní seznam")
        return _fallback_cities()

    # Parsuj výsledky – filtruj, odstraň duplikáty, seřaď podle počtu obyvatel
    cities = {}
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        name = tags.get("name:cs") or tags.get("name")
        place_type = tags.get("place", "")
        if not name:
            continue

        pop_str = tags.get("population", "0").replace(" ", "").replace(",", "").replace("\xa0", "")
        try:
            pop = int(float(pop_str))
        except ValueError:
            pop = 0

        # Zahrň: city/town vždy, village jen pokud má dost obyvatel
        if place_type in ("city", "town"):
            effective_pop = max(pop, min_population)  # town/city vždy zahrni
        elif pop >= min_population:
            effective_pop = pop
        else:
            continue  # příliš malá vesnice

        # Největší populace wins pro duplicitní názvy
        if name not in cities or effective_pop > cities[name]:
            cities[name] = effective_pop

    # Seřaď: nejlidnatější první
    sorted_cities = sorted(cities.items(), key=lambda x: x[1], reverse=True)
    result = [name for name, _ in sorted_cities]

    print(f"  ✅ Nalezeno {len(result)} měst/obcí")

    # Pokud Overpass vrátil prázdný výsledek, použij záložní seznam (necachuj prázdno)
    if not result:
        print("  ⚠️  Overpass vrátil 0 měst – používám záložní seznam")
        return _fallback_cities()

    # Ulož do cache
    import json
    with open(CITIES_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False)

    return result


def _fallback_cities() -> list[str]:
    """Komprehenzivní záložní seznam ~600 českých měst (všechna statutární města + města + větší obce)."""
    return list(dict.fromkeys([
        # Největší města
        "Praha", "Brno", "Ostrava", "Plzeň", "Liberec", "Olomouc",
        "České Budějovice", "Hradec Králové", "Ústí nad Labem", "Pardubice",
        "Zlín", "Havířov", "Kladno", "Most", "Opava", "Frýdek-Místek",
        "Karviná", "Jihlava", "Teplice", "Děčín", "Chomutov", "Přerov",
        "Jablonec nad Nisou", "Mladá Boleslav", "Prostějov",
        # Středočeský kraj
        "Benešov", "Beroun", "Brandýs nad Labem", "Čáslav", "Čelákovice",
        "Černošice", "Český Brod", "Dobříš", "Hořovice", "Kolín",
        "Kralupy nad Vltavou", "Kutná Hora", "Lysá nad Labem", "Mělník",
        "Mnichovo Hradiště", "Neratovice", "Nové Strašecí", "Nymburk",
        "Poděbrady", "Příbram", "Rakovník", "Říčany", "Sedlčany",
        "Slaný", "Vlašim", "Votice", "Zruč nad Sázavou",
        "Kostelec nad Černými Lesy", "Hostivice", "Mnichovice", "Roztoky",
        "Odolena Voda", "Úvaly", "Čerčany", "Ledeč nad Sázavou",
        # Jihočeský kraj
        "Český Krumlov", "Dačice", "Jindřichův Hradec", "Kaplice",
        "Milevsko", "Písek", "Prachatice", "Protivín", "Soběslav",
        "Strakonice", "Tábor", "Třeboň", "Týn nad Vltavou", "Vimperk",
        "Vodňany", "Blatná", "Veselí nad Lužnicí", "Lomnice nad Lužnicí",
        "Netolice", "Volary", "Trhové Sviny", "Větřní", "Nové Hrady",
        # Plzeňský kraj
        "Domažlice", "Horažďovice", "Klatovy", "Kralovice", "Nepomuk",
        "Nýřany", "Přeštice", "Rokycany", "Stod", "Stříbro", "Sušice",
        "Blovice", "Starý Plzenec", "Spálené Poříčí", "Tachov", "Bor",
        # Karlovarský kraj
        "Karlovy Vary", "Aš", "Cheb", "Chodov", "Horní Slavkov",
        "Kadaň", "Klášterec nad Ohří", "Kraslice", "Mariánské Lázně",
        "Nejdek", "Ostrov", "Sokolov", "Toužim", "Žlutice", "Rotava",
        # Ústecký kraj
        "Bílina", "Chomutov", "Krupka", "Litoměřice", "Litvínov",
        "Louny", "Lovosice", "Podbořany", "Postoloprty",
        "Roudnice nad Labem", "Rumburk", "Štětí", "Varnsdorf", "Žatec",
        "Dubí", "Jirkov", "Lom", "Osek", "Benešov nad Ploučnicí",
        # Liberecký kraj
        "Česká Lípa", "Chrastava", "Desná", "Frýdlant",
        "Hrádek nad Nisou", "Jilemnice", "Nový Bor",
        "Rokytnice nad Jizerou", "Semily", "Tanvald",
        "Turnov", "Železný Brod", "Mimoň", "Zákupy", "Cvikov",
        "Stráž pod Ralskem", "Doksy",
        # Královéhradecký kraj
        "Broumov", "Chlumec nad Cidlinou", "Červený Kostelec",
        "Dobruška", "Dvůr Králové nad Labem", "Hořice", "Jaroměř",
        "Jičín", "Kostelec nad Orlicí", "Náchod", "Nová Paka",
        "Nové Město nad Metují", "Nový Bydžov", "Police nad Metují",
        "Rychnov nad Kněžnou", "Trutnov", "Úpice", "Vrchlabí",
        "Třebechovice pod Orebem", "Opočno", "Týniště nad Orlicí",
        # Pardubický kraj
        "Chrudim", "Česká Třebová", "Heřmanův Městec", "Hlinsko",
        "Holice", "Lanškroun", "Litomyšl", "Polička", "Přelouč",
        "Sezemice", "Svitavy", "Ústí nad Orlicí", "Vysoké Mýto",
        "Žamberk", "Skuteč", "Chrast",
        # Kraj Vysočina
        "Brtnice", "Bystřice nad Pernštejnem", "Chotěboř",
        "Havlíčkův Brod", "Humpolec", "Ledeč nad Sázavou",
        "Moravské Budějovice", "Náměšť nad Oslavou",
        "Nové Město na Moravě", "Pacov", "Pelhřimov",
        "Světlá nad Sázavou", "Telč", "Třebíč", "Velké Meziříčí",
        "Žďár nad Sázavou", "Počátky", "Velká Bíteš",
        # Jihomoravský kraj
        "Blansko", "Boskovice", "Břeclav", "Bučovice", "Hodonín",
        "Hustopeče", "Ivančice", "Kuřim", "Kyjov", "Letovice",
        "Mikulov", "Moravský Krumlov", "Pohořelice", "Rosice",
        "Rousínov", "Šlapanice", "Slavkov u Brna", "Tišnov",
        "Veselí nad Moravou", "Vyškov", "Znojmo", "Strážnice",
        "Klobouky u Brna", "Bzenec", "Podivín", "Dubňany",
        # Olomoucký kraj
        "Hranice", "Jeseník", "Konice", "Litovel",
        "Lipník nad Bečvou", "Mohelnice", "Šternberk", "Šumperk",
        "Uničov", "Zábřeh", "Zlaté Hory", "Hanušovice",
        "Vidnava", "Červenka", "Náměšť na Hané",
        # Zlínský kraj
        "Bojkovice", "Bystřice pod Hostýnem", "Holešov", "Hulín",
        "Kroměříž", "Luhačovice", "Napajedla", "Otrokovice",
        "Rožnov pod Radhoštěm", "Slavičín", "Staré Město",
        "Uherské Hradiště", "Uherský Brod", "Uherský Ostroh",
        "Valašské Klobouky", "Valašské Meziříčí", "Vizovice",
        "Vsetín", "Karolinka", "Kelč",
        # Moravskoslezský kraj
        "Bílovec", "Bohumín", "Bruntál", "Brušperk",
        "Budišov nad Budišovkou", "Frenštát pod Radhoštěm",
        "Fulnek", "Hlučín", "Klimkovice", "Kopřivnice",
        "Kravaře", "Krnov", "Nový Jičín", "Odry", "Orlová",
        "Petřvald", "Příbor", "Rýmařov", "Studénka", "Třinec",
        "Vítkov", "Město Albrechtice", "Jablunkov",
        "Frýdlant nad Ostravicí", "Šenov", "Rychvald",
        "Dolní Benešov", "Osoblaha",
    ]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-city outreach pipeline – celá ČR")
    parser.add_argument("--cities", type=str, default="",
                        help="Čárkou oddělený seznam měst (default: všechna z Overpass API)")
    parser.add_argument("--target", type=int, default=2,
                        help="Počet demo+draft na město (default: 2)")
    parser.add_argument("--skip", type=int, default=0,
                        help="Přeskoč prvních N měst (pro resume)")
    parser.add_argument("--min-pop", type=int, default=1000,
                        help="Minimální počet obyvatel (default: 1000)")
    parser.add_argument("--industry", type=str, default="restaurace",
                        help="Odvětví (default: restaurace)")
    args = parser.parse_args()

    if args.cities:
        cities = [c.strip() for c in args.cities.split(",") if c.strip()]
    else:
        cities = fetch_czech_cities(min_population=args.min_pop)

    cities = cities[args.skip:]

    # Náhodné zpoždění startu (0–90s) aby paralelní GitHub Actions joby nestrefily Sheets API najednou
    startup_delay = random.uniform(0, 90)
    print(f"⏱️  Startup delay: {startup_delay:.0f}s (aby paralelní joby nestrefily Sheets najednou)")
    time.sleep(startup_delay)

    print(f"🏙️  Zpracovávám {len(cities)} měst, cíl {args.target} demo/město (odvětví: {args.industry})")
    if args.skip:
        print(f"   (přeskočeno prvních {args.skip} měst)")
    print(f"   Ukázka: {', '.join(cities[:8])}...\n")

    used_domains: set = set()
    total = 0

    for city in cities:
        results = process_restaurants(
            city=city,
            target=args.target,
            used_domains=used_domains,
            industry=args.industry,
        )
        total += sum(1 for r in results if r.get("demo_path"))

    print(f"\n{'='*50}")
    print(f"🎉 Celkem vygenerováno: {total} demo+draft pro {len(cities)} měst")
