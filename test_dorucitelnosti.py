#!/usr/bin/env python3
"""Zkouška doručitelnosti: z KAŽDÉ odesílací schránky pošle jeden mail na zadané adresy.

Slouží k ověření, kam maily padají (doručená / spam) a jestli sedí SPF, DKIM
a DMARC — v Gmailu přes „Zobrazit originál". Nesahá na Google token, jede jen
přes M365 SMTP, takže nepotřebuje zámek `google-oauth-token`.

    python3 test_dorucitelnosti.py --komu a@gmail.com,b@seznam.cz
"""
import argparse
import os
import smtplib
import sys
import time
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid


def schranky():
    """Unikátní (user, heslo) ze stejných secretů, jaké používá send_drafts.py."""
    ucty, videne = [], set()
    u, p = os.environ.get("M365_SMTP_USER"), os.environ.get("M365_SMTP_PASS")
    if u and p:
        ucty.append((u, p)); videne.add(u.lower())
    for kus in os.environ.get("M365_ACCOUNTS", "").split("|"):
        casti = kus.strip().split(":")
        if len(casti) >= 3 and casti[-1].strip().isdigit():
            casti = casti[:-1]          # poslední díl je váha v rotaci
        if len(casti) < 2:
            continue
        u, p = casti[0].strip(), ":".join(casti[1:])
        if u and p and u.lower() not in videne:
            ucty.append((u, p)); videne.add(u.lower())
    return ucty


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--komu", required=True, help="adresy příjemců oddělené čárkou")
    args = ap.parse_args()
    komu = [a.strip() for a in args.komu.split(",") if "@" in a]
    ucty = schranky()
    if not ucty or not komu:
        print("Chybí odesílací schránky (secrets) nebo příjemci.")
        return 1

    chyb = 0
    for user, pwd in ucty:
        for adresa in komu:
            telo = (
                "Dobrý den,\n\n"
                f"tohle je zkušební zpráva odeslaná ze schránky {user}.\n"
                "Slouží jen k ověření, že pošta z této adresy dorazí v pořádku.\n\n"
                "Hezký den\nMatyáš Vrba\nStránkyProVás\n"
            )
            msg = MIMEText(telo, "plain", "utf-8")
            msg["Subject"] = f"Zkouška doručení ze schránky {user}"
            msg["From"] = f"Matyáš Vrba <{user}>"
            msg["To"] = adresa
            msg["Reply-To"] = os.environ.get("M365_REPLY_TO", "matyas@strankyprovas.cz")
            msg["Date"] = formatdate(localtime=False)
            msg["Message-ID"] = make_msgid(domain=user.split("@")[-1])
            try:
                with smtplib.SMTP("smtp.office365.com", 587, timeout=60) as smtp:
                    smtp.ehlo(); smtp.starttls(); smtp.ehlo()
                    smtp.login(user, pwd)
                    smtp.send_message(msg)
                print(f"✉️  {user}: odesláno")
            except Exception as e:
                chyb += 1
                print(f"❌ {user}: {type(e).__name__}: {str(e)[:160]}")
            time.sleep(8)
    print(f"Hotovo. Schránek: {len(ucty)}, příjemců: {len(komu)}, chyb: {chyb}.")
    return 1 if chyb else 0


if __name__ == "__main__":
    sys.exit(main())
