#!/usr/bin/env python3
"""
run_all_labs.py
Menjalankan ulang seluruh Lab 1, Lab 2, dan Lab 3 dari awal dan menyimpan output mentahnya ke logs/.
    python3 run_all_labs.py
"""

import os
import subprocess
import sys
import time

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

STEPS = [
    ("Generate aset (model, texture, web/)", "make_model.py", None),
    ("Lab 1: validasi OBJ", "validate_obj.py", "logs/lab1_validate_obj_latest.txt"),
    ("Lab 1: telusuran vertex", "worked_example.py", "logs/lab1_worked_example.txt"),
    ("Lab 2: raster candi", "raster3d.py --scene temple", None),
    ("Lab 2: raytrace candi", "raytrace.py --scene temple", None),
    ("Lab 2: raster model sendiri", "raster3d.py --scene mymodel", None),
    ("Lab 2: raytrace model sendiri", "raytrace.py --scene mymodel", None),
    ("Lab 2: bandingkan candi raster vs raytrace", "compare.py out/temple_raster.ppm out/temple_rt.ppm --diff out/temple_diff_raster_rt.ppm", None),
    ("Lab 2: bandingkan candi vs referensi", "compare.py out/temple_raster.ppm ref/temple_ref_512.ppm", None),
    ("Lab 2: tiga bug", "broken_scene.py --all", "logs/lab2_broken_scene.txt"),
    ("Lab 2: E4 perspective-correct", "perspective_check.py", "logs/lab2_e4_perspective.txt"),
    ("Lab 2: mipmap", "mipmap_demo.py", "logs/lab2_mipmap.txt"),
    ("Lab 2: back-face culling", "culling_check.py", "logs/lab2_culling.txt"),
    ("Lab 3: frame Three.js (Chrome headless)", "tools/three_export.py", None),
    ("Lab 3: bandingkan raster vs Three.js", "compare.py out/mymodel_raster.ppm web/mymodel_three.ppm --diff out/mymodel_diff_raster_three.ppm", None),
    ("Lab 3: frame time + hard shadow", "lab3_benchmark.py", "logs/lab3_benchmark.txt"),
    ("Tes otomatis", "tests.py", "logs/lab2_tests.txt"),
]


def main():
    failed = []
    for title, cmd, log in STEPS:
        t0 = time.perf_counter()
        if cmd.startswith("tools/three_export.py") and not os.path.exists(CHROME):
            print(f"[LEWATI] {title}  (Google Chrome tidak ditemukan)")
            continue
        r = subprocess.run([sys.executable] + cmd.split(), capture_output=True, text=True)
        dt = time.perf_counter() - t0
        status = "OK" if r.returncode == 0 else f"GAGAL (exit {r.returncode})"
        print(f"[{status}] {title}  ({dt:.1f} s)")
        if log:
            with open(log, "w") as f:
                f.write(r.stdout)
        if r.returncode != 0:
            failed.append(title)
            print(r.stdout[-2000:], r.stderr[-2000:])
    print("-" * 60)
    print("SEMUA LANGKAH OK" if not failed else f"GAGAL: {failed}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
