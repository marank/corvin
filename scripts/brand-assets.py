"""Generate Corvin brand assets from the raven-head mark and the Space Grotesk wordmark.

Writes the lockup SVGs (wordmark as outlines), PNGs and ICOs into branding/ and the
favicons, manifest icons and link-preview image into frontend/public/. Needs Inkscape,
ImageMagick and `pnpm install` in frontend/ (for the font); run from the repo root:

    uv run --no-project --with fonttools --with brotli --with uharfbuzz python scripts/brand-assets.py
"""

import io
import subprocess
import tempfile
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

root = Path(__file__).resolve().parent.parent
work = Path(tempfile.mkdtemp(prefix="brand-assets-"))
branding = root / "branding"
public = root / "frontend" / "public"
font = TTFont(
    root
    / "frontend/node_modules/@fontsource/space-grotesk/files/space-grotesk-latin-600-normal.woff2"
)
font.flavor = None
_buf = io.BytesIO()
font.save(_buf)
FONT_BYTES = _buf.getvalue()  # HarfBuzz needs plain sfnt, not WOFF2

# Raven head from basic shapes, centred in a 64x64 box: head = half circle (r 28, centre
# 32,32) in violet (upper quarter) and blue (lower quarter), beak = cyan right triangle,
# eye = hole at the incentre of the upper quarter. Shapes overlap underneath their
# neighbours so no background shows between the colours; the eye is cut out.
MARK_SHAPES = (
    '<path fill="#22d3ee" d="M32 4L60 32H26V4.646Z"/>'
    '<path fill="#3b82f6" d="M32 30H4.071A28 28 0 0 0 32 60Z"/>'
    '<path fill="#a855f7" fill-rule="evenodd" '
    'd="M32 32H4A28 28 0 0 1 32 4ZM23.8 20.4a3.4 3.4 0 1 0-6.8 0a3.4 3.4 0 1 0 6.8 0Z"/>'
)


def wordmark(text, font_size, x0, baseline):
    """Outline path of `text` set at font_size with its baseline at (x0, baseline); returns (path, width)."""
    upem = font["head"].unitsPerEm
    glyphs, order = font.getGlyphSet(), font.getGlyphOrder()
    s = font_size / upem
    # Shape with HarfBuzz so GPOS kerning matches what the browser renders.
    hb_font = hb.Font(hb.Face(FONT_BYTES))
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hb_font, buf, {"kern": True, "liga": True})
    pen = SVGPathPen(glyphs)
    x = 0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions, strict=True):
        glyphs[order[info.codepoint]].draw(
            TransformPen(pen, (s, 0, 0, -s, x0 + (x + pos.x_offset) * s, baseline))
        )
        x += pos.x_advance
    return pen.getCommands(), x * s


# Lockup like AppLogo size="lg": mark h-8 (32px) next to text-3xl (30px), gap-3 (12px), leading-none.
MARK = (4, 4, 56, 56)  # tight viewBox of the mark
mark_h = MARK[3]
font_size = 30 / 32 * mark_h
gap = 12 / 32 * mark_h
hhea = font["hhea"]
upem = font["head"].unitsPerEm
asc, desc = hhea.ascent / upem * font_size, -hhea.descent / upem * font_size
baseline = (mark_h - font_size) / 2 + (font_size - (asc + desc)) / 2 + asc
text_x = MARK[2] + gap
path, text_w = wordmark("Corvin", font_size, text_x, baseline)
width = text_x + text_w + 2
height = mark_h


def lockup(text_color):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.2f} {height:.2f}">'
        f'<g transform="translate({-MARK[0]},{-MARK[1]})">{MARK_SHAPES}</g>'
        f'<path d="{path}" fill="{text_color}"/></svg>\n'
    )


(branding / "corvin-logo.svg").write_text(lockup("#1e293b"))
(branding / "corvin-logo-white.svg").write_text(lockup("#ffffff"))


def svg(view_box, background=None):
    bg = (
        f'<rect x="-100" y="-100" width="400" height="400" fill="{background}"/>'
        if background
        else ""
    )
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}">{bg}{MARK_SHAPES}</svg>\n'


def render(svg_text, out, w, h=None):
    src = work / (out.stem + ".svg")
    src.write_text(svg_text)
    subprocess.run(
        ["inkscape", str(src), "-w", str(w), "-h", str(h or w), "-o", str(out)],
        check=True,
        capture_output=True,
    )


def ico(out, sizes):
    pngs = []
    for size in sizes:
        p = work / f"ico-{size}.png"
        render(svg("0 0 64 64"), p, size)
        pngs.append(str(p))
    subprocess.run(["convert", *pngs, str(out)], check=True)


# Mark: transparent PNGs and a multi-size ICO for the branding folder.
for size in (256, 512):
    render(svg("0 0 64 64"), branding / f"corvin-mark-{size}.png", size)
ico(branding / "corvin.ico", (16, 24, 32, 48, 64, 128, 256))
render(lockup("#1e293b"), branding / "corvin-logo-1024.png", 1024, round(1024 * height / width))

# Web app: favicon.ico fallback, manifest icons (any + maskable with safe zone), Apple touch icon on white.
ico(public / "favicon.ico", (16, 32, 48))
render(svg("0 0 64 64"), public / "icon-192.png", 192)
render(svg("0 0 64 64"), public / "icon-512.png", 512)
render(svg("-18 -18 100 100", "#ffffff"), public / "icon-maskable-512.png", 512)
render(svg("-14 -14 92 92", "#ffffff"), public / "apple-touch-icon.png", 180)

# Link preview: lockup centred on white, 1200x630.
lw = 640
lh = lw * height / width
og = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630"><rect width="1200" height="630" fill="#ffffff"/>'
    f'<svg x="{(1200 - lw) / 2:.1f}" y="{(630 - lh) / 2:.1f}" width="{lw}" height="{lh:.1f}" '
    f'viewBox="0 0 {width:.2f} {height:.2f}">{lockup("#1e293b")[lockup("#1e293b").index(">") + 1 : -7]}</svg></svg>\n'
)
render(og, public / "og-image.png", 1200, 630)
render(og, branding / "corvin-og-image.png", 1200, 630)
print(f"lockup {width:.1f}x{height:.1f}")
