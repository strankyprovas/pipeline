#!/usr/bin/env python3
"""Příjem faktur e-mailem pro aplikaci na schvalování faktur.

Přečte schránku faktury@strankyprovas.cz, u každého nového mailu vezme přílohu
(PDF nebo fotku), nechá z ní vytěžit údaje a pošle je do aplikace, která fakturu
založí té firmě, které patří adresa odesílatele.

Proč takhle: klíč k modelu je v GitHub Secrets, ne na webhostingu, takže čtení
i vytěžování běží tady a aplikace dostane hotová data přes své API.

Spouští se z GitHub Actions (workflow prijem_faktur.yml), ručně:
    python3 prijem_faktur.py --dry-run
"""
import argparse
import base64
import email
import imaplib
import json
import os
import re
import sys
from email.header import decode_header, make_header

IMAP_SERVER = os.environ.get("FAKTURY_IMAP", "wes1-imap.wedos.net")
IMAP_USER = os.environ.get("FAKTURY_USER", "")
IMAP_PASS = os.environ.get("FAKTURY_PASS", "")
APP_URL = os.environ.get("FAKTURY_APP", "https://strankyprovas.cz/schvalovani-demo/")
APP_KLIC = os.environ.get("FAKTURY_KLIC", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

PRIPONY = (".pdf", ".jpg", ".jpeg", ".png")
MAX_MB = 9


def hlavicka(raw):
    """Dekóduje hlavičku do čitelného textu."""
    try:
        return str(make_header(decode_header(raw or "")))
    except Exception:
        return raw or ""


def adresa_z(odesilatel):
    m = re.search(r"[\w.+-]+@[\w.-]+\.\w+", odesilatel or "")
    return m.group(0).lower() if m else ""


def vytez(data, nazev, predmet):
    """Z přílohy vytáhne údaje faktury. Vrací slovník, i když se něco nepovede."""
    prazdne = {"dodavatel": "", "ico": "", "castka": "", "vs": "", "ucet": "", "splatnost": ""}
    if not ANTHROPIC_API_KEY:
        print("      ⚠️  chybí ANTHROPIC_API_KEY — fakturu založím bez údajů")
        return prazdne
    try:
        import anthropic
    except ImportError:
        print("      ⚠️  chybí knihovna anthropic")
        return prazdne

    je_pdf = nazev.lower().endswith(".pdf")
    blok = {
        "type": "document" if je_pdf else "image",
        "source": {
            "type": "base64",
            "media_type": "application/pdf" if je_pdf else (
                "image/png" if nazev.lower().endswith(".png") else "image/jpeg"),
            "data": base64.b64encode(data).decode(),
        },
    }
    pokyn = (
        "Z přiložené faktury vytáhni údaje a vrať JEN JSON bez komentáře, v tomto tvaru:\n"
        '{"dodavatel":"","ico":"","castka":"","vs":"","ucet":"","splatnost":""}\n\n'
        "Pravidla:\n"
        "- dodavatel = kdo fakturu vystavil (ne odběratel)\n"
        "- ico = IČO dodavatele, jen číslice\n"
        "- castka = celková částka k úhradě včetně DPH, jen číslo s tečkou (např. 12500.00)\n"
        "- vs = variabilní symbol, jen číslice\n"
        "- ucet = číslo účtu dodavatele ve tvaru 123456789/0100, nebo IBAN\n"
        "- splatnost = datum splatnosti ve tvaru RRRR-MM-DD\n"
        "Co na faktuře není, nech jako prázdný řetězec. Nic si nedomýšlej.\n"
        f"Předmět e-mailu pro kontext: {predmet}"
    )
    try:
        klient = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        odpoved = klient.messages.create(
            model="claude-haiku-5-5",
            max_tokens=600,
            messages=[{"role": "user", "content": [blok, {"type": "text", "text": pokyn}]}],
        )
        text = "".join(b.text for b in odpoved.content if getattr(b, "type", "") == "text")
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            return prazdne
        udaje = json.loads(m.group(0))
        return {k: str(udaje.get(k, "") or "").strip() for k in prazdne}
    except Exception as e:
        print(f"      ⚠️  vytěžení selhalo: {type(e).__name__}: {str(e)[:120]}")
        return prazdne


def posli_do_aplikace(udaje, odesilatel, predmet, data, nazev):
    import requests
    telo = dict(udaje)
    telo.update({
        "odesilatel": odesilatel,
        "predmet": predmet,
        "soubor_nazev": nazev,
        "soubor_base64": base64.b64encode(data).decode(),
    })
    r = requests.post(APP_URL, params={"api": "faktura", "klic": APP_KLIC},
                      json=telo, timeout=60)
    return r.status_code, (r.text or "")[:200]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="jen vypsat, nic neodesílat ani neoznačovat")
    ap.add_argument("--limit", type=int, default=20)
    args = ap.parse_args()

    # Dokud není schránka založená a přístupy uložené, jen tiše skončíme —
    # workflow běží každou půlhodinu a nemá smysl kvůli tomu hlásit chybu.
    if not (IMAP_USER and IMAP_PASS):
        print("⏭️  Schránka na faktury zatím není nastavená (FAKTURY_USER / FAKTURY_PASS) — přeskakuji.")
        return 0
    if not APP_KLIC and not args.dry_run:
        print("⏭️  Chybí FAKTURY_KLIC (klíč k API aplikace) — přeskakuji.")
        return 0

    posta = imaplib.IMAP4_SSL(IMAP_SERVER)
    posta.login(IMAP_USER, IMAP_PASS)
    posta.select("INBOX")
    typ, data = posta.search(None, "UNSEEN")
    cisla = data[0].split()[: args.limit] if data and data[0] else []
    print(f"📬 Nepřečtených mailů: {len(cisla)}")

    hotovo = preskoceno = 0
    for cislo in cisla:
        typ, syrove = posta.fetch(cislo, "(RFC822)")
        if typ != "OK" or not syrove or not syrove[0]:
            continue
        zprava = email.message_from_bytes(syrove[0][1])
        odesilatel = adresa_z(hlavicka(zprava.get("From")))
        predmet = hlavicka(zprava.get("Subject"))
        print(f"\n✉️  od {odesilatel}: {predmet[:60]}")

        prilohy = []
        for cast in zprava.walk():
            nazev = hlavicka(cast.get_filename())
            if not nazev or not nazev.lower().endswith(PRIPONY):
                continue
            obsah = cast.get_payload(decode=True)
            if obsah and len(obsah) <= MAX_MB * 1024 * 1024:
                prilohy.append((nazev, obsah))

        if not prilohy:
            print("      ⏭️  bez přílohy (PDF/foto) — přeskakuji, mail nechávám nepřečtený")
            preskoceno += 1
            continue

        for nazev, obsah in prilohy:
            print(f"      📄 {nazev} ({len(obsah)//1024} kB)")
            udaje = vytez(obsah, nazev, predmet)
            print(f"         → {udaje.get('dodavatel') or '(dodavatel nerozpoznán)'}, "
                  f"{udaje.get('castka') or '?'} Kč, VS {udaje.get('vs') or '?'}, "
                  f"splatnost {udaje.get('splatnost') or '?'}")
            if args.dry_run:
                continue
            kod, odpoved = posli_do_aplikace(udaje, odesilatel, predmet, obsah, nazev)
            if kod == 200:
                print(f"         ✅ založeno: {odpoved}")
                hotovo += 1
            else:
                print(f"         ❌ aplikace vrátila {kod}: {odpoved}")
                preskoceno += 1

        if not args.dry_run:
            posta.store(cislo, "+FLAGS", "\\Seen")

    posta.logout()
    print(f"\nHotovo. Založeno {hotovo}, přeskočeno {preskoceno}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
