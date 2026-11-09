#!/usr/bin/env python3
"""tools/figures_studi.py -- diagram SVG untuk Studi Pendahuluan Modul 4.
Koordinat dihitung dengan fk.py / ik.py / spline.py yang sama (tanpa pustaka
plotting).          python3 tools/figures_studi.py -> docs/figures/"""
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from fk import Bone, forward_kinematics          # noqa: E402
from ik import solve_two_bone_ik                 # noqa: E402
from spline import catmull_rom_point             # noqa: E402

OUT = os.path.join(ROOT, "docs", "figures")
os.makedirs(OUT, exist_ok=True)
F = 'font-family="Helvetica,Arial,sans-serif"'


def svg(w, h, b):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}"><rect width="{w}" height="{h}" fill="#fff"/>{b}</svg>'


def t(x, y, s, size=12, fill="#222", anchor="start", bold=False):
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" {"font-weight=\"bold\"" if bold else ""} {F}>{s}</text>'


def line(a, b, c="#222", w=1.0, extra=""):
    return f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="{c}" stroke-width="{w}" {extra}/>'


def dot(p, r=5, c="#222"):
    return f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="{r}" fill="{c}"/>'


def grid(X, Y, xs, ys):
    b = ""
    for x in xs:
        b += line(X((x, ys[0])), X((x, ys[-1])), "#eee") + t(X((x, ys[0]))[0], X((x, ys[0]))[1] + 14, x, 10, "#888", "middle")
    for y in ys:
        b += line(X((xs[0], y)), X((xs[-1], y)), "#eee") + t(X((xs[0], y))[0] - 6, X((xs[0], y))[1] + 4, y, 10, "#888", "end")
    return b


def fk_fig():
    s, ox, oy = 52, 70, 260
    X = lambda p: (ox + p[0] * s, oy - p[1] * s)
    pts, _ = forward_kinematics([Bone(3.0, 30.0), Bone(2.0, 60.0)])
    b = grid(X, None, list(range(0, 6)), list(range(0, 5)))
    b += line(X(pts[0]), X(pts[1]), "#2e75b6", 6) + line(X(pts[1]), X(pts[2]), "#e07b00", 6)
    for p, n in zip(pts, ["bahu (0, 0)", "siku (2.598, 1.500)", "tangan (2.598, 3.500)"]):
        b += dot(X(p), 6) + t(X(p)[0] + 10, X(p)[1] - 6, n, 12, bold=True)
    b += line(X(pts[1]), X((pts[1][0] + 1.6, pts[1][1] + 1.6 * math.tan(math.radians(30)))), "#2e75b6", 1, 'stroke-dasharray="4 3"')
    b += t(X(pts[0])[0] + 60, X(pts[0])[1] - 12, "30° (lokal = global)", 11, "#2e75b6")
    b += t(X(pts[1])[0] + 30, X(pts[1])[1] - 38, "+60° lokal → 90° global", 11, "#b35900")
    b += t(20, 20, "FK Contoh E1: panjang 3 dan 2, sudut lokal 30° dan 60° (dari fk.py)", 13, bold=True)
    return svg(470, 300, b)


def ik_fig():
    s, ox, oy = 52, 60, 160
    X = lambda p: (ox + p[0] * s, oy - p[1] * s)
    th1, th2 = solve_two_bone_ik(3.0, 2.0, (4.0, 1.0))
    e = (3 * math.cos(math.radians(th1)), 3 * math.sin(math.radians(th1)))
    b = grid(X, None, list(range(0, 6)), list(range(-1, 3)))
    b += line(X((0, 0)), X((4, 1)), "#999", 1.5, 'stroke-dasharray="5 4"')
    b += line(X((0, 0)), X(e), "#2e75b6", 6) + line(X(e), X((4, 1)), "#e07b00", 6)
    b += dot(X((0, 0)), 6) + t(X((0, 0))[0] - 4, X((0, 0))[1] - 10, "bahu", 12, bold=True)
    b += dot(X(e), 6) + t(X(e)[0] + 8, X(e)[1] + 16, f"siku ({e[0]:.3f}, {e[1]:.3f})", 12, bold=True)
    b += dot(X((4, 1)), 7, "#c00000") + t(X((4, 1))[0] + 10, X((4, 1))[1] - 6, "target (4, 1)", 12, "#c00000", bold=True)
    b += t(X((2, 0.5))[0] - 10, X((2, 0.5))[1] - 8, "d = √17 = 4.123", 11, "#555")
    b += t(X((1.5, -0.35))[0], X((1.5, -0.35))[1] + 12, "ℓ₁ = 3", 11, "#2e75b6")
    b += t(X((3.5, 0.0))[0] + 6, X((3.5, 0.0))[1] + 4, "ℓ₂ = 2", 11, "#b35900")
    b += t(20, 20, f"IK Contoh E2: θ₁ = {th1:.2f}°, θ₂ = {th2:.2f}° (dari ik.py)", 13, bold=True)
    b += t(20, 245, "cos θ₂ = (d² − ℓ₁² − ℓ₂²) / (2ℓ₁ℓ₂) = (17 − 9 − 4)/12 = 1/3  →  θ₂ = 70.53°", 12, "#222")
    return svg(470, 258, b)


def spline_fig():
    s, ox, oy = 44, 40, 210
    X = lambda p: (ox + p[0] * s, oy - p[1] * s)
    cps = [(0, 0), (2, 3), (5, 3), (7, 0), (10, 1)]
    ext = [cps[0]] + cps + [cps[-1]]
    pts = []
    for i in range(len(ext) - 3):
        for k in range(0, 21):
            q = catmull_rom_point(ext[i], ext[i + 1], ext[i + 2], ext[i + 3], k / 20)
            pts.append(X((q[0], q[1])))
    b = grid(X, None, list(range(0, 11, 2)), list(range(-1, 5)))
    b += f'<polyline points="{" ".join(f"{X(p)[0]:.1f},{X(p)[1]:.1f}" for p in cps)}" fill="none" stroke="#999" stroke-width="1.5" stroke-dasharray="5 4"/>'
    b += f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="none" stroke="#2e75b6" stroke-width="2.6"/>'
    for p in cps:
        b += dot(X(p), 5, "#e07b00")
    b += t(20, 20, "Titik kontrol saya: polyline (abu-abu, sudut tajam) vs Catmull–Rom (biru, C¹)", 13, bold=True)
    return svg(520, 280, b)


def loop_fig():
    st = [("Input", "keyboard, mouse, gamepad", "#f4f4f4", "#999"),
          ("Update: fisika", "posisi root, tabrakan", "#f4f4f4", "#999"),
          ("Update: animasi", "keyframe/slerp → sudut lokal → FK → pose tulang (world)", "#fff1e0", "#e07b00"),
          ("Update: AI / logika", "keputusan NPC, kamera spline", "#f4f4f4", "#999"),
          ("Render (Modul 3)", "skinning → M·V·P → rasterisasi → shading", "#e8f1fb", "#2e75b6"),
          ("Present", "swap buffer, tunggu vsync (16.7 ms @ 60 Hz)", "#f4f4f4", "#999")]
    b = '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#1f4e79"/></marker></defs>'
    for i, (n, d, fill, stroke) in enumerate(st):
        y = 12 + i * 54
        b += f'<rect x="20" y="{y}" width="500" height="40" rx="6" fill="{fill}" stroke="{stroke}"/>'
        b += t(32, y + 17, n, 13, bold=True) + t(32, y + 33, d, 11, "#444")
        if i < len(st) - 1:
            b += line((270, y + 40), (270, y + 52), "#1f4e79", 1.6, 'marker-end="url(#a)"')
    y0, y1 = 12 + 5 * 54 + 20, 32
    b += f'<path d="M520,{y0} C690,{y0} 690,{y1} 520,{y1}" fill="none" stroke="#1f4e79" stroke-width="1.6" marker-end="url(#a)"/>'
    b += t(700, (y0 + y1) / 2, "frame", 11, "#1f4e79") + t(700, (y0 + y1) / 2 + 14, "berikutnya", 11, "#1f4e79")
    b += t(530, 12 + 2 * 54 + 25, "← FK di sini", 12, "#b35900", bold=True)
    b += t(530, 12 + 4 * 54 + 25, "← Modul 3", 12, "#1f4e79", bold=True)
    return svg(780, 340, b)


for name, fn in (("fig_fk", fk_fig), ("fig_ik", ik_fig), ("fig_spline", spline_fig), ("fig_loop", loop_fig)):
    with open(os.path.join(OUT, name + ".svg"), "w", encoding="utf-8") as fh:
        fh.write(fn())
    print("tulis docs/figures/" + name + ".svg")
