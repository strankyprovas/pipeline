"""
Hromadné spuštění pipeline pro česká města (top 80 dle počtu obyvatel).
Použití:
    venv/bin/python3 run_all_cities.py              # 3 demo+draft na město
    venv/bin/python3 run_all_cities.py --target 5
    venv/bin/python3 run_all_cities.py --cities Praha,Brno --target 10
    venv/bin/python3 run_all_cities.py --skip 10    # přeskoč prvních 10 měst (resume)
"""
import argparse
from main import process_restaurants

DEFAULT_CITIES = [
    # Největší města (100k+)
    "Praha", "Brno", "Ostrava", "Plzeň", "Liberec",
    "Olomouc", "České Budějovice", "Hradec Králové", "Ústí nad Labem", "Pardubice",

    # 50k–100k
    "Zlín", "Havířov", "Kladno", "Most", "Opava",
    "Frýdek-Místek", "Karviná", "Jihlava", "Teplice", "Děčín",
    "Chomutov", "Přerov", "Jablonec nad Nisou", "Mladá Boleslav", "Prostějov",

    # 30k–50k
    "Česká Lípa", "Třebíč", "Znojmo", "Příbram", "Tábor",
    "Karlovy Vary", "Kolín", "Trutnov", "Šumperk", "Kroměříž",
    "Uherské Hradiště", "Hodonín", "Břeclav", "Cheb", "Nový Jičín",

    # 20k–30k
    "Vsetín", "Sokolov", "Písek", "Strakonice", "Havlíčkův Brod",
    "Žďár nad Sázavou", "Vyškov", "Blansko", "Náchod", "Valašské Meziříčí",
    "Beroun", "Kutná Hora", "Uherský Brod", "Mělník", "Hranice",

    # 10k–20k
    "Rožnov pod Radhoštěm", "Klatovy", "Bruntál", "Pelhřimov", "Dvůr Králové nad Labem",
    "Jičín", "Rychnov nad Kněžnou", "Zábřeh", "Šternberk", "Nymburk",
    "Jindřichův Hradec", "Rakovník", "Mariánské Lázně", "Litovel", "Kopřivnice",
    "Domažlice", "Prachatice", "Jeseník", "Turnov", "Český Krumlov",
    "Poděbrady", "Bílovec", "Litvínov", "Vrchlabí", "Holešov",
    "Strážnice", "Rýmařov", "Rokycany", "Třinec",

    # 5k–10k – Středočeský kraj
    "Benešov", "Vlašim", "Votice", "Sedlčany", "Dobříš", "Hořovice", "Slaný",
    "Kralupy nad Vltavou", "Neratovice", "Mnichovo Hradiště", "Lysá nad Labem",
    "Brandýs nad Labem", "Říčany", "Čelákovice", "Kostelec nad Černými Lesy",
    "Zruč nad Sázavou", "Čáslav", "Nové Strašecí", "Sázava", "Vlašim",

    # 5k–10k – Jihočeský kraj
    "Milevsko", "Soběslav", "Třeboň", "Dačice", "Vimperk", "Blatná",
    "Vodňany", "Týn nad Vltavou", "Kaplice", "Veselí nad Lužnicí",
    "Protivín", "Lhenice", "Lomnice nad Lužnicí",

    # 5k–10k – Plzeňský kraj
    "Stříbro", "Přeštice", "Stod", "Sušice", "Horažďovice", "Nepomuk",
    "Nýřany", "Kralovice", "Blovice", "Starý Plzenec",

    # 5k–10k – Karlovarský kraj
    "Aš", "Kraslice", "Ostrov", "Kadaň", "Klášterec nad Ohří", "Nejdek",
    "Horní Slavkov", "Chodov", "Toužim",

    # 5k–10k – Ústecký kraj
    "Roudnice nad Labem", "Lovosice", "Litoměřice", "Žatec", "Louny",
    "Krupka", "Bílina", "Podbořany", "Štětí", "Postoloprty",
    "Červený Hrádek", "Kadaň",

    # 5k–10k – Liberecký kraj
    "Nový Bor", "Semily", "Chrastava", "Hrádek nad Nisou", "Tanvald",
    "Frýdlant", "Železný Brod", "Rokytnice nad Jizerou", "Desná",

    # 5k–10k – Královéhradecký kraj
    "Jaroměř", "Nové Město nad Metují", "Broumov", "Nový Bydžov",
    "Chlumec nad Cidlinou", "Hořice", "Dobruška", "Kostelec nad Orlicí",
    "Police nad Metují", "Červený Kostelec", "Nová Paka", "Úpice",
    "Vrchlabí",

    # 5k–10k – Pardubický kraj
    "Chrudim", "Přelouč", "Česká Třebová", "Svitavy", "Litomyšl",
    "Lanškroun", "Žamberk", "Ústí nad Orlicí", "Vysoké Mýto", "Polička",
    "Hlinsko", "Heřmanův Městec", "Holice", "Sezemice",

    # 5k–10k – Kraj Vysočina
    "Velké Meziříčí", "Chotěboř", "Světlá nad Sázavou", "Humpolec",
    "Moravské Budějovice", "Telč", "Nové Město na Moravě",
    "Náměšť nad Oslavou", "Bystřice nad Pernštejnem", "Pacov",
    "Počátky", "Ledeč nad Sázavou", "Brtnice",

    # 5k–10k – Jihomoravský kraj
    "Veselí nad Moravou", "Kyjov", "Bučovice", "Hustopeče", "Pohořelice",
    "Mikulov", "Slavkov u Brna", "Kuřim", "Tišnov", "Ivančice",
    "Moravský Krumlov", "Šlapanice", "Rosice", "Boskovice",
    "Letovice", "Velká Bíteš", "Rousínov", "Ždánice",

    # 5k–10k – Olomoucký kraj
    "Uničov", "Mohelnice", "Konice", "Lipník nad Bečvou",
    "Šternberk", "Zábřeh", "Vidnava", "Zlaté Hory", "Hanušovice",

    # 5k–10k – Zlínský kraj
    "Otrokovice", "Napajedla", "Vizovice", "Luhačovice", "Bojkovice",
    "Valašské Klobouky", "Slavičín", "Bystřice pod Hostýnem", "Hulín",
    "Uherský Ostroh", "Staré Město", "Veselí nad Moravou",

    # 5k–10k – Moravskoslezský kraj
    "Bohumín", "Orlová", "Krnov", "Studénka", "Hlučín", "Odry",
    "Fulnek", "Vítkov", "Frenštát pod Radhoštěm", "Štítná nad Vláří",
    "Klimkovice", "Brušperk", "Kravaře", "Petřvald",
    "Třanovice", "Albrechtice", "Budišov nad Budišovkou",
]

# Odstraň případné duplikáty (zachová pořadí)
DEFAULT_CITIES = list(dict.fromkeys(DEFAULT_CITIES))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Multi-city outreach pipeline")
    parser.add_argument("--cities", type=str, default="",
                        help="Čárkou oddělený seznam měst (default: všech 80)")
    parser.add_argument("--target", type=int, default=3,
                        help="Počet demo+draft na město (default: 3)")
    parser.add_argument("--skip", type=int, default=0,
                        help="Přeskoč prvních N měst (pro resume po přerušení)")
    parser.add_argument("--industry", type=str, default="restaurace",
                        help="Odvětví (default: restaurace)")
    args = parser.parse_args()

    cities = [c.strip() for c in args.cities.split(",") if c.strip()] if args.cities else DEFAULT_CITIES
    cities = cities[args.skip:]

    print(f"🏙️  Zpracovávám {len(cities)} měst, cíl {args.target} demo/město (odvětví: {args.industry})")
    if args.skip:
        print(f"   (přeskočeno prvních {args.skip} měst)")
    print(f"   Města: {', '.join(cities[:10])}{'...' if len(cities) > 10 else ''}\n")

    used_domains: set = set()
    total = 0

    for city in cities:
        results = process_restaurants(city=city, target=args.target, used_domains=used_domains, industry=args.industry)
        total += sum(1 for r in results if r.get("demo_path"))

    print(f"\n{'='*50}")
    print(f"🎉 Celkem vygenerováno: {total} demo+draft pro {len(cities)} měst")
