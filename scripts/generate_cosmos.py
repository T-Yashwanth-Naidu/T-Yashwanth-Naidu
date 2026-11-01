#!/usr/bin/env python3
"""
Generate an animated solar-system SVG for a GitHub profile README.

  planet       = public repo (non-fork, non-archived)
  planet size  = stars (log scale)
  orbit radius = recency of last push (inner = most recent)
  planet color = primary language
  background   = one twinkling star per day with contributions (last 365 days)

Stdlib only. GitHub strips JS/CSS from READMEs, but SMIL animation inside an
SVG loaded through <img> still runs, which is what this relies on.

Usage:
  GITHUB_TOKEN=... python scripts/generate_cosmos.py --user T-Yashwanth-Naidu --out assets/cosmos.svg
"""
import argparse
import hashlib
import json
import math
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

API = "https://api.github.com"
W, H = 1000, 440
CX, CY = 500, 236
TOP, BOT = 76, H - 34  # keep twinkling stars out of the title and legend bands
FONT = "'Segoe UI', -apple-system, BlinkMacSystemFont, Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

LANG_COLORS = {
    "C": "#8fb3e8",
    "C++": "#f3628f",
    "Python": "#5b9bd5",
    "JavaScript": "#f1e05a",
    "TypeScript": "#4f8fe0",
    "Assembly": "#d39a4a",
    "Cuda": "#76b900",
    "Rust": "#e8a07a",
    "Shell": "#89e051",
    "HTML": "#f06a3b",
    "CMake": "#4cb5a0",
    "Makefile": "#6fd18a",
}
DEFAULT_COLOR = "#a48cff"
SHOW_STATS = True
DISPLAY_NAMES = {"C-Programming-Questions": "C-Questions"}


# ---------------------------------------------------------------- data

def gh(url, token, body=None):
    req = urllib.request.Request(url, data=body, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "cosmos-readme",
    })
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_repos(user, token):
    repos, page = [], 1
    while True:
        batch = gh(f"{API}/users/{user}/repos?per_page=100&page={page}&type=owner", token)
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    return [r for r in repos
            if not r["fork"] and not r.get("archived")
            and r["name"].lower() != user.lower()]


def fetch_contributions(user, token):
    """Needs a token (GraphQL). Returns (total, days) or None."""
    if not token:
        return None
    q = {
        "query": "query($l:String!){user(login:$l){contributionsCollection{"
                 "contributionCalendar{totalContributions weeks{contributionDays"
                 "{date contributionCount}}}}}}",
        "variables": {"l": user},
    }
    try:
        d = gh(f"{API}/graphql", token, json.dumps(q).encode())
        cal = d["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        days = [x for w in cal["weeks"] for x in w["contributionDays"]]
        return cal["totalContributions"], days
    except Exception as e:  # keep the image building even if GraphQL fails
        print(f"warn: contributions unavailable ({e})", file=sys.stderr)
        return None


# ---------------------------------------------------------------- helpers

def h01(s, salt=""):
    """Deterministic pseudo-random in [0,1] so the SVG only changes when data does."""
    return int(hashlib.sha256((salt + s).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def mix(hex_color, other, t):
    a = [int(hex_color[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(other[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def ellipse_path(rx, ry):
    return (f"M{CX + rx:.1f},{CY} A{rx:.1f},{ry:.1f} 0 1,0 {CX - rx:.1f},{CY} "
            f"A{rx:.1f},{ry:.1f} 0 1,0 {CX + rx:.1f},{CY}")


# ---------------------------------------------------------------- layers

def defs(colors):
    g = ['<defs>',
         '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
         '<stop offset="0" stop-color="#020306"/><stop offset="1" stop-color="#090c14"/></linearGradient>',
         '<radialGradient id="neb1"><stop offset="0" stop-color="#4a4258" stop-opacity=".35"/>'
         '<stop offset="1" stop-color="#4a4258" stop-opacity="0"/></radialGradient>',
         '<radialGradient id="neb2"><stop offset="0" stop-color="#2c3a48" stop-opacity=".35"/>'
         '<stop offset="1" stop-color="#2c3a48" stop-opacity="0"/></radialGradient>',
         '<radialGradient id="sunglow"><stop offset="0" stop-color="#ffb347" stop-opacity=".55"/>'
         '<stop offset=".5" stop-color="#ff7a2f" stop-opacity=".15"/>'
         '<stop offset="1" stop-color="#ff7a2f" stop-opacity="0"/></radialGradient>',
         '<radialGradient id="suncore" fx=".4" fy=".4"><stop offset="0" stop-color="#fffbe8"/>'
         '<stop offset=".45" stop-color="#ffd56b"/><stop offset="1" stop-color="#ff8a3d"/></radialGradient>',
         '<linearGradient id="trail" x1="0" y1="0" x2="1" y2="0">'
         '<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff"/></linearGradient>',
         # black hole: warm disk, brighter on the approaching (left) side
         f'<linearGradient id="disk" gradientUnits="userSpaceOnUse" x1="{CX - 110}" y1="0" x2="{CX + 110}" y2="0">'
         '<stop offset="0" stop-color="#fff3cf"/><stop offset=".35" stop-color="#ffc56b"/>'
         '<stop offset=".7" stop-color="#e57a2c"/><stop offset="1" stop-color="#7a2a12"/></linearGradient>',
         '<linearGradient id="lens" x1="0" y1="0" x2="0" y2="1">'
         '<stop offset="0" stop-color="#fff0c4"/><stop offset=".45" stop-color="#ffb04f" stop-opacity=".85"/>'
         '<stop offset="1" stop-color="#c25a1e" stop-opacity=".15"/></linearGradient>',
         '<filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.2"/></filter>',
         '<filter id="smear" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="1.4"/></filter>',
         '<radialGradient id="bhglow"><stop offset=".2" stop-color="#ff9a3c" stop-opacity=".35"/>'
         '<stop offset=".55" stop-color="#c2541f" stop-opacity=".1"/>'
         '<stop offset="1" stop-color="#c2541f" stop-opacity="0"/></radialGradient>',
         # pulsar
         '<linearGradient id="beam" x1="0" y1="1" x2="0" y2="0">'
         '<stop offset="0" stop-color="#d9e8ff" stop-opacity=".9"/>'
         '<stop offset="1" stop-color="#7fa8ff" stop-opacity="0"/></linearGradient>',
         '<radialGradient id="psrglow"><stop offset="0" stop-color="#cfe0ff" stop-opacity=".9"/>'
         '<stop offset="1" stop-color="#5f86ff" stop-opacity="0"/></radialGradient>',
         # wormhole
         '<radialGradient id="whcore"><stop offset="0" stop-color="#0b0f1a"/>'
         '<stop offset=".7" stop-color="#1d2738"/><stop offset="1" stop-color="#9fb2cf"/></radialGradient>',
         '<radialGradient id="whshade" fx=".35" fy=".3"><stop offset="0" stop-color="#fff" stop-opacity=".18"/>'
         '<stop offset=".6" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".35"/></radialGradient>',
         '<radialGradient id="whglow"><stop offset=".6" stop-color="#9fb2cf" stop-opacity=".14"/>'
         '<stop offset="1" stop-color="#9fb2cf" stop-opacity="0"/></radialGradient>',
         '<clipPath id="whclip"><circle r="36"/></clipPath>',
         '<clipPath id="frame"><rect width="%d" height="%d" rx="16"/></clipPath>' % (W, H)]
    for i, c in enumerate(colors):
        g.append(f'<radialGradient id="p{i}" fx=".32" fy=".3">'
                 f'<stop offset="0" stop-color="{mix(c, "#ffffff", .55)}"/>'
                 f'<stop offset=".55" stop-color="{c}"/>'
                 f'<stop offset="1" stop-color="{mix(c, "#000000", .65)}"/></radialGradient>')
    g.append('</defs>')
    return "\n".join(g)


def background():
    return "\n".join([
        f'<rect width="{W}" height="{H}" fill="url(#bg)"/>',
        '<ellipse cx="230" cy="150" rx="320" ry="170" fill="url(#neb1)">'
        '<animate attributeName="opacity" values=".6;1;.6" dur="18s" repeatCount="indefinite"/></ellipse>',
        '<ellipse cx="790" cy="320" rx="300" ry="150" fill="url(#neb2)">'
        '<animate attributeName="opacity" values="1;.55;1" dur="23s" repeatCount="indefinite"/></ellipse>',
    ])


def starfield(days):
    out = []
    for i in range(150):  # static dust
        k = str(i)
        out.append(f'<circle cx="{h01(k, "dx") * W:.1f}" cy="{h01(k, "dy") * H:.1f}" '
                   f'r="{0.35 + h01(k, "dr") * 0.6:.2f}" fill="#cfd8ff" '
                   f'opacity="{0.12 + h01(k, "do") * 0.25:.2f}"/>')
    pts = []
    if days:
        mx = max(d["contributionCount"] for d in days) or 1
        pts = [(d["date"], d["contributionCount"] / mx) for d in days if d["contributionCount"]]
    else:  # no token: decorative twinkle only
        pts = [(f"s{i}", h01(str(i), "fallback") * 0.6) for i in range(110)]
    for k, t in pts:
        dur = 2.5 + h01(k, "t") * 4.5
        lo = 0.2 + 0.3 * t
        out.append(
            f'<circle cx="{h01(k, "x") * W:.1f}" cy="{TOP + h01(k, "y") * (BOT - TOP):.1f}" '
            f'r="{0.7 + 1.7 * math.sqrt(t):.2f}" fill="#fff3d4">'
            f'<animate attributeName="opacity" values="{lo:.2f};1;{lo:.2f}" dur="{dur:.1f}s" '
            f'begin="-{h01(k, "b") * dur:.1f}s" repeatCount="indefinite"/></circle>')
    return "\n".join(out)


def shooting_star():
    return ('<g opacity="0"><line x1="0" y1="0" x2="90" y2="38" stroke="url(#trail)" '
            'stroke-width="1.6" stroke-linecap="round"/>'
            '<animateTransform attributeName="transform" type="translate" '
            'values="80,20;640,256;640,256" keyTimes="0;.09;1" dur="13s" begin="4s" repeatCount="indefinite"/>'
            '<animate attributeName="opacity" values="0;1;0;0" keyTimes="0;.02;.09;1" '
            'dur="13s" begin="4s" repeatCount="indefinite"/></g>')


BH_R = 30          # shadow radius
DISK_RX, DISK_RY = 108, 13


def _half(rx, ry, upper):
    """Half of an ellipse around (CX,CY): upper = far side, lower = near side."""
    sweep = 1 if upper else 0
    return f"M{CX - rx},{CY} A{rx},{ry} 0 0,{sweep} {CX + rx},{CY}"


def _disk(upper):
    out = []
    for rx, ry, w, op in ((DISK_RX * 1.08, DISK_RY * 1.1, 16, .14), (DISK_RX, DISK_RY, 6, .9), (DISK_RX * .72, DISK_RY * .72, 3.5, .8)):
        d = _half(rx, ry, upper)
        out.append(f'<path d="{d}" fill="none" stroke="url(#disk)" stroke-width="{w}" '
                   f'stroke-linecap="round" opacity="{op}"/>')
        if w > 10:
            continue
        # swirling hot clumps riding the disk
        out.append(f'<path d="{d}" fill="none" stroke="#fff6dc" stroke-width="{w * .35:.1f}" '
                   'stroke-dasharray="3 14 1 9" stroke-linecap="round" opacity=".55">'
                   f'<animate attributeName="stroke-dashoffset" values="0;{-54 if upper else 54}" '
                   'dur="2.4s" repeatCount="indefinite"/></path>')
    return "".join(out)


def black_hole():
    """Thin accretion disk seen near edge-on. The far side of the disk is lensed
    up and over the shadow (and faintly under it); the approaching side (left)
    is Doppler-boosted brighter than the receding side."""
    return "".join([
        f'<circle cx="{CX}" cy="{CY}" r="120" fill="url(#bhglow)">'
        '<animate attributeName="opacity" values=".75;1;.75" dur="6s" repeatCount="indefinite"/></circle>',
        _disk(upper=True),                                            # far side, behind
        f'<circle cx="{CX}" cy="{CY}" r="{BH_R + 9}" fill="none" stroke="url(#lens)" '
        'stroke-width="9" opacity=".35" filter="url(#soft)"/>',
        f'<circle cx="{CX}" cy="{CY}" r="{BH_R + 7}" fill="none" stroke="url(#lens)" stroke-width="4"/>',                            # lensed image of the far disk
        f'<ellipse cx="{CX}" cy="{CY + 2}" rx="{BH_R + 6}" ry="{BH_R + 4}" fill="none" '
        'stroke="url(#lens)" stroke-width="1.4" opacity=".5"/>',     # secondary image, underneath
        f'<circle cx="{CX}" cy="{CY}" r="{BH_R}" fill="#000"/>',      # shadow
        f'<circle cx="{CX}" cy="{CY}" r="{BH_R + 1.5}" fill="none" stroke="#fff4d6" '
        'stroke-width="1.1" opacity=".85"/>',                         # photon ring
        _disk(upper=False),                                           # near side, in front
    ])


def pulsar(x=905, y=96):
    """Neutron star: tiny hot core, two beams sweeping on a tilted axis, flash per half-turn."""
    beam = '<polygon points="0,0 -7,-150 7,-150" fill="url(#beam)"/>'
    return "".join([
        f'<g transform="translate({x},{y})">',
        '<circle r="22" fill="url(#psrglow)"><animate attributeName="opacity" '
        'values=".35;1;.35" dur="1.6s" repeatCount="indefinite"/></circle>',
        '<g transform="scale(1,.42) rotate(-25)"><g>',
        beam, f'<g transform="rotate(180)">{beam}</g>',
        '<animateTransform attributeName="transform" type="rotate" from="0" to="360" '
        'dur="3.2s" repeatCount="indefinite"/></g></g>',
        '<circle r="3.6" fill="#f2f7ff"/>',
        f'<text y="30" text-anchor="middle" font-family="{FONT}" font-size="9.5" '
        'fill="#6e7681">neutron star</text>',
        '</g>',
    ])


def wormhole(x=92, y=330, r=36):
    """A sphere showing a distorted view of somewhere else, with an Einstein ring."""
    streaks = []
    for i in range(10):
        k = f"wh{i}"
        rr = r * (.25 + .7 * h01(k, "rr"))
        a0 = h01(k, "a") * 360
        span = 50 + 90 * h01(k, "s")
        x0, y0 = rr * math.cos(math.radians(a0)), rr * math.sin(math.radians(a0))
        x1, y1 = rr * math.cos(math.radians(a0 + span)), rr * math.sin(math.radians(a0 + span))
        streaks.append(
            f'<path d="M{x0:.1f},{y0:.1f} A{rr:.1f},{rr:.1f} 0 0,1 {x1:.1f},{y1:.1f}" fill="none" '
            f'stroke="{["#e8dcc4", "#b9c8e0", "#d0d6e0"][i % 3]}" stroke-width="{1 + 2.2 * h01(k, "w"):.1f}" '
            f'stroke-linecap="round" opacity="{.35 + .4 * h01(k, "o"):.2f}"/>')
    for i in range(14):
        k = f"whs{i}"
        streaks.append(f'<circle cx="{(h01(k, "x") - .5) * 1.6 * r:.1f}" cy="{(h01(k, "y") - .5) * 1.6 * r:.1f}" '
                       f'r=".8" fill="#fff"/>')
    return "".join([
        f'<g transform="translate({x},{y})">',
        f'<circle r="{r + 16}" fill="url(#whglow)"/>',
        f'<circle r="{r + 6}" fill="none" stroke="#c9d1d9" stroke-width=".8" opacity=".25"/>',
        f'<circle r="{r}" fill="url(#whcore)"/>',
        f'<g clip-path="url(#whclip)"><g filter="url(#smear)">{"".join(streaks)}'
        '<animateTransform attributeName="transform" type="rotate" from="0" to="-360" '
        'dur="48s" repeatCount="indefinite"/></g></g>',
        f'<circle r="{r}" fill="url(#whshade)"/>',
        f'<circle r="{r}" fill="none" stroke="#e6efff" stroke-width="1.2" opacity=".7"/>',
        f'<text y="{r + 20}" text-anchor="middle" font-family="{FONT}" font-size="9.5" '
        'fill="#6e7681">wormhole</text>',
        '</g>',
    ])


def solar_system(repos, max_planets):
    repos = sorted(repos, key=lambda r: r["pushed_at"] or "", reverse=True)[:max_planets]
    n = len(repos)
    if not n:
        return "", "", []
    colors = [r.get("_color") or LANG_COLORS.get(r.get("language") or "", DEFAULT_COLOR) for r in repos]
    top_stars = max(r["stargazers_count"] for r in repos)
    rx_min, rx_max = 150, 430
    orbits, bodies = [], []
    for i, r in enumerate(repos):
        rx = rx_min + (rx_max - rx_min) * (i / max(n - 1, 1))
        ry = rx * 0.34
        path = ellipse_path(rx, ry)
        orbits.append(f'<path d="{path}" fill="none" stroke="#ffffff" stroke-opacity=".07" '
                      'stroke-dasharray="2 6"/>')
        stars = r["stargazers_count"]
        pr = max(3.5, min(16.0, 4 + 4.2 * math.log10(stars + 1)))
        dur = 14 + rx * 0.11  # outer planets slower
        begin = h01(r["name"], "phase") * dur
        ring = ""
        if stars == top_stars and stars > 0:
            ring = (f'<ellipse rx="{pr * 1.9:.1f}" ry="{pr * 0.55:.1f}" fill="none" '
                    f'stroke="{mix(colors[i], "#ffffff", .4)}" stroke-opacity=".75" stroke-width="1.6" '
                    'transform="rotate(-18)"/>')
        name = DISPLAY_NAMES.get(r["name"], r["name"])
        name = name if len(name) <= 18 else name[:17] + "."
        label = name + (f"  {stars}*" if stars else "")
        ly = pr + 13 if i % 2 == 0 else -(pr + 6)  # alternate above/below to cut collisions
        bodies.append(
            f'<g><title>{escape(r["name"])} - {escape(r.get("language") or "n/a")}, {stars} stars</title>'
            f'<animateMotion dur="{dur:.1f}s" begin="-{begin:.1f}s" repeatCount="indefinite" path="{path}"/>'
            f'<circle r="{pr * 1.8:.1f}" fill="{colors[i]}" opacity=".12"/>'
            f'<circle r="{pr:.1f}" fill="url(#p{i})"/>{ring}'
            f'<text y="{ly:.1f}" text-anchor="middle" font-size="11" fill="#c9d1d9" '
            f'fill-opacity=".85">{escape(label)}</text></g>')
    return "\n".join(orbits), "\n".join(bodies), colors


def text_layer(title, subtitle, n_repos, total_stars, contribs):
    stats = f"{n_repos} repos | {total_stars} stars" if SHOW_STATS else ""
    if contribs is not None and SHOW_STATS:
        stats += f" | {contribs} contributions"
    legend = "planet = repo  |  size = stars  |  inner orbit = recent push  |  stars = commit days"
    return (f'<g font-family="{FONT}">'
            f'<text x="28" y="40" font-size="22" font-weight="600" fill="#e6edf3">{escape(title)}</text>'
            f'<text x="28" y="60" font-size="13" fill="#8b949e">{escape(subtitle)}</text>'
            f'<text x="28" y="{H - 16}" font-size="11" fill="#8b949e">{escape(legend)}</text>'
            f'<text x="{W - 28}" y="{H - 16}" font-size="11" fill="#8b949e" '
            f'text-anchor="end">{escape(stats)}</text></g>')


# ---------------------------------------------------------------- main

def build(repos, contrib, title, subtitle, max_planets):
    orbits, bodies, colors = solar_system(repos, max_planets)
    total_stars = sum(r["stargazers_count"] for r in repos)
    contribs, days = (contrib if contrib else (None, None))
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        'role="img" aria-labelledby="t d">',
        '<title id="t">Repository system around a black hole</title>',
        '<desc id="d">Planets orbit a black hole: each planet is a repository, sized by stars, '
        'orbiting by recency; background stars are daily contributions.</desc>',
        defs(colors),
        '<g clip-path="url(#frame)">',
        background(), starfield(days), shooting_star(), pulsar(), wormhole(), orbits, black_hole(),
        f'<g font-family="{FONT}">{bodies}</g>',
        text_layer(title, subtitle, len(repos), total_stars, contribs),
        '</g>',
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="16" fill="none" '
        'stroke="#30363d"/>',
        '</svg>',
    ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--out", default="assets/cosmos.svg")
    ap.add_argument("--title", default="Yashwanth Naidu")
    ap.add_argument("--subtitle", default="embedded software | onboard diagnostics for autonomous trucks")
    ap.add_argument("--max-planets", type=int, default=9)
    a = ap.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    repos = fetch_repos(a.user, token)
    contrib = fetch_contributions(a.user, token)
    svg = build(repos, contrib, a.title, a.subtitle, a.max_planets)

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {a.out}: {len(repos)} planets, {len(svg) // 1024} KB")


if __name__ == "__main__":
    main()
