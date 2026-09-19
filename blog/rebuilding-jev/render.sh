#!/bin/bash
# Render each figure to PNG through headless Chrome, so CSS custom properties,
# flexbox layout and the web font resolve exactly as designed. PNG rather than
# inline SVG so the figures survive RSS, Medium and social previews.
set -euo pipefail
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p "$DIR/img"
render(){ # name width height
  "$CHROME" --headless --disable-gpu --hide-scrollbars \
    --force-device-scale-factor=2 --window-size="$2,$3" \
    --default-background-color=FBFAF7FF \
    --screenshot="$DIR/img/$1.png" "file://$DIR/fig/$1.html" >/dev/null 2>&1
  printf "  %-16s %s\n" "$1.png" "$(du -h "$DIR/img/$1.png" | cut -f1)"
}
render mask         900 400
render order        900 300
  render calibration  860 400
render surgery      900 648
render io           900 600
