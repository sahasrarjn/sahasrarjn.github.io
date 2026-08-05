"""
Render the article's tables to PNG.

Medium has no table support at all, so the five tables that carry most of the
evidence have to go in as images. We pull the already-styled tables out of the
site page and render them through headless Chrome, same as the figures, so they
look identical to the ones on the site.
"""

import pathlib
import re
import shutil
import subprocess
import tempfile

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
ROOT = pathlib.Path("/Users/sahasra/Personal/work/sahasrarjn.github.io/blog/scaffold-splits")
OUT = ROOT / "img" / "png"
SCALE = 2

NAMES = [
    "table_1_distances",
    "table_2_acyclic_policy",
    "table_3_tiebreak",
    "table_4_model_scores",
    "table_5_maccs",
]

CSS = """
:root{
  --paper:#F6F5F2; --paper-2:#FFFFFF; --paper-3:#EDECE7;
  --ink:#14161A; --ink-2:#4A4E58; --ink-3:#747984;
  --rule:#D8D7D1; --rule-2:#C4C3BC;
  --accent:#2D4EC8; --accent-soft:#E4E8F8; --leak:#9B3B24;
  --f-mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,monospace;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:#FFFFFF}
body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
     font-size:17px;color:var(--ink);-webkit-font-smoothing:antialiased}
.frame{display:inline-block;padding:20px;background:#FFFFFF}
.tscroll{border:1px solid var(--rule);background:var(--paper-2)}
table{border-collapse:collapse;font-size:.92rem;white-space:nowrap}
th,td{text-align:left;padding:.6rem .95rem;border-bottom:1px solid var(--rule)}
thead th{font-family:var(--f-mono);font-size:.68rem;letter-spacing:.07em;text-transform:uppercase;
  color:var(--ink-3);font-weight:500;border-bottom:1px solid var(--rule-2);vertical-align:bottom}
tbody tr:last-child td{border-bottom:none}
td.num,th.num{text-align:right;font-family:var(--f-mono);font-variant-numeric:tabular-nums}
td.num b{color:var(--leak)}
tbody tr.hi{background:var(--accent-soft)}
"""


def extract_tables(html):
    return re.findall(r'<div class="tscroll">\s*<table>.*?</table>\s*</div>', html, re.S)


def render(frag, name, tmp):
    page = tmp / f"{name}.html"
    page.write_text(
        f'<!doctype html><meta charset="utf-8"><style>{CSS}</style>'
        f'<div class="frame">{frag}</div>'
    )
    # oversize window, then let Chrome crop to content via a first measure pass
    subprocess.run(
        [CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
         f"--force-device-scale-factor={SCALE}",
         "--window-size=1500,900",
         "--default-background-color=FFFFFFFF",
         f"--screenshot={OUT / (name + '_raw.png')}",
         f"file://{page}"],
        check=True, capture_output=True,
    )
    return OUT / f"{name}_raw.png"


def trim(path, out):
    """Crop the uniform white margin off the right and bottom."""
    from PIL import Image, ImageChops
    im = Image.open(path).convert("RGB")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    box = ImageChops.difference(im, bg).getbbox()
    if box:
        pad = 16
        l, t, r, b = box
        im = im.crop((max(0, l - pad), max(0, t - pad),
                      min(im.width, r + pad), min(im.height, b + pad)))
    im.save(out)
    return im.size


if __name__ == "__main__":
    html = (ROOT / "index.html").read_text()
    frags = extract_tables(html)
    assert len(frags) == len(NAMES), f"found {len(frags)} tables, expected {len(NAMES)}"

    OUT.mkdir(parents=True, exist_ok=True)
    tmp = pathlib.Path(tempfile.mkdtemp())
    for frag, name in zip(frags, NAMES):
        raw = render(frag, name, tmp)
        size = trim(raw, OUT / f"{name}.png")
        raw.unlink()
        kb = (OUT / f"{name}.png").stat().st_size // 1024
        print(f"{name + '.png':28s} {size[0]}x{size[1]}  {kb}K")
    shutil.rmtree(tmp)
    print(f"\nwrote {len(NAMES)} table PNGs to {OUT}")
