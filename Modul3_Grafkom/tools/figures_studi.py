#!/usr/bin/env python3
"""tools/figures_studi.py -- diagram SVG untuk Studi Pendahuluan Modul 3.

Ditulis tangan sebagai SVG (tanpa pustaka plotting); kurva dihitung dari rumus,
bukan digambar kira-kira.        python3 tools/figures_studi.py -> docs/figures/
"""
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "figures")
os.makedirs(OUT, exist_ok=True)
FONT = 'font-family="Helvetica,Arial,sans-serif"'


def svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
            f'<rect width="{w}" height="{h}" fill="#fff"/>{body}</svg>')


def t(x, y, s, size=12, fill="#222", anchor="start", bold=False):
    b = ' font-weight="bold"' if bold else ""
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}"{b} {FONT}>{s}</text>'


def line(x1, y1, x2, y2, c="#222", w=1.0, extra=""):
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{c}" stroke-width="{w}" {extra}/>'


def poly(pts, c, w=2.0, extra=""):
    return f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="none" stroke="{c}" stroke-width="{w}" {extra}/>'


ARROW = ('<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
         'orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#1f4e79"/></marker></defs>')


def pinhole():
    # side view: z to the right (distance in front of camera), y up
    ox, oy, s = 60, 200, 52
    X = lambda z: ox + z * s
    Y = lambda y: oy - y * s
    d, (py, pz) = 2.0, (2.4, 8.0)
    b = ARROW
    b += line(X(0), Y(0), X(9.5), Y(0), "#999", 1, 'stroke-dasharray="4 3"')
    b += t(X(9.5), Y(0) + 16, "sumbu optik (z)", 11, "#666", "end")
    b += line(X(d), Y(-1.2), X(d), Y(3.0), "#2e75b6", 2.5)
    b += t(X(d) + 4, Y(3.0) - 4, "bidang citra (jarak d)", 11, "#2e75b6")
    b += f'<circle cx="{X(0):.1f}" cy="{Y(0):.1f}" r="5" fill="#222"/>' + t(X(0) - 8, Y(0) + 18, "pinhole O", 11, "#222", "middle")
    b += line(X(0), Y(0), X(pz), Y(py), "#e07b00", 1.8)
    b += f'<circle cx="{X(pz):.1f}" cy="{Y(py):.1f}" r="5" fill="#e07b00"/>' + t(X(pz) + 8, Y(py) - 6, "P = (y, z)", 12, "#b35900", bold=True)
    yp = d * py / pz
    b += f'<circle cx="{X(d):.1f}" cy="{Y(yp):.1f}" r="5" fill="#1f4e79"/>' + t(X(d) + 8, Y(yp) + 16, "P′ = (d·y/z)", 12, "#1f4e79", bold=True)
    b += line(X(pz), Y(0), X(pz), Y(py), "#e07b00", 1, 'stroke-dasharray="3 3"') + t(X(pz) + 5, Y(py / 2), "y", 12, "#b35900")
    b += line(X(d), Y(0), X(d), Y(yp), "#1f4e79", 1.2, 'stroke-dasharray="3 3"')
    b += t(X(d / 2), Y(0) + 16, "d", 12, "#1f4e79", "middle") + t(X(pz / 2), Y(0) + 34, "z", 12, "#b35900", "middle")
    b += t(20, 22, "Segitiga sebangun: y′/d = y/z  ⇒  y′ = d·y/z (dan x′ = d·x/z)", 13, bold=True)
    return svg(600, 270, b)


def depth_curve():
    W, H, ox, oy, pw, ph = 620, 330, 60, 270, 520, 220
    zmin, zmax = math.log10(0.01), math.log10(1000)
    X = lambda z: ox + (math.log10(z) - zmin) / (zmax - zmin) * pw
    Y = lambda d: oy - d * ph
    b = ""
    for e in range(-2, 4):
        b += line(X(10 ** e), oy, X(10 ** e), oy - ph, "#eee") + t(X(10 ** e), oy + 16, f"{10 ** e:g} m", 11, "#555", "middle")
    for k in range(5):
        b += line(ox, Y(k / 4), ox + pw, Y(k / 4), "#eee") + t(ox - 6, Y(k / 4) + 4, f"{k / 4:g}", 11, "#555", "end")
    for (n, f, col, lab) in ((0.01, 1000.0, "#c0504d", "near 0.01, far 1000"), (0.1, 20.0, "#2e75b6", "near 0.1, far 20 (model saya)")):
        pts = []
        z = n
        while z <= f:
            pts.append((X(z), Y(f * (z - n) / (z * (f - n)))))
            z *= 1.05
        b += poly(pts, col, 2.4)
        b += t(ox + pw - 4, Y(0.12 if f > 100 else 0.22), lab, 11, col, "end", True)
    d1 = 1000 * (1 - 0.01) / (1 * (1000 - 0.01))
    b += f'<circle cx="{X(1):.1f}" cy="{Y(d1):.1f}" r="5" fill="#c0504d"/>'
    b += t(X(1) + 8, Y(d1) + 18, f"z = 1 m → depth {d1:.3f}: 99 % kode sudah terpakai", 11, "#c0504d", bold=True)
    b += t(ox + pw / 2, oy + 36, "jarak dari kamera (skala log)", 12, "#222", "middle")
    b += t(14, oy - ph / 2, "depth [0,1]", 12, "#222", "middle").replace("<text", f'<text transform="rotate(-90 14 {oy - ph / 2})"')
    b += t(ox, 22, "Depth (window) d(z) = f(z−n) / (z(f−n)) — naik seperti 1/z, jenuh di dekat kamera", 13, bold=True)
    return svg(W, H, b)


def clip_w():
    W, H, ox, oy, pw, ph = 560, 300, 60, 150, 460, 220
    X = lambda w: ox + (w + 1.2) / 2.4 * pw
    Y = lambda v: oy - max(-6, min(6, v)) / 6 * (ph / 2)
    b = line(ox, oy, ox + pw, oy, "#999") + line(X(0), oy - ph / 2, X(0), oy + ph / 2, "#999")
    for side in (-1, 1):
        pts, w = [], side * 1.2
        while abs(w) >= 1 / 6:
            pts.append((X(w), Y(1.0 / w)))
            w -= side * 0.01
        b += poly(pts, "#c0504d", 2.4)
    b += t(X(0) + 6, oy - ph / 2 + 12, "x/w → +∞", 11, "#c0504d") + t(X(0) - 6, oy + ph / 2 - 4, "x/w → −∞", 11, "#c0504d", "end")
    b += t(X(1.1), oy + 16, "w", 12, "#222", "middle") + t(X(0) + 4, oy + 16, "0", 11, "#555")
    b += t(X(0.6), Y(1 / 0.6) - 10, "di depan kamera (w > 0)", 11, "#1f4e79")
    b += t(X(-1.15), Y(-1 / 0.9) + 26, "di belakang kamera (w &lt; 0): tanda terbalik", 11, "#1f4e79")
    b += t(20, 22, "x = 1 tetap, w melewati 0: x/w meledak lalu berbalik tanda", 13, bold=True)
    return svg(W, H, b)


def drawcall():
    st = [("Vertex buffer (posisi, normal, UV)", "data kita", "#f4f4f4", "#999"),
          ("Vertex shader: gl_Position = P·V·M·p", "PROGRAMMABLE (kita tulis)", "#e8f1fb", "#2e75b6"),
          ("Primitive assembly + clipping + /w + viewport", "fixed", "#f4f4f4", "#999"),
          ("Rasteriser (coverage, interpolasi atribut)", "fixed", "#f4f4f4", "#999"),
          ("Fragment shader: texture + lighting", "PROGRAMMABLE (kita tulis)", "#e8f1fb", "#2e75b6"),
          ("Depth test / blend", "fixed, dikonfigurasi", "#f4f4f4", "#999"),
          ("Framebuffer → layar", "memori", "#f4f4f4", "#999")]
    b = ARROW
    for i, (name, kind, fill, stroke) in enumerate(st):
        y = 12 + i * 52
        b += f'<rect x="20" y="{y}" width="540" height="38" rx="6" fill="{fill}" stroke="{stroke}"/>'
        b += t(32, y + 24, name, 12.5, bold=True) + t(550, y + 24, kind, 11, "#1f4e79" if "PROG" in kind else "#666", "end", "PROG" in kind)
        if i < len(st) - 1:
            b += line(290, y + 38, 290, y + 50, "#1f4e79", 1.6, 'marker-end="url(#a)"')
    return svg(580, 382, b)


for name, fn in (("fig_pinhole", pinhole), ("fig_depth", depth_curve), ("fig_clip_w", clip_w), ("fig_drawcall", drawcall)):
    with open(os.path.join(OUT, name + ".svg"), "w", encoding="utf-8") as fh:
        fh.write(fn())
    print("tulis docs/figures/" + name + ".svg")
