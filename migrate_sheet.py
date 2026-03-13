"""
Přidá chybějící sloupce do existujícího Google Sheetu.
Spusť jednou: venv/bin/python3 migrate_sheet.py
"""
from sheets import get_or_create_sheet, HEADERS

def migrate():
    print("📊 Připojuji Google Sheet...")
    sheet = get_or_create_sheet()

    existing = sheet.row_values(1)
    print(f"  Aktuální sloupce ({len(existing)}): {existing}")

    missing = [h for h in HEADERS if h not in existing]
    if not missing:
        print("✅ Sheet je aktuální, žádné sloupce nechybí.")
        return

    print(f"  Přidávám {len(missing)} chybějících sloupců: {missing}")
    next_col = len(existing) + 1
    for i, header in enumerate(missing):
        sheet.update_cell(1, next_col + i, header)
        print(f"  ✓ Přidán sloupec: {header}")

    # Tučné formátování celé hlavičky
    last_col = chr(ord("A") + len(HEADERS) - 1)
    sheet.format(f"A1:{last_col}1", {
        "textFormat": {"bold": True},
        "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.2},
    })

    print(f"\n✅ Hotovo! Sheet má teď {len(HEADERS)} sloupců.")

if __name__ == "__main__":
    migrate()
