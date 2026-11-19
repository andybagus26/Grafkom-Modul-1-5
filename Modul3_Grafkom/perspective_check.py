"""
perspective_check.py
Lab 2 langkah 3: reproduksi Contoh E4 dan tunjukkan texture "berenang" pada interpolasi UV naif.

1. Angka E4: tepi horizontal dari L (x=0, u=0, w=1) ke R (x=100, u=1, w=9); u di x=50.
2. Render lantai berpapan catur yang menjauh: naif (u linear di layar) vs perspective-correct (u/w, 1/w).
3. "Berenang": kamera maju sedikit demi sedikit. Untuk satu titik WORLD tetap di lantai, UV yang
   seharusnya konstan dibandingkan dengan UV yang benar-benar dipakai renderer di piksel titik itu.

    python3 perspective_check.py
"""

import os

import numpy as np

import raster3d as R
import transforms as T
from objio import Mesh
from ppm_io import write_ppm


def e4_numbers():
    xL, uL, wL = 0.0, 0.0, 1.0
    xR, uR, wR = 100.0, 1.0, 9.0
    t = (50.0 - xL) / (xR - xL)                 # bobot linear di layar (barycentric 1D)
    naive = (1 - t) * uL + t * uR
    u_over_w = (1 - t) * uL / wL + t * uR / wR
    one_over_w = (1 - t) / wL + t / wR
    correct = u_over_w / one_over_w
    print("E4: L(x=0,u=0,w=1) -> R(x=100,u=1,w=9), titik tengah layar x=50")
    print(f"  (a) naif: u = {naive:.4f}")
    print(f"  (b) u/w di tengah = {u_over_w:.6f} (=1/18), 1/w di tengah = {one_over_w:.6f} (=5/9), "
          f"u = {correct:.4f}")
    return naive, correct


def checker(n=256, squares=8):
    y, x = np.mgrid[0:n, 0:n] // (n // squares)
    c = np.where((x + y) % 2 == 0, 235, 40).astype(np.uint8)
    img = np.stack([c, c, c], -1)
    img[..., 0] = np.where((x + y) % 2 == 0, 235, 170)       # kotak gelap kemerahan supaya mudah dilihat
    img[..., 1] = np.where((x + y) % 2 == 0, 235, 40)
    return img


# lantai 4 x 11 di y=0, dari z=-1 ke z=-12; UV 0..1 (tekstur 8x8 kotak)
FLOOR = Mesh(np.array([[-2.0, 0.0, -1.0], [2.0, 0.0, -1.0], [2.0, 0.0, -12.0], [-2.0, 0.0, -12.0]]),
             np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]),
             np.array([[0, 1, 2], [0, 2, 3]]), np.array([[0, 1, 2], [0, 2, 3]]))
W = H = 512


def cam(dz):
    return dict(model=np.eye(4), eye=(0.0, 1.0, 0.0 - dz), target=(0.0, 0.3, -6.0 - dz), fovy_deg=60.0,
                near=0.1, far=50.0, light_dir=(0.0, 1.0, 0.0), ambient=1.0)


def true_uv(p):
    """UV sebenarnya dari titik world di lantai (pemetaan linear di WORLD, sesuai vertex)."""
    return np.array([(p[0] + 2.0) / 4.0, (-1.0 - p[2]) / 11.0])


def main():
    os.makedirs("out", exist_ok=True)
    naive, correct = e4_numbers()

    tex = checker()
    imgs = {}
    for pc in (False, True):
        r = R.render(FLOOR, W, H, tex_u8=tex, perspective_correct=pc, keep_uv=True, **cam(0.0))
        name = "correct" if pc else "naive"
        write_ppm(f"out/e4_floor_{name}.ppm", r.color)
        imgs[name] = r
    d = np.abs(imgs["naive"].color.astype(int) - imgs["correct"].color.astype(int)).max(axis=2)
    print(f"\nRender lantai {W}x{H}: piksel yang berbeda naif vs benar = {int((d > 0).sum())} "
          f"dari {int(np.isfinite(imgs['correct'].depth).sum())} piksel lantai")
    write_ppm("out/e4_floor_diff.ppm", np.repeat(np.clip(d * 2, 0, 255).astype(np.uint8)[..., None], 3, 2))

    # Berenang: titik world tetap di lantai, kamera maju 0.0 .. 1.0
    print("\nBerenang: titik world tetap P=(0.6, 0, -5.0); UV benar =", true_uv([0.6, 0, -5.0]).round(4))
    print(f"{'kamera maju':>12} {'piksel':>12} | {'UV naif':>18} {'galat naif':>11} | {'UV benar':>18} {'galat benar':>11}")
    P = np.array([0.6, 0.0, -5.0])
    errs = {False: [], True: []}
    for dz in np.linspace(0.0, 1.0, 5):
        c = cam(dz)
        Pm = T.perspective_deg(c["fovy_deg"], 1.0, c["near"], c["far"])
        Vm = T.look_at(c["eye"], c["target"], (0, 1, 0))
        _, ndc = T.project(Pm, Vm, np.eye(4), [P])
        sx, sy, _ = T.viewport_points(ndc, W, H)[0]
        px, py = int(sx), int(sy)
        # titik pusat piksel tidak tepat di P; hitung UV benar DI pusat piksel itu (balik proyeksi ke lantai)
        Vinv = np.linalg.inv(Vm)
        ray_ndc = np.array([(px + 0.5) / W * 2 - 1, 1 - (py + 0.5) / H * 2])
        th = np.tan(np.radians(c["fovy_deg"]) / 2)
        d_view = np.array([ray_ndc[0] * th, ray_ndc[1] * th, -1.0, 0.0])
        d_world = (Vinv @ d_view)[:3]
        eye = np.asarray(c["eye"])
        hit = eye + d_world * (-eye[1] / d_world[1])
        uv_true = true_uv(hit)
        row = [f"{dz:12.2f} {f'({px},{py})':>12} |"]
        for pc in (False, True):
            r = R.render(FLOOR, W, H, tex_u8=None, perspective_correct=pc, keep_uv=True, **c)
            uv = r.uv[py, px]
            err = float(np.linalg.norm(uv - uv_true))
            errs[pc].append(err)
            row.append(f" {np.array2string(uv, precision=4):>18} {err:11.5f} |")
        print("".join(row))
    print(f"galat UV maks: naif {max(errs[False]):.4f} (= {max(errs[False]) * 8:.2f} kotak catur), "
          f"benar {max(errs[True]):.2e}")
    print("Kesimpulan: dengan interpolasi naif UV di titik world yang sama BERUBAH saat kamera bergerak "
          "(texture berenang); dengan u/w dan 1/w UV-nya tetap (galat ~0).")

    try:
        from PIL import Image
        a = Image.open("out/e4_floor_naive.ppm"); b = Image.open("out/e4_floor_correct.ppm")
        c = Image.open("out/e4_floor_diff.ppm")
        panel = Image.new("RGB", (3 * W + 40, H), "white")
        for k, im in enumerate((a, b, c)):
            panel.paste(im, (k * (W + 20), 0))
        panel.save("out/lab2_e4_panel.png")
        print("tulis out/lab2_e4_panel.png (kiri naif, tengah perspective-correct, kanan selisih)")
    except ImportError:
        pass


if __name__ == "__main__":
    main()
