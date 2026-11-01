"""
Hero image: public repos orbiting a Schwarzschild black hole, with physics
that is actually computed rather than drawn by eye.

  black hole   M = 4.3e6 solar masses (Sgr A*).  Shadow radius 2.6 r_s,
               disk from the ISCO (3 r_s) outward, inclined 81 deg.
               Each disk annulus rotates at its own Keplerian period
               (differential rotation, P ~ r^1.5) on the same clock as the
               planets. Temperature follows the thin-disk profile
               T ~ r^-3/4 (1 - sqrt(r_in/r))^1/4. The approaching side is
               Doppler-boosted. The far side of the disk is lensed up over
               the shadow; a photon ring sits on the shadow edge.
  lensing      background stars near the hole are moved to their two
               point-lens images, theta = (beta +- sqrt(beta^2 + 4 theta_E^2))/2,
               and stretched tangentially by theta/beta.
  orbits       Kepler's equation E - e sin E = M solved per frame, so planets
               speed up at periapsis. Periods from Kepler's third law with
               the real mass. Periapsis advances by the 1PN GR value
               dw = 6 pi G M / (c^2 a (1 - e^2)) per orbit, which turns each
               orbit into a rosette. Planets are hidden when they pass
               behind the shadow and dimmed behind the disk.
  pulsar       magnetic axis tilted from the spin axis; the beam is
               projected each frame and the star flashes only when the beam
               sweeps the line of sight. Its pulse train is the last 60 days
               of GitHub contributions.
  wormhole     a sphere showing another sky, with an Einstein ring of our
               own stars around the throat.
"""
import math
from xml.sax.saxutils import escape

from fontembed import PLEX, STIX, embed

W, H = 1000, 560
CX, CY = 500, 272

# --- physical constants (SI)
G, C_LIGHT, M_SUN = 6.674e-11, 2.998e8, 1.989e30
MASS = 4.3e6 * M_SUN
GM = G * MASS
RS_M = 2 * GM / C_LIGHT ** 2          # Schwarzschild radius, metres (~1.27e10)
TIME_SCALE = 1200                     # 1 s of animation = 20 min of system time

# --- drawing scale
RS = 13.0                             # px per r_s
R_SH = 2.6 * RS                       # shadow radius (critical impact parameter 3*sqrt(3)/2 r_s)
DISK_IN, DISK_OUT = 3 * RS, 11 * RS   # ISCO to outer edge
DISK_INC = math.radians(81)
K = math.cos(DISK_INC)                # vertical squash of the disk
THETA_E = 1.35 * R_SH                 # Einstein radius for background stars

ACCENT, TEXT, MUTED, FAINT = "#d9a85b", "#e6edf3", "#8b949e", "#6e7681"


def h01(s, salt=""):
    import hashlib
    return int(hashlib.sha256((salt + s).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def period_s(a_rs):
    """Kepler III with the real mass. a in units of r_s."""
    a = a_rs * RS_M
    return 2 * math.pi * math.sqrt(a ** 3 / GM)


def precession_rad(a_rs, e):
    """1PN periapsis advance per orbit: 6 pi GM / (c^2 a (1-e^2)) = 3 pi r_s / (a (1-e^2))."""
    return 3 * math.pi / (a_rs * (1 - e * e))


def kepler_E(Mm, e):
    E = Mm if e < .8 else math.pi
    for _ in range(30):
        E -= (E - e * math.sin(E) - Mm) / (1 - e * math.cos(E))
    return E


def temp_color(t):
    """t in [0,1] (1 = hottest) -> blackbody-ish colour."""
    stops = [(0, (120, 30, 10)), (.25, (190, 70, 20)), (.5, (240, 140, 50)),
             (.75, (255, 205, 130)), (.9, (255, 238, 205)), (1, (255, 250, 240))]
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            f = (t - t0) / (t1 - t0)
            return "#%02x%02x%02x" % tuple(round(a + (b - a) * f) for a, b in zip(c0, c1))
    return "#fffaf0"


# ======================================================================= sky

STAR_COLORS = [("#9bb0ff", .05), ("#aabfff", .08), ("#cad7ff", .15), ("#f8f7ff", .25),
               ("#fff4ea", .2), ("#ffd2a1", .17), ("#ffcc6f", .1)]


def _star_color(u):
    acc = 0
    for c, w in STAR_COLORS:
        acc += w
        if u <= acc:
            return c
    return STAR_COLORS[-1][0]


def sky():
    out = []
    # Milky Way: a soft band with a dark dust lane, slope ~0.35
    ang = math.degrees(math.atan(.35))
    out.append(f'<g transform="translate(500,{175 + 175}) rotate({ang:.1f})" filter="url(#band)">'
               '<ellipse rx="640" ry="70" fill="#cfc8bc" opacity=".055"/>'
               '<ellipse rx="560" ry="30" fill="#e6dccb" opacity=".05"/>'
               '<ellipse cx="60" cy="6" rx="420" ry="9" fill="#000" opacity=".55"/></g>')
    stars = []
    for i in range(620):
        k = f"s{i}"
        if i < 290:  # band stars
            t = h01(k, "t")
            x = -40 + t * 1080
            y = 175 + .35 * x + (h01(k, "g1") + h01(k, "g2") + h01(k, "g3") - 1.5) * 85
        else:
            x, y = h01(k, "x") * W, h01(k, "y") * H
        mag = h01(k, "m") ** .35            # most stars faint
        b = 10 ** (-1.6 * mag)              # relative flux
        r = .3 + 1.5 * math.sqrt(b)
        op = min(1, .25 + 1.6 * b)
        stars.append((x, y, r, op, _star_color(h01(k, "c")), b))
    for x, y, r, op, col, b in stars:
        dx, dy = x - CX, y - CY
        beta = math.hypot(dx, dy)
        if beta < 4 * THETA_E:
            out.append(_lensed(dx, dy, beta, r, op, col))
            continue
        out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" fill="{col}" opacity="{op:.1f}"/>')
        if False:
            L = 7 + 14 * b
            out.append(f'<g stroke="{col}" stroke-width=".5" opacity="{.35 * op:.2f}">'
                       f'<line x1="{x - L:.1f}" y1="{y:.1f}" x2="{x + L:.1f}" y2="{y:.1f}"/>'
                       f'<line x1="{x:.1f}" y1="{y - L:.1f}" x2="{x:.1f}" y2="{y + L:.1f}"/></g>')
    return "".join(out)


def _lensed(dx, dy, beta, r, op, col):
    """Point-lens images of a background star at angular offset beta."""
    beta = max(beta, .8)
    u = beta / THETA_E
    root = math.sqrt(beta * beta + 4 * THETA_E ** 2)
    out = []
    for sign in (1, -1):
        theta = (beta + sign * root) / 2          # signed image position
        mu = abs((u * u + 2) / (2 * u * math.sqrt(u * u + 4)) + sign * .5)
        if mu < .08:
            continue
        stretch = min(9, abs(theta) / beta)       # tangential stretch
        radial = max(.35, min(1, 1 / max(stretch, 1)))
        ux, uy = dx / beta, dy / beta
        x, y = CX + ux * theta, CY + uy * theta
        rot = math.degrees(math.atan2(uy, ux)) + 90
        o = min(1, op * (.5 + .5 * min(mu, 2)))
        if stretch < 1.15:   # weakly lensed: just moved outward
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" fill="{col}" opacity="{o:.1f}"/>')
        else:
            out.append(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{r * stretch:.2f}" ry="{r * radial:.2f}" '
                       f'fill="{col}" opacity="{o:.1f}" transform="rotate({rot:.0f} {x:.1f} {y:.1f})"/>')
    return "".join(out)


# ======================================================================= black hole

def _rings(radius_map, salt):
    """Disk annuli with temperature colour and Keplerian rotation.
    radius_map maps the physical radius (px) to the radius it is drawn at."""
    out = []
    n = 46
    for j in range(n):
        r = DISK_IN + (DISK_OUT - DISK_IN) * (j + .5) / n
        x = r / DISK_IN
        T = x ** -.75 * max(0, 1 - math.sqrt(1 / x)) ** .25
        out.append((r, T))
    tmax = max(T for _, T in out)
    g = []
    for j, (r, T) in enumerate(out):
        t = T / tmax
        col = temp_color(.08 + .8 * t)
        rr = radius_map(r)
        circ = 2 * math.pi * rr
        k = f"{salt}{j}"
        segs = []
        left = circ
        while left > 0:
            on = circ * (.015 + .16 * h01(k + str(len(segs)), "on") ** 2)
            off = circ * (.006 + .05 * h01(k + str(len(segs)), "off"))
            segs += [on, off]
            left -= on + off
        dash = " ".join(f"{s:.1f}" for s in segs)
        dr = (DISK_OUT - DISK_IN) / n
        width = (radius_map(r + dr) - rr) * 1.6     # follow the mapped spacing
        edge = min(1, (DISK_OUT - r) / (.25 * (DISK_OUT - DISK_IN)))   # soft outer edge
        op = (.06 + .94 * t ** 1.6) * edge
        p = period_s(r / RS) / TIME_SCALE    # Keplerian period of this annulus
        start = h01(k, "ph") * 360
        g.append(f'<circle r="{rr:.2f}" fill="none" stroke="{col}" stroke-width="{width:.2f}" '
                 f'stroke-dasharray="{dash}" opacity="{op:.2f}" transform="rotate({start:.0f})">'
                 f'<animateTransform attributeName="transform" type="rotate" from="{start:.0f}" '
                 f'to="{start - 360:.0f}" dur="{p:.2f}s" repeatCount="indefinite"/></circle>')
        # a smooth underlayer so the disk reads as gas, not dashes
        g.append(f'<circle r="{rr:.2f}" fill="none" stroke="{col}" stroke-width="{width:.2f}" '
                 f'opacity="{op * .5:.2f}"/>')
    return "".join(g)


def black_hole_defs():
    lens_map = lambda r: R_SH * 1.03 + (r - DISK_IN) / (DISK_OUT - DISK_IN) * .95 * R_SH
    return "".join([
        f'<g id="disk" filter="url(#gas)">{_rings(lambda r: r, "d")}</g>',
        f'<g id="lensdisk" filter="url(#gas)">{_rings(lens_map, "d")}</g>',
        # Doppler beaming: approaching (left) side much brighter
        f'<linearGradient id="dopg" gradientUnits="userSpaceOnUse" x1="{CX - DISK_OUT}" y1="0" x2="{CX + DISK_OUT}" y2="0">'
        '<stop offset="0" stop-color="#fff"/><stop offset=".5" stop-color="#7a7a7a"/>'
        '<stop offset="1" stop-color="#0c0c0c"/></linearGradient>',
        f'<mask id="dop" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">'
        f'<rect width="{W}" height="{H}" fill="url(#dopg)"/></mask>',
        # lensed image: thick over the top, thin underneath
        f'<mask id="lensm" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">'
        f'<g filter="url(#soft)">'
        f'<path d="M{CX - R_SH * 1.1:.1f},{CY} A{R_SH * 1.1:.1f},{R_SH * 2.0:.1f} 0 0,1 {CX + R_SH * 1.1:.1f},{CY} Z" fill="#fff"/>'
        f'<path d="M{CX - R_SH * 1.12:.1f},{CY} A{R_SH * 1.12:.1f},{R_SH * 1.22:.1f} 0 0,0 {CX + R_SH * 1.12:.1f},{CY} Z" fill="#9a9a9a"/>'
        '</g></mask>',
        '<filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="1.6"/></filter>',
        f'<clipPath id="farhalf"><rect width="{W}" height="{CY}"/></clipPath>',
        f'<clipPath id="nearhalf"><rect y="{CY}" width="{W}" height="{H - CY}"/></clipPath>',
        '<filter id="gas" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation=".55"/></filter>',
        '<filter id="band" x="-20%" y="-200%" width="140%" height="500%"><feGaussianBlur stdDeviation="22"/></filter>',
        '<radialGradient id="bhglow"><stop offset="0" stop-color="#ffb070" stop-opacity=".16"/>'
        '<stop offset=".5" stop-color="#ff8a40" stop-opacity=".05"/><stop offset="1" stop-color="#ff8a40" stop-opacity="0"/></radialGradient>',
    ])


def black_hole():
    disk = f'<use xlink:href="#disk" href="#disk" transform="translate({CX},{CY}) scale(1,{K:.4f})"/>'
    return "".join([
        f'<circle cx="{CX}" cy="{CY}" r="190" fill="url(#bhglow)"/>',
        f'<g mask="url(#dop)"><g clip-path="url(#farhalf)">{disk}</g></g>',
        f'<g mask="url(#dop)"><g mask="url(#lensm)">'
        f'<use xlink:href="#lensdisk" href="#lensdisk" transform="translate({CX},{CY})"/></g></g>',
        f'<circle cx="{CX}" cy="{CY}" r="{R_SH}" fill="#000"/>',
        f'<g mask="url(#dop)" fill="none">'
        f'<circle cx="{CX}" cy="{CY}" r="{R_SH + .7:.1f}" stroke="#fff6e6" stroke-width="1.1" opacity=".95"/>'
        f'<circle cx="{CX}" cy="{CY}" r="{R_SH + 2.2:.1f}" stroke="#ffe2b8" stroke-width=".6" opacity=".4"/></g>',
        f'<g mask="url(#dop)"><g clip-path="url(#nearhalf)">{disk}</g></g>',
    ])


# ======================================================================= orbits

ORBIT_A = [12.5, 16.5, 21, 26.5, 32.5]   # r_s, innermost = most recently pushed
ORBIT_I = [64, 70, 58, 74, 73]           # inclination, deg
ORBIT_NODE = [-12, 8, -5, 14, -4]        # position angle of the node, deg
LETTERS = "bcdef"


def orbital_elements(repos):
    """repos ordered innermost first. Returns list of dicts with real elements."""
    els = []
    for k, r in enumerate(repos[:5]):
        a = ORBIT_A[k]
        e = round((.06 + .24 * h01(r["name"], "ecc")) * (1 if k < 3 else .55), 3)
        dw = precession_rad(a, e)
        els.append(dict(repo=r, letter=LETTERS[k], a=a, e=e, i=ORBIT_I[k], node=ORBIT_NODE[k],
                        w0=h01(r["name"], "w") * 2 * math.pi, P=period_s(a), dw=dw,
                        n_orbits=max(1, round(2 * math.pi / dw))))
    return els


def _project(el, t_frac_orbits):
    """Sky position (px) and depth for time measured in orbits."""
    a, e = el["a"] * RS, el["e"]
    Mm = 2 * math.pi * (t_frac_orbits % 1)
    E = kepler_E(Mm, e)
    nu = 2 * math.atan2(math.sqrt(1 + e) * math.sin(E / 2), math.sqrt(1 - e) * math.cos(E / 2))
    r = a * (1 - e * math.cos(E))
    w = el["w0"] + (2 * math.pi / el["n_orbits"]) * t_frac_orbits   # loop-closing precession
    inc, node = math.radians(el["i"]), math.radians(el["node"])
    u = w + nu
    X = r * (math.cos(node) * math.cos(u) - math.sin(node) * math.sin(u) * math.cos(inc))
    Y = r * (math.sin(node) * math.cos(u) + math.cos(node) * math.sin(u) * math.cos(inc))
    Z = r * math.sin(u) * math.sin(inc)          # > 0: behind the hole
    return CX + X, CY + Y, Z


def planet_svg(el, color, radius, ring=False):
    per_orbit = 54
    frames = per_orbit * el["n_orbits"]
    pts, vis = [], []
    for f in range(frames + 1):
        x, y, z = _project(el, f / per_orbit)
        pts.append(f"{x:.1f},{y:.1f}")
        d = math.hypot(x - CX, y - CY)
        in_disk = ((x - CX) / DISK_OUT) ** 2 + ((y - CY) / (DISK_OUT * K + 2)) ** 2 < 1
        if z > 0 and d < R_SH * 1.5:
            vis.append("0")
        elif z > 0 and in_disk:
            vis.append(".35")
        else:
            vis.append("1")
    dur = el["P"] / TIME_SCALE * el["n_orbits"]
    # compress visibility to its change points
    vals, times = [], []
    for f, v in enumerate(vis):
        if not vals or v != vals[-1]:
            vals.append(v)
            times.append(f / frames)
    occl = ""
    if len(vals) > 1:
        occl = (f'<animate attributeName="opacity" calcMode="discrete" values="{";".join(vals)}" '
                f'keyTimes="{";".join(f"{t:.4f}" for t in times)}" dur="{dur:.1f}s" repeatCount="indefinite"/>')
    trail = (f'<polyline points="{" ".join(pts[::2])}" fill="none" stroke="#ffffff" stroke-opacity=".045" '
             'stroke-width=".6"/>')
    body = [f'<circle r="{radius + 3:.1f}" fill="{color}" opacity=".12"/>',
            f'<circle r="{radius:.1f}" fill="url(#pl{el["letter"]})"/>']
    if ring:
        body.insert(1, f'<ellipse rx="{radius * 2:.1f}" ry="{radius * .5:.1f}" fill="none" stroke="#e9dcb8" '
                       'stroke-width="1.3" opacity=".75" transform="rotate(-16)"/>')
    label = (f'<text x="{radius + 5:.1f}" y="{-radius - 2:.1f}" font-family="{PLEX}" font-size="12" '
             f'fill="{TEXT}" fill-opacity=".85">{el["letter"]}</text>')
    grad = (f'<radialGradient id="pl{el["letter"]}" fx=".35" fy=".32"><stop offset="0" stop-color="#ffffff" '
            f'stop-opacity=".9"/><stop offset=".25" stop-color="{color}"/>'
            f'<stop offset="1" stop-color="#0b0b0b"/></radialGradient>')
    return trail, (f'<defs>{grad}</defs><g>{occl}'
                   f'<animateMotion values="{";".join(pts)}" calcMode="linear" dur="{dur:.1f}s" '
                   f'repeatCount="indefinite"/>{"".join(body)}{label}</g>')


# ======================================================================= pulsar

PX, PY = 912, 70


def pulsar(days):
    frames, period = 48, 1.6
    zeta, alpha, pa = math.radians(60), math.radians(58), math.radians(18)
    A = (math.sin(zeta) * math.sin(pa), -math.sin(zeta) * math.cos(pa), -math.cos(zeta))
    # orthonormal basis around the spin axis
    t = (1, 0, 0)
    e1 = _norm(_cross(A, t))
    e2 = _cross(A, e1)
    L = 105
    beams = {1: [], -1: []}
    flash = []
    for f in range(frames + 1):
        ph = 2 * math.pi * f / frames
        m = tuple(math.cos(alpha) * A[i] + math.sin(alpha) * (math.cos(ph) * e1[i] + math.sin(ph) * e2[i])
                  for i in range(3))
        # observer looks along +z, so "toward us" is -z
        gam = min(math.degrees(math.acos(max(-1, min(1, -m[2])))),
                  math.degrees(math.acos(max(-1, min(1, m[2])))))
        flash.append(f"{.25 + .75 * math.exp(-(gam / 7) ** 2):.2f}")
        for s in (1, -1):
            mx, my = s * m[0], s * m[1]
            pl = math.hypot(mx, my) or 1e-6
            tipx, tipy = PX + mx * L, PY + my * L
            wdt = 1.2 + 7 * pl
            nx, ny = -my / pl * wdt, mx / pl * wdt
            beams[s].append(f"{PX:.1f},{PY:.1f} {tipx + nx:.1f},{tipy + ny:.1f} {tipx - nx:.1f},{tipy - ny:.1f}")
    beam_svg = "".join(
        f'<polygon fill="#cfe0ff" opacity=".3"><animate attributeName="points" values="{";".join(v)}" '
        f'dur="{period}s" repeatCount="indefinite"/></polygon>' for v in beams.values())
    axis = (f'<line x1="{PX - A[0] * 40:.1f}" y1="{PY - A[1] * 40:.1f}" x2="{PX + A[0] * 40:.1f}" '
            f'y2="{PY + A[1] * 40:.1f}" stroke="{FAINT}" stroke-width=".6" stroke-dasharray="2 3"/>')
    glow = (f'<circle cx="{PX}" cy="{PY}" r="16" fill="url(#psrg)"><animate attributeName="opacity" '
            f'values="{";".join(flash)}" dur="{period}s" repeatCount="indefinite"/></circle>')
    core = f'<circle cx="{PX}" cy="{PY}" r="2.6" fill="#f4f8ff"/>'

    # pulse train: last 60 days of contributions, one pulse per day
    sx0, sx1, base = 800, 982, 150
    vals = [d["contributionCount"] for d in (days or [])][-60:] or [0] * 60
    mx = max(vals) or 1
    step = (sx1 - sx0) / len(vals)
    pts = []
    for i, v in enumerate(vals):
        x0 = sx0 + i * step
        hgt = 1.2 + 26 * math.sqrt(v / mx) if v else .6 + .8 * h01(str(i), "noise")
        for k in range(7):
            x = x0 + step * k / 6
            g = math.exp(-((k - 3) / 1.1) ** 2)
            pts.append(f"{x:.1f},{base - hgt * g:.1f}")
    trace = (f'<rect x="{sx0 - 8}" y="{base - 40}" width="{sx1 - sx0 + 16}" height="58" rx="4" fill="#000" '
             'opacity=".45"/>'
             f'<polyline points="{" ".join(pts)}" fill="none" stroke="#cfe0ff" stroke-width=".9" opacity=".85"/>'
             f'<line x1="{sx0}" y1="{base + .5}" x2="{sx1}" y2="{base + .5}" stroke="{FAINT}" stroke-width=".4"/>'
             f'<line y1="{base - 34}" y2="{base + 2}" stroke="{ACCENT}" stroke-width=".8" opacity=".7">'
             f'<animate attributeName="x1" values="{sx0};{sx1}" dur="9s" repeatCount="indefinite"/>'
             f'<animate attributeName="x2" values="{sx0};{sx1}" dur="9s" repeatCount="indefinite"/></line>'
             f'<text x="{sx0}" y="{base + 13}" font-family="{PLEX}" font-size="9.5" fill="{MUTED}">'
             f'60 d of commits, 1 pulse = 1 day</text>')
    label = (f'<text x="{PX - 18}" y="{PY + 4}" font-family="{PLEX}" font-size="11" fill="{TEXT}" '
             f'text-anchor="end">PSR YN-1</text>'
             f'<text x="{PX - 18}" y="{PY + 18}" font-family="{PLEX}" font-size="9.5" fill="{MUTED}" '
             f'text-anchor="end">P = {period} s</text>')
    return f'<g mask="url(#beamfade)">{beam_svg}</g>' + axis + glow + core + trace + label


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(v):
    n = math.sqrt(sum(x * x for x in v))
    return tuple(x / n for x in v)


# ======================================================================= wormhole

WX, WY, WR = 104, 440, 34


def wormhole(WX=WX, WY=WY, WR=WR, label=True, cid='throat'):
    arms = []
    for arm in range(2):
        for j in range(70):
            th = j * .11
            rr = 1.4 * math.exp(.28 * th)
            ang = th + arm * math.pi
            jit = (h01(f"w{arm}{j}", "j") - .5) * 1.6
            x, y = (rr + jit) * math.cos(ang), (rr + jit) * math.sin(ang)
            arms.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{.35 + .5 * h01(f"w{arm}{j}", "r"):.2f}" '
                        f'fill="#ffe8cf" opacity="{.35 + .5 * (1 - j / 70):.2f}"/>')
    other_stars = "".join(
        f'<circle cx="{(h01(f"o{i}", "x") - .5) * 2.2 * WR:.1f}" cy="{(h01(f"o{i}", "y") - .5) * 2.2 * WR:.1f}" '
        f'r="{.3 + .5 * h01(f"o{i}", "r"):.2f}" fill="#fff1e0" opacity="{.4 + .5 * h01(f"o{i}", "o"):.2f}"/>'
        for i in range(40))
    streaks = []
    for i in range(9):  # our own stars, lensed into arcs around the throat
        rr = WR + 1.5 + 7 * h01(f"st{i}", "r")
        a0 = h01(f"st{i}", "a") * 360
        span = 14 + 30 * h01(f"st{i}", "s") * (WR / rr)
        x0, y0 = rr * math.cos(math.radians(a0)), rr * math.sin(math.radians(a0))
        x1, y1 = rr * math.cos(math.radians(a0 + span)), rr * math.sin(math.radians(a0 + span))
        streaks.append(f'<path d="M{x0:.1f},{y0:.1f} A{rr:.1f},{rr:.1f} 0 0,1 {x1:.1f},{y1:.1f}" fill="none" '
                       f'stroke="#e4ebff" stroke-width=".7" stroke-linecap="round" '
                       f'opacity="{.25 + .45 * h01(f"st{i}", "o"):.2f}"/>')
    return "".join([
        f'<g transform="translate({WX},{WY})">',
        f'<circle r="{WR}" fill="url(#othersky)"/>',
        f'<clipPath id="{cid}"><circle r="{WR}"/></clipPath>'
        f'<g clip-path="url({chr(35)}{cid})">{other_stars}'
        f'<g transform="rotate(28) scale({WR / 34:.3f},{.55 * WR / 34:.3f})"><circle r="5" fill="url(#gcore)"/>{"".join(arms)}</g>'
        '<animateTransform attributeName="transform" type="translate" values="-2,1;2,-1;-2,1" dur="40s" '
        'repeatCount="indefinite"/></g>',
        f'<circle r="{WR}" fill="url(#rimdark)"/>',
        f'<circle r="{WR + .4}" fill="none" stroke="#e8eeff" stroke-width=".8" opacity=".55"/>',
        f'<g>{"".join(streaks)}<animateTransform attributeName="transform" type="rotate" from="0" to="-360" '
        'dur="140s" repeatCount="indefinite"/></g>',
        (f'<text y="{WR + 20}" text-anchor="middle" font-family="{PLEX}" font-size="10.5" fill="{MUTED}">'
         'wormhole &#8594; cthecosmos.com</text>') if label else '',
        '</g>'])


def wormhole_defs():
    return ('<radialGradient id="othersky"><stop offset="0" stop-color="#2b2016"/>'
            '<stop offset="1" stop-color="#0d0a08"/></radialGradient>'
            '<radialGradient id="gcore"><stop offset="0" stop-color="#fff2dc"/>'
            '<stop offset="1" stop-color="#ffd9a8" stop-opacity="0"/></radialGradient>'
            '<radialGradient id="rimdark"><stop offset=".72" stop-color="#000" stop-opacity="0"/>'
            '<stop offset=".97" stop-color="#000" stop-opacity=".75"/>'
            '<stop offset="1" stop-color="#c9d6ff" stop-opacity=".35"/></radialGradient>'
            '<radialGradient id="psrg"><stop offset="0" stop-color="#e6efff" stop-opacity=".95"/>'
            '<stop offset="1" stop-color="#7fa6ff" stop-opacity="0"/></radialGradient>'
            f'<radialGradient id="bfade" gradientUnits="userSpaceOnUse" cx="{PX}" cy="{PY}" r="105">'
            '<stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#000"/></radialGradient>'
            f'<mask id="beamfade" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">'
            f'<rect width="{W}" height="{H}" fill="url(#bfade)"/></mask>')


# ======================================================================= text

def text_layer(title):
    sup = 'baseline-shift="super" font-size="9"'
    return (f'<text x="36" y="58" font-family="{STIX}" font-size="31" font-weight="600" fill="{TEXT}">'
            f'{escape(title)}</text>'
            f'<text x="37" y="82" font-family="{PLEX}" font-size="12.5" fill="{MUTED}">'
            f'<tspan fill="{ACCENT}">$ whoami</tspan>  embedded software engineer, onboard diagnostics for '
            'autonomous trucks</text>'
            f'<g font-family="{STIX}" font-size="13.5" font-style="italic" fill="{MUTED}">'
            f'<text x="36" y="{H - 36}"><tspan font-style="normal" font-weight="600" fill="{TEXT}">Fig. 1</tspan>'
            '  My public repos on Keplerian orbits around a Schwarzschild black hole of '
            f'4.3 × 10<tspan {sup}>6</tspan> solar masses (Sgr A*), seen at 81°.</text>'
            f'<text x="36" y="{H - 17}">Periapsis advances 6πGM / c²a(1 - e²) per orbit (1PN), the disk turns at '
            'its local Kepler rate, the approaching side is Doppler-boosted. Time × 1200.</text></g>')


# ======================================================================= build

def build(featured, palette, days, title="Yashwanth Naidu"):
    """featured: repos innermost first (most recent push first).
    palette: dict repo name -> planet colour."""
    els = orbital_elements(featured)
    top_stars = max((e["repo"]["stargazers_count"] for e in els), default=0)
    trails, bodies = [], []
    for el in els:
        s = el["repo"]["stargazers_count"]
        rad = 3.8 + 2.3 * math.log10(s + 1)
        tr, body = planet_svg(el, palette.get(el["repo"]["name"], "#9aa4b2"), rad,
                              ring=(s == top_stars and s > 0))
        trails.append(tr)
        bodies.append(body)
    svg = "".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img">',
        '<title>Repositories orbiting a black hole, with a pulsar and a wormhole</title>',
        f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#010204"/>'
        f'<stop offset="1" stop-color="#05070c"/></linearGradient>'
        f'<clipPath id="frame"><rect width="{W}" height="{H}" rx="12"/></clipPath>'
        f'{black_hole_defs()}{wormhole_defs()}</defs>',
        '<g clip-path="url(#frame)">',
        f'<rect width="{W}" height="{H}" fill="url(#bg)"/>',
        sky(), "".join(trails), black_hole(), "".join(bodies),
        pulsar(days), wormhole(), text_layer(title),
        '</g>',
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="12" fill="none" stroke="#30363d"/>',
        '</svg>'])
    return embed(svg), els
