#!/usr/bin/env python3
"""tools/figures_m5.py -- every figure in docs/ (Studi Pendahuluan + Laporan),
computed from the repo's own code and outputs. Run after fit_nerf_toy.py
(both scenes, init 0 and -1), nerf_bug.py, lab2_improve.py and
ar_app/occlusion_test.py:

    python tools/figures_m5.py      -> docs/figures/*.png
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                     # noqa: E402
import numpy as np                                  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from capture import load_ppm                         # noqa: E402
from nerf_toy import VoxelGrid, render_analytic, render_grid, ring_camera, psnr   # noqa: E402
from ray_generator import running_example as ray_ex  # noqa: E402
from volume_render import running_example as vr_ex  # noqa: E402

OUT = os.path.join(ROOT, "docs", "figures")
DATA = os.path.join(ROOT, "out")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.size": 9, "font.family": "DejaVu Sans", "axes.spines.top": False,
                     "axes.spines.right": False, "savefig.dpi": 200, "savefig.bbox": "tight"})
BLUE, ORANGE, GREEN, RED, GREY = "#2e75b6", "#e07b00", "#2d6a4f", "#c00000", "#888888"


def save(fig, name):
    fig.savefig(os.path.join(OUT, name))
    plt.close(fig)
    print("wrote docs/figures/" + name)


# ----------------------------------------------------------------- Q1: pinhole
def fig_pinhole():
    d, n = ray_ex()
    fig, ax = plt.subplots(1, 2, figsize=(8.2, 3.2), gridspec_kw=dict(width_ratios=[1.35, 1]))
    fig.subplots_adjust(wspace=0.32)
    a = ax[0]
    a.plot([-1.3, 1.3], [-1, -1], color=GREY, lw=2)
    a.text(-1.3, -1.07, "bidang gambar z = −1", va="top", fontsize=7.5, color=GREY)
    a.plot([0, 0], [0, -1.45], ls=":", color=GREY)
    a.text(-0.12, -0.62, "sumbu optik (−z)", fontsize=7.5, color=GREY, rotation=90, ha="center", va="center")
    a.annotate("", xy=(0.8 * 1.4, -1.4), xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", color=BLUE, lw=1.8))
    a.plot([0.8], [-1], "o", color=ORANGE, ms=7, zorder=5)
    a.text(1.25, -1.28, "piksel (400, 240)\nx = (400−320)/100 = 0.8", fontsize=7.5, color=ORANGE, va="center")
    a.plot([0], [0], "ks", ms=6)
    a.text(-0.1, 0.1, "pusat kamera o", ha="right", fontsize=7.5)
    a.text(0.75, -0.25, f"d = (0.8, 0, −1)\n|d| = √1.64 = 1.2806\nd̂ = ({n[0]:.3f}, 0, {n[2]:.3f})",
           fontsize=7.5, color=BLUE)
    a.set_xlim(-1.45, 2.6); a.set_ylim(-1.55, 0.3); a.set_aspect("equal")
    a.set_xlabel("x kamera"); a.set_ylabel("z kamera")
    a.set_title("E1 dilihat dari atas (bidang x–z)", fontsize=9)
    b = ax[1]
    b.add_patch(plt.Rectangle((0, 0), 640, 480, fill=False, color=GREY))
    b.plot([320], [240], "k+", ms=10)
    b.text(320, 270, "(cₓ, c_y) = (320, 240)", fontsize=7.5, ha="center", va="top")
    b.plot([400], [240], "o", color=ORANGE)
    b.annotate("", xy=(600, 450), xytext=(600, 330), arrowprops=dict(arrowstyle="-|>", color=RED))
    b.text(590, 390, "v (baris)\ntumbuh ke bawah", fontsize=7.5, color=RED, ha="right", va="center")
    b.annotate("", xy=(40, 30), xytext=(40, 150), arrowprops=dict(arrowstyle="-|>", color=GREEN))
    b.text(52, 90, "y kamera ke atas\n→ y = −(v − c_y)/f", fontsize=7.5, color=GREEN, va="center")
    b.set_xlim(0, 640); b.set_ylim(480, 0); b.set_aspect("equal")
    b.set_xlabel("u (kolom piksel)"); b.set_ylabel("v (baris piksel)")
    b.set_title("alasan tanda minus pada y", fontsize=9)
    save(fig, "fig_q1_pinhole.png")


# ----------------------------------------------------------------- Q2: compositing
def fig_composite():
    final, w, T, bg = vr_ex()
    a = np.array([0.5, 0.5, 1.0])
    fig, ax = plt.subplots(1, 2, figsize=(7.6, 2.6), gridspec_kw=dict(width_ratios=[2.2, 1]))
    x = np.arange(3)
    cols = ["#d62728", "#2ca02c", "#1f77b4"]
    ax[0].bar(x - 0.27, T, 0.25, color="#cccccc", label="Tᵢ (cahaya yang tersisa)")
    ax[0].bar(x, a, 0.25, color="#999999", label="αᵢ (opasitas)")
    ax[0].bar(x + 0.27, w, 0.25, color=cols, label="wᵢ = Tᵢαᵢ (bobot)")
    for i in range(3):
        ax[0].text(i + 0.27, w[i] + 0.03, f"{w[i]:.2f}", ha="center", fontsize=8)
        ax[0].text(i - 0.27, T[i] + 0.03, f"{T[i]:.2f}", ha="center", fontsize=8)
    ax[0].set_xticks(x, ["sampel 1\nmerah", "sampel 2\nhijau", "sampel 3\nbiru (padat)"])
    ax[0].set_ylim(0, 1.18); ax[0].legend(fontsize=7, frameon=False, loc="upper left", ncol=3)
    ax[0].set_title(f"E2: Σw + T_bg = {w.sum() + bg:.2f}", fontsize=9)
    ax[1].add_patch(plt.Rectangle((0, 0), 1, 1, color=final))
    ax[1].text(0.5, -0.18, f"C = ({final[0]:.2f}, {final[1]:.2f}, {final[2]:.2f})", ha="center", fontsize=9)
    ax[1].set_xlim(0, 1); ax[1].set_ylim(-0.3, 1); ax[1].axis("off")
    ax[1].set_title("warna piksel akhir", fontsize=9)
    save(fig, "fig_q2_composite.png")


# ----------------------------------------------------------------- Q2a/Q3b: activations
def fig_activations():
    fig, ax = plt.subplots(1, 3, figsize=(7.8, 2.4))
    sd = np.linspace(-1.0, 5, 300)
    al = 1 - np.exp(-sd)
    ax[0].plot(sd[sd >= 0], al[sd >= 0], color=BLUE)
    ax[0].plot(sd[sd < 0], al[sd < 0], color=RED, ls="--")
    ax[0].axhline(1, color=GREY, lw=0.6, ls=":"); ax[0].axhline(0, color=GREY, lw=0.6)
    ax[0].text(-0.95, -1.4, "σ < 0 → α < 0:\n'opasitas negatif'", color=RED, fontsize=7)
    ax[0].set_xlabel("σδ"); ax[0].set_title("α = 1 − e^(−σδ)", fontsize=9)
    x = np.linspace(-8, 4, 300)
    sp = np.logaddexp(0, x)
    sg = 1 / (1 + np.exp(-x))
    ax[1].plot(x, sp, color=BLUE, label="σ = softplus(x)")
    ax[1].plot(x, sg, color=ORANGE, label="softplus′(x) = sigmoid(x)")
    for v in (-5, 0):
        ax[1].plot([v], [1 / (1 + np.exp(-v))], "o", color=ORANGE, ms=4)
    ax[1].text(-7.8, 0.75, "x = −5: gradien ×0.0067", fontsize=7, color=ORANGE)
    ax[1].set_ylim(-0.1, 3); ax[1].legend(fontsize=7, frameon=False); ax[1].set_xlabel("σ_raw")
    ax[1].set_title("densitas tak pernah negatif", fontsize=9)
    ax[2].plot(x, sg, color=GREEN, label="c = sigmoid(x)")
    ax[2].plot(x, sg * (1 - sg), color=GREY, ls="--", label="sigmoid′ = s(1−s)")
    ax[2].set_ylim(-0.05, 1.05); ax[2].legend(fontsize=7, frameon=False); ax[2].set_xlabel("c_raw")
    ax[2].set_title("warna selalu di [0, 1]", fontsize=9)
    fig.tight_layout()
    save(fig, "fig_q3_activations.png")


# ----------------------------------------------------------------- my scene reconstruction
def _load_grid(name):
    path = os.path.join(DATA, name)
    if not os.path.exists(path):
        return None
    z = np.load(path)
    g = VoxelGrid(resolution=z["sigma_raw"].shape[0])
    g.sigma_raw, g.color_raw = z["sigma_raw"], z["color_raw"]
    return g


def fig_recon_andy():
    W, H, FOV, NS = 120, 96, 50.0, 96
    grids = [("hasil init 0", _load_grid("andy_grid.npz")), ("hasil init −1", _load_grid("andy_init-1_grid.npz"))]
    if any(g is None for _, g in grids):
        print("skip fig_recon_andy (run fit_nerf_toy.py --scene andy [--init -1] first)")
        return
    angles = [(0.0, "0° (view latih,\ntepat di depan gapura)"), (22.5, "22.5° (held-out)"),
              (190.0, "190° (held-out,\nbelakang candi)")]
    fig, ax = plt.subplots(3, 3, figsize=(7.4, 6.0))
    for j, (ang, lab) in enumerate(angles):
        cam, c2w = ring_camera(ang, 3.0, 1.0)
        gt = render_analytic(W, H, FOV, cam, c2w, n_samples=NS, scene="andy")
        ax[0, j].imshow(np.clip(gt, 0, 1)); ax[0, j].set_title(lab, fontsize=8)
        for i, (gl, g) in enumerate(grids):
            im = render_grid(g, W, H, FOV, cam, c2w, n_samples=NS)[0]
            ax[i + 1, j].imshow(np.clip(im, 0, 1))
            ax[i + 1, j].text(2, H - 4, f"PSNR {psnr(im, gt):.1f} dB", color="k", fontsize=7,
                              bbox=dict(fc="white", ec="none", alpha=0.8, pad=1))
    for i, lab in enumerate(["ground truth\n(analitik)", "voxel 12³\ninit 0", "voxel 12³\ninit −1"]):
        ax[i, 0].set_ylabel(lab, fontsize=8)
    for a in ax.flat:
        a.set_xticks([]); a.set_yticks([])
    fig.suptitle("Scene saya: candi + candi bentar (render 120×96, 96 sampel/sinar)", fontsize=9)
    fig.tight_layout()
    save(fig, "fig_recon_andy.png")


def fig_capture_andy():
    folder = os.path.join(ROOT, "data", "andy_capture")
    if not os.path.isdir(folder):
        return
    with open(os.path.join(folder, "poses.json")) as f:
        frames = json.load(f)["frames"]
    fig, ax = plt.subplots(1, 8, figsize=(8.0, 1.0))
    for a, fr in zip(ax, frames):
        a.imshow(load_ppm(os.path.join(folder, fr["file"])), interpolation="nearest")
        a.set_title(f"{fr['angle_deg']}°", fontsize=7); a.axis("off")
    save(fig, "fig_capture_andy.png")


# ----------------------------------------------------------------- Lab 2 experiments
def fig_diagnose():
    names = [("bug_novel_target.ppm", "ground truth 190°"), ("bug_novel_buggy.ppm", "2 view [0°, 20°]"),
             ("bug_novel_fixed.ppm", "8 view tiap 45°")]
    if not all(os.path.exists(os.path.join(DATA, n)) for n, _ in names):
        print("skip fig_diagnose (run nerf_bug.py first)")
        return
    imgs = [load_ppm(os.path.join(DATA, n)) for n, _ in names]
    fig, ax = plt.subplots(1, 3, figsize=(6.0, 1.9))
    for a, im, (_, lab) in zip(ax, imgs, names):
        a.imshow(im, interpolation="nearest")
        t = lab if im is imgs[0] else f"{lab}\nPSNR {psnr(im, imgs[0]):.2f} dB*"
        a.set_title(t, fontsize=8); a.axis("off")
    save(fig, "fig_diagnose.png")


def fig_experiments():
    path = os.path.join(DATA, "lab2_improve.json")
    if not os.path.exists(path):
        print("skip fig_experiments (run lab2_improve.py first)")
        return
    r = json.load(open(path))
    # init sweep
    fig, ax = plt.subplots(1, 2, figsize=(7.8, 2.7))
    cmap = plt.get_cmap("viridis")
    A = r["A"]
    for k, row in enumerate(A):
        it, m = zip(*row["history"])
        ax[0].semilogy(it, m, color=cmap(k / (len(A) - 1)), lw=1.4,
                       label=f"{row['init']:+.1f}")
    ax[0].set_xlabel("iterasi"); ax[0].set_ylabel("MSE latih (log)")
    ax[0].legend(title="σ_raw awal", fontsize=7, title_fontsize=7, frameon=False, ncol=3,
                 loc="upper right", bbox_to_anchor=(1.0, 1.0))
    ax[0].set_ylim(6e-3, 0.4)
    ax[0].set_title("A. inisialisasi σ_raw (8 view, lr 100)", fontsize=9)
    inits = np.array([row["init"] for row in A])
    ax[1].plot(inits, [row["ring_mean"] for row in A], "o-", color=BLUE, label="PSNR rata-rata 24 view held-out")
    ax[1].plot(inits, [row["ring_min"] for row in A], "s--", color=GREY, ms=4, label="PSNR terburuk (min)")
    xs = np.linspace(-8, 3, 200)
    sig = 1 / (1 + np.exp(-xs))
    T_end = np.exp(-np.logaddexp(0, xs) * 4.0)          # transmittance after the full ray, length far-near = 4
    prod = sig * np.sqrt(T_end)                          # gradient reaching the MIDDLE of the ray
    ax2 = ax[1].twinx()
    ax2.plot(xs, prod / prod.max(), color=ORANGE, lw=1, alpha=0.8)
    ax2.set_ylabel("softplus′·T(tengah), dinormalisasi", color=ORANGE, fontsize=7)
    ax2.tick_params(axis="y", colors=ORANGE, labelsize=7)
    ax2.spines["right"].set_visible(True); ax2.spines["top"].set_visible(False)
    ax[1].set_xlabel("σ_raw awal"); ax[1].set_ylabel("PSNR (dB)")
    ax[1].legend(fontsize=7, frameon=False, loc="upper left")
    ax[1].set_ylim(9, 23)
    ax[1].set_title("hasil setelah 500 iterasi", fontsize=9)
    fig.tight_layout()
    save(fig, "fig_init_sweep.png")

    # coverage, on the ring
    fig = plt.figure(figsize=(7.6, 3.4))
    a = fig.add_axes([0.02, 0.22, 0.42, 0.68], projection="polar")
    sets = [(r["B"][0], "[0, 20]", RED, "-"), (next(x for x in r["B"] if x.get("third") == 180), "[0, 20, 180]", ORANGE, "-"),
            (r["C"][0], "8 view rapat (0–21°)", GREY, "--"), (r["C"][1], "8 view tiap 45°", BLUE, "-")]
    for row, lab, col, ls in sets:
        ang = sorted(float(k) for k in row["ring"])
        val = [row["ring"][str(k) if str(k) in row["ring"] else f"{k}"] for k in ang]
        th = np.radians(ang + [ang[0]])
        a.plot(th, val + [val[0]], color=col, ls=ls, lw=1.4, label=f"{lab}: {row['ring_mean']:.1f} dB")
    a.set_theta_zero_location("E"); a.set_rlim(8, 18); a.set_rticks([10, 14, 18])
    a.tick_params(labelsize=7)
    a.set_title("PSNR held-out per sudut kamera", fontsize=9)
    a.legend(fontsize=7, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=2)
    b = fig.add_axes([0.52, 0.05, 0.46, 0.9])
    b.axis("off")
    rows = [("[0, 20]", r["B"][0])] + [(f"[0, 20, {x['third']}]", x) for x in r["B"][1:]]
    txt = "PSNR (dB)          latih  190°  ring  jauh*\n" + "\n".join(
        f"{lab:17s} {x['train_psnr']:5.1f} {x['novel_psnr']:5.1f} {x['ring_mean']:5.1f} "
        f"{(x['far_mean'] or float('nan')):5.1f}" for lab, x in rows)
    labs = ["8 view rapat 0–21°", "8 view tiap 45°"]
    txt += "\n" + "\n".join(f"{l:17s} {x['train_psnr']:5.1f} {x['novel_psnr']:5.1f} "
                            f"{x['ring_mean']:5.1f}    –" for l, x in zip(labs, r["C"]))
    txt += ("\n\nlatih = rata-rata view latih\n190° = satu view held-out (modul)\n"
            "ring = rata-rata 24 view held-out\n*jauh = view ≥30° dari semua view latih")
    b.text(0.0, 0.5, txt, family="monospace", fontsize=7.2, va="center")
    save(fig, "fig_coverage.png")


# ----------------------------------------------------------------- Lab 3: occlusion
def fig_occlusion():
    path = os.path.join(DATA, "occlusion.json")
    if not os.path.exists(path):
        print("skip fig_occlusion (run ar_app/occlusion_test.py first)")
        return
    rows = json.load(open(path))["rows"]["gapura"]
    th = np.array([r.get("theta_actual", r["theta"]) for r in rows])
    th = np.where(th > 180, th - 360, th)
    order = np.argsort(th)
    fig, ax = plt.subplots(2, 1, figsize=(7.4, 2.8), sharex=True)
    for a, hid in zip(ax, ("celah", "tangga")):
        for k, (key, lab, col) in enumerate((("truth", "kebenaran (Python, ray–box)", GREEN),
                                             ("mv", "model-viewer (uji normal saja)", RED),
                                             ("app", "app saya (+ raycast)", BLUE))):
            y = np.array([r["spots"][hid][key] for r in rows])[order]
            a.scatter(th[order][y], np.full(y.sum(), 2 - k), s=9, color=col, marker="s", label=lab)
        if hid == "celah":
            for lo, hi in ((-39, 0), (180 - 360, 219 - 360)):
                a.axvspan(lo, hi, color=ORANGE, alpha=0.15, lw=0)
            a.text(-38, 2.55, "jendela prediksi saya: [−39°, 0°] ∪ [180°, 219°]", fontsize=7, color=ORANGE)
        a.set_yticks([2, 1, 0], ["truth", "model-viewer", "app saya"], fontsize=7)
        a.set_ylim(-0.6, 2.9)
        a.set_title(f"hotspot '{hid}': sudut kamera di mana ia ditampilkan", fontsize=8, loc="left")
    ax[1].set_xlabel("azimut kamera θ (°; 0 = melihat lurus ke lorong dari +z, 90 = dari +x)")
    ax[1].set_xticks(range(-180, 181, 30))
    save(fig, "fig_occlusion.png")


if __name__ == "__main__":
    fig_pinhole()
    fig_composite()
    fig_activations()
    fig_capture_andy()
    fig_recon_andy()
    fig_diagnose()
    fig_experiments()
    fig_occlusion()
