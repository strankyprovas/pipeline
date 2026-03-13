"""
Smaže staré pension drafty s chybnou URL a vygeneruje nové správné.
"""
import sys
sys.path.insert(0, "/root/restaurant-outreach")

from ai_email import generate_ai_email
from gmail_draft import create_draft, get_gmail_service as gmail_service

# Data penzionů z dnešního runu
PENZIONY = [
    {
        "name": "Pension Beránek",
        "slug": "pension-beranek",
        "email": "pension.beranek@tiscali.cz",
        "website": "http://www.pensionberanek.cz/",
        "pagespeed": 35,
        "category": "spatny_web",
        "address": "Praha",
        "city_real": "Praha",
        "reasons": ["❌ Chybí viewport meta – nefunguje na mobilu"],
        "industry": "penzion",
        "rating": 0, "reviews_count": 0, "phone": "",
        "draft_id": "19cb284a1d441317",
    },
    {
        "name": "Penzion Palouček",
        "slug": "penzion-paloucek",
        "email": "info@penzionpaloucek.cz",
        "website": "http://www.penzionpaloucek.cz/",
        "pagespeed": 60,
        "category": "spatny_web",
        "address": "Praha 4",
        "city_real": "Praha 4",
        "reasons": ["~ jQuery 3.x nalezen", "~ Bootstrap detekován"],
        "industry": "penzion",
        "rating": 0, "reviews_count": 0, "phone": "",
        "draft_id": "19cb284f911f22e3",
    },
    {
        "name": "ARTHARMONY Pension & Hostel",
        "slug": "artharmony-pension-hostel",
        "email": "info@artharmony.cz",
        "website": "http://www.artharmony.cz/",
        "pagespeed": 30,
        "category": "spatny_web",
        "address": "Praha",
        "city_real": "Praha",
        "reasons": ["❌ Copyright rok 2000 – starý web", "❌ Starý jQuery 1.12"],
        "industry": "penzion",
        "rating": 0, "reviews_count": 0, "phone": "",
        "draft_id": "19cb2852ffa6d6fb",
    },
    {
        "name": "Pension VĚTRNÝ MLÝN",
        "slug": "pension-vetrny-mlyn-ubytovani-praha-windmill-b-b-accommodation-prague",
        "email": "alex@pensionmlyn.cz",
        "website": "http://www.penzionmlynpraha.cz/",
        "pagespeed": 55,
        "category": "spatny_web",
        "address": "Praha 6",
        "city_real": "Praha 6",
        "reasons": ["❌ Starý jQuery 1.10 – zastaralý kód"],
        "industry": "penzion",
        "rating": 0, "reviews_count": 0, "phone": "",
        "draft_id": "19cb285b03c6b46d",
    },
    {
        "name": "Pension Milk Inn",
        "slug": "pension-milk-inn",
        "email": "info@pensionmilkinn.cz",
        "website": "http://www.pensionmilkinn.cz/",
        "pagespeed": 15,
        "category": "spatny_web",
        "address": "Praha",
        "city_real": "Praha",
        "reasons": ["❌ Chybí viewport meta – nefunguje na mobilu"],
        "industry": "penzion",
        "rating": 0, "reviews_count": 0, "phone": "",
        "draft_id": "19cb285dae666dad",
    },
    {
        "name": "Pension Březina",
        "slug": "pension-brezina",
        "email": "info@brezina.cz",
        "website": "http://www.brezina.cz/",
        "pagespeed": 50,
        "category": "spatny_web",
        "address": "Praha",
        "city_real": "Praha",
        "reasons": ["❌ Copyright rok 2019 – starý web"],
        "industry": "penzion",
        "rating": 0, "reviews_count": 0, "phone": "",
        "draft_id": "19cb28792ca2b614",
    },
]

PAGES_BASE = "https://strankyprovas.github.io/penzion"

def delete_draft(service, draft_id):
    try:
        service.users().drafts().delete(userId="me", id=draft_id).execute()
        print(f"  🗑️  Draft {draft_id} smazán")
    except Exception as e:
        print(f"  ⚠️  Nelze smazat {draft_id}: {e}")

def main():
    service = gmail_service()

    for p in PENZIONY:
        print(f"\n[{p['name']}]")
        demo_url = f"{PAGES_BASE}/{p['slug']}/"

        # Smaž starý draft
        delete_draft(service, p["draft_id"])

        # Vygeneruj nový email
        try:
            email_data = generate_ai_email(p, demo_url=demo_url, city=p["city_real"])
            create_draft(
                to_email=p["email"],
                subject=email_data["subject"],
                body_plain=email_data["body"],
                body_html=email_data["html_body"],
            )
            print(f"  ✅ Nový draft vytvořen → {demo_url}")
        except Exception as e:
            print(f"  ❌ Chyba: {e}")

    print("\n✅ Hotovo!")

if __name__ == "__main__":
    main()
