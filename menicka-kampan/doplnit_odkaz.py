#!/usr/bin/env python3
"""
Doplní do už vytvořených pilotních draftů odkaz na strankyprovas.cz/restaurace.

Bere jen drafty, které pořád existují — část vlny už je odeslaná a ty se
pochopitelně měnit nedají. Upravuje se podle e-mailu adresáta, obsah se
skládá znovu z pilot-100.csv, takže se nic neztratí ani nerozhodí.
"""
import base64, csv, os, sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr

SEM = os.path.dirname(os.path.abspath(__file__))
KOREN = os.path.dirname(SEM)
sys.path.insert(0, KOREN)

from gmail_draft import get_gmail_service        # noqa: E402
from config import SENDER_EMAIL, SENDER_NAME, REPLY_TO  # noqa: E402
import generuj_drafty as gen                     # noqa: E402

ODKAZ = 'https://strankyprovas.cz/restaurace/'

DOVETEK_PLAIN = f"""
A kdybyste si chtěl nejdřív projít, co pro restaurace děláme a jak to celé funguje, sepsali jsme to tady:
→ {ODKAZ}
"""

DOVETEK_HTML = f"""<p>A kdybyste si chtěl nejdřív projít, co pro restaurace děláme a jak to celé funguje, sepsali jsme to tady:<br>
→ <a href="{ODKAZ}">strankyprovas.cz/restaurace</a></p>"""


def s_odkazem_plain(nazev, demo):
    t = gen.telo_plain(nazev, demo)
    return t.replace('\nCO TO STOJÍ\n', DOVETEK_PLAIN + '\nCO TO STOJÍ\n')


def s_odkazem_html(nazev, demo, slug):
    t = gen.telo_html(nazev, demo, slug)
    return t.replace('<p><strong>Co to stojí</strong>', DOVETEK_HTML + '\n<p><strong>Co to stojí</strong>')


def main():
    radky = {r['email'].strip().lower(): r
             for r in csv.DictReader(open(os.path.join(SEM, 'pilot-100.csv'), encoding='utf-8'))
             if r.get('email')}

    service = get_gmail_service()

    # posbírat všechny drafty (stránkovaně)
    drafty, token = [], None
    while True:
        odp = service.users().drafts().list(userId='me', maxResults=500,
                                            pageToken=token).execute()
        drafty.extend(odp.get('drafts', []))
        token = odp.get('nextPageToken')
        if not token:
            break
    print(f'draftů v účtu celkem: {len(drafty)}')

    upraveno, nenalezeno = 0, 0
    for d in drafty:
        plny = service.users().drafts().get(userId='me', id=d['id'],
                                            format='metadata').execute()
        hlavicky = {h['name'].lower(): h['value']
                    for h in plny['message']['payload'].get('headers', [])}
        komu = hlavicky.get('to', '')
        predmet = hlavicky.get('subject', '')

        if predmet != gen.PREDMET:
            continue
        adresa = komu.split('<')[-1].strip('> ').lower()
        r = radky.get(adresa)
        if not r:
            nenalezeno += 1
            continue

        nazev, demo = r['nazev'].strip(), r['demo'].strip()
        slug = gen.slug_z_dema(demo)

        msg = MIMEMultipart('alternative')
        msg['To'] = adresa
        msg['From'] = formataddr((str(Header(SENDER_NAME, 'utf-8')), SENDER_EMAIL))
        msg['Subject'] = gen.PREDMET
        if REPLY_TO:
            msg['Reply-To'] = REPLY_TO
        msg.attach(MIMEText(s_odkazem_plain(nazev, demo), 'plain', 'utf-8'))
        msg.attach(MIMEText(s_odkazem_html(nazev, demo, slug), 'html', 'utf-8'))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().drafts().update(
            userId='me', id=d['id'], body={'message': {'raw': raw}}).execute()
        upraveno += 1
        print(f'  ✅ {nazev} — {adresa}', flush=True)

    print(f'\nHOTOVO: upraveno {upraveno} draftů')
    if nenalezeno:
        print(f'  (na {nenalezeno} draftů s tímhle předmětem jsem neměl řádek v CSV)')
    print(f'  odesláno dřív, a proto neupraveno: {len(radky) - upraveno - 1} '
          f'(mínus Sport Babice, který se generoval ručně)')


if __name__ == '__main__':
    main()
