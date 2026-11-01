#!/usr/bin/env python3
"""
Build the whole profile README as one universe.

  assets/cosmos.svg            hero: repos orbiting a black hole (links to website)
  assets/banner-NN.svg         animated section banners
  assets/star-chart.svg        skills as constellations
  assets/planets/<repo>.svg    one card per public repo -> links to that repo
  assets/uncharted/<id>.svg    projects without a public repo -> link to website
  assets/telemetry.svg         repos / stars / contributions / language spectrum
  assets/channel-*.svg         contact buttons
  assets/footer.svg            quote with a toggling bit
  README.md                    rendered from scripts/README.template.md

GitHub serves each SVG as a plain image, so links can't live inside an SVG.
Every clickable thing is therefore its own image wrapped in <a>.

Stdlib only. Usage:
  GITHUB_TOKEN=... python scripts/universe.py --user T-Yashwanth-Naidu
"""
import argparse
import math
import os
import re
import sys
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_cosmos as gc  # noqa: E402
from generate_cosmos import FONT, h01, mix, LANG_COLORS, DEFAULT_COLOR  # noqa: E402

SITE = "https://cthecosmos.com"
LINKEDIN = "https://www.linkedin.com/in/t-yashwanth-naidu/"

# ----------------------------------------------------------------- content
# Edit these, not the SVG code.

STAR_CHART = [
    ("LANGUAGES",  "#8fb3e8", ["C", "C++", "Python", "CUDA", "Assembly"]),
    ("AUTOMOTIVE", "#ffb05a", ["UDS", "DoIP", "SOVD", "AUTOSAR", "CAN-FD"]),
    ("SYSTEMS",    "#9ae6b4", ["Linux", "QNX", "ROS2", "GDB", "OpenACC"]),
    ("SILICON",    "#e7b8ff", ["Orin AGX", "Aurix TC375", "TIVA-C", "ESP32", "8051"]),
    ("SAFETY",     "#ff8fa3", ["ISO 26262", "MISRA C", "EN 50128", "VectorCAST", "Simulink"]),
]

UNCHARTED = [  # projects without a public repo -> website
    dict(id="gpu-knn", name="GPU KNN", language="Cuda",
         description="CUDA-parallel K-nearest neighbors, benchmarked against a CPU baseline"),
    dict(id="aeb", name="AEB System", language="MATLAB",
         description="Emergency braking from radar, LiDAR and camera sensor fusion"),
    dict(id="mlsa", name="Multi-Level Access", language="C",
         description="8051 security access system with GSM, UART and I2C"),
    dict(id="biometric", name="Secure Biometric", language="C",
         description="AES-encrypted biometric auth on Arduino, tested against MITM and DoS"),
]

BANNERS = [  # (number, title, subtitle, accent)
    ("01", "MISSION LOG", "who is flying this ship", "#ffb05a"),
    ("02", "STAR CHART", "the stack, as constellations", "#8fb3e8"),
    ("03", "PLANETS", "public repos - click to land", "#9ae6b4"),
    ("04", "UNCHARTED WORLDS", "built, not public - logs on cthecosmos", "#e7b8ff"),
    ("05", "TRANSMISSIONS", "papers and articles", "#ff8fa3"),
    ("06", "TELEMETRY", "live from the GitHub API", "#7fd3ff"),
    ("07", "OPEN CHANNEL", "say hi", "#ffd56b"),
]

LANG_COLORS = dict(LANG_COLORS, MATLAB="#e16737", Java="#b07219", Go="#00add8")


# ----------------------------------------------------------------- helpers

def svg_open(w, h, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img"><title>{escape(title)}</title>')


def dust(w, h, n, salt, y0=0, y1=None, twinkle=0):
    y1 = h if y1 is None else y1
    out = []
    for i in range(n):
        k = f"{salt}{i}"
        x, y = h01(k, "x") * w, y0 + h01(k, "y") * (y1 - y0)
        r = .4 + h01(k, "r") * .9
        op = .25 + h01(k, "o") * .5
        if i < twinkle:
            d = 2 + h01(k, "d") * 4
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r + .4:.2f}" fill="#fff3d4">'
                       f'<animate attributeName="opacity" values=".15;1;.15" dur="{d:.1f}s" '
                       f'begin="-{h01(k, "b") * d:.1f}s" repeatCount="indefinite"/></circle>')
        else:
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" fill="#cfd8ff" opacity="{op:.2f}"/>')
    return "".join(out)


def panel(w, h, rx=14, accent="#3a4380"):
    return (f'<defs><linearGradient id="pbg" x1="0" y1="0" x2="1" y2="1">'
            f'<stop offset="0" stop-color="#05060f"/><stop offset="1" stop-color="#0e1438"/></linearGradient>'
            f'<clipPath id="pclip"><rect width="{w}" height="{h}" rx="{rx}"/></clipPath></defs>'
            f'<rect width="{w}" height="{h}" rx="{rx}" fill="url(#pbg)"/>'), \
           (f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="{rx}" fill="none" '
            f'stroke="{accent}" stroke-opacity=".55"/>')


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
        lines[-1] = lines[-1][: width - 2].rstrip() + ".."
    return lines


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def write(path, content):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ----------------------------------------------------------------- planet card

CW, CH = 400, 210


def planet_card(name, description, language, stars, tag, seed, dashed=False):
    color = LANG_COLORS.get(language or "", DEFAULT_COLOR)
    px, py = 96, 108
    pr = 30 + min(16, 5 * math.log10(stars + 1)) if stars is not None else 32
    bg, border = panel(CW, CH, accent=color)
    if dashed:
        border = border.replace('stroke-opacity=".55"', 'stroke-opacity=".6" stroke-dasharray="5 5"')

    bands = []
    for i in range(5):
        k = f"{seed}b{i}"
        y = (h01(k, "y") - .5) * 1.6 * pr
        hgt = 3 + h01(k, "h") * 8
        tone = mix(color, "#ffffff" if i % 2 else "#000000", .25 + .2 * h01(k, "t"))
        bands.append(f'<ellipse cx="0" cy="{y:.1f}" rx="{pr * 1.6:.1f}" ry="{hgt:.1f}" '
                     f'fill="{tone}" opacity=".55"/>')
    spin = 9 + h01(seed, "spin") * 8
    surface = (f'<g clip-path="url(#pc)"><circle r="{pr:.1f}" fill="url(#psurf)"/>'
               f'<g filter="url(#bl)">{"".join(bands)}'
               f'<animateTransform attributeName="transform" type="translate" '
               f'values="{-pr * .6:.1f},0;{pr * .6:.1f},0;{-pr * .6:.1f},0" dur="{spin:.1f}s" '
               'repeatCount="indefinite"/></g>'
               f'<circle r="{pr:.1f}" fill="url(#pshade)"/></g>')
    ring = ""
    if stars and stars >= 10:
        ring_back = (f'<path d="M{-pr * 1.75:.1f},0 A{pr * 1.75:.1f},{pr * .42:.1f} 0 0,1 {pr * 1.75:.1f},0" '
                     f'fill="none" stroke="{mix(color, "#ffffff", .45)}" stroke-width="3" opacity=".55" '
                     'transform="rotate(-16)"/>')
        ring_front = ring_back.replace("0 0,1", "0 0,0").replace('opacity=".55"', 'opacity=".9"')
        ring = (ring_back, ring_front)
    moon_path = f"M{-pr - 18:.1f},0 A{pr + 18:.1f},{(pr + 18) * .28:.1f} 0 1,0 {pr + 18:.1f},0 " \
                f"A{pr + 18:.1f},{(pr + 18) * .28:.1f} 0 1,0 {-pr - 18:.1f},0"
    moon = (f'<circle r="3.2" fill="#e8ecff"><animateMotion dur="{6 + h01(seed, "m") * 4:.1f}s" '
            f'repeatCount="indefinite" path="{moon_path}"/></circle>')

    tx = 186
    lines = wrap(description or "no description yet", 26, 3)
    desc = "".join(f'<text x="{tx}" y="{92 + i * 17}" font-size="12.5" fill="#a7b2e0">{escape(l)}</text>'
                   for i, l in enumerate(lines))
    fs = 19 if len(name) <= 15 else 16 if len(name) <= 19 else 14
    nm = name if len(name) <= 24 else name[:23] + "."
    meta = f'<circle cx="{tx + 5}" cy="{CH - 33}" r="5" fill="{color}"/>' \
           f'<text x="{tx + 16}" y="{CH - 29}" font-size="12" fill="#c9d2ff">{escape(language or "n/a")}</text>'
    if stars:
        meta += f'<text x="{CW - 22}" y="{CH - 29}" font-size="12" fill="#ffd56b" text-anchor="end">{stars} *</text>'
    tagline = f'<text x="{CW - 22}" y="28" font-size="10.5" fill="{color}" text-anchor="end" ' \
              f'letter-spacing="1.5">{escape(tag)}</text>'

    return "".join([
        svg_open(CW, CH, f"{name}: {description or ''}"),
        bg,
        '<defs>'
        f'<radialGradient id="psurf" fx=".35" fy=".3"><stop offset="0" stop-color="{mix(color, "#ffffff", .5)}"/>'
        f'<stop offset=".6" stop-color="{color}"/><stop offset="1" stop-color="{mix(color, "#000000", .55)}"/></radialGradient>'
        '<radialGradient id="pshade" cx=".35" cy=".35" r=".75"><stop offset=".55" stop-color="#000" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#000" stop-opacity=".7"/></radialGradient>'
        f'<radialGradient id="patm"><stop offset=".7" stop-color="{color}" stop-opacity=".35"/>'
        f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>'
        f'<clipPath id="pc"><circle r="{pr:.1f}"/></clipPath>'
        '<filter id="bl" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="1.6"/></filter>'
        '</defs>',
        f'<g clip-path="url(#pclip)">{dust(CW, CH, 40, seed, twinkle=8)}',
        f'<g transform="translate({px},{py})">',
        f'<circle r="{pr + 14:.1f}" fill="url(#patm)"/>',
        ring[0] if ring else "", surface, ring[1] if ring else "", moon, '</g>',
        f'<g font-family="{FONT}">',
        f'<text x="{tx}" y="60" font-size="{fs}" font-weight="700" fill="#eef1ff">{escape(nm)}</text>',
        desc, meta, tagline, '</g></g>', border, '</svg>'])


# ----------------------------------------------------------------- banners

BW, BH = 830, 64


def banner(num, title, subtitle, accent):
    bg, border = panel(BW, BH, rx=12, accent=accent)
    line_y = 40
    return "".join([
        svg_open(BW, BH, f"{num} {title}"), bg,
        f'<g clip-path="url(#pclip)">{dust(BW, BH, 70, "ban" + num, twinkle=14)}',
        f'<g font-family="{FONT}">'
        f'<text x="24" y="{line_y}" font-size="13" fill="{accent}" letter-spacing="2">// {num}</text>'
        f'<text x="{24 + 13 * (len(num) + 4)}" y="{line_y + 1}" font-size="20" font-weight="700" fill="#eef1ff" '
        f'letter-spacing="3">{escape(title)}</text>'
        f'<text x="{BW - 24}" y="{line_y}" font-size="12" fill="#8f9ad0" text-anchor="end">{escape(subtitle)}</text></g>',
        f'<line x1="24" y1="{BH - 10}" x2="{BW - 24}" y2="{BH - 10}" stroke="{accent}" stroke-opacity=".25"/>',
        f'<circle r="2.6" fill="{accent}"><animateMotion dur="5.5s" repeatCount="indefinite" '
        f'path="M24,{BH - 10} L{BW - 24},{BH - 10}"/></circle>',
        f'<circle r="9" fill="{accent}" opacity=".18"><animateMotion dur="5.5s" repeatCount="indefinite" '
        f'path="M24,{BH - 10} L{BW - 24},{BH - 10}"/></circle>',
        '</g>', border, '</svg>'])


# ----------------------------------------------------------------- star chart

SW, SH = 830, 340


def star_chart(chart):
    bg, border = panel(SW, SH, accent="#3a4380")
    centers = [(145, 110), (415, 110), (685, 110), (280, 250), (550, 250)]
    out = []
    for (title, color, skills), (cx, cy) in zip(chart, centers):
        n = len(skills)
        span = 186
        pts = []
        for i, s in enumerate(skills):
            x = cx - span / 2 + span * i / max(n - 1, 1)
            y = cy + (14 if i % 2 else -14) + (h01(s, "jit") - .5) * 14
            pts.append((x, y, s))
        poly = " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in pts)
        out.append(f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-opacity=".45" '
                   'stroke-width="1.2" stroke-dasharray="1 0">'
                   '<animate attributeName="stroke-opacity" values=".25;.6;.25" dur="5s" repeatCount="indefinite"/>'
                   '</polyline>')
        out.append(f'<text x="{cx}" y="{cy - 50}" font-size="12" fill="{color}" text-anchor="middle" '
                   f'letter-spacing="2.5">{escape(title)}</text>')
        for i, (x, y, s) in enumerate(pts):
            d = 2.4 + h01(s, "tw") * 3
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="9" fill="{color}" opacity=".16"/>'
                       f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.4" fill="#fffaf0">'
                       f'<animate attributeName="r" values="2.6;4.2;2.6" dur="{d:.1f}s" '
                       f'begin="-{h01(s, "b") * d:.1f}s" repeatCount="indefinite"/></circle>')
            ly = y + 24 if i % 2 else y - 15
            out.append(f'<text x="{x:.1f}" y="{ly:.1f}" font-size="12" fill="#d8deff" '
                       f'text-anchor="middle">{escape(s)}</text>')
    return "".join([svg_open(SW, SH, "Skills as constellations"), bg,
                     f'<g clip-path="url(#pclip)">{dust(SW, SH, 160, "chart", twinkle=30)}',
                     f'<g font-family="{FONT}">{"".join(out)}</g></g>', border, '</svg>'])


# ----------------------------------------------------------------- telemetry

TW, TH = 830, 200


def telemetry(n_repos, stars, contribs, followers, langs):
    bg, border = panel(TW, TH, accent="#2f6f8f")
    cells = [("REPOS", n_repos), ("STARS", stars),
             ("CONTRIB / 1Y" if contribs is not None else "FOLLOWERS",
              contribs if contribs is not None else followers)]
    out = []
    for i, (label, val) in enumerate(cells):
        x = 40 + i * 140
        out.append(f'<text x="{x}" y="86" font-size="34" font-weight="700" fill="#eef1ff">{val}</text>'
                   f'<text x="{x}" y="110" font-size="11" fill="#7fd3ff" letter-spacing="2">{label}</text>')
    total = sum(v for _, v in langs) or 1
    bx, bw, by = 470, 320, 62
    out.append(f'<text x="{bx}" y="{by - 14}" font-size="11" fill="#7fd3ff" letter-spacing="2">LANGUAGE SPECTRUM</text>')
    x = bx
    for name, v in langs:
        w = bw * v / total
        out.append(f'<rect x="{x:.1f}" y="{by}" width="{max(w - 1.5, 1):.1f}" height="12" rx="3" '
                   f'fill="{LANG_COLORS.get(name, DEFAULT_COLOR)}"/>')
        x += w
    for i, (name, v) in enumerate(langs[:6]):
        lx, ly = bx + (i % 2) * 165, by + 36 + (i // 2) * 20
        out.append(f'<circle cx="{lx + 5}" cy="{ly - 4}" r="4.5" fill="{LANG_COLORS.get(name, DEFAULT_COLOR)}"/>'
                   f'<text x="{lx + 16}" y="{ly}" font-size="12" fill="#c9d2ff">{escape(name)} '
                   f'{100 * v / total:.0f}%</text>')
    scan = (f'<rect x="0" y="0" width="60" height="{TH}" fill="url(#scan)">'
            f'<animate attributeName="x" values="-60;{TW}" dur="6s" repeatCount="indefinite"/></rect>')
    return "".join([svg_open(TW, TH, "GitHub telemetry"), bg,
                    '<defs><linearGradient id="scan" x1="0" x2="1"><stop offset="0" stop-color="#7fd3ff" stop-opacity="0"/>'
                    '<stop offset=".5" stop-color="#7fd3ff" stop-opacity=".08"/>'
                    '<stop offset="1" stop-color="#7fd3ff" stop-opacity="0"/></linearGradient></defs>',
                    f'<g clip-path="url(#pclip)">{dust(TW, TH, 90, "tel", twinkle=16)}{scan}',
                    f'<line x1="430" y1="36" x2="430" y2="{TH - 36}" stroke="#2f6f8f" stroke-opacity=".6"/>',
                    f'<g font-family="{FONT}">{"".join(out)}',
                    f'<text x="40" y="{TH - 30}" font-size="10.5" fill="#6f7bb0">auto-refreshed daily by GitHub Actions</text>'
                    '</g></g>', border, '</svg>'])


# ----------------------------------------------------------------- channels + footer

def channel(label, sub, accent):
    w, h = 300, 64
    bg, border = panel(w, h, rx=32, accent=accent)
    return "".join([svg_open(w, h, label), bg,
                    f'<g clip-path="url(#pclip)">{dust(w, h, 30, "ch" + label, twinkle=6)}',
                    f'<circle cx="34" cy="32" r="12" fill="{accent}" opacity=".2">'
                    '<animate attributeName="r" values="9;15;9" dur="2.4s" repeatCount="indefinite"/></circle>',
                    f'<circle cx="34" cy="32" r="5" fill="{accent}"/>',
                    f'<g font-family="{FONT}"><text x="60" y="29" font-size="16" font-weight="700" fill="#eef1ff">'
                    f'{escape(label)}</text><text x="60" y="47" font-size="11" fill="#8f9ad0">{escape(sub)}</text></g>',
                    '</g>', border, '</svg>'])


def footer():
    w, h = 830, 110
    bg, border = panel(w, h, accent="#3a4380")
    q1, q2 = "Life is a bit. You are either 0 or a 1.", "I like to toggle every now and then."
    bit = ('<g transform="translate(415,30)">'
           '<rect x="-16" y="-16" width="32" height="32" rx="7" fill="#11173f" stroke="#ffd56b" stroke-opacity=".7"/>'
           '<text y="7" text-anchor="middle" font-size="18" font-weight="700" fill="#ffd56b">0'
           '<animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;.45;.5;.95;1" dur="3s" repeatCount="indefinite"/></text>'
           '<text y="7" text-anchor="middle" font-size="18" font-weight="700" fill="#7fd3ff" opacity="0">1'
           '<animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;.45;.5;.95;1" dur="3s" repeatCount="indefinite"/></text>'
           '</g>')
    return "".join([svg_open(w, h, q1 + " " + q2), bg,
                    f'<g clip-path="url(#pclip)">{dust(w, h, 80, "foot", twinkle=20)}',
                    f'<g font-family="{FONT}">{bit}'
                    f'<text x="415" y="72" font-size="15" fill="#e3e8ff" text-anchor="middle">{escape(q1)}</text>'
                    f'<text x="415" y="94" font-size="15" fill="#a7b2e0" text-anchor="middle">{escape(q2)}</text></g>',
                    '</g>', border, '</svg>'])


# ----------------------------------------------------------------- data

def fetch_languages(user, repos, token):
    totals = {}
    for r in repos:
        try:
            for k, v in gc.gh(f"{gc.API}/repos/{user}/{r['name']}/languages", token).items():
                totals[k] = totals.get(k, 0) + v
        except Exception:
            if r.get("language"):
                totals[r["language"]] = totals.get(r["language"], 0) + 1
    return sorted(totals.items(), key=lambda kv: -kv[1])[:8]


def fetch_followers(user, token):
    try:
        return gc.gh(f"{gc.API}/users/{user}", token).get("followers", 0)
    except Exception:
        return 0


# ----------------------------------------------------------------- build

def build_all(root, user, repos, contrib, langs, followers):
    a = os.path.join(root, "assets")
    contribs, _ = contrib if contrib else (None, None)

    write(f"{a}/cosmos.svg", gc.build(repos, contrib, "Yashwanth Naidu",
                                      "embedded software | onboard diagnostics for autonomous trucks", 9))
    for num, title, sub, acc in BANNERS:
        write(f"{a}/banner-{num}.svg", banner(num, title, sub, acc))
    write(f"{a}/star-chart.svg", star_chart(STAR_CHART))
    write(f"{a}/telemetry.svg", telemetry(len(repos), sum(r["stargazers_count"] for r in repos),
                                          contribs, followers, langs))
    write(f"{a}/channel-linkedin.svg", channel("LinkedIn", "/in/t-yashwanth-naidu", "#5fa8ff"))
    write(f"{a}/channel-site.svg", channel("cthecosmos.com", "writing, logs, projects", "#ffb05a"))
    write(f"{a}/footer.svg", footer())

    planet_md = []
    for r in sorted(repos, key=lambda r: (-r["stargazers_count"], r["name"].lower())):
        s = slug(r["name"])
        write(f"{a}/planets/{s}.svg", planet_card(r["name"], r.get("description"), r.get("language"),
                                                  r["stargazers_count"], "PLANET", r["name"]))
        alt = escape(f'{r["name"]} - {r.get("description") or "repository"}', {'"': "&quot;"})
        planet_md.append(f'<a href="{r["html_url"]}"><img src="assets/planets/{s}.svg" width="49%" alt="{alt}"></a>')

    unch_md = []
    for p in UNCHARTED:
        write(f"{a}/uncharted/{p['id']}.svg", planet_card(p["name"], p["description"], p["language"],
                                                         None, "UNCHARTED", p["id"], dashed=True))
        alt = escape(f'{p["name"]} - {p["description"]}', {'"': "&quot;"})
        unch_md.append(f'<a href="{SITE}"><img src="assets/uncharted/{p["id"]}.svg" width="49%" alt="{alt}"></a>')

    tpl = open(os.path.join(root, "scripts", "README.template.md"), encoding="utf-8").read()
    readme = tpl.replace("{{PLANETS}}", "\n".join(planet_md)).replace("{{UNCHARTED}}", "\n".join(unch_md))
    write(os.path.join(root, "README.md"), readme)
    return len(repos)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--root", default=".")
    a = ap.parse_args()
    token = os.environ.get("GITHUB_TOKEN")
    repos = gc.fetch_repos(a.user, token)
    contrib = gc.fetch_contributions(a.user, token)
    langs = fetch_languages(a.user, repos, token)
    followers = fetch_followers(a.user, token)
    n = build_all(a.root, a.user, repos, contrib, langs, followers)
    print(f"built universe: {n} planets")


if __name__ == "__main__":
    main()
