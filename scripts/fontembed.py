"""
Embed real typefaces inside an SVG.

An SVG served through <img> (which is how GitHub shows README images) can't
load web fonts from a URL, but it can use a font inlined as a data: URI.
Each SVG gets only the glyphs it actually uses, so the overhead stays small.

  font-family "Plex" -> IBM Plex Mono 400/600   (terminal, readouts)
  font-family "Stix" -> STIX Two Text            (the typeface journals use for physics)

Both fonts are SIL OFL 1.1; licenses are in scripts/fonts/.
Needs: fonttools, brotli.
"""
import base64
import html
import io
import os
import re

from fontTools import subset
from fontTools.ttLib import TTFont

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")

FACES = [  # (family, weight, style, file)
    ("Plex", 400, "normal", "ibm-plex-mono-latin-400-normal.woff2"),
    ("Plex", 600, "normal", "ibm-plex-mono-latin-600-normal.woff2"),
    ("Stix", 400, "normal", "stix-two-text-latin-400-normal.woff2"),
    ("Stix", 400, "italic", "stix-two-text-latin-400-italic.woff2"),
    ("Stix", 600, "normal", "stix-two-text-latin-600-normal.woff2"),
    ("Stix", 400, "normal", "stix-two-text-greek-400-normal.woff2"),
    ("Stix", 400, "italic", "stix-two-text-greek-400-italic.woff2"),
]

PLEX = "Plex, ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
STIX = "Stix, 'STIX Two Text', 'Times New Roman', Georgia, serif"

_cache = {}


def _load(name):
    if name not in _cache:
        _cache[name] = open(os.path.join(FONT_DIR, name), "rb").read()
    return _cache[name]


def _subset(data, chars):
    font = TTFont(io.BytesIO(data))
    have = set(font.getBestCmap())
    use = {ord(c) for c in chars} & have
    if not use:
        return None
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern"]
    opts.name_IDs = []
    opts.hinting = False            # screen rendering at these sizes doesn't need it
    opts.desubroutinize = True
    opts.notdef_outline = False
    opts.drop_tables += ["DSIG", "GDEF", "GSUB", "STAT", "MVAR", "HVAR"]
    s = subset.Subsetter(opts)
    s.populate(unicodes=use)
    s.subset(font)
    out = io.BytesIO()
    font.flavor = "woff2"
    font.save(out)
    return out.getvalue()


def embed(svg):
    """Return svg with @font-face rules for the glyphs it uses."""
    text = html.unescape("".join(re.findall(r">([^<>]+)<", svg)))
    chars = set(text) | set(" 0123456789")
    rules = []
    for family, weight, style, fname in FACES:
        if f"{family}," not in svg and f'"{family}"' not in svg:
            continue
        data = _subset(_load(fname), chars)
        if data:
            b64 = base64.b64encode(data).decode()
            rules.append(f"@font-face{{font-family:{family};font-weight:{weight};font-style:{style};"
                         f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}")
    if not rules:
        return svg
    style = "<style>" + "".join(rules) + "</style>"
    i = svg.index(">", svg.index("<svg")) + 1
    return svg[:i] + style + svg[i:]
