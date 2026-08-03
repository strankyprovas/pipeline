"""
Follow-up reminder – zkontroluje Sheet a ukáže komu napsat znovu.

Použití:
    venv/bin/python3 check_followups.py           # výpis do terminálu
    venv/bin/python3 check_followups.py --draft   # vytvoří Gmail drafty follow-up emailů
    venv/bin/python3 check_followups.py --send    # rovnou odešle follow-upy (pro cron)
    venv/bin/python3 check_followups.py --days 7  # čekej 7 dní místo 5
"""
import argparse
import base64
import os
import time
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    import anthropic
except ImportError:
    # AI personalizace je vypnutá (organizace bez kreditů), takže balíček
    # v Actions neinstalujeme. Bez tohohle obalu spadl celý follow-up běh
    # na ModuleNotFoundError ještě před prvním řádkem práce.
    anthropic = None
from sheets import get_or_create_sheet, HEADERS, mark_followup_sent
from gmail_draft import create_draft, get_gmail_service
from email_template import SENDER_NAME, SENDER_COMPANY, SENDER_WEBSITE

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


def sync_replies(sheet) -> int:
    """
    Prohledá Gmail inbox a označí v Sheetu kontakty, od kterých přišla odpověď.
    Vrátí počet nově označených odpovědí.
    """
    try:
        records = sheet.get_all_records()
    except Exception as e:
        print(f"❌ Chyba čtení Sheetu: {e}")
        return 0

    # Emaily které jsou osloveno nebo follow_up_odesl a ještě neodpověděly
    pending = {
        r["Email"].lower(): i + 2  # +2 = 1 pro header + 1 pro 0-index
        for i, r in enumerate(records)
        if r.get("Stav", "").strip() in ("osloveno", "follow_up_odesl")
        and not r.get("Odpověděl", "").strip()
        and r.get("Email", "").strip()
    }

    if not pending:
        return 0

    try:
        service = get_gmail_service()
    except Exception as e:
        print(f"⚠️  Gmail API nedostupné: {e}")
        return 0

    updated = 0
    odpov_col = HEADERS.index("Odpověděl") + 1
    stav_col = HEADERS.index("Stav") + 1

    for email_addr, row_idx in pending.items():
        try:
            # Hledej zprávy OD tohoto emailu v inboxu
            query = f"from:{email_addr} in:inbox"
            result = service.users().messages().list(
                userId="me", q=query, maxResults=1
            ).execute()
            if result.get("messages"):
                sheet.update_cell(row_idx, odpov_col, "ano")
                sheet.update_cell(row_idx, stav_col, "odpověděl")
                print(f"  ✅ Odpověď od: {email_addr}")
                updated += 1
        except Exception:
            pass

    return updated


def get_followup_candidates(sheet, days: int = 5, max_days: int = 30) -> list[dict]:
    """
    Vrátí seznam kontaktů kde:
    - Stav = 'osloveno' (follow-up ještě nebyl poslán)
    - Datum emailu je starší než `days` dní, ale zároveň mladší než `max_days`
    - Odpověděl = prázdné

    Horní hranice je důležitá: follow-up text mluví o „nedávno zaslané ukázce",
    takže kontaktu z března by tvrdil nepravdu. V DB je přes 14 000 starých
    kontaktů, bez `max_days` by se první běh pokusil oslovit všechny.
    """
    try:
        records = sheet.get_all_records()
    except Exception as e:
        print(f"❌ Chyba čtení Sheetu: {e}")
        return []

    cutoff = datetime.now() - timedelta(days=days)
    oldest = datetime.now() - timedelta(days=max_days)
    candidates = []

    for r in records:
        stav = r.get("Stav", "").strip()
        # Pouze "osloveno" – ti co dostali follow-up (follow_up_odesl) nebo odpověděli se přeskakují
        if stav != "osloveno":
            continue
        if r.get("Odpověděl", "").strip():
            continue

        datum_str = r.get("Datum emailu", "").strip()
        if not datum_str:
            continue

        try:
            fmt = "%d.%m.%Y %H:%M" if " " in datum_str else "%d.%m.%Y"
            datum = datetime.strptime(datum_str, fmt)
        except ValueError:
            continue

        if datum < cutoff and datum >= oldest:
            days_ago = (datetime.now() - datum).days
            candidates.append({
                "name":     r.get("Název", ""),
                "email":    r.get("Email", ""),
                "demo_url": r.get("Demo URL", ""),
                "industry": r.get("Odvětví", "restaurace"),
                "sent":     datum_str,
                "days_ago": days_ago,
                "opened":   r.get("Otevřel email", ""),
            })

    # Seřaď od nejstaršího
    candidates.sort(key=lambda x: x["days_ago"], reverse=True)
    return candidates


def _generate_ai_followup(contact: dict) -> tuple[str, str] | None:
    """Vygeneruje AI follow-up text přes Claude Haiku. Vrátí (plain, html) nebo None."""
    if not ANTHROPIC_API_KEY or anthropic is None:
        return None

    name = contact["name"]
    demo_url = contact["demo_url"]
    opened = contact["opened"]
    days_ago = contact["days_ago"]
    industry = contact.get("industry", "restaurace")

    opener_hint = (
        "Víš, že příjemce email otevřel (máš tracking pixel). Zmínit to přirozeně."
        if opened else
        f"Příjemce se pravděpodobně nedostal k emailu (odeslán před {days_ago} dny)."
    )

    prompt = f"""Napiš krátký follow-up cold email (max 3 věty) v češtině.

Kontext:
- Jsi Matyáš Vrba z firmy StránkyProVás (webdesign)
- Před {days_ago} dny jsi podniku "{name}" ({industry}) poslal/a nabídku s demo webem
- Demo stránka: {demo_url}
- {opener_hint}

Požadavky:
- Začni "Dobrý den," pak prázdný řádek, pak tělo
- Maximálně 3 věty – krátké, přátelské, nenásilné
- Zmínit demo URL s šipkou →
- Podpis NEVKLÁDEJ (bude přidán automaticky)
- Tón: přátelský, bez tlaku

Napiš jen tělo emailu."""

    try:
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=250,
            messages=[{"role": "user", "content": prompt}],
        )
        ai_text = message.content[0].text.strip()

        plain = ai_text + f"\n\nS pozdravem,\n{SENDER_NAME}\n\n--\n{SENDER_NAME}\n{SENDER_COMPANY} | {SENDER_WEBSITE}"

        html_body = ai_text.replace("\n", "<br>")
        if demo_url:
            html_body = html_body.replace(demo_url, f'<a href="{demo_url}">{demo_url}</a>')
        html = f"""<div style="font-family: Arial, sans-serif; font-size: 15px; line-height: 1.6; color: #222;">
<p>{html_body}</p>
<p style="color:#888; font-size:13px;">--<br>{SENDER_NAME}<br>{SENDER_COMPANY} | <a href="{SENDER_WEBSITE}">{SENDER_WEBSITE}</a></p>
</div>"""

        return plain, html
    except Exception as e:
        print(f"  ⚠️  AI follow-up selhal ({e}), použiji fallback")
        return None


def make_followup_body(contact: dict) -> tuple[str, str, str]:
    """Vrátí (subject, plain_body, html_body) pro follow-up email."""
    name = contact["name"]
    demo_url = contact["demo_url"]
    opened = contact["opened"]

    subject = f"Připomínám – demo stránka pro {name}"

    # Zkus AI personalizaci
    ai_result = _generate_ai_followup(contact)
    if ai_result:
        plain, html = ai_result
        return subject, plain, html

    # Fallback – statická šablona
    if opened:
        opener = f"Vidím, že jste se na email podíval/a – možná vás zaujal."
    else:
        opener = f"Před pár dny jsem vám posílal ukázku webu pro {name}."

    plain = (
        f"Dobrý den,\n\n"
        f"{opener}\n\n"
        f"Chtěl jsem se jen ujistit, že vám zpráva nezapadla. "
        f"Demo stránka je stále k dispozici:\n"
        f"→ {demo_url}\n\n"
        f"Pokud máte zájem nebo otázky, stačí odpovědět. "
        f"Pokud ne, žádný problém – jen dejte vědět a nebudu dále obtěžovat.\n\n"
        f"Hezký den,\n{SENDER_NAME}\n{SENDER_COMPANY}"
    )

    demo_link = f'<a href="{demo_url}">{demo_url}</a>' if demo_url else ""
    html = f"""<div style="font-family: Arial, sans-serif; font-size: 15px; line-height: 1.6; color: #222;">
<p>Dobrý den,</p>
<p>{opener}</p>
<p>Chtěl jsem se jen ujistit, že vám zpráva nezapadla.
Demo stránka je stále k dispozici:<br>→ {demo_link}</p>
<p>Pokud máte zájem nebo otázky, stačí odpovědět.
Pokud ne, žádný problém – jen dejte vědět a nebudu dále obtěžovat.</p>
<p>Hezký den,<br>{SENDER_NAME}<br><small style="color:#888">{SENDER_COMPANY}</small></p>
</div>"""

    return subject, plain, html


def _send_email_now(service, to_email: str, subject: str, body_plain: str, body_html: str):
    """Odešle email přímo přes Gmail API (bez draftu)."""
    msg = MIMEMultipart("alternative")
    msg["To"] = to_email
    msg["From"] = f"{SENDER_NAME} <me>"
    msg["Subject"] = subject
    msg.attach(MIMEText(body_plain, "plain", "utf-8"))
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Follow-up reminder")
    parser.add_argument("--draft", action="store_true",
                        help="Vytvoř Gmail drafty pro follow-up emaily")
    parser.add_argument("--send", action="store_true",
                        help="Rovnou odešli follow-up emaily (pro automatický cron)")
    parser.add_argument("--days", type=int, default=5,
                        help="Počet dní čekání před follow-up (default: 5)")
    parser.add_argument("--max-days", type=int, default=30,
                        help="Nejstarší kontakt k oslovení – starším by text lhal (default: 30)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Max. počet follow-upů za běh (0 = bez omezení)")
    parser.add_argument("--delay", type=int, default=30,
                        help="Prodleva mezi emaily v sekundách při --send (default: 30)")
    args = parser.parse_args()

    print("📊 Připojuji Google Sheet...")
    sheet = get_or_create_sheet()

    print("📬 Synchronizuji odpovědi z Gmailu...")
    new_replies = sync_replies(sheet)
    if new_replies:
        print(f"  🎉 {new_replies} nových odpovědí zaznamenáno do Sheetu\n")
    else:
        print(f"  (žádné nové odpovědi)\n")

    print(f"🔍 Hledám kontakty oslovené před {args.days}–{args.max_days} dny bez odpovědi...\n")
    candidates = get_followup_candidates(sheet, days=args.days, max_days=args.max_days)
    if args.limit and len(candidates) > args.limit:
        print(f"   (nalezeno {len(candidates)}, beru prvních {args.limit})")
        candidates = candidates[:args.limit]

    if not candidates:
        print("✅ Žádné follow-upy k řešení – všechno je aktuální.")
    else:
        print(f"📬 Nalezeno {len(candidates)} kontaktů k follow-up:\n")
        for c in candidates:
            opened_info = f" 👁️ otevřel {c['opened']}" if c["opened"] else ""
            print(f"  • {c['name']} <{c['email']}> – odesláno před {c['days_ago']} dny{opened_info}")

        if args.send:
            print(f"\n🚀 Odesílám follow-up emaily (prodleva {args.delay}s)...\n")
            try:
                service = get_gmail_service()
            except Exception as e:
                print(f"❌ Gmail API nedostupné: {e}")
                exit(1)

            sent = 0
            for c in candidates:
                try:
                    subject, plain, html = make_followup_body(c)
                    _send_email_now(service, c["email"], subject, plain, html)
                    mark_followup_sent(sheet, c["email"])
                    print(f"  ✅ [{datetime.now().strftime('%H:%M:%S')}] Odesláno → {c['email']} | {c['name']}")
                    sent += 1
                    if sent < len(candidates):
                        time.sleep(args.delay)
                except Exception as e:
                    print(f"  ⚠️  Chyba pro {c['name']}: {e}")

            print(f"\n✅ Hotovo: {sent} follow-up emailů odesláno")

        elif args.draft:
            print(f"\n✍️  Vytvářím Gmail drafty...\n")
            created = 0
            for c in candidates:
                try:
                    subject, plain, html = make_followup_body(c)
                    create_draft(
                        to_email=c["email"],
                        subject=subject,
                        body_plain=plain,
                        body_html=html,
                    )
                    print(f"  📨 Draft vytvořen: {c['name']}")
                    created += 1
                except Exception as e:
                    print(f"  ⚠️  Chyba pro {c['name']}: {e}")
            print(f"\n✅ Hotovo: {created} follow-up draftů vytvořeno")

        else:
            print(f"\nTip: spusť s --send pro automatické odeslání, nebo --draft pro Gmail drafty")
