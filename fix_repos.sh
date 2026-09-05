#!/bin/bash
set -e

BASE=/root/restaurant-outreach

# Mapování: repo_dir -> industry_name (pro stock fotky)
declare -A REPOS=(
  ["demos"]="restaurace"
  ["demos-kavarny"]="kavarna"
  ["demos-penziony"]="penzion"
  ["demos-kadernictvi"]="kadernictvi"
  ["demos-kosmetika"]="kosmetika"
  ["demos-autoservis"]="autoservis"
  ["demos-masaze"]="masaze"
  ["demos-zubni"]="zubni"
  ["demos-psycholog"]="psycholog"
)

for REPO_NAME in "${!REPOS[@]}"; do
  INDUSTRY="${REPOS[$REPO_NAME]}"
  REPO_DIR="$BASE/$REPO_NAME"
  STOCK_SRC="$BASE/stock_photos/$INDUSTRY"

  echo ""
  echo "=== $REPO_NAME ($INDUSTRY) ==="

  # 1. Zkopíruj stock fotky do root repa
  mkdir -p "$REPO_DIR/stock_photos"
  cp "$STOCK_SRC"/*.jpg "$REPO_DIR/stock_photos/"
  echo "  ✅ Stock fotky zkopírovány"

  # 2. Nahraď `photos/photo_X.jpg` -> `../stock_photos/photo_X.jpg` ve všech index.html
  find "$REPO_DIR" -maxdepth 2 -name "index.html" -exec \
    sed -i "s|'photos/photo_|'../stock_photos/photo_|g; s|\"photos/photo_|\"../stock_photos/photo_|g; s|(photos/photo_|(../stock_photos/photo_|g" {} \;
  echo "  ✅ HTML aktualizovány"

  # 3. Smaž všechny photos/ složky v demo adresářích
  find "$REPO_DIR" -mindepth 2 -maxdepth 2 -type d -name "photos" -exec rm -rf {} + 2>/dev/null || true
  echo "  ✅ Duplicitní photos/ složky smazány"

  # 4. Přidej .nojekyll
  touch "$REPO_DIR/.nojekyll"
  echo "  ✅ .nojekyll přidán"

  # 5. Orphan branch - smaže git historii
  cd "$REPO_DIR"
  git checkout --orphan temp_clean
  git add -A
  git commit -m "Cleanup: shared stock photos, removed duplicates"
  git branch -D master
  git branch -m master
  echo "  ✅ Orphan branch vytvořen"

  # 6. Force push
  git push origin master --force
  echo "  ✅ Pushnutý na GitHub"

  du -sh --exclude='.git' "$REPO_DIR" | awk '{print "  📦 Velikost working tree: " $1}'
  cd "$BASE"
done

echo ""
echo "🎉 Hotovo! Všechny repozitáře vyčištěny."
