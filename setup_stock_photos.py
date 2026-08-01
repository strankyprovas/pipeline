#!/usr/bin/env python3
"""
Jednorázový script – stáhne generické stock fotky pro každé odvětví.
Spustit před prvním použitím pipeline: venv/bin/python3 setup_stock_photos.py

Fotky se ukládají do stock_photos/{industry}/photo_1.jpg ... photo_6.jpg
Používá Unsplash source API (zdarma, bez klíče).
"""
import os
import time
import requests

STOCK_DIR = os.path.join(os.path.dirname(__file__), "stock_photos")

# Hardcoded Pexels photo IDs – ručně ověřené, přímý CDN link bez API klíče
PEXELS_IDS = {
    "restaurace":  [1640777, 1279330, 769289, 3616956, 784633, 376464],
    "autoservis":  [3807517, 2244746, 3807386, 1409999, 279949, 4488660],
    "penzion":     [271624, 164595, 2631746, 3659683, 1579253, 271639],
    "kadernictvi": [3993449, 1813272, 1319460, 3993456, 897262, 3065171],
    "kavarna":     [302899, 312418, 1307698, 3879495, 1695052, 585753],
    "kosmetika":   [3736398, 6417957, 17545641, 7607305, 3735626, 6417954],
    "zubni":       [3779706, 5355715, 3845745, 3779713, 6529110, 3845735],
    "masaze":      [19695969, 19695966, 6187430, 3865570, 10894305, 6560280],
    "psycholog":   [7176229, 7579306, 7447253, 7176077, 7579308, 5710923],
}

# 6 klíčových slov pro každé odvětví (každé = 1 fotka) – loremflickr fallback
INDUSTRY_KEYWORDS = {
    "restaurace":   [],  # řeší se přes PEXELS_IDS
    "kavarna":      [],  # řeší se přes PEXELS_IDS
    "penzion":      [],  # řeší se přes PEXELS_IDS
    "kosmetika":    [],  # řeší se přes PEXELS_IDS
    "kadernictvi":  [],  # řeší se přes PEXELS_IDS
    "zubni":        [],  # řeší se přes PEXELS_IDS
    "masaze":       [],  # řeší se přes PEXELS_IDS
    "autoservis":   [],  # řeší se přes PEXELS_IDS
    "psycholog":    [],  # řeší se přes PEXELS_IDS
    "pekarna":      ["bakery bread", "fresh bread", "croissant pastry", "baker bakery", "bread loaf", "bakery shop"],
    "kvetinarstvi": ["flower shop", "flower bouquet", "florist flowers", "roses bouquet", "flower arrangement", "flowers colorful"],
}

HEADERS = {"User-Agent": "StrankyProVas/1.0"}


def download_photo(keyword: str, path: str) -> bool:
    """Stáhne jednu fotku z loremflickr.com (zdarma, téma-specifické)."""
    # loremflickr.com vrací náhodnou Flickr fotku odpovídající klíčovým slovům
    # lock=seed zajistí různé fotky pro každý soubor
    seed = abs(hash(path)) % 100_000
    kw = keyword.replace(" ", ",")  # "food meal" → "food,meal" (AND logika)
    url = f"https://loremflickr.com/1400/900/{kw}?lock={seed}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
        if resp.status_code == 200 and len(resp.content) > 20_000:
            with open(path, "wb") as f:
                f.write(resp.content)
            return True
        # Fallback: picsum.photos – krásné náhodné fotky (ne topic-specific)
        url2 = f"https://picsum.photos/seed/{seed}/1400/900"
        resp2 = requests.get(url2, headers=HEADERS, timeout=30, allow_redirects=True)
        if resp2.status_code == 200 and len(resp2.content) > 20_000:
            with open(path, "wb") as f:
                f.write(resp2.content)
            return True
        print(f"    ⚠️  Malá odpověď ({resp.status_code}, {len(resp.content)} B)")
    except Exception as e:
        print(f"    ⚠️  Chyba stahování: {e}")
    return False


def download_pexels(photo_id: int, path: str) -> bool:
    """Stáhne fotku přímo z Pexels CDN (bez API klíče)."""
    url = f"https://images.pexels.com/photos/{photo_id}/pexels-photo-{photo_id}.jpeg?auto=compress&cs=tinysrgb&w=1400"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        if resp.status_code == 200 and len(resp.content) > 20_000:
            with open(path, "wb") as f:
                f.write(resp.content)
            return True
    except Exception as e:
        print(f"    ⚠️  Chyba: {e}")
    return False


def main():
    print("📸 Stahuji stock fotky pro všechna odvětví...\n")
    total_ok = 0
    total_fail = 0

    all_industries = set(INDUSTRY_KEYWORDS.keys()) | set(PEXELS_IDS.keys())

    for industry in sorted(all_industries):
        ind_dir = os.path.join(STOCK_DIR, industry)
        os.makedirs(ind_dir, exist_ok=True)
        print(f"  [{industry}]")

        # Pexels IDs mají přednost
        if industry in PEXELS_IDS:
            for i, photo_id in enumerate(PEXELS_IDS[industry], start=1):
                path = os.path.join(ind_dir, f"photo_{i}.jpg")
                if os.path.exists(path) and os.path.getsize(path) > 20_000:
                    print(f"    photo_{i}.jpg ✓ (existuje)")
                    total_ok += 1
                    continue
                print(f"    photo_{i}.jpg  (pexels #{photo_id})... ", end="", flush=True)
                if download_pexels(photo_id, path):
                    print("✓")
                    total_ok += 1
                else:
                    print("✗")
                    total_fail += 1
                time.sleep(0.5)

        # Ostatní odvětví přes loremflickr
        else:
            for i, kw in enumerate(INDUSTRY_KEYWORDS.get(industry, [])[:6], start=1):
                path = os.path.join(ind_dir, f"photo_{i}.jpg")
                if os.path.exists(path) and os.path.getsize(path) > 20_000:
                    print(f"    photo_{i}.jpg ✓ (existuje)")
                    total_ok += 1
                    continue
                print(f"    photo_{i}.jpg  ({kw})... ", end="", flush=True)
                if download_photo(kw, path):
                    print("✓")
                    total_ok += 1
                else:
                    print("✗")
                    total_fail += 1
                time.sleep(1.2)

        print()

    print(f"✅ Hotovo!  Staženo: {total_ok}  Selhalo: {total_fail}")
    if total_fail > 0:
        print("   Spusť script znovu – nespolehlivé fotky se přeskočí.")


if __name__ == "__main__":
    main()
