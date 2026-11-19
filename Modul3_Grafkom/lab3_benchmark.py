"""
lab3_benchmark.py
Lab 3 langkah 3: ukur frame time dan kualitas hard shadow, raster3d.py (shadow map) vs raytrace.py
(shadow ray), lalu bandingkan dengan prediksi tertulis di docs/Lab3_prediksi.md.

Scene: mymodel.obj + lantai (y = -1.2), kamera/light scene "mymodel", 512x512.
Waktu = median dari beberapa run (time.perf_counter), di mesin yang sama.

    python3 lab3_benchmark.py
"""

import json
import os
import statistics
import time

import numpy as np

import raster3d as R
import raytrace as RT
from metrics import fmt_psnr, psnr, ssim_global
from ppm_io import write_ppm

W = H = 512


def timed(fn, runs):
    ts, out = [], None
    for _ in range(runs):
        t0 = time.perf_counter()
        out = fn()
        ts.append(time.perf_counter() - t0)
    return statistics.median(ts), out


def main():
    os.makedirs("out", exist_ok=True)
    mesh, tex = R.load_scene("mymodel")
    kw = R.scene_kwargs("mymodel")
    scene, k = R.add_ground(mesh, -1.2, 3.0)
    print(f"scene: mymodel.obj + lantai = {scene.n_tris} segitiga, {W}x{H}")

    rows = []
    t_r, r0 = timed(lambda: R.render(scene, W, H, tex_u8=tex, flat_from=k, **kw), 5)
    rows.append(("raster3d.py tanpa shadow", t_r))
    t_rs, rs = timed(lambda: R.render(scene, W, H, tex_u8=tex, flat_from=k, shadow_res=1024, **kw), 5)
    rows.append(("raster3d.py + shadow map 1024", t_rs))
    t_t, (t0img, _) = timed(lambda: RT.render(scene, W, H, tex_u8=tex, flat_from=k, **kw), 3)
    rows.append(("raytrace.py tanpa shadow", t_t))
    t_ts, (tsimg, _) = timed(lambda: RT.render(scene, W, H, tex_u8=tex, flat_from=k, shadows=True, **kw), 3)
    rows.append(("raytrace.py + shadow ray", t_ts))

    three = None
    if os.path.exists("logs/lab3_three_bench.json"):
        with open("logs/lab3_three_bench.json") as f:
            three = json.load(f)

    print("\n== Frame time (median) ==")
    for name, t in rows:
        print(f"  {name:32s} {t * 1000:9.1f} ms")
    if three:
        print(f"  {'Three.js r128 (GPU, tanpa shadow)':32s} {three['median_ms']:9.2f} ms   [{three['gpu']}]")
    print(f"  rasio raytrace/raster tanpa shadow  : {t_t / t_r:.1f}x")
    print(f"  rasio raytrace/raster dengan shadow : {t_ts / t_rs:.1f}x")
    print(f"  biaya shadow: raster x{t_rs / t_r:.2f}, raytrace x{t_ts / t_t:.2f}")
    if three:
        print(f"  raster NumPy / Three.js GPU         : {t_r * 1000 / three['median_ms']:.0f}x")

    # Kualitas: tanpa shadow kedua renderer harus sama; dengan shadow, selisihnya = kesalahan shadow map
    print("\n== Kualitas (raytrace + shadow ray dianggap kebenaran) ==")
    print(f"  tanpa shadow  raster vs raytrace: PSNR {fmt_psnr(psnr(r0.color, t0img))} dB")
    write_ppm("out/lab3_raster_shadow.ppm", rs.color)
    write_ppm("out/lab3_rt_shadow.ppm", tsimg)
    print(f"{'':2s}{'shadow map':>12} {'bias':>6} | {'PSNR':>8} {'SSIM':>7} {'piksel beda':>12} {'raster terlalu gelap':>21} {'raster terlalu terang':>22}")
    best = None
    for res in (512, 1024, 2048):
        for bias in (0.0, 0.5, 1.5, 4.0):
            img = R.render(scene, W, H, tex_u8=tex, flat_from=k, shadow_res=res, shadow_bias_texels=bias, **kw).color
            a, b = img.astype(int).sum(2), tsimg.astype(int).sum(2)
            darker = int((a < b - 30).sum())      # raster bilang bayangan, raytrace bilang terang -> acne / tepi
            lighter = int((a > b + 30).sum())     # raster bilang terang, raytrace bilang bayangan -> bocor / tepi
            p = psnr(img, tsimg)
            print(f"  {res:12d} {bias:6.1f} | {fmt_psnr(p):>8} {ssim_global(img, tsimg):7.4f} "
                  f"{int((np.abs(img.astype(int) - tsimg).max(2) > 0).sum()):12d} {darker:21d} {lighter:22d}")
            if res == 1024 and bias == 0.0:
                write_ppm("out/lab3_raster_shadow_bias0.ppm", img)
    diff = np.clip(np.abs(rs.color.astype(int) - tsimg) * 4, 0, 255).astype(np.uint8)
    write_ppm("out/lab3_shadow_diff.ppm", diff)

    try:
        from PIL import Image
        names = ["lab3_raster_shadow_bias0", "lab3_raster_shadow", "lab3_rt_shadow", "lab3_shadow_diff"]
        ims = [Image.open(f"out/{n}.ppm") for n in names]
        panel = Image.new("RGB", (4 * W + 60, H), "white")
        for i, im in enumerate(ims):
            panel.paste(im, (i * (W + 20), 0))
        panel.save("out/lab3_shadow_panel.png")
        crop = (60, 60, 316, 316)          # zoom tepi bayangan kepala pilar
        z = [Image.open(f"out/{n}.ppm").crop((130, 80, 258, 208)).resize((384, 384), Image.NEAREST) for n in names[:3]]
        zp = Image.new("RGB", (3 * 384 + 40, 384), "white")
        for i, im in enumerate(z):
            zp.paste(im, (i * 404, 0))
        zp.save("out/lab3_shadow_zoom.png")
        print("\ntulis out/lab3_shadow_panel.png (bias 0 | bias 1.5 | raytrace | selisih x4) dan out/lab3_shadow_zoom.png")
    except ImportError:
        pass


if __name__ == "__main__":
    main()
