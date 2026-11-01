#!/usr/bin/env python3
"""
Build the profile README.

  assets/cosmos.svg              hero (scripts/hero.py): repos orbiting a black hole
  assets/portal.svg              wormhole tile -> portfolio
  assets/ephemeris-*.svg         one row per orbiting body -> its repo
  assets/banner-NN.svg           section headers, written as shell commands
  assets/toolkit.svg             `ls toolkit/`
  assets/planets/<repo>.svg      repo cards -> repo
  assets/uncharted/<id>.svg      projects without a public repo -> portfolio
  assets/telemetry.svg           `gh api` stats
  assets/channel-*.svg           contact
  assets/footer.svg              quote
  README.md                      from scripts/README.template.md

GitHub shows every SVG as a plain <img>, so a link can't live inside one.
Every clickable thing is its own image wrapped in <a>.

Needs fonttools + brotli.  GITHUB_TOKEN=... python scripts/universe.py --user T-Yashwanth-Naidu
"""
import argparse
import hashlib
import json
import math
import os
import re
import shutil
import sys
import urllib.request
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hero  # noqa: E402
from fontembed import PLEX, STIX, embed  # noqa: E402

API = "https://api.github.com"


# ----------------------------------------------------------------- GitHub API

def gh(url, token, body=None):
    req = urllib.request.Request(url, data=body, headers={
        "Accept": "application/vnd.github+json", "User-Agent": "cosmos-readme"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_repos(user, token):
    """Public, non-fork, non-archived repos, excluding the profile repo itself."""
    repos, page = [], 1
    while True:
        batch = gh(f"{API}/users/{user}/repos?per_page=100&page={page}&type=owner", token)
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    return [r for r in repos if not r["fork"] and not r.get("archived") and r["name"].lower() != user.lower()]


def fetch_contributions(user, token):
    """(total, days) for the last year via GraphQL, or None without a token."""
    if not token:
        return None
    q = {"query": "query($l:String!){user(login:$l){contributionsCollection{contributionCalendar"
                  "{totalContributions weeks{contributionDays{date contributionCount}}}}}}",
         "variables": {"l": user}}
    try:
        d = gh(f"{API}/graphql", token, json.dumps(q).encode())
        cal = d["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        return cal["totalContributions"], [x for w in cal["weeks"] for x in w["contributionDays"]]
    except Exception as e:
        print(f"warn: contributions unavailable ({e})", file=sys.stderr)
        return None


def h01(s, salt=""):
    """Deterministic pseudo-random in [0,1], so images only change when data does."""
    return int(hashlib.sha256((salt + s).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def mix(a, b, t):
    x = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    y = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(p + (q - p) * t):02x}" for p, q in zip(x, y))

PORTFOLIO = "https://cthecosmos.com/?page_id=4955"
LINKEDIN = "https://www.linkedin.com/in/t-yashwanth-naidu/"

BG0, BG1 = "#020306", "#090c14"
BORDER = "#30363d"
TEXT, MUTED, FAINT = "#e6edf3", "#8b949e", "#6e7681"
ACCENT = "#d9a85b"        # starlight
DIR = "#79c0ff"           # ls directory blue
NUM = "#a5d6ff"

LANG = {"C": "#555555", "C++": "#f34b7d", "Python": "#3572A5", "JavaScript": "#f1e05a",
        "TypeScript": "#3178c6", "Cuda": "#3A4E3A", "Assembly": "#6E4C13", "MATLAB": "#e16737",
        "Shell": "#89e051", "HTML": "#e34c26", "CMake": "#DA3434", "Makefile": "#427819"}

PLANETS = {
    "saturn":  ("#d6bf8e", ["#bfa06d", "#ecdcb5", "#c9ad7c"]),
    "jupiter": ("#c8a47a", ["#a9784e", "#e3cfae", "#8c5a3c"]),
    "mars":    ("#b25a3c", ["#8e4128", "#c87a55", "#9c4a30"]),
    "neptune": ("#4f6fae", ["#3d5a96", "#7c9bd1", "#46659f"]),
    "mercury": ("#8e8a85", ["#75716c", "#a8a49f", "#807c77"]),
    "venus":   ("#d8c59c", ["#c8b282", "#e9dcbd", "#cdb98e"]),
    "uranus":  ("#9ccfd2", ["#86bcc0", "#b6e0e2", "#8fc5c8"]),
}

# ----------------------------------------------------------------- content (edit here)

PRIMARY = "C-Programming-Questions"
FEATURED = [
    ("understanding_memory_in_c", "jupiter"),
    ("C-Programs", "mars"),
    ("Socket_Manager", "neptune"),
    ("LinkedIn-Highlighter", "mercury"),
]
DESCRIPTIONS = {}   # override weak repo descriptions, e.g. {"Socket_Manager": "..."}

TOOLKIT = [
    ("languages", ["C", "C++", "Python", "CUDA", "Assembly"]),
    ("automotive", ["UDS", "DoIP", "SOVD", "AUTOSAR", "CAN-FD"]),
    ("systems", ["Linux kernel", "QNX", "ROS2", "GDB", "OpenACC"]),
    ("hardware", ["Orin AGX", "Aurix TC375", "TIVA-C", "ESP32", "8051"]),
    ("safety", ["ISO 26262", "MISRA C", "EN 50128", "VectorCAST", "Simulink"]),
]

UNCHARTED = [
    dict(id="gpu-knn", name="GPU KNN", language="Cuda", planet="uranus",
         description="CUDA-parallel K-nearest neighbors, benchmarked against a CPU baseline"),
    dict(id="aeb", name="AEB System", language="MATLAB", planet="mars",
         description="Emergency braking from radar, LiDAR and camera sensor fusion"),
    dict(id="mlsa", name="Multi-Level Access", language="C", planet="mercury",
         description="8051 security access system with GSM, UART and I2C"),
    dict(id="biometric", name="Secure Biometric", language="C", planet="venus",
         description="AES-encrypted biometric auth on Arduino, tested against MITM and DoS"),
]

BANNERS = [  # (file number, command, note)
    ("01", "cat about.md", ""),
    ("02", "ls toolkit/", ""),
    ("03", "ls repos/ --sort=stars", "every card opens its repo"),
    ("04", "ls projects/ --no-public-repo", "write-ups live on the portfolio"),
    ("05", "cat publications.bib", ""),
    ("06", "gh api users/T-Yashwanth-Naidu", "refreshed daily by an Action"),
    ("07", "ping yash", ""),
]


# ----------------------------------------------------------------- primitives

def svg_open(w, h, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img"><title>{escape(title)}</title>')


STAR_TONES = ["#ffffff", "#cad7ff", "#fff4ea", "#ffd2a1", "#f8f7ff"]


def stars(w, h, n, salt):
    """Static, realistic sky: many faint stars, a few bright ones. Stars don't twinkle in space."""
    out = []
    for i in range(n):
        k = f"{salt}{i}"
        b = 10 ** (-1.6 * h01(k, "m") ** .35)
        out.append(f'<circle cx="{h01(k, "x") * w:.0f}" cy="{h01(k, "y") * h:.0f}" r="{.3 + 1.2 * math.sqrt(b):.1f}" '
                   f'fill="{STAR_TONES[i % 5]}" opacity="{min(1, .2 + 1.4 * b):.1f}"/>')
    return "".join(out)


def panel(w, h, rx=8, border=BORDER, dashed=False):
    dash = ' stroke-dasharray="4 4"' if dashed else ""
    head = (f'<defs><linearGradient id="pbg" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{BG0}"/><stop offset="1" stop-color="{BG1}"/></linearGradient>'
            f'<clipPath id="pclip"><rect width="{w}" height="{h}" rx="{rx}"/></clipPath></defs>'
            f'<rect width="{w}" height="{h}" rx="{rx}" fill="url(#pbg)"/>')
    tail = f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{rx}" fill="none" stroke="{border}"{dash}/>'
    return head, tail


def wrap(text, width, max_lines):
    words, lines, cur = (text or "").split(), [], ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= width:
            cur = f"{cur} {w}".strip()
        else:
            lines.append(cur)
            cur = w
            if len(lines) == max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    if len(lines) == max_lines and len(" ".join(lines)) < len(text or ""):
        lines[-1] = lines[-1][: width - 3].rstrip() + "..."
    return lines


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def write(path, content):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def link_img(href, src, width, alt):
    a = escape(alt, {'"': "&quot;"})
    return f'<a href="{href}"><img src="{src}" width="{width}" alt="{a}"></a>'


# ----------------------------------------------------------------- planet body (cards)

def planet_body(planet, pr, seed, ring=False):
    base, tones = PLANETS[planet]
    bands = []
    for i in range(7):
        k = f"{seed}b{i}"
        y = (h01(k, "y") - .5) * 1.8 * pr
        hh = 2 + h01(k, "h") * (pr * .16)
        bands.append(f'<ellipse cx="0" cy="{y:.1f}" rx="{pr * 1.7:.1f}" ry="{hh:.1f}" '
                     f'fill="{tones[i % len(tones)]}" opacity=".7"/>')
    spin = 26 + h01(seed, "spin") * 14
    defs = (f'<defs><radialGradient id="ps{seed}" fx=".38" fy=".35">'
            f'<stop offset="0" stop-color="{mix(base, "#ffffff", .25)}"/>'
            f'<stop offset="1" stop-color="{mix(base, "#000000", .25)}"/></radialGradient>'
            f'<radialGradient id="sh{seed}" cx=".32" cy=".3" r=".9"><stop offset=".45" stop-color="#000" stop-opacity="0"/>'
            '<stop offset=".8" stop-color="#000" stop-opacity=".65"/><stop offset="1" stop-color="#000" stop-opacity=".92"/>'
            '</radialGradient>'
            f'<clipPath id="pc{seed}"><circle r="{pr:.1f}"/></clipPath>'
            f'<filter id="bl{seed}" x="-20%" y="-60%" width="140%" height="220%">'
            '<feGaussianBlur stdDeviation="1.3"/></filter></defs>')
    surface = (f'<g clip-path="url(#pc{seed})"><circle r="{pr:.1f}" fill="url(#ps{seed})"/>'
               f'<g filter="url(#bl{seed})">{"".join(bands)}'
               f'<animateTransform attributeName="transform" type="translate" '
               f'values="{-pr * .5:.1f},0;{pr * .5:.1f},0;{-pr * .5:.1f},0" dur="{spin:.1f}s" '
               'repeatCount="indefinite"/></g>'
               f'<circle r="{pr:.1f}" fill="url(#sh{seed})"/></g>')
    if not ring:
        return defs + surface
    rx, ry = pr * 1.9, pr * .42
    arc = (lambda sweep, op, w: f'<path d="M{-rx:.1f},0 A{rx:.1f},{ry:.1f} 0 0,{sweep} {rx:.1f},0" fill="none" '
           f'stroke="{tones[1]}" stroke-width="{w}" opacity="{op}" transform="rotate(-14)"/>')
    return defs + arc(1, .45, pr * .14) + arc(1, .25, pr * .05) + surface + arc(0, .85, pr * .14) + arc(0, .5, pr * .05)


# ----------------------------------------------------------------- cards

def repo_card(name, description, language, stars_n, forks_n, planet, seed, w=400, h=190,
              primary=False, dashed=False, tag=""):
    head, tail = panel(w, h, border=ACCENT if primary else BORDER, dashed=dashed)
    pr = 54 if primary else 34
    px, py = (120 if primary else 88), h / 2 + 4
    tx = 250 if primary else 168
    fs = 24 if primary else (17 if len(name) <= 16 else 14.5 if len(name) <= 20 else 12.5)
    nm = name if len(name) <= 26 else name[:25] + "..."
    lines = wrap(description, 52 if primary else 27, 2 if primary else 3)
    desc = "".join(f'<text x="{tx}" y="{(94 if primary else 84) + i * (22 if primary else 19)}" '
                   f'font-family="{STIX}" font-size="{17 if primary else 15}" fill="{MUTED}">{escape(l)}</text>'
                   for i, l in enumerate(lines))
    my = h - (40 if primary else 30)
    meta = (f'<circle cx="{tx + 5}" cy="{my - 4}" r="5" fill="{LANG.get(language, MUTED)}"/>'
            f'<text x="{tx + 16}" y="{my}" font-family="{PLEX}" font-size="12" fill="{MUTED}">{escape(language or "")}</text>')
    nx = tx + 16 + 7.3 * len(language or "") + 22
    if stars_n:
        meta += (f'<text x="{nx:.0f}" y="{my}" font-family="{PLEX}" font-size="12" fill="{MUTED}">'
                 f'<tspan fill="{ACCENT}">*</tspan> {stars_n}</text>')
        nx += 7.3 * (len(str(stars_n)) + 2) + 22
    if forks_n:
        meta += (f'<text x="{nx:.0f}" y="{my}" font-family="{PLEX}" font-size="12" fill="{MUTED}">'
                 f'forks {forks_n}</text>')
    badge = (f'<text x="{w - 22}" y="30" font-family="{PLEX}" font-size="11.5" '
             f'fill="{ACCENT if primary else FAINT}" text-anchor="end">{escape(tag)}</text>') if tag else ""
    return embed("".join([
        svg_open(w, h, f"{name}: {description or ''}"), head,
        f'<g clip-path="url(#pclip)">{stars(w, h, 55 if primary else 34, seed)}',
        f'<g transform="translate({px},{py})">{planet_body(planet, pr, slug(seed), ring=primary)}</g>',
        f'<text x="{tx}" y="{56 if primary else 52}" font-family="{PLEX}" font-size="{fs}" font-weight="600" '
        f'fill="{TEXT}">{escape(nm)}</text>',
        desc, meta, badge, '</g>', tail, '</svg>']))


# ----------------------------------------------------------------- portal + ephemeris

def portal():
    w, h = 830, 96
    head, tail = panel(w, h)
    body = hero.wormhole(WX=60, WY=48, WR=30, label=False, cid="pthroat")
    return embed("".join([
        svg_open(w, h, "Through the wormhole to cthecosmos.com"), head,
        '<defs>', hero.wormhole_defs(), '</defs>',
        f'<g clip-path="url(#pclip)">{stars(w, h, 70, "portal")}{body}',
        f'<text x="118" y="42" font-family="{PLEX}" font-size="16" font-weight="600" fill="{TEXT}">'
        f'<tspan fill="{ACCENT}">$</tspan> ssh guest@cthecosmos.com</text>',
        f'<text x="118" y="68" font-family="{STIX}" font-size="16" font-style="italic" fill="{MUTED}">'
        'Through the wormhole: portfolio, projects, and the space blog.</text>',
        f'<text x="{w - 28}" y="54" font-family="{PLEX}" font-size="13" fill="{TEXT}" text-anchor="end">'
        'enter &#8594;</text>',
        '</g>', tail, '</svg>']))


EPH_COLS = [("", 22), ("body", 52), ("repository", 96), ("a", 372), ("e", 466), ("P", 540),
            ("Δω / orbit", 622), ("stars", 742)]


def ephemeris_header():
    w, h = 830, 34
    head, tail = panel(w, h, rx=6)
    cols = []
    for label, x in EPH_COLS[1:]:
        fam = STIX if any(ord(c) > 127 for c in label) or label in ("a", "e", "P") else PLEX
        style = ' font-style="italic"' if fam == STIX else ""
        size = 15 if fam == STIX else 11.5
        cols.append(f'<text x="{x}" y="22" font-family="{fam}"{style} font-size="{size}" fill="{MUTED}">{escape(label)}</text>')
    return embed("".join([svg_open(w, h, "Orbital elements"), head,
                          f'<g clip-path="url(#pclip)">{"".join(cols)}</g>', tail, '</svg>']))


def ephemeris_row(el, color):
    w, h = 830, 40
    head, tail = panel(w, h, rx=6)
    r = el["repo"]
    cells = [
        f'<circle cx="34" cy="20" r="6" fill="{color}"/>'
        f'<circle cx="32" cy="18" r="2.2" fill="#fff" opacity=".35"/>',
        f'<text x="{EPH_COLS[1][1]}" y="25" font-family="{STIX}" font-style="italic" font-size="17" '
        f'fill="{TEXT}">{el["letter"]}</text>',
        f'<text x="{EPH_COLS[2][1]}" y="25" font-family="{PLEX}" font-size="14" font-weight="600" '
        f'fill="{TEXT}">{escape(r["name"])}</text>',
        f'<text x="{EPH_COLS[3][1]}" y="25" font-family="{PLEX}" font-size="13" fill="{NUM}">{el["a"]:g}'
        f'<tspan font-family="{STIX}" font-style="italic" fill="{MUTED}"> r</tspan>'
        f'<tspan font-family="{STIX}" font-style="italic" fill="{MUTED}" font-size="10" baseline-shift="sub">s</tspan></text>',
        f'<text x="{EPH_COLS[4][1]}" y="25" font-family="{PLEX}" font-size="13" fill="{NUM}">{el["e"]:.2f}</text>',
        f'<text x="{EPH_COLS[5][1]}" y="25" font-family="{PLEX}" font-size="13" fill="{NUM}">{el["P"] / 3600:.1f}'
        f'<tspan fill="{MUTED}"> h</tspan></text>',
        f'<text x="{EPH_COLS[6][1]}" y="25" font-family="{PLEX}" font-size="13" fill="{NUM}">{math.degrees(el["dw"]):.1f}°</text>',
        f'<text x="{EPH_COLS[7][1]}" y="25" font-family="{PLEX}" font-size="13" fill="{ACCENT}">'
        f'{r["stargazers_count"]}</text>',
        f'<text x="{w - 22}" y="25" font-family="{PLEX}" font-size="13" fill="{MUTED}" text-anchor="end">&#8594;</text>',
    ]
    return embed("".join([svg_open(w, h, f'{el["letter"]}: {r["name"]}'), head,
                          f'<g clip-path="url(#pclip)">{"".join(cells)}</g>', tail, '</svg>']))


# ----------------------------------------------------------------- section header

def banner(num, cmd, note):
    w, h = 830, 48
    head, tail = panel(w, h)
    return embed("".join([
        svg_open(w, h, cmd), head,
        f'<g clip-path="url(#pclip)">{stars(w, h, 50, "ban" + num)}',
        f'<text x="22" y="30" font-family="{PLEX}" font-size="16" fill="{TEXT}">'
        f'<tspan fill="{ACCENT}">~ $</tspan> <tspan font-weight="600">{escape(cmd)}</tspan>'
        f'<tspan fill="{ACCENT}">_<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.5;.5;1" '
        'dur="1.1s" repeatCount="indefinite"/></tspan></text>',
        (f'<text x="{w - 22}" y="30" font-family="{STIX}" font-style="italic" font-size="15" fill="{FAINT}" '
         f'text-anchor="end">{escape(note)}</text>') if note else "",
        '</g>', tail, '</svg>']))


# ----------------------------------------------------------------- toolkit (ls output)

def toolkit(rows):
    w, row_h, top = 830, 40, 22
    h = top * 2 + row_h * len(rows) - 6
    head, tail = panel(w, h)
    out = []
    for i, (cat, items) in enumerate(rows):
        y = top + 24 + i * row_h
        out.append(f'<text x="26" y="{y}" font-family="{PLEX}" font-size="14.5" font-weight="600" '
                   f'fill="{DIR}">{escape(cat)}/</text>')
        for j, it in enumerate(items):
            out.append(f'<text x="{190 + j * 126}" y="{y}" font-family="{PLEX}" font-size="14.5" '
                       f'fill="{TEXT}">{escape(it)}</text>')
    return embed("".join([svg_open(w, h, "Toolkit"), head,
                          f'<g clip-path="url(#pclip)">{stars(w, h, 110, "tool")}{"".join(out)}</g>',
                          tail, '</svg>']))


# ----------------------------------------------------------------- telemetry (gh api JSON)

def telemetry(n_repos, stars_n, contribs, followers, langs):
    w, h = 830, 196
    head, tail = panel(w, h)
    rows = [("public_repos", n_repos), ("stargazers", stars_n), ("followers", followers)]
    if contribs is not None:
        rows.append(("contributions_1y", contribs))
    out = [f'<text x="30" y="40" font-family="{PLEX}" font-size="14" fill="{MUTED}">{{</text>']
    for i, (k, v) in enumerate(rows):
        comma = "," if i < len(rows) - 1 else ""
        out.append(f'<text x="48" y="{64 + i * 24}" font-family="{PLEX}" font-size="14" fill="{MUTED}">'
                   f'<tspan fill="{DIR}">"{k}"</tspan>: <tspan fill="{NUM}">{v}</tspan>{comma}</text>')
    out.append(f'<text x="30" y="{64 + len(rows) * 24}" font-family="{PLEX}" font-size="14" fill="{MUTED}">}}</text>')
    total = sum(v for _, v in langs) or 1
    bx, bw, by = 470, 324, 56
    out.append(f'<text x="{bx}" y="{by - 16}" font-family="{STIX}" font-style="italic" font-size="15" '
               f'fill="{MUTED}">languages, by bytes of code</text>')
    out.append(f'<clipPath id="bar"><rect x="{bx}" y="{by}" width="{bw}" height="8" rx="4"/></clipPath><g clip-path="url(#bar)">')
    xx = bx
    for name, v in langs:
        seg = bw * v / total
        out.append(f'<rect x="{xx:.1f}" y="{by}" width="{seg + .5:.1f}" height="8" fill="{LANG.get(name, MUTED)}"/>')
        xx += seg
    out.append('</g>')
    for i, (name, v) in enumerate(langs[:6]):
        lx, ly = bx + (i % 2) * 165, by + 36 + (i // 2) * 24
        out.append(f'<circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{LANG.get(name, MUTED)}"/>'
                   f'<text x="{lx + 16}" y="{ly}" font-family="{PLEX}" font-size="13" fill="{TEXT}">{escape(name)} '
                   f'<tspan fill="{MUTED}">{100 * v / total:.1f}%</tspan></text>')
    return embed("".join([svg_open(w, h, "GitHub stats"), head,
                          f'<g clip-path="url(#pclip)">{stars(w, h, 80, "tel")}',
                          f'<line x1="440" y1="28" x2="440" y2="{h - 28}" stroke="{BORDER}"/>',
                          "".join(out), '</g>', tail, '</svg>']))


# ----------------------------------------------------------------- contact + footer

def channel(label, sub, dot):
    w, h = 300, 62
    head, tail = panel(w, h)
    return embed("".join([svg_open(w, h, label), head,
                          f'<g clip-path="url(#pclip)">{stars(w, h, 24, "ch" + label)}',
                          f'<circle cx="26" cy="31" r="5" fill="{dot}"/>',
                          f'<text x="44" y="28" font-family="{PLEX}" font-size="15" font-weight="600" fill="{TEXT}">'
                          f'{escape(label)}</text>',
                          f'<text x="44" y="47" font-family="{STIX}" font-style="italic" font-size="14" fill="{MUTED}">'
                          f'{escape(sub)}</text>', '</g>', tail, '</svg>']))


def footer():
    w, h = 830, 100
    head, tail = panel(w, h)
    q1, q2 = "Life is a bit. You are either 0 or a 1.", "I like to toggle every now and then."
    bit = (f'<g transform="translate(415,30)" font-family="{PLEX}" font-size="15" text-anchor="middle">'
           f'<rect x="-13" y="-13" width="26" height="26" rx="4" fill="none" stroke="{BORDER}"/>'
           f'<text y="5.5" fill="{TEXT}">0<animate attributeName="opacity" values="1;1;0;0;1" '
           'keyTimes="0;.48;.5;.98;1" dur="4s" repeatCount="indefinite"/></text>'
           f'<text y="5.5" fill="{ACCENT}" opacity="0">1<animate attributeName="opacity" values="0;0;1;1;0" '
           'keyTimes="0;.48;.5;.98;1" dur="4s" repeatCount="indefinite"/></text></g>')
    return embed("".join([svg_open(w, h, q1 + " " + q2), head,
                          f'<g clip-path="url(#pclip)">{stars(w, h, 70, "foot")}{bit}',
                          f'<g font-family="{STIX}" font-style="italic" text-anchor="middle">'
                          f'<text x="415" y="68" font-size="18" fill="{TEXT}">{escape(q1)}</text>'
                          f'<text x="415" y="89" font-size="18" fill="{MUTED}">{escape(q2)}</text></g>',
                          '</g>', tail, '</svg>']))


# ----------------------------------------------------------------- data

def fetch_languages(user, repos, token):
    totals = {}
    for r in repos:
        try:
            for k, v in gh(f"{API}/repos/{user}/{r['name']}/languages", token).items():
                totals[k] = totals.get(k, 0) + v
        except Exception:
            if r.get("language"):
                totals[r["language"]] = totals.get(r["language"], 0) + 1
    return sorted(totals.items(), key=lambda kv: -kv[1])[:6]


def fetch_followers(user, token):
    try:
        return gh(f"{API}/users/{user}", token).get("followers", 0)
    except Exception:
        return 0


# ----------------------------------------------------------------- build

def build_all(root, user, repos, contrib, langs, followers):
    a = os.path.join(root, "assets")
    for d in ("planets", "uncharted"):
        shutil.rmtree(os.path.join(a, d), ignore_errors=True)
    if os.path.isdir(a):
        for f in os.listdir(a):
            if f.startswith("ephemeris-") or f in ("star-chart.svg",):
                os.remove(os.path.join(a, f))

    contribs, days = contrib if contrib else (None, None)
    by_name = {r["name"]: r for r in repos}
    desc = lambda r: DESCRIPTIONS.get(r["name"]) or r.get("description") or ""

    shown = [(PRIMARY, "saturn")] + FEATURED
    present = [(n, p) for n, p in shown if n in by_name]
    for n, _ in shown:
        if n not in by_name:
            print(f"warn: featured repo {n} not found (private, renamed or a fork?)", file=sys.stderr)
    palette = {n: PLANETS[p][0] for n, p in present}

    # hero: innermost orbit = most recently pushed
    inner_first = sorted((by_name[n] for n, _ in present), key=lambda r: r["pushed_at"] or "", reverse=True)
    hero_svg, els = hero.build(inner_first, palette, days)
    write(f"{a}/cosmos.svg", hero_svg)
    write(f"{a}/portal.svg", portal())
    write(f"{a}/ephemeris-head.svg", ephemeris_header())
    eph_md = ['<img src="assets/ephemeris-head.svg" width="100%" alt="Orbital elements">']
    for el in els:
        r = el["repo"]
        write(f"{a}/ephemeris-{el['letter']}.svg", ephemeris_row(el, palette[r["name"]]))
        eph_md.append(link_img(r["html_url"], f"assets/ephemeris-{el['letter']}.svg", "100%",
                               f'{el["letter"]}: {r["name"]} (a = {el["a"]:g} r_s, e = {el["e"]:.2f})'))

    for num, cmd, note in BANNERS:
        write(f"{a}/banner-{num}.svg", banner(num, cmd, note))
    write(f"{a}/toolkit.svg", toolkit(TOOLKIT))
    write(f"{a}/telemetry.svg", telemetry(len(repos), sum(r["stargazers_count"] for r in repos),
                                          contribs, followers, langs))
    write(f"{a}/channel-linkedin.svg", channel("LinkedIn", "in/t-yashwanth-naidu", "#0a66c2"))
    write(f"{a}/channel-site.svg", channel("cthecosmos.com", "portfolio and the space blog", ACCENT))
    write(f"{a}/footer.svg", footer())

    cards = []
    if PRIMARY in by_name:
        r = by_name[PRIMARY]
        write(f"{a}/planets/{slug(PRIMARY)}.svg",
              repo_card(r["name"], desc(r), r.get("language"), r["stargazers_count"], r.get("forks_count"),
                        "saturn", r["name"], w=830, h=220, primary=True, tag="most starred"))
        cards.append(link_img(r["html_url"], f"assets/planets/{slug(PRIMARY)}.svg", "100%",
                              f'{r["name"]} - {desc(r)}'))
    row = []
    for n, planet in FEATURED:
        if n not in by_name:
            continue
        r = by_name[n]
        write(f"{a}/planets/{slug(n)}.svg",
              repo_card(r["name"], desc(r), r.get("language"), r["stargazers_count"], r.get("forks_count"),
                        planet, r["name"]))
        row.append(link_img(r["html_url"], f"assets/planets/{slug(n)}.svg", "49%", f'{r["name"]} - {desc(r)}'))
    planets_md = "\n".join(cards) + '\n</p>\n<p align="center">\n' + "\n".join(row)

    unch = []
    for p in UNCHARTED:
        write(f"{a}/uncharted/{p['id']}.svg",
              repo_card(p["name"], p["description"], p["language"], 0, 0, p["planet"], p["id"],
                        dashed=True, tag="on the portfolio"))
        unch.append(link_img(PORTFOLIO, f"assets/uncharted/{p['id']}.svg", "49%", f'{p["name"]} - {p["description"]}'))

    tpl = open(os.path.join(root, "scripts", "README.template.md"), encoding="utf-8").read()
    write(os.path.join(root, "README.md"),
          tpl.replace("{{EPHEMERIS}}", "\n".join(eph_md))
             .replace("{{PLANETS}}", planets_md)
             .replace("{{UNCHARTED}}", "\n".join(unch))
             .replace("{{PORTFOLIO}}", PORTFOLIO))
    return len(els)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--root", default=".")
    a = ap.parse_args()
    token = os.environ.get("GITHUB_TOKEN")
    repos = fetch_repos(a.user, token)
    contrib = fetch_contributions(a.user, token)
    langs = fetch_languages(a.user, repos, token)
    followers = fetch_followers(a.user, token)
    print(f"built: {build_all(a.root, a.user, repos, contrib, langs, followers)} orbiting repos")


if __name__ == "__main__":
    main()