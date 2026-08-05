#!/bin/bash
# Render each article SVG to a Medium-compatible PNG.
#
# Medium accepts JPEG/PNG/WEBP/AVIF/GIF but not SVG. We render through headless
# Chrome rather than a converter so the CSS custom properties, <style> blocks
# and web fonts resolve exactly as they do on the page. Light theme is pinned,
# since Medium has no dark mode.
set -euo pipefail

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SRC="/Users/sahasra/Personal/work/sahasrarjn.github.io/blog/scaffold-splits/img"
OUT="$SRC/png"
TMP="$(mktemp -d)"
SCALE=2          # retina; Medium downsamples gracefully

mkdir -p "$OUT"

for svg in spread hist scaffold_chain scaffold_sink scaffold_hole; do
  # native viewBox size, so the PNG is not distorted
  read -r W H < <(sed -n 's/.*viewBox="0 0 \([0-9.]*\) \([0-9.]*\)".*/\1 \2/p' "$SRC/$svg.svg" | head -1)
  PAD=24
  PW=$(python3 -c "print(int($W + 2*$PAD))")
  PH=$(python3 -c "print(int($H + 2*$PAD))")

  cat > "$TMP/$svg.html" <<HTML
<!doctype html><meta charset="utf-8">
<style>
  :root{
    --paper:#F6F5F2; --paper-2:#FFFFFF; --paper-3:#EDECE7;
    --ink:#14161A; --ink-2:#4A4E58; --ink-3:#747984;
    --rule:#D8D7D1; --rule-2:#C4C3BC;
    --accent:#2D4EC8; --leak:#9B3B24;
  }
  html,body{margin:0;padding:0;background:#FFFFFF}
  .frame{width:${PW}px;padding:${PAD}px;box-sizing:border-box;background:#FFFFFF}
  svg{display:block;width:${W}px;height:${H}px}
</style>
<div class="frame">$(cat "$SRC/$svg.svg")</div>
HTML

  "$CHROME" --headless --disable-gpu --hide-scrollbars \
      --force-device-scale-factor=$SCALE \
      --window-size="$PW,$PH" \
      --default-background-color=FFFFFFFF \
      --screenshot="$OUT/$svg.png" \
      "file://$TMP/$svg.html" >/dev/null 2>&1

  printf "%-16s %sx%s -> %s\n" "$svg.png" "$PW" "$PH" "$(du -h "$OUT/$svg.png" | cut -f1)"
done

rm -rf "$TMP"
echo
echo "PNGs written to $OUT"
