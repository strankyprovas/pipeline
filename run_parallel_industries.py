"""
Paralelní spuštění pipeline pro všechna odvětví najednou.
Každé odvětví běží v samostatném procesu.

Použití:
    venv/bin/python3 run_parallel_industries.py
    venv/bin/python3 run_parallel_industries.py --target 2 --log-dir /tmp/outreach-logs
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

INDUSTRIES = [
    "restaurace",
    "kavarna",
    "penzion",
    "kadernictvi",
    "kosmetika",
    "autoservis",
    "masaze",
    "zubni",
    "psycholog",
]

# Větší česká města s dobrým pokrytím OSM (více podniků s kontakty).
# Dedup v DB automaticky přeskočí podniky, které tam už jsou.
# ~40 měst × target 3 × 9 odvětví = max ~1080 potenciálních draftů
MEDIUM_CITIES = ",".join([
    # Největší města – nejlepší OSM pokrytí, nejvíce emailů
    "Praha", "Brno", "Ostrava", "Plzeň",
    # Krajská a velká města (nejlepší OSM pokrytí)
    "Liberec", "Olomouc", "České Budějovice", "Hradec Králové",
    "Pardubice", "Zlín", "Ústí nad Labem", "Opava", "Ostrava", "Plzeň",
    "Havířov", "Kladno", "Most", "Frýdek-Místek", "Karviná",
    "Děčín", "Chomutov", "Přerov", "Jablonec nad Nisou",
    # Středočeský kraj
    "Benešov", "Beroun", "Brandýs nad Labem", "Čáslav", "Čelákovice",
    "Český Brod", "Dobříš", "Hořovice", "Kolín", "Kralupy nad Vltavou",
    "Kutná Hora", "Lysá nad Labem", "Mělník", "Mnichovo Hradiště",
    "Neratovice", "Nymburk", "Poděbrady", "Příbram", "Rakovník",
    "Říčany", "Sedlčany", "Slaný", "Vlašim", "Votice",
    # Jihočeský kraj
    "Český Krumlov", "Dačice", "Jindřichův Hradec", "Kaplice",
    "Milevsko", "Písek", "Prachatice", "Protivín", "Soběslav",
    "Strakonice", "Tábor", "Třeboň", "Týn nad Vltavou", "Vimperk",
    "Vodňany", "Blatná", "Veselí nad Lužnicí", "Trhové Sviny",
    # Plzeňský kraj
    "Domažlice", "Horažďovice", "Klatovy", "Kralovice", "Nepomuk",
    "Nýřany", "Přeštice", "Rokycany", "Stříbro", "Sušice", "Tachov",
    # Karlovarský kraj
    "Karlovy Vary", "Aš", "Cheb", "Chodov", "Horní Slavkov",
    "Kadaň", "Klášterec nad Ohří", "Kraslice", "Mariánské Lázně",
    "Nejdek", "Ostrov", "Sokolov",
    # Ústecký kraj
    "Bílina", "Krupka", "Litoměřice", "Litvínov", "Louny",
    "Lovosice", "Podbořany", "Roudnice nad Labem", "Rumburk",
    "Štětí", "Varnsdorf", "Žatec", "Jirkov",
    # Liberecký kraj
    "Česká Lípa", "Frýdlant", "Hrádek nad Nisou", "Jilemnice",
    "Nový Bor", "Semily", "Tanvald", "Turnov", "Železný Brod",
    # Královéhradecký kraj
    "Broumov", "Chlumec nad Cidlinou", "Červený Kostelec",
    "Dobruška", "Dvůr Králové nad Labem", "Hořice", "Jaroměř",
    "Jičín", "Kostelec nad Orlicí", "Náchod", "Nová Paka",
    "Nové Město nad Metují", "Nový Bydžov", "Police nad Metují",
    "Rychnov nad Kněžnou", "Trutnov", "Úpice", "Vrchlabí",
    # Pardubický kraj
    "Chrudim", "Česká Třebová", "Heřmanův Městec", "Hlinsko",
    "Holice", "Lanškroun", "Litomyšl", "Polička", "Přelouč",
    "Svitavy", "Ústí nad Orlicí", "Vysoké Mýto", "Žamberk",
    # Vysočina
    "Bystřice nad Pernštejnem", "Chotěboř", "Havlíčkův Brod",
    "Humpolec", "Jihlava", "Moravské Budějovice", "Náměšť nad Oslavou",
    "Nové Město na Moravě", "Pacov", "Pelhřimov", "Světlá nad Sázavou",
    "Telč", "Třebíč", "Velké Meziříčí", "Žďár nad Sázavou",
    # Jihomoravský kraj
    "Blansko", "Boskovice", "Břeclav", "Bučovice", "Hodonín",
    "Hustopeče", "Ivančice", "Kuřim", "Kyjov", "Letovice",
    "Mikulov", "Moravský Krumlov", "Pohořelice", "Rosice",
    "Slavkov u Brna", "Tišnov", "Veselí nad Moravou", "Vyškov",
    "Znojmo", "Strážnice", "Bzenec",
    # Olomoucký kraj
    "Hranice", "Jeseník", "Litovel", "Lipník nad Bečvou",
    "Mohelnice", "Prostějov", "Přerov", "Šternberk", "Šumperk",
    "Uničov", "Zábřeh", "Zlaté Hory",
    # Zlínský kraj
    "Bojkovice", "Bystřice pod Hostýnem", "Holešov", "Hulín",
    "Kroměříž", "Luhačovice", "Napajedla", "Otrokovice",
    "Rožnov pod Radhoštěm", "Slavičín", "Uherské Hradiště",
    "Uherský Brod", "Valašské Klobouky", "Valašské Meziříčí",
    "Vizovice", "Vsetín",
    # Moravskoslezský kraj
    "Bílovec", "Bohumín", "Bruntál", "Frenštát pod Radhoštěm",
    "Fulnek", "Hlučín", "Kopřivnice", "Kravaře", "Krnov",
    "Nový Jičín", "Odry", "Orlová", "Příbor", "Rýmařov",
    "Studénka", "Třinec", "Vítkov", "Jablunkov",
    "Frýdlant nad Ostravicí",
])


def run_industry(industry: str, target: int, cities: str, log_dir: str, skip: int = 0) -> subprocess.Popen:
    log_path = os.path.join(log_dir, f"{industry}.log")
    python = os.path.join(os.path.dirname(__file__), "venv", "bin", "python3")
    script = os.path.join(os.path.dirname(__file__), "run_all_cities.py")
    cmd = [
        python, script,
        "--cities", cities,
        "--target", str(target),
        "--industry", industry,
    ]
    if skip > 0:
        cmd += ["--skip", str(skip)]
    print(f"▶  Spouštím {industry:15s} → log: {log_path}")
    log_file = open(log_path, "w", encoding="utf-8")
    return subprocess.Popen(cmd, stdout=log_file, stderr=log_file, cwd=os.path.dirname(__file__))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=2,
                        help="Počet demo+draft na město (default: 2)")
    parser.add_argument("--log-dir", type=str, default="/tmp/outreach-logs",
                        help="Adresář pro logy (default: /tmp/outreach-logs)")
    parser.add_argument("--industries", type=str, default="",
                        help="Čárkou oddělený seznam odvětví (default: všechna)")
    parser.add_argument("--skip", type=int, default=0,
                        help="Přeskoč prvních N měst (default: 0)")
    args = parser.parse_args()

    os.makedirs(args.log_dir, exist_ok=True)
    industries = [i.strip() for i in args.industries.split(",") if i.strip()] if args.industries else INDUSTRIES

    print(f"🚀 Spouštím {len(industries)} odvětví paralelně")
    print(f"   Cíl: {args.target} demo/město × {len(MEDIUM_CITIES.split(','))} měst")
    print(f"   Max možný výstup: ~{args.target * len(MEDIUM_CITIES.split(',')) * len(industries)} draftů")
    print(f"   Logy: {args.log_dir}/\n")

    processes = []
    for ind in industries:
        p = run_industry(ind, args.target, MEDIUM_CITIES, args.log_dir, skip=args.skip)
        processes.append((ind, p))
        time.sleep(3)  # malý delay aby se nepřetěžoval Sheets API při startu

    print(f"\n✅ Všech {len(processes)} procesů spuštěno. Čekám na dokončení...\n")

    # Monitoring loop
    start = time.time()
    while True:
        alive = [(ind, p) for ind, p in processes if p.poll() is None]
        done  = [(ind, p) for ind, p in processes if p.poll() is not None]
        elapsed = int(time.time() - start)
        print(f"[{elapsed//60:02d}:{elapsed%60:02d}] Běží: {len(alive)} | Hotovo: {len(done)}", flush=True)

        # Zobraz stav každého odvětví
        for ind, p in processes:
            log_path = os.path.join(args.log_dir, f"{ind}.log")
            if os.path.exists(log_path):
                try:
                    lines = Path(log_path).read_text(encoding="utf-8").splitlines()
                    # Najdi poslední řádek se statusem
                    status_lines = [l for l in lines if any(x in l for x in ["Hotovo:", "⚠️", "✅", "🎯", "demo+draft", "Zpracovávám"])]
                    last = status_lines[-1].strip() if status_lines else "..."
                    rc = p.poll()
                    icon = "✅" if rc == 0 else ("🔄" if rc is None else "❌")
                    print(f"  {icon} {ind:15s}: {last[:80]}")
                except Exception:
                    pass

        if not alive:
            print(f"\n🎉 Všechny procesy dokončeny za {elapsed//60} minut {elapsed%60} sekund")
            break

        time.sleep(60)  # kontrola každou minutu

    # Výsledky
    print("\n📊 Výsledky:")
    for ind, p in processes:
        log_path = os.path.join(args.log_dir, f"{ind}.log")
        if os.path.exists(log_path):
            lines = Path(log_path).read_text(encoding="utf-8").splitlines()
            total_lines = [l for l in lines if "Celkem vygenerováno:" in l]
            if total_lines:
                print(f"  {ind}: {total_lines[-1].strip()}")
            else:
                done_lines = [l for l in lines if "Hotovo!" in l or "vygenerováno" in l.lower()]
                print(f"  {ind}: {done_lines[-1].strip() if done_lines else '(viz log)'}")
