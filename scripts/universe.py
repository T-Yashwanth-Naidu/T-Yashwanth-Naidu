#!/usr/bin/env python3
"""
Build the profile README as one space-themed page.

  assets/cosmos.svg              hero: featured repos orbiting a black hole -> portfolio
  assets/banner-NN.svg           section headers
  assets/toolkit.svg             skills
  assets/planets/<repo>.svg      featured repos -> each links to its repo
  assets/uncharted/<id>.svg      projects without a public repo -> portfolio
  assets/telemetry.svg           live GitHub stats
  assets/channel-*.svg           contact buttons
  assets/footer.svg              quote
  README.md                      rendered from scripts/README.template.md

GitHub serves each SVG as a plain image, so links can't live inside one.
Every clickable thing is its own image wrapped in <a>.

Stdlib only.  GITHUB_TOKEN=... python scripts/universe.py --user T-Yashwanth-Naidu
"""
import argparse
import math
import os
import re
import sys
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_cosmos as gc  # noqa: E402
from generate_cosmos import h01, mix  # noqa: E402

SANS = gc.FONT
MONO = gc.MONO

PORTFOLIO = "https://cthecosmos.com/?page_id=4955"
SITE = "https://cthecosmos.com"
LINKEDIN = "https://www.linkedin.com/in/t-yashwanth-naidu/"

# ----------------------------------------------------------------- palette
# GitHub dark greys + one warm starlight accent. Nothing neon.
BG0, BG1 = "#04060a", "#0b0f17"
BORDER = "#30363d"
TEXT, MUTED, FAINT = "#e6edf3", "#8b949e", "#6e7681"
ACCENT = "#d9a85b"

# GitHub's own language colors (only used for the small language dot).
LANG = {"C": "#555555", "C++": "#f34b7d", "Python": "#3572A5", "JavaScript": "#f1e05a",
        "TypeScript": "#3178c6", "Cuda": "#3A4E3A", "Assembly": "#6E4C13", "MATLAB": "#e16737",
        "Shell": "#89e051", "HTML": "#e34c26", "CMake": "#DA3434", "Makefile": "#427819"}

# Real-planet tones: (base, band tones)
PLANETS = {
    "saturn":  ("#d6bf8e", ["#bfa06d", "#ecdcb5", "#c9ad7c"]),
    "jupiter": ("#c8a47a", ["#a9784e", "#e3cfae", "#8c5a3c"]),
    "mars":    ("#b25a3c", ["#8e4128", "#c87a55", "#9c4a30"]),
    "neptune": ("#4f6fae", ["#3d5a96", "#7c9bd1", "#46659f"]),
    "mercury": ("#8e8a85", ["#75716c", "#a8a49f", "#807c77"]),
    "venus":   ("#d8c59c", ["#c8b282", "#e9dcbd", "#cdb98e"]),
    "uranus":  ("#9ccfd2", ["#86bcc0", "#b6e0e2", "#8fc5c8"]),
    "earth":   ("#3f6e9e", ["#5b8a4a", "#e8edf0", "#2f5a86"]),
}

# ----------------------------------------------------------------- content (edit here)

PRIMARY = "C-Programming-Questions"
FEATURED = [  # order shown under the primary card; (repo name, planet)
    ("understanding_memory_in_c", "jupiter"),
    ("C-Programs", "mars"),
    ("Socket_Manager", "neptune"),
    ("LinkedIn-Highlighter", "mercury"),
]
DESCRIPTIONS = {  # override empty or weak repo descriptions here
}

TOOLKIT = [
    ("Languages", ["C", "C++", "Python", "CUDA", "Assembly"]),
    ("Automotive", ["UDS", "DoIP", "SOVD", "AUTOSAR", "CAN / CAN-FD"]),
    ("Systems", ["Linux kernel", "QNX", "ROS2", "GDB", "OpenACC"]),
    ("Hardware", ["Nvidia Orin AGX", "Aurix TC375", "TIVA-C", "ESP32", "8051"]),
    ("Safety & test", ["ISO 26262", "MISRA C", "EN 50128", "VectorCAST", "Simulink"]),
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

BANNERS = [  # (number, title, note)
    ("01", "About", ""),
    ("02", "Toolkit", ""),
    ("03", "Repositories", "click a card to open the repo"),
    ("04", "Projects", "no public repo - details on my portfolio"),
    ("05", "Publications", ""),
    ("06", "GitHub stats", "updated daily"),
    ("07", "Contact", ""),
]


# ----------------------------------------------------------------- helpers

def svg_open(w, h, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'role="img"><title>{escape(title)}</title>')


STAR_TONES = ["#ffffff", "#cad7ff", "#ffe9c4", "#ffffff", "#dfe6ff"]


def stars(w, h, n, salt, twinkle=0):
    out = []
    for i in range(n):
        k = f"{salt}{i}"
        x, y = h01(k, "x") * w, h01(k, "y") * h
        r = .35 + h01(k, "r") ** 3 * 1.1
        c = STAR_TONES[i % len(STAR_TONES)]
        op = .2 + h01(k, "o") * .55
        if i < twinkle:
            d = 3 + h01(k, "d") * 5
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r + .3:.2f}" fill="{c}">'
                       f'<animate attributeName="opacity" values="{op * .3:.2f};{op + .25:.2f};{op * .3:.2f}" '
                       f'dur="{d:.1f}s" begin="-{h01(k, "b") * d:.1f}s" repeatCount="indefinite"/></circle>')
        else:
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" fill="{c}" opacity="{op:.2f}"/>')
    return "".join(out)


def panel(w, h, rx=10, border=BORDER, dashed=False):
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


# ----------------------------------------------------------------- planet body

def planet_body(planet, pr, seed, ring=False):
    base, tones = PLANETS[planet]
    bands = []
    for i in range(7):
        k = f"{seed}b{i}"
        y = (h01(k, "y") - .5) * 1.8 * pr
        hh = 2 + h01(k, "h") * (pr * .16)
        bands.append(f'<ellipse cx="0" cy="{y:.1f}" rx="{pr * 1.7:.1f}" ry="{hh:.1f}" '
                     f'fill="{tones[i % len(tones)]}" opacity=".7"/>')
    spin = 26 + h01(seed, "spin") * 14  # slow, like a real rotation
    defs = (f'<defs><radialGradient id="ps{seed}" fx=".38" fy=".35">'
            f'<stop offset="0" stop-color="{mix(base, "#ffffff", .25)}"/>'
            f'<stop offset="1" stop-color="{mix(base, "#000000", .25)}"/></radialGradient>'
            # light from the upper left, deep night side
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
               f'<circle r="{pr:.1f}" fill="url(#sh{seed})"/></g>'
               f'<circle r="{pr + 1.2:.1f}" fill="none" stroke="{mix(base, "#ffffff", .5)}" '
               'stroke-opacity=".18" stroke-width="1.5"/>')
    if not ring:
        return defs + surface
    rx, ry = pr * 1.9, pr * .42
    arc = (lambda sweep, op, w: f'<path d="M{-rx:.1f},0 A{rx:.1f},{ry:.1f} 0 0,{sweep} {rx:.1f},0" fill="none" '
           f'stroke="{tones[1]}" stroke-width="{w}" opacity="{op}" transform="rotate(-14)"/>')
    back = arc(1, .45, pr * .14) + arc(1, .25, pr * .05)
    front = arc(0, .85, pr * .14) + arc(0, .5, pr * .05)
    return defs + back + surface + front


# ----------------------------------------------------------------- cards

def repo_card(name, description, language, stars_n, forks_n, planet, seed, w=400, h=190,
              primary=False, dashed=False, tag=""):
    head, tail = panel(w, h, border=ACCENT if primary else BORDER, dashed=dashed)
    pr = 54 if primary else 34
    px, py = (120 if primary else 88), h / 2 + 4
    tx = 250 if primary else 168
    fs_name = 26 if primary else (19 if len(name) <= 16 else 16 if len(name) <= 20 else 14)
    nm = name if len(name) <= 26 else name[:25] + "..."
    desc_lines = wrap(description, 50 if primary else 28, 2 if primary else 3)
    desc = "".join(f'<text x="{tx}" y="{(96 if primary else 84) + i * (22 if primary else 18)}" '
                   f'font-size="{15 if primary else 13}" fill="{MUTED}">{escape(l)}</text>'
                   for i, l in enumerate(desc_lines))
    my = h - (40 if primary else 30)
    meta = (f'<circle cx="{tx + 6}" cy="{my - 4}" r="6" fill="{LANG.get(language, "#8b949e")}"/>'
            f'<text x="{tx + 18}" y="{my}" font-size="13" fill="{MUTED}">{escape(language or "")}</text>')
    nx = tx + 28 + 8 * len(language or "") + 18
    if stars_n:
        meta += f'<text x="{nx}" y="{my}" font-size="13" fill="{MUTED}">{stars_n} {"star" if stars_n == 1 else "stars"}</text>'
        nx += 8 * len(f"{stars_n} stars") + 18
    if forks_n:
        meta += f'<text x="{nx}" y="{my}" font-size="13" fill="{MUTED}">{forks_n} forks</text>'
    badge = ""
    if tag:
        badge = (f'<text x="{w - 22}" y="30" font-size="12" fill="{ACCENT if primary else FAINT}" '
                 f'text-anchor="end">{escape(tag)}</text>')
    return "".join([
        svg_open(w, h, f"{name}: {description or ''}"), head,
        f'<g clip-path="url(#pclip)">{stars(w, h, 55 if primary else 32, seed, twinkle=6)}',
        f'<g transform="translate({px},{py})">{planet_body(planet, pr, slug(seed), ring=primary)}</g>',
        f'<g font-family="{SANS}">',
        f'<text x="{tx}" y="{56 if primary else 52}" font-size="{fs_name}" font-weight="600" fill="{TEXT}">{escape(nm)}</text>',
        desc, meta, badge, '</g></g>', tail, '</svg>'])


# ----------------------------------------------------------------- section header

BW, BH = 830, 52


def banner(num, title, note):
    head, tail = panel(BW, BH, rx=8)
    return "".join([
        svg_open(BW, BH, title), head,
        f'<g clip-path="url(#pclip)">{stars(BW, BH, 60, "ban" + num, twinkle=10)}',
        f'<g font-family="{SANS}">'
        f'<text x="22" y="33" font-size="13" fill="{FAINT}" font-family="{MONO}">{num}</text>'
        f'<text x="52" y="34" font-size="20" font-weight="600" fill="{TEXT}">{escape(title)}</text>'
        f'<text x="{BW - 22}" y="33" font-size="12.5" fill="{FAINT}" text-anchor="end">{escape(note)}</text></g>',
        '</g>', tail, '</svg>'])


# ----------------------------------------------------------------- toolkit

def toolkit(rows):
    w, row_h, top = 830, 44, 26
    h = top * 2 + row_h * len(rows) - 8
    head, tail = panel(w, h)
    out = []
    for i, (cat, items) in enumerate(rows):
        y = top + 22 + i * row_h
        out.append(f'<circle cx="28" cy="{y - 5}" r="2.2" fill="{ACCENT}" opacity=".8"/>'
                   f'<text x="42" y="{y}" font-size="13.5" fill="{MUTED}">{escape(cat)}</text>')
        for j, it in enumerate(items):
            out.append(f'<text x="{180 + j * 128}" y="{y}" font-size="14.5" fill="{TEXT}">{escape(it)}</text>')
        if i < len(rows) - 1:
            out.append(f'<line x1="22" y1="{y + 18}" x2="{w - 22}" y2="{y + 18}" stroke="#ffffff" stroke-opacity=".05"/>')
    return "".join([svg_open(w, h, "Toolkit"), head,
                    f'<g clip-path="url(#pclip)">{stars(w, h, 120, "tool", twinkle=14)}',
                    f'<g font-family="{SANS}">{"".join(out)}</g></g>', tail, '</svg>'])


# ----------------------------------------------------------------- stats

def telemetry(n_repos, stars_n, contribs, followers, langs):
    w, h = 830, 176
    head, tail = panel(w, h)
    cells = [("public repos", n_repos), ("stars", stars_n),
             ("contributions, last year" if contribs is not None else "followers",
              contribs if contribs is not None else followers)]
    out = []
    x = 36
    for label, val in cells:
        out.append(f'<text x="{x}" y="78" font-size="34" font-weight="600" fill="{TEXT}">{val}</text>'
                   f'<text x="{x}" y="102" font-size="12.5" fill="{MUTED}">{escape(label)}</text>')
        x += 120 if len(label) < 14 else 190
    total = sum(v for _, v in langs) or 1
    bx, bw, by = 500, 294, 52
    out.append(f'<text x="{bx}" y="{by - 12}" font-size="12.5" fill="{MUTED}">Languages</text>')
    out.append(f'<clipPath id="bar"><rect x="{bx}" y="{by}" width="{bw}" height="8" rx="4"/></clipPath><g clip-path="url(#bar)">')
    xx = bx
    for name, v in langs:
        seg = bw * v / total
        out.append(f'<rect x="{xx:.1f}" y="{by}" width="{seg + .5:.1f}" height="8" fill="{LANG.get(name, "#8b949e")}"/>')
        xx += seg
    out.append('</g>')
    for i, (name, v) in enumerate(langs[:6]):
        lx, ly = bx + (i % 2) * 150, by + 34 + (i // 2) * 22
        out.append(f'<circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{LANG.get(name, "#8b949e")}"/>'
                   f'<text x="{lx + 16}" y="{ly}" font-size="13" fill="{TEXT}">{escape(name)} '
                   f'<tspan fill="{MUTED}">{100 * v / total:.1f}%</tspan></text>')
    out.append(f'<text x="36" y="{h - 28}" font-size="11.5" fill="{FAINT}">Pulled from the GitHub API by a daily Action</text>')
    return "".join([svg_open(w, h, "GitHub stats"), head,
                    f'<g clip-path="url(#pclip)">{stars(w, h, 80, "tel", twinkle=10)}',
                    f'<line x1="460" y1="30" x2="460" y2="{h - 30}" stroke="{BORDER}"/>',
                    f'<g font-family="{SANS}">{"".join(out)}</g></g>', tail, '</svg>'])


# ----------------------------------------------------------------- contact + footer

def channel(label, sub, dot):
    w, h = 300, 60
    head, tail = panel(w, h, rx=8)
    return "".join([svg_open(w, h, label), head,
                    f'<g clip-path="url(#pclip)">{stars(w, h, 24, "ch" + label, twinkle=4)}',
                    f'<circle cx="28" cy="30" r="5" fill="{dot}"/>',
                    f'<g font-family="{SANS}"><text x="46" y="27" font-size="16" font-weight="600" fill="{TEXT}">'
                    f'{escape(label)}</text><text x="46" y="45" font-size="12" fill="{MUTED}">{escape(sub)}</text></g>',
                    '</g>', tail, '</svg>'])


def footer():
    w, h = 830, 96
    head, tail = panel(w, h)
    q1, q2 = "Life is a bit. You are either 0 or a 1.", "I like to toggle every now and then."
    bit = (f'<g transform="translate(415,28)" font-family="{MONO}" font-size="16" text-anchor="middle">'
           f'<rect x="-13" y="-13" width="26" height="26" rx="5" fill="none" stroke="{BORDER}"/>'
           f'<text y="6" fill="{TEXT}">0<animate attributeName="opacity" values="1;1;0;0;1" '
           'keyTimes="0;.48;.5;.98;1" dur="4s" repeatCount="indefinite"/></text>'
           f'<text y="6" fill="{ACCENT}" opacity="0">1<animate attributeName="opacity" values="0;0;1;1;0" '
           'keyTimes="0;.48;.5;.98;1" dur="4s" repeatCount="indefinite"/></text></g>')
    return "".join([svg_open(w, h, q1 + " " + q2), head,
                    f'<g clip-path="url(#pclip)">{stars(w, h, 70, "foot", twinkle=12)}{bit}',
                    f'<g font-family="{SANS}" font-style="italic" text-anchor="middle">'
                    f'<text x="415" y="64" font-size="15" fill="{TEXT}">{escape(q1)}</text>'
                    f'<text x="415" y="84" font-size="15" fill="{MUTED}">{escape(q2)}</text></g>',
                    '</g>', tail, '</svg>'])


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
    return sorted(totals.items(), key=lambda kv: -kv[1])[:6]


def fetch_followers(user, token):
    try:
        return gc.gh(f"{gc.API}/users/{user}", token).get("followers", 0)
    except Exception:
        return 0


# ----------------------------------------------------------------- build

def build_all(root, user, repos, contrib, langs, followers):
    a = os.path.join(root, "assets")
    contribs = contrib[0] if contrib else None
    import shutil  # drop cards for repos no longer featured
    for d in ("planets", "uncharted"):
        shutil.rmtree(os.path.join(a, d), ignore_errors=True)
    for stale in ("star-chart.svg",):
        if os.path.exists(os.path.join(a, stale)):
            os.remove(os.path.join(a, stale))
    by_name = {r["name"]: r for r in repos}

    def desc(r):
        return DESCRIPTIONS.get(r["name"]) or r.get("description") or ""

    # hero: only the featured repos, in their planet colors
    hero = []
    for name, planet in [(PRIMARY, "saturn")] + FEATURED:
        if name in by_name:
            hero.append(dict(by_name[name], _color=PLANETS[planet][0]))
    gc.SHOW_STATS = False  # the stats panel below already shows these
    write(f"{a}/cosmos.svg", gc.build(hero, contrib, "Yashwanth Naidu",
                                      "Embedded software  |  onboard diagnostics for autonomous trucks", 9))

    for num, title, note in BANNERS:
        write(f"{a}/banner-{num}.svg", banner(num, title, note))
    write(f"{a}/toolkit.svg", toolkit(TOOLKIT))
    write(f"{a}/telemetry.svg", telemetry(len(repos), sum(r["stargazers_count"] for r in repos),
                                          contribs, followers, langs))
    write(f"{a}/channel-linkedin.svg", channel("LinkedIn", "in/t-yashwanth-naidu", "#0a66c2"))
    write(f"{a}/channel-site.svg", channel("cthecosmos.com", "portfolio and writing", ACCENT))
    write(f"{a}/footer.svg", footer())

    md = []
    if PRIMARY in by_name:
        r = by_name[PRIMARY]
        write(f"{a}/planets/{slug(PRIMARY)}.svg",
              repo_card(r["name"], desc(r), r.get("language"), r["stargazers_count"], r.get("forks_count"),
                        "saturn", r["name"], w=830, h=220, primary=True, tag="Most starred"))
        md.append(f'<a href="{r["html_url"]}"><img src="assets/planets/{slug(PRIMARY)}.svg" width="100%" '
                  f'alt="{escape(r["name"] + " - " + desc(r), {chr(34): "&quot;"})}"></a>')
    row = []
    for name, planet in FEATURED:
        if name not in by_name:
            print(f"warn: featured repo {name} not found (private, renamed or a fork?)", file=sys.stderr)
            continue
        r = by_name[name]
        write(f"{a}/planets/{slug(name)}.svg",
              repo_card(r["name"], desc(r), r.get("language"), r["stargazers_count"], r.get("forks_count"),
                        planet, r["name"]))
        row.append(f'<a href="{r["html_url"]}"><img src="assets/planets/{slug(name)}.svg" width="49%" '
                   f'alt="{escape(r["name"] + " - " + desc(r), {chr(34): "&quot;"})}"></a>')
    planets_md = "\n".join(md) + "\n</p>\n<p align=\"center\">\n" + "\n".join(row)

    unch = []
    for p in UNCHARTED:
        write(f"{a}/uncharted/{p['id']}.svg",
              repo_card(p["name"], p["description"], p["language"], 0, 0, p["planet"], p["id"],
                        dashed=True, tag="portfolio"))
        unch.append(f'<a href="{PORTFOLIO}"><img src="assets/uncharted/{p["id"]}.svg" width="49%" '
                    f'alt="{escape(p["name"] + " - " + p["description"], {chr(34): "&quot;"})}"></a>')

    tpl = open(os.path.join(root, "scripts", "README.template.md"), encoding="utf-8").read()
    write(os.path.join(root, "README.md"),
          tpl.replace("{{PLANETS}}", planets_md).replace("{{UNCHARTED}}", "\n".join(unch))
             .replace("{{PORTFOLIO}}", PORTFOLIO))
    return len(hero)


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
    print(f"built: {build_all(a.root, a.user, repos, contrib, langs, followers)} featured repos")


if __name__ == "__main__":
    main()
