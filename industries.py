"""
Konfigurace odvětví pro outreach pipeline.
Každé odvětví má vlastní vyhledávací dotaz, Google Places typ,
texty pro emaily a texty pro demo stránku.
"""

INDUSTRIES = {
    "restaurace": {
        "name_cs": "restaurace",          # pro email CTA "Pracujeme s restauracemi..."
        "name_cs_4": "restauraci",         # akuzativ – "nemáte web pro restauraci"
        "search_query": "restaurace {city}",
        "places_type": "restaurant",
        "osm_filter": '["amenity"="restaurant"]',
        "email_problem_no_web": (
            "nemáte vlastní webové stránky – přitom 70 % lidí hledá restauraci "
            "online ještě před tím, než vyjde z domu"
        ),
        "email_problem_bad_web": (
            "web by mohl lépe fungovat na mobilech – přitom 70 % lidí hledá "
            "restauraci z telefonu"
        ),
        "email_cta": "Pracujeme s restauracemi {city_phrase}.",
        "taglines": [
            "Kde každé jídlo vypráví příběh",
            "Chutě, které nezapomenete",
            "Poctivá kuchyně, přátelská atmosféra",
            "Tradiční kuchyně s moderním šmrncem",
            "Vítejte u nás – jako doma",
            "Gastronomie s duší",
        ],
        "subtitles": [
            "Přijďte ochutnat autentické chutě připravené s láskou a čerstvými surovinami.",
            "Čerstvé suroviny od lokálních farmářů, recepty plné vášně a péče.",
            "Každý pokrm je výsledkem let zkušeností a lásky ke gastronomii.",
        ],
        "about_texts": [
            "Jsme rodinný podnik s vášní pro dobré jídlo a pohostinnost. Každý den připravujeme čerstvá jídla z lokálních surovin a věříme, že dobrý oběd nebo večeře je víc než jen jídlo – je to zážitek, který spojuje lidi.",
            "Naše restaurace vznikla z lásky k poctivé kuchyni. Používáme suroviny od lokálních farmářů a každý recept je výsledkem let zkušeností. Přijďte ochutnat, co to opravdu znamená dobré jídlo.",
            "V naší kuchyni se snoubí tradice s moderním přístupem. Každý pokrm připravujeme s maximální péčí a důrazem na kvalitu surovin. Těšíme se na vás!",
        ],
        "about_short": [
            "Poctivá kuchyně s důrazem na čerstvé suroviny a přátelskou atmosféru.",
            "Rodinná restaurace s láskou k dobrému jídlu.",
            "Moderní kuchyně s tradicí a duší.",
        ],
    },

    "kavarna": {
        "name_cs": "kavárny",
        "name_cs_4": "kavárnu",
        "search_query": "kavárna {city}",
        "places_type": "cafe",
        "osm_filter": '["amenity"="cafe"]',
        "email_problem_no_web": (
            "nemáte vlastní webové stránky – přitom lidé před návštěvou kavárny "
            "hledají otevírací dobu, menu a atmosféru online"
        ),
        "email_problem_bad_web": (
            "web by mohl lépe prezentovat atmosféru a menu – zákazníci se rozhodují "
            "podle online dojmu ještě doma"
        ),
        "email_cta": "Pracujeme s kavárnami {city_phrase}.",
        "taglines": [
            "Kde každý šálek chutná víc",
            "Váš druhý obývák",
            "Káva, klid a dobrá nálada",
            "Místo, kde se čas zastavuje",
            "Skvělá káva, ještě lepší atmosféra",
            "Více než jen káva – zážitek",
        ],
        "subtitles": [
            "Přijďte si odpočinout s šálkem výborné kávy a domácím dezertem.",
            "Specialty káva, čerstvé dezerty a přátelská obsluha – to jsme my.",
            "Každý šálek je připravený s péčí a láskou k dobrému kávovaru.",
        ],
        "about_texts": [
            "Jsme malá kavárna s velkým srdcem. Každý den pražíme čerstvou kávu a pečeme domácí dezerty. Věříme, že dobrá kavárna je místem, kde se lidé cítí jako doma – a ke kterému se rádi vracejí.",
            "Naše kavárna vznikla z lásky ke specialty kávě a přátelské atmosféře. Vybíráme zrna od lokálních pražíren a každý šálek připravujeme s maximální péčí. Přijďte si odpočinout a ochutnat.",
            "Milujeme kávu a lidi kolem ní. V naší kavárně najdete vždy čerstvě připravenou specialty kávu, sezónní dezerty a místo, kde si rádi sednete a zůstanete.",
        ],
        "about_short": [
            "Specialty káva a domácí dezerty v přátelské atmosféře.",
            "Vaše oblíbené místo na dobrou kávu.",
            "Malá kavárna s velkým srdcem.",
        ],
    },

    "penzion": {
        "name_cs": "penziony",
        "name_cs_4": "penzion",
        "search_query": "penzion ubytování {city}",
        "places_type": "lodging",
        "osm_filter": '["tourism"~"guest_house|hostel|hotel"]',
        "email_problem_no_web": (
            "nemáte vlastní webové stránky – přitom 90 % cestovatelů hledá ubytování "
            "online a rezervuje přes web ještě před příjezdem"
        ),
        "email_problem_bad_web": (
            "web by mohl lépe prezentovat vaše pokoje a přilákat přímé rezervace – "
            "bez provizí od Booking.com nebo Airbnb"
        ),
        "email_cta": "Pracujeme s penziony a ubytováními {city_phrase}.",
        "taglines": [
            "Váš domov daleko od domova",
            "Pohodlné ubytování v srdci regionu",
            "Odpočiňte si u nás",
            "Kde se hosté rádi vracejí",
            "Klid, pohoda a přátelská péče",
            "Ubytování s duší",
        ],
        "subtitles": [
            "Útulné pokoje, domácí snídaně a srdečná péče v každém detailu.",
            "Rodinné ubytování s přátelskou atmosférou a krásným výhledem.",
            "Pohodlné pokoje a vynikající snídaně – ideální základ pro výlety.",
        ],
        "about_texts": [
            "Jsme rodinný penzion s dlouholetou tradicí pohostinství. Naši hosté u nás nacházejí klid, útulné pokoje a domácí snídaně připravené každé ráno s láskou. Těšíme se na vás!",
            "Náš penzion stojí v klidném prostředí s výbornou dostupností do okolních atraktivit. Nabízíme útulné pokoje, bezplatné parkování a snídaně z lokálních surovin. Udělejte si radost a navštivte nás.",
            "Věříme, že dobré ubytování je základ skvělého výletu. Proto se staráme o každý detail – od pohodlných postelí po domácí snídaně a tipy na nejhezčí místní trasy.",
        ],
        "about_short": [
            "Rodinný penzion s domácí atmosférou a skvělými snídaněmi.",
            "Útulné pokoje a přátelská obsluha.",
            "Pohodlné ubytování s přátelskou péčí.",
        ],
    },

    "kosmetika": {
        "name_cs": "kosmetické salony",
        "name_cs_4": "kosmetický salon",
        "search_query": "kosmetický salon {city}",
        "places_type": "beauty_salon",
        "osm_filter": '["shop"="beauty"]',
        "email_problem_no_web": (
            "nemáte vlastní webové stránky – přitom klientky hledají kosmetický salon "
            "online a rozhodují se podle portfolia a recenzí"
        ),
        "email_problem_bad_web": (
            "web by mohl lépe prezentovat vaše služby a umožnit online rezervace – "
            "klientky to dnes očekávají"
        ),
        "email_cta": "Pracujeme s kosmetickými salony {city_phrase}.",
        "taglines": [
            "Krása je naše vášeň",
            "Péče, která proměňuje",
            "Váš salon krásy",
            "Kde se cítíte výjimečně",
            "Profesionální péče o vaši krásu",
            "Přijďte, odejdete jinak",
        ],
        "subtitles": [
            "Profesionální kosmetická péče přizpůsobená vašim potřebám.",
            "Relaxace a krása v jednom – přijďte si odpočinout a zkrásnet.",
            "Individuální přístup a prémiové produkty pro vaši pleť.",
        ],
        "about_texts": [
            "Jsme kosmetický salon s vášní pro krásu a péči o pleť. Každé ošetření přizpůsobujeme individuálním potřebám klientky a používáme pouze prémiové produkty. Naším cílem je, abyste od nás odcházely krásné a spokojené.",
            "Věříme, že péče o sebe je investice do pohody. V našem salonu najdete profesionální kosmetiku, relaxační ošetření a přátelskou atmosféru, kde se budete cítit jako doma.",
            "Náš tým zkušených kosmetiček se stará o to, aby každá návštěva byla pro vás příjemným zážitkem. Nabízíme širokou škálu ošetření přizpůsobených typu vaší pleti.",
        ],
        "about_short": [
            "Profesionální kosmetika a individuální přístup.",
            "Péče o vaši krásu s láskou a precizností.",
            "Salon krásy, kde se cítíte výjimečně.",
        ],
    },

    "kadernictvi": {
        "name_cs": "kadeřnictví",
        "name_cs_4": "kadeřnictví",
        "search_query": "kadeřnictví {city}",
        "places_type": "hair_care",
        "osm_filter": '["shop"="hairdresser"]',
        "email_problem_no_web": (
            "nemáte vlastní webové stránky – přitom zákazníci hledají kadeřnictví "
            "online, prohlíží portfolio a hledají online rezervace"
        ),
        "email_problem_bad_web": (
            "web by mohl lépe prezentovat vaše práce a umožnit jednoduchou online "
            "rezervaci – zákazníci to dnes vyžadují"
        ),
        "email_cta": "Pracujeme s kadeřnictvími {city_phrase}.",
        "taglines": [
            "Váš styl, naše vášeň",
            "Kde vlasy mluví za vás",
            "Střih, který vám sluší",
            "Proměňujeme image, měníme náladu",
            "Profesionální péče o vaše vlasy",
            "Kadeřnictví s osobním přístupem",
        ],
        "subtitles": [
            "Profesionální kadeřnické služby s individuálním přístupem ke každému zákazníkovi.",
            "Střihy, barvy a styling od zkušených kadeřníků s vášní pro krásu.",
            "Moderní techniky, prémiové produkty a přátelská atmosféra.",
        ],
        "about_texts": [
            "Jsme kadeřnictví s vášní pro vlasy a styling. Každého klienta bereme individuálně a navrhneme styl, který mu skutečně sluší. Používáme prémiové produkty a sledujeme nejnovější trendy.",
            "Naše kadeřnictví vzniklo z lásky ke kráse a transformaci. Věříme, že správný střih a barva dokáže proměnit nejen vzhled, ale i náladu. Přijďte se přesvědčit!",
            "Máme zkušený tým kadeřníků, kteří milují svou práci. Ať hledáte klasiku nebo moderní trend, najdete u nás to, co vám sedí. Těšíme se na vás!",
        ],
        "about_short": [
            "Kadeřnictví s vášní pro styl a individualitu.",
            "Profesionální střihy a barvy s osobním přístupem.",
            "Váš styl v dobrých rukou.",
        ],
    },

    "zubni": {
        "name_cs": "zubní ordinace",
        "name_cs_4": "zubní ordinaci",
        "search_query": "zubní ordinace zubař {city}",
        "places_type": "dentist",
        "osm_filter": '["amenity"="dentist"]',
        "email_problem_no_web": (
            "nemáte vlastní webové stránky – pacienti dnes hledají zubaře online "
            "a rozhodují se podle webu, než vůbec zavolají"
        ),
        "email_problem_bad_web": (
            "web by mohl lépe prezentovat vaše služby, tým a umožnit online objednání "
            "– pacienti to čím dál více očekávají"
        ),
        "email_cta": "Pracujeme se zubními ordinacemi {city_phrase}.",
        "taglines": [
            "Váš úsměv je naší prioritou",
            "Zdravé zuby, spokojený pacient",
            "Moderní stomatologie s lidským přístupem",
            "Péče o váš úsměv",
            "Kde se zubaře nebojíte",
            "Profesionální a přátelská stomatologie",
        ],
        "subtitles": [
            "Moderní zubní péče v příjemném prostředí a s přátelským přístupem.",
            "Zdravé zuby a krásný úsměv – to je náš cíl pro každého pacienta.",
            "Preventivní i estetická stomatologie s důrazem na bezbolestnost.",
        ],
        "about_texts": [
            "Jsme moderní zubní ordinace s důrazem na komfort pacienta a nejnovější technologie. Naším cílem je, aby návštěva zubaře byla co nejpříjemnější. Věříme v preventivní přístup a dlouhodobou péči.",
            "V naší ordinaci dbáme na to, aby se každý pacient cítil bezpečně a pohodlně. Používáme moderní vybavení a šetrné metody léčby. Rádi vás přivítáme – i když jste u zubaře nervózní.",
            "Nabízíme kompletní zubní péči od prevence a čištění až po estetickou stomatologii a implantáty. Každého pacienta bereme individuálně a péči přizpůsobujeme jeho potřebám.",
        ],
        "about_short": [
            "Moderní stomatologie s přátelským přístupem.",
            "Péče o váš úsměv v komfortním prostředí.",
            "Zubní ordinace, kde se nebojíte.",
        ],
    },

    "masaze": {
        "name_cs": "masážní salony",
        "name_cs_4": "masážní salon",
        "search_query": "masáže wellness salon {city}",
        "places_type": "spa",
        "osm_filter": '["shop"~"massage|wellness"]',
        "email_problem_no_web": (
            "nemáte vlastní webové stránky – přitom klienti hledají masáže online "
            "a rozhodují se podle prostředí a procedur ještě před objednáním"
        ),
        "email_problem_bad_web": (
            "web by mohl lépe prezentovat vaše procedury a umožnit snadné objednání "
            "– klienti to dnes očekávají"
        ),
        "email_cta": "Pracujeme s masážními salony a wellness studii {city_phrase}.",
        "taglines": [
            "Váš prostor pro klid a regeneraci",
            "Kde tělo i mysl najdou odpočinek",
            "Péče, která obnovuje energii",
            "Relaxace jako umění",
            "Chvíle jen pro vás",
            "Harmonie těla a duše",
        ],
        "subtitles": [
            "Profesionální masáže a wellness procedury přizpůsobené vašim potřebám.",
            "Zapomeňte na každodenní stres – přijďte si odpočinout a načerpat novou energii.",
            "Relaxační i sportovní masáže, aromaterapie a speciální procedury na jednom místě.",
        ],
        "about_texts": [
            "Jsme masážní studio s vášní pro relaxaci a péči o tělo. Každou proceduru přizpůsobujeme individuálním potřebám klienta a věříme, že pravidelná masáž je investice do zdraví a pohody.",
            "Naše studio vzniklo z touhy nabídnout lidem prostor, kde mohou skutečně vypnout. Pracujeme s prověřenými technikami, kvalitnými oleji a srdcem na správném místě. Přijďte si to sami vyzkoušet.",
            "Věříme, že každý si zaslouží chvíli klidu. Proto se věnujeme každému klientovi individuálně a vytváříme atmosféru, ve které se okamžitě cítíte bezpečně a uvolněně.",
        ],
        "about_short": [
            "Profesionální masáže a wellness v příjemném prostředí.",
            "Váš ostrůvek klidu a relaxace v srdci města.",
            "Masážní studio s individuálním přístupem a srdcem.",
        ],
    },

    "autoservis": {
        "name_cs": "autoservisy",
        "name_cs_4": "autoservis",
        "search_query": "autoservis {city}",
        "places_type": "car_repair",
        "osm_filter": '["shop"="car_repair"]',
        "email_problem_no_web": (
            "nemáte vlastní webové stránky – přitom zákazníci hledají autoservis "
            "online a rozhodují se podle webu dřív, než vůbec zavolají"
        ),
        "email_problem_bad_web": (
            "web by mohl lépe prezentovat vaše služby a usnadnit zákazníkům objednání "
            "– většina lidí hledá servis z telefonu"
        ),
        "email_cta": "Pracujeme s autoservisy {city_phrase}.",
        "taglines": [
            "Váš spolehlivý partner na cestách",
            "Poctivý servis, férová cena",
            "Staráme se o vaše auto jako o vlastní",
            "Profesionální autoservis s tradicí",
            "Rychle, spolehlivě, za rozumnou cenu",
            "Opravíme vše – od oleje po motor",
        ],
        "subtitles": [
            "Kompletní péče o vaše vozidlo – servis, diagnostika a pneuservis na jednom místě.",
            "Moderní vybavení, zkušení mechanici a férové ceny. Objednejte se ještě dnes.",
            "Záruční i pozáruční servis všech značek. Rychlá diagnostika, spolehlivé opravy.",
        ],
        "about_texts": [
            "Jsme rodinný autoservis s dlouholetou tradicí a vášní pro automobily. Každé vozidlo bereme jako vlastní – opravujeme pečlivě, rychle a za férovú cenu. Naším cílem je, abyste odjeli spokojení a mohli se kdykoli vrátit.",
            "Náš autoservis vznikl z lásky k technice a touhy pomáhat lidem na cestách. Máme moderní diagnostické vybavení a tým zkušených mechaniků. Provádíme záruční i pozáruční servis všech značek a modelů.",
            "Věříme, že dobrý autoservis je o důvěře. Proto vždy předem sdělíme rozsah prací a jejich cenu – bez překvapení. Pracujeme rychle, kvalitně a stojíme si za svou prací.",
        ],
        "about_short": [
            "Spolehlivý autoservis s férovými cenami a moderním vybavením.",
            "Pečujeme o vaše vozidlo s odborností a poctivostí.",
            "Rychlé opravy, profesionální diagnostika, férový přístup.",
        ],
    },

    "psycholog": {
        "name_cs": "psychologické poradny",
        "name_cs_4": "psychologickou poradnu",
        "search_query": "psycholog terapeut poradna {city}",
        "places_type": "doctor",
        "osm_filter": '["healthcare"~"psychotherapist|psychologist"]',
        "email_problem_no_web": (
            "nemáte vlastní webové stránky – klienti hledají psychologa online "
            "a důvěra začíná tím, jak prezentujete sebe a svůj přístup"
        ),
        "email_problem_bad_web": (
            "web by mohl lépe prezentovat váš přístup, specializaci a umožnit "
            "jednoduché objednání – první dojem je klíčový"
        ),
        "email_cta": "Pracujeme s psychology a terapeuty {city_phrase}.",
        "taglines": [
            "Bezpečné místo pro vaše myšlenky",
            "Cesta k sobě samému",
            "Odborná pomoc s lidským přístupem",
            "Váš prostor pro růst",
            "Psychologie, která mění životy",
            "Přijďte, jak jste. Odejdete silnější.",
        ],
        "subtitles": [
            "Profesionální psychologická podpora v bezpečném a přátelském prostředí.",
            "Individuální terapie zaměřená na vaše potřeby a cíle.",
            "Odborná péče s empatickým přístupem pro dospělé i mladé.",
        ],
        "about_texts": [
            "Jsem psycholog s vášní pro pomoc lidem na jejich cestě k sobě samým. Pracuji s dospělými i dospívajícími a specializuji se na úzkosti, vztahová témata a osobní rozvoj. Moje ordinace je bezpečný prostor, kde se nemusíte bát být sami sebou.",
            "Věřím, že každý člověk má v sobě sílu překonat těžkosti – někdy potřebuje jen průvodce. Nabízím individuální terapii, párové poradenství a skupinové workshopy. Přijďte, jak jste.",
            "V mé praxi klademe důraz na individuální přístup, respekt a diskrétnost. Pracujeme s různými terapeutickými metodami a přizpůsobujeme postup vašim potřebám a cílům.",
        ],
        "about_short": [
            "Bezpečné místo pro vaše myšlenky a emoce.",
            "Odborná psychologická pomoc s empatickým přístupem.",
            "Terapie přizpůsobená vašim individuálním potřebám.",
        ],
    },
}


def get_industry(key: str) -> dict:
    """Vrátí konfiguraci odvětví podle klíče. Fallback na restaurace."""
    return INDUSTRIES.get(key, INDUSTRIES["restaurace"])


def list_industries() -> list[str]:
    """Vrátí seznam dostupných klíčů odvětví."""
    return list(INDUSTRIES.keys())
