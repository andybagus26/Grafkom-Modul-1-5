"""
mipmap_demo.py
Lab 2 langkah 4: piramida mip 4 level (box downscale 2x2 di linear light = gamma-correct, Modul 1),
lalu render candi dari JAUH dengan dan tanpa mipmap.

Bukti bahwa kelap-kelip hilang (tiga angka):
  1. Kebenaran (ground truth): frame yang sama dirender 8x lebih besar tanpa mipmap lalu dirata-rata
     8x8 di linear light (supersampling 64 sampel/piksel, praktis bebas alias). PSNR tiap mode ke sini.
  2. Kelap-kelip temporal: kamera bergeser sub-piksel dalam 8 frame; rata-rata |frame_k+1 - frame_k|
     di bagian dalam candi (tepi siluet dibuang supaya yang terukur hanya texture).
  3. Energi frekuensi tinggi: rata-rata |Laplacian| di bagian dalam candi.

    python3 mipmap_demo.py
"""

import os

import numpy as np

import raster3d as R
from colorspace import linear_to_srgb, srgb_to_linear
from metrics import psnr
from ppm_io import write_ppm

W = H = 192
SS = 8                      # faktor supersampling untuk ground truth
LEVELS = 4
FAR_K = 3.0                 # kamera 3x lebih jauh dari scene candi normal


def far_camera(shift=0.0):
    kw = R.scene_kwargs("temple")
    eye, tgt = np.array(kw["eye"]), np.array(kw["target"])
    right = np.cross(tgt - eye, (0, 1, 0))
    right /= np.linalg.norm(right)
    e = tgt + (eye - tgt) * FAR_K + right * shift
    kw.update(eye=tuple(e), target=tuple(tgt + right * shift), far=40.0)
    return kw


def interior_mask(depth):
    """Piksel candi yang keempat tetangganya juga candi (buang siluet)."""
    obj = np.isfinite(depth)
    m = obj.copy()
    m[1:, :] &= obj[:-1, :]; m[:-1, :] &= obj[1:, :]
    m[:, 1:] &= obj[:, :-1]; m[:, :-1] &= obj[:, 1:]
    return m


def lap_energy(img, mask):
    g = img.astype(np.float64).mean(axis=2)
    lap = np.zeros_like(g)
    lap[1:-1, 1:-1] = 4 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]
    return float(np.abs(lap[mask]).mean())


def save_pyramid(tex_u8, path):
    pyr = R.build_mipmap(srgb_to_linear(tex_u8 / 255.0), LEVELS)
    canvas = np.full((pyr[0].shape[0], sum(p.shape[1] for p in pyr) + 8 * (LEVELS - 1), 3), 255, np.uint8)
    x = 0
    for p in pyr:
        canvas[:p.shape[0], x:x + p.shape[1]] = np.clip(linear_to_srgb(p) * 255, 0, 255).astype(np.uint8)
        x += p.shape[1] + 8
    write_ppm(path, canvas)
    return [p.shape[:2] for p in pyr]


def main():
    os.makedirs("out", exist_ok=True)
    mesh, tex = R.load_scene("temple")
    shapes = save_pyramid(tex, "out/mip_pyramid.ppm")
    print(f"piramida mip {LEVELS} level (box 2x2 di linear light): ukuran {shapes}; tulis out/mip_pyramid.ppm")

    kw = far_camera()
    nomip = R.render(mesh, W, H, tex_u8=tex, **kw)
    mip = R.render(mesh, W, H, tex_u8=tex, mip_levels=LEVELS, **kw)
    big = R.render(mesh, W * SS, H * SS, tex_u8=tex, **kw)
    lin = srgb_to_linear(big.color / 255.0).reshape(H, SS, W, SS, 3).mean(axis=(1, 3))
    truth = np.clip(linear_to_srgb(lin) * 255, 0, 255).astype(np.uint8)
    for name, img in (("nomip", nomip.color), ("mip", mip.color), ("truth", truth)):
        write_ppm(f"out/mip_far_{name}.ppm", img)

    m = interior_mask(nomip.depth)
    print(f"\nCandi dari jauh ({W}x{H}, kamera {FAR_K:g}x lebih jauh): {int(m.sum())} piksel bagian dalam")
    print(f"{'mode':>18} | {'PSNR ke truth (dalam)':>22} | {'energi HF |Lap|':>15} | {'kelap-kelip temporal':>20}")
    rows = {}
    for name, levels in (("tanpa mipmap", 0), ("mipmap trilinear", LEVELS)):
        frames = [R.render(mesh, W, H, tex_u8=tex, mip_levels=levels, **far_camera(s)) for s in np.linspace(0, 0.05, 8)]
        fm = m.copy()
        for f in frames:
            fm &= interior_mask(f.depth)
        flick = np.mean([np.abs(frames[k + 1].color.astype(float) - frames[k].color.astype(float)).max(axis=2)[fm].mean()
                         for k in range(len(frames) - 1)])
        img = frames[0].color
        p = psnr(img[m], truth[m])
        hf = lap_energy(img, m)
        rows[name] = (p, hf, flick)
        print(f"{name:>18} | {p:20.2f} dB | {hf:15.2f} | {flick:20.2f}")
        if levels == 0:
            write_ppm("out/mip_flicker_nomip.ppm", np.clip(np.abs(frames[1].color.astype(int) - frames[0].color) * 4, 0, 255).astype(np.uint8))
        else:
            write_ppm("out/mip_flicker_mip.ppm", np.clip(np.abs(frames[1].color.astype(int) - frames[0].color) * 4, 0, 255).astype(np.uint8))
    print(f"{'kebenaran (SS 8x8)':>18} | {'-':>22} | {lap_energy(truth, m):15.2f} | {'-':>20}")
    a, b = rows["tanpa mipmap"], rows["mipmap trilinear"]
    print(f"\nkelap-kelip turun {a[2] / b[2]:.1f}x, energi HF turun {a[1] / b[1]:.1f}x, "
          f"PSNR ke kebenaran naik {b[0] - a[0]:+.1f} dB")

    try:
        from PIL import Image
        names = ["mip_far_nomip", "mip_far_mip", "mip_far_truth", "mip_flicker_nomip", "mip_flicker_mip"]
        box = (W // 4, H // 4, 3 * W // 4, 3 * H // 4)            # crop ke area candi, perbesar 4x
        ims = [Image.open(f"out/{n}.ppm").crop(box).resize((W * 2, H * 2), Image.NEAREST) for n in names]
        panel = Image.new("RGB", (len(ims) * (W * 2 + 10), H * 2), "white")
        for k, im in enumerate(ims):
            panel.paste(im, (k * (W * 2 + 10), 0))
        panel.save("out/lab2_mipmap_panel.png")
        Image.open("out/mip_pyramid.ppm").save("out/lab2_mip_pyramid.png")
        print("tulis out/lab2_mipmap_panel.png (tanpa mip | mip | kebenaran | selisih frame tanpa mip x4 | selisih frame mip x4)")
    except ImportError:
        pass


if __name__ == "__main__":
    main()
