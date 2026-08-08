#!/usr/bin/env python3
"""
Jednorázová (klidně i opakovatelná) analýza toho, co outreach za celou dobu
skutečně přinesl. Čte Google Sheet a sečte odezvu podle oboru, města, A/B
varianty a měsíce.

Proč to existuje: od 25. 2. 2026 odešly tisíce mailů a nikdo je nikdy nesečetl.
Bez toho se kapacita rozděluje mezi obory od oka.

⚠️ Spouštět přes workflow "Outreach report", ne lokálně – sahá to na týž Google
   token jako pipeline a sender, a souběžné obnovení tokenu ho zneplatní.
   Workflow drží concurrency group `google-oauth-token`, takže se to nepotká.

Použití:
    python3 analyze_outreach.py                 # report na stdout
    python3 analyze_outreach.py --out report.md # + do souboru
    python3 analyze_outreach.py --min-vzorek 50 # jiný práh průkaznosti
"""
import argparse
import math
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)


def wilson(uspechy: int, pokusy: int, z: float = 1.96) -> tuple[float, float]:
    """
    95% Wilsonův interval spolehlivosti pro podíl.

    Bez intervalu se z čísel jako "3 odpovědi ze 40 vs 1 ze 45" vyčte
    trojnásobná odezva, i když je to čirá náhoda. Interval to ukáže: ty dva
    rozsahy se překrývají skoro celé.
    """
    if pokusy == 0:
        return (0.0, 0.0)
    p = uspechy / pokusy
    denom = 1 + z**2 / pokusy
    stred = (p + z**2 / (2 * pokusy)) / denom
    rozptyl = z * math.sqrt(p * (1 - p) / pokusy + z**2 / (4 * pokusy**2)) / denom
    return (max(0.0, stred - rozptyl) * 100, min(1.0, stred + rozptyl) * 100)


def nacti_radky() -> tuple[list[str], list[list[str]]]:
    """Načte celý Sheet. get_all_values, ne get_all_records – ten padá na prázdné hlavičce."""
    from sheets import get_or_create_sheet

    sheet = get_or_create_sheet()
    hodnoty = sheet.get_all_values()
    if not hodnoty:
        return [], []
    return hodnoty[0], hodnoty[1:]


def _sloupec(hlavicky: list[str], nazev: str) -> int:
    try:
        return hlavicky.index(nazev)
    except ValueError:
        return -1


def _mesic(datum: str) -> str:
    """'09.03.2026 14:15' → '2026-03'. Prázdno když se to nepovede rozparsovat."""
    m = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", datum.strip())
    return f"{m.group(3)}-{m.group(2)}" if m else ""


class Segment:
    __slots__ = ("odeslano", "odpovedi", "prokliky", "otevreni", "follow_upy")

    def __init__(self):
        self.odeslano = 0
        self.odpovedi = 0
        self.prokliky = 0
        self.otevreni = 0
        self.follow_upy = 0


def analyzuj(hlavicky: list[str], radky: list[list[str]]) -> dict:
    i_datum = _sloupec(hlavicky, "Datum emailu")
    i_stav = _sloupec(hlavicky, "Stav")
    i_mesto = _sloupec(hlavicky, "Město")
    i_odvetvi = _sloupec(hlavicky, "Odvětví")
    i_odpov = _sloupec(hlavicky, "Odpověděl")
    i_ab = _sloupec(hlavicky, "AB Varianta")
    i_fup = _sloupec(hlavicky, "Datum follow-up")

    def bunka(r, i):
        return r[i].strip() if 0 <= i < len(r) else ""

    podle = {
        "obor": defaultdict(Segment),
        "mesto": defaultdict(Segment),
        "varianta": defaultdict(Segment),
        "mesic": defaultdict(Segment),
    }
    celkem = Segment()
    radku_celkem = 0
    bez_oboru = 0
    kde_znacky = {"klik": defaultdict(int), "pixel": defaultdict(int)}

    for r in radky:
        radku_celkem += 1
        datum = bunka(r, i_datum)
        stav = bunka(r, i_stav).lower()
        # Odesláno = má datum mailu, nebo je ve stavu, který odeslání předpokládá.
        # Samotné "nový" znamená jen vygenerované demo, mail ještě neodešel.
        odeslano = bool(datum) or stav in ("osloveno", "follow_up_odesl", "odpověděl",
                                           "bez_odpovědi", "nezájem")
        if not odeslano:
            continue

        odpovedel = bool(bunka(r, i_odpov)) or stav == "odpověděl"

        # Značky "klik …" / "pixel …" zapisuje Apps Script tracker a nesedí vždy
        # ve stejném sloupci (viděl jsem je v Poznámce i jinde). Když se hledaly
        # jen v Poznámce, vyšlo 0 prokliků, ačkoli v Sheetu jsou. Proto se
        # prohledává celý řádek a zároveň se sleduje, kde se to našlo.
        proklik = otevrel = False
        for idx, hodnota in enumerate(r):
            h = hodnota.lower()
            if "klik" in h:
                proklik = True
                kde_znacky["klik"][hlavicky[idx] if idx < len(hlavicky) else f"sl. {idx}"] += 1
            if "pixel" in h:
                otevrel = True
                kde_znacky["pixel"][hlavicky[idx] if idx < len(hlavicky) else f"sl. {idx}"] += 1
        follow_up = bool(bunka(r, i_fup)) or stav == "follow_up_odesl"

        obor = bunka(r, i_odvetvi) or "(nevyplněno)"
        if obor == "(nevyplněno)":
            bez_oboru += 1
        klice = {
            "obor": obor,
            "mesto": bunka(r, i_mesto) or "(nevyplněno)",
            "varianta": bunka(r, i_ab) or "(nevyplněno)",
            "mesic": _mesic(datum) or "(bez data)",
        }

        for rozmer, klic in klice.items():
            s = podle[rozmer][klic]
            s.odeslano += 1
            s.odpovedi += odpovedel
            s.prokliky += proklik
            s.otevreni += otevrel
            s.follow_upy += follow_up

        celkem.odeslano += 1
        celkem.odpovedi += odpovedel
        celkem.prokliky += proklik
        celkem.otevreni += otevrel
        celkem.follow_upy += follow_up

    return {
        "podle": podle,
        "celkem": celkem,
        "radku_celkem": radku_celkem,
        "bez_oboru": bez_oboru,
        "kde_znacky": kde_znacky,
    }


def tabulka(nazev: str, segmenty: dict, min_vzorek: int, celkova_odezva: float,
            limit: int = 0) -> list[str]:
    polozky = sorted(segmenty.items(), key=lambda kv: kv[1].odeslano, reverse=True)
    orezano = 0
    if limit and len(polozky) > limit:
        orezano = len(polozky) - limit
        polozky = polozky[:limit]

    out = [f"### {nazev}", "",
           "| | Odesláno | Odpovědi | Odezva | 95% interval | Prokliky | Follow-upy |",
           "|---|---:|---:|---:|---|---:|---:|"]
    for klic, s in polozky:
        odezva = s.odpovedi / s.odeslano * 100 if s.odeslano else 0
        dolni, horni = wilson(s.odpovedi, s.odeslano)
        if s.odeslano < min_vzorek:
            interval = "málo dat"
        else:
            interval = f"{dolni:.1f}–{horni:.1f} %"
            # Průkazné je to jen tehdy, když interval celkový průměr nepřekrývá.
            if dolni > celkova_odezva:
                interval += " ▲"
            elif horni < celkova_odezva:
                interval += " ▼"
        out.append(
            f"| {klic} | {s.odeslano} | {s.odpovedi} | {odezva:.1f} % | {interval} "
            f"| {s.prokliky} | {s.follow_upy} |"
        )
    if orezano:
        out.append(f"| _(a dalších {orezano} s menším objemem)_ | | | | | | |")
    out.append("")
    return out


def sestav_report(data: dict, min_vzorek: int) -> str:
    c = data["celkem"]
    odezva = c.odpovedi / c.odeslano * 100 if c.odeslano else 0
    dolni, horni = wilson(c.odpovedi, c.odeslano)

    r = [
        "# Outreach – co to za celou dobu přineslo",
        "",
        f"Vygenerováno {datetime.now().strftime('%d. %m. %Y')} "
        f"z {data['radku_celkem']} řádků databáze.",
        "",
        "## Celkem",
        "",
        f"- **Odesláno mailů:** {c.odeslano}",
        f"- **Odpovědí:** {c.odpovedi} → **odezva {odezva:.2f} %** "
        f"(95% interval {dolni:.2f}–{horni:.2f} %)",
        f"- **Prokliků na demo:** {c.prokliky} "
        f"({c.prokliky / c.odeslano * 100:.2f} %)" if c.odeslano else "",
        f"- **Otevření (pixel):** {c.otevreni} – "
        "měřeno nespolehlivě, Gmail i Seznam obrázky proxují, ber jen orientačně",
        f"- **Odeslaných follow-upů:** {c.follow_upy}",
        "",
        "Sloupec „95% interval“ říká, kde se skutečná odezva segmentu nachází. "
        "Dokud se intervaly dvou oborů překrývají, rozdíl mezi nimi je šum a "
        "nemá cenu podle něj přesouvat kapacitu. ▲/▼ značí segment, který se "
        "od celkového průměru odlišuje průkazně.",
        "",
        "## ⚠️ Než z toho začneš vyvozovat závěry",
        "",
        "**Odpovědi se dopočítávají z pošty jen 60 dní zpět** "
        "(`sync_replies` v `check_followups.py`). Cokoli staršího nemá odpovědi "
        "spočítané, i kdyby přišly – vypadá to pak jako propadák, přitom jde jen "
        "o díru v měření. Rozdíly mezi měsíci proto neber vážně, dokud se "
        "historie nedopočítá: `check_followups.py --sync-only --reply-window-days 250`.",
        "",
        "Totéž platí pro A/B varianty: zapisovat se začaly až 3. 8. 2026, "
        "u starších mailů je sloupec prázdný.",
        "",
    ]

    znacky = data.get("kde_znacky", {})
    nalezene = {k: dict(v) for k, v in znacky.items() if v}
    if nalezene:
        r += ["Značky trackeru nalezeny ve sloupcích: "
              + "; ".join(f"**{typ}** → {v}" for typ, v in nalezene.items()), ""]
    else:
        r += ["Značky trackeru (`klik …`, `pixel …`) se v databázi nenašly vůbec – "
              "buď tracker nezapisuje, nebo píše jinam, než se hledá.", ""]

    r += tabulka("Podle oboru", data["podle"]["obor"], min_vzorek, odezva)
    r += tabulka("Podle A/B varianty předmětu", data["podle"]["varianta"], min_vzorek, odezva)
    r += tabulka("Podle měsíce odeslání", data["podle"]["mesic"], min_vzorek, odezva)
    r += tabulka("Podle města (20 největších)", data["podle"]["mesto"], min_vzorek, odezva, limit=20)

    if data["bez_oboru"]:
        r += [
            f"> Pozn.: {data['bez_oboru']} odeslaných kontaktů nemá vyplněné odvětví "
            "(pochází z doby, kdy pipeline jela jen na restaurace).",
            "",
        ]
    return "\n".join(x for x in r if x != "")


def main():
    p = argparse.ArgumentParser(description="Analýza výsledků outreachu")
    p.add_argument("--out", default="", help="Zapsat report i do souboru")
    p.add_argument("--min-vzorek", type=int, default=100,
                   help="Od kolika odeslaných mailů brát odezvu segmentu vážně (default 100)")
    args = p.parse_args()

    hlavicky, radky = nacti_radky()
    if not hlavicky:
        print("Sheet je prázdný.")
        return 1

    report = sestav_report(analyzuj(hlavicky, radky), args.min_vzorek)
    print(report)

    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report + "\n")
        print(f"\nUloženo do {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
