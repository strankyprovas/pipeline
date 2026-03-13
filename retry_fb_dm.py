"""
Retry skript – pošle FB DM podnikům kde to minule selhalo.
Použití: venv/bin/python3 retry_fb_dm.py
"""
from facebook_dm import send_facebook_dm

DEMO_BASE = "https://strankyprovas.github.io/restaurace"

FAILED = [
    ("Little Saigon Brno",       "https://www.facebook.com/littlesaigonbrno/",                                      "little-saigon-brno",         "Brně"),
    ("Bonjour Vietnam",           "https://www.facebook.com/Bonjour-Vietnam-100107981688480",                         "bonjour-vietnam",            "Brně"),
    ("Hostinec U Bláhovky",       "https://www.facebook.com/ublahovky/",                                              "hostinec-u-blahovky",        "Brně"),
    ("Little Vietnam",            "https://www.facebook.com/littlevietnambistro/",                                    "little-vietnam",             "Ostravě"),
    ("Restaurace Dáma Pyková",    "https://www.facebook.com/D%C3%A1ma-Pykov%C3%A1-Restaurant-1403673229907011/",      "restaurace-dama-pykova-rodinn-a-firemni-oslavy-letni-zahrada-skvela-kuchyne", "Ostravě"),
    ("Simba Restaurant",          "https://www.facebook.com/profile.php?id=61567068615572",                           "simba-restaurant",           "Liberci"),
    ("Restaurace Kotelna",        "https://www.facebook.com/restauracekotelnalbc/",                                   "restaurace-kotelna",         "Liberci"),
    ("Bistro Mercato per tutti",  "https://www.facebook.com/profile.php?id=61553319097380",                           "bistro-mercato-per-tutti",   "Olomouci"),
    ("Restaurace U Anči",         "https://www.facebook.com/restauraceuanci/",                                        "restaurace-u-anci",          "Olomouci"),
    ("Restaurace Bohemia",        "https://www.facebook.com/profile.php?id=100063612126984",                          "restaurace-bohemia",         "Olomouci"),
]

MSG_TEMPLATE = (
    "Dobrý den,\n\n"
    "jmenuji se Matyáš Vrba a pomáhám restauracím v {city} získat více hostů přes "
    "profesionální webové stránky.\n\n"
    "Připravil jsem pro {name} ukázkové stránky zdarma – podívejte se:\n"
    "{demo_url}\n\n"
    "Pokud by vás to zajímalo, stačí odpovědět na tuto zprávu.\n\n"
    "Matyáš Vrba, StránkyProVás"
)

ok = 0
fail = 0
for name, fb_url, slug, city in FAILED:
    demo_url = f"{DEMO_BASE}/{slug}/"
    message = MSG_TEMPLATE.format(name=name, city=city, demo_url=demo_url)
    print(f"\n🔁 {name}")
    success = send_facebook_dm(fb_url, message, headless=True)
    if success:
        ok += 1
    else:
        fail += 1

print(f"\n{'='*40}")
print(f"✅ Odesláno: {ok}  ❌ Selhalo: {fail}")
