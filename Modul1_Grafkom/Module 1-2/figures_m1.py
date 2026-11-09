"""Module 1 -- figures for the pre-study (Q1a, Q1b, Q2a, Q2c) as hand-written SVG.

No plotting library: every curve is computed with NumPy and written as an SVG
polyline, so the figures are reproducible and inspectable as text.

Writes figures/:
  fig_sampling.svg   continuous signal, samples every Delta, stair-step
                     reconstruction, 3-bit quantisation levels      (Q1a)
  fig_alias.svg      a 0.7 c/px wave and the 0.3 c/px alias that passes
                     through exactly the same samples              (Q1b)
  fig_rgb_cube.svg   RGB cube: black, white, primaries, secondaries,
                     grey diagonal                                 (Q2a)
  fig_hsv_cone.svg   HSV hexcone: hue angle, saturation radius, value axis
  fig_srgb_curve.svg real sRGB decode vs gamma-2 vs identity; code 0.5 marked (Q2c)

Run:  python figures_m1.py
"""
from __future__ import annotations

import colorsys
import os

import numpy as np

from srgb import srgb_to_linear

OUT = "figures"
FONT = 'font-family="Helvetica,Arial,sans-serif"'


def _svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
            f'<rect width="{w}" height="{h}" fill="#fff"/>{body}</svg>')


def _poly(xs, ys, color, width=2, dash=""):
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{width}"{d}/>'


def _t(x, y, s, size=12, color="#222", anchor="start", extra=""):
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{color}" text-anchor="{anchor}" {FONT} {extra}>{s}</text>'


def sampling():
    W, H, x0, y0, sx, sy = 640, 300, 50, 250, 560 / 10, 200
    f = lambda x: 0.5 + 0.35 * np.sin(2 * np.pi * x / 6.0) + 0.1 * np.sin(2 * np.pi * x / 2.3)
    xs = np.linspace(0, 10, 600)
    b = []
    for k in range(9):                                   # 3-bit levels
        y = y0 - sy * k / 7
        b.append(f'<line x1="{x0}" x2="{x0 + 560}" y1="{y:.1f}" y2="{y:.1f}" stroke="#eee"/>')
        b.append(_t(x0 + 565, y + 4, f"{k}", 10, "#999")) if k < 8 else None
    b.append(_poly(x0 + xs * sx, y0 - sy * f(xs), "#1f4e79", 2.5))
    n = np.arange(0.5, 10, 1.0)
    q = np.round(f(n) * 7) / 7
    sx_pts, sy_pts = [], []
    for xi, qi in zip(n, q):
        sx_pts += [x0 + (xi - 0.5) * sx, x0 + (xi + 0.5) * sx]
        sy_pts += [y0 - sy * qi] * 2
    b.append(_poly(sx_pts, sy_pts, "#e07b00", 2, "6 3"))
    for xi in n:
        b.append(f'<line x1="{x0 + xi * sx:.1f}" x2="{x0 + xi * sx:.1f}" y1="{y0}" y2="{y0 - sy * f(xi):.1f}" stroke="#e07b00" stroke-dasharray="2 3"/>')
        b.append(f'<circle cx="{x0 + xi * sx:.1f}" cy="{y0 - sy * f(xi):.1f}" r="4.5" fill="#e07b00"/>')
    b.append(f'<line x1="{x0}" x2="{x0 + 570}" y1="{y0}" y2="{y0}" stroke="#222"/>'
             f'<line x1="{x0}" x2="{x0}" y1="{y0}" y2="30" stroke="#222"/>')
    a, c = x0 + 0.5 * sx, x0 + 1.5 * sx
    b.append(f'<line x1="{a}" x2="{c}" y1="{y0 + 18}" y2="{y0 + 18}" stroke="#222" marker-end="url(#ar)" marker-start="url(#ar)"/>')
    b.insert(0, '<defs><marker id="ar" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#222"/></marker></defs>')
    b.append(_t((a + c) / 2, y0 + 34, "Δ = jarak sampel (1 pixel)", 12, "#222", "middle"))
    b.append(_t(x0, 22, "sinyal kontinu (biru), sampel di pusat pixel (oranye), rekonstruksi tangga 3-bit (putus-putus)", 12))
    b.append(_t(x0 + 590, 40, "level", 10, "#999"))
    return _svg(W, H + 20, "".join(b))


def alias():
    W, H, x0, y0, sx, A = 640, 260, 40, 140, 56, 80
    xs = np.linspace(0, 10, 800)
    b = [f'<line x1="{x0}" x2="{x0 + 570}" y1="{y0}" y2="{y0}" stroke="#bbb"/>',
         _poly(x0 + xs * sx, y0 - A * np.cos(2 * np.pi * 0.7 * xs), "#1f4e79", 2),
         _poly(x0 + xs * sx, y0 - A * np.cos(2 * np.pi * 0.3 * xs), "#c0504d", 2, "7 4")]
    for n in range(11):
        b.append(f'<circle cx="{x0 + n * sx}" cy="{y0 - A * np.cos(2 * np.pi * 0.7 * n):.1f}" r="5" fill="#e07b00"/>')
    b.append(_t(x0, 24, "biru: pola asli 0.7 cycles/pixel   merah putus-putus: alias |0.7 − 1| = 0.3 cycles/pixel", 12))
    b.append(_t(x0, H - 12, "Titik oranye (1 sampel/pixel) identik untuk kedua gelombang: setelah sampling, 0.7 tidak bisa dibedakan dari 0.3.", 12))
    return _svg(W, H, "".join(b))


def rgb_cube():
    W, H = 580, 420
    o, ex, ey, ez = np.array([170, 340]), np.array([200, 0]), np.array([0, -200]), np.array([110, -80])

    def P(r, g, bb):            # R right, G up, B into the page
        return o + r * ex + g * ey + bb * ez
    verts = {(r, g, bb): P(r, g, bb) for r in (0, 1) for g in (0, 1) for bb in (0, 1)}
    names = {(0, 0, 0): "hitam (0,0,0)", (1, 1, 1): "putih (1,1,1)", (1, 0, 0): "merah R",
             (0, 1, 0): "hijau G", (0, 0, 1): "biru B", (1, 1, 0): "kuning", (0, 1, 1): "cyan",
             (1, 0, 1): "magenta"}
    b = []
    for a in verts:
        for k in range(3):
            if a[k] == 0:
                c = list(a); c[k] = 1; c = tuple(c)
                dash = ' stroke-dasharray="4 4"' if (a[2] == 1 or c[2] == 1) and (a[0] == 0 and c[0] == 0 or a[1] == 0 and c[1] == 0) else ""
                b.append(f'<line x1="{verts[a][0]}" y1="{verts[a][1]}" x2="{verts[c][0]}" y2="{verts[c][1]}" stroke="#888"{dash}/>')
    p0, p1 = verts[(0, 0, 0)], verts[(1, 1, 1)]
    b.append(f'<line x1="{p0[0]}" y1="{p0[1]}" x2="{p1[0]}" y2="{p1[1]}" stroke="#333" stroke-width="3"/>')
    mid = (p0 + p1) / 2
    b.append(_t(mid[0] + 8, mid[1] + 18, "diagonal abu-abu R=G=B", 12, "#333"))
    for k, p in verts.items():
        col = "#%02x%02x%02x" % tuple(int(v * 255) for v in k)
        b.append(f'<circle cx="{p[0]}" cy="{p[1]}" r="9" fill="{col}" stroke="#333"/>')
        dx = 14 if k[0] == 1 else -14
        b.append(_t(p[0] + dx, p[1] - 12, names[k], 12, "#222", "start" if dx > 0 else "end"))
    b.append(_t(20, 24, "Kubus RGB (aditif): sumbu R, G, B dari 0 sampai 1", 13))
    return _svg(W, H, "".join(b))


def hsv_cone():
    W, H, cx, top, R, h = 640, 470, 360, 140, 170, 280
    b = []
    for deg in range(0, 360, 3):            # hue ring as wedges on the top face (ellipse)
        a0, a1 = np.radians(deg), np.radians(deg + 3)
        r, g, bb = colorsys.hsv_to_rgb(deg / 360, 1, 1)
        col = "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(bb * 255))
        pts = [(cx, top), (cx + R * np.cos(a0), top - 0.35 * R * np.sin(a0)),
               (cx + R * np.cos(a1), top - 0.35 * R * np.sin(a1))]
        b.append('<polygon points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + f'" fill="{col}" stroke="{col}"/>')
    b.append(f'<line x1="{cx - R}" y1="{top}" x2="{cx}" y2="{top + h}" stroke="#333"/>'
             f'<line x1="{cx + R}" y1="{top}" x2="{cx}" y2="{top + h}" stroke="#333"/>'
             f'<line x1="{cx}" y1="{top}" x2="{cx}" y2="{top + h}" stroke="#333" stroke-width="2.5" stroke-dasharray="5 4"/>')
    b.append(f'<circle cx="{cx}" cy="{top}" r="6" fill="#fff" stroke="#333"/>'
             f'<circle cx="{cx}" cy="{top + h}" r="6" fill="#000"/>')
    b.append(_t(cx + 10, top + h + 4, "V = 0 (hitam)", 12))
    b.append(_t(cx - R - 8, top + 4, "puncak: V = 1, S = 0 → putih", 12, "#222", "end"))
    b.append(f'<line x1="{cx}" y1="{top}" x2="{cx + R}" y2="{top}" stroke="#222" stroke-width="2"/>')
    b.append(_t(cx + R + 4, top + 22, "S: 0 → 1 (radius)", 12))
    b.append(_t(cx + 12, top + h / 2 + 30, "V: value (sumbu)", 12))
    b.append(_t(cx + R + 4, top + 4, "H = 0° merah", 12))
    b.append(_t(cx - R * 0.5, top - 0.35 * R * 0.866 - 10, "H = 120° hijau", 12, "#222", "middle"))
    b.append(_t(cx - R * 0.5, top + 0.35 * R * 0.866 + 20, "H = 240° biru", 12, "#222", "middle"))
    b.append(_t(20, 24, "Kerucut HSV: H = sudut, S = jarak dari sumbu, V = tinggi", 13))
    return _svg(W, H, "".join(b))


def srgb_curve():
    W, H, x0, y0, s = 460, 440, 60, 380, 340
    c = np.linspace(0, 1, 400)
    b = []
    for k in range(5):
        v = k / 4
        b.append(f'<line x1="{x0}" x2="{x0 + s}" y1="{y0 - v * s}" y2="{y0 - v * s}" stroke="#eee"/>'
                 f'<line y1="{y0}" y2="{y0 - s}" x1="{x0 + v * s}" x2="{x0 + v * s}" stroke="#eee"/>')
        b.append(_t(x0 - 8, y0 - v * s + 4, f"{v:g}", 11, "#555", "end"))
        b.append(_t(x0 + v * s, y0 + 16, f"{v:g}", 11, "#555", "middle"))
    b.append(_poly(x0 + c * s, y0 - c * s, "#999", 1.5, "5 4"))
    b.append(_poly(x0 + c * s, y0 - c ** 2 * s, "#e07b00", 2, "8 4"))
    b.append(_poly(x0 + c * s, y0 - srgb_to_linear(c) * s, "#1f4e79", 3))
    l_real = float(srgb_to_linear(0.5))
    b.append(f'<line x1="{x0 + 0.5 * s}" x2="{x0 + 0.5 * s}" y1="{y0}" y2="{y0 - 0.25 * s}" stroke="#c0504d" stroke-dasharray="3 3"/>'
             f'<line x1="{x0}" x2="{x0 + 0.5 * s}" y1="{y0 - l_real * s}" y2="{y0 - l_real * s}" stroke="#c0504d" stroke-dasharray="3 3"/>'
             f'<circle cx="{x0 + 0.5 * s}" cy="{y0 - l_real * s}" r="5" fill="#c0504d"/>')
    b.append(_t(x0 + 0.5 * s + 8, y0 - l_real * s + 18, f"kode 0.5 → ℓ = {l_real:.3f} (sRGB)", 12, "#c0504d"))
    b.append(_t(x0 + 0.5 * s - 8, y0 - 0.25 * s - 8, "gamma-2: 0.25", 11, "#e07b00", "end"))
    b.append(_t(x0 + s / 2, y0 + 36, "kode sRGB c (yang disimpan berkas)", 12, "#222", "middle"))
    b.append(_t(18, y0 - s / 2, "linear light ℓ", 12, "#222", "middle", f'transform="rotate(-90 18 {y0 - s / 2})"'))
    b.append(_t(x0 + 8, 26, "biru: decode sRGB sungguhan · oranye: c² · abu-abu: ℓ = c", 12))
    return _svg(W, H, "".join(b))


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    for name, fn in (("fig_sampling", sampling), ("fig_alias", alias), ("fig_rgb_cube", rgb_cube),
                     ("fig_hsv_cone", hsv_cone), ("fig_srgb_curve", srgb_curve)):
        with open(os.path.join(OUT, name + ".svg"), "w", encoding="utf-8") as f:
            f.write(fn())
        print(f"wrote {OUT}/{name}.svg")


if __name__ == "__main__":
    main()
