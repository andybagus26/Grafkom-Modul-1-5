#!/usr/bin/env python3
"""
validate_obj.py
Validator untuk model 3D OBJ kustom (Lab 1, langkah 2).
Memeriksa:
- Jumlah vertex dan UV
- Jumlah face segitiga (harus >= 200)
- Keberadaan koordinat tekstur (vt) di setiap face
- Format face (harus triangulated: 3 vertex per face)
- Bounding box dimensi model
- KONSISTENSI WINDING (baru):
    a) Pasangan edge: pada mesh tertutup yang winding-nya konsisten, setiap edge
       berarah (i -> j) muncul tepat satu kali, dan pasangannya (j -> i) dimiliki
       segitiga tetangga. Kalau (i -> j) muncul dua kali, dua segitiga yang
       bertetangga punya winding berlawanan.
    b) Arah keluar: signed volume = sum(a . (b x c)) / 6. Positif berarti normal
       (CCW) menunjuk keluar. Negatif berarti seluruh model inside-out.
  Vertex dengan posisi sama di-"weld" dulu, karena jahitan UV menduplikasi vertex.
"""

import sys
import os
from collections import Counter

import numpy as np


def check_winding(positions, faces):
    """Mengembalikan (jumlah edge berarah ganda, jumlah edge tanpa pasangan, signed volume)."""
    weld = {}
    remap = [weld.setdefault(tuple(round(c, 5) + 0.0 for c in p), len(weld)) for p in positions]

    edges = Counter()
    for f in faces:
        g = [remap[i] for i in f]
        for k in range(3):
            edges[(g[k], g[(k + 1) % 3])] += 1

    duplicated = sum(1 for c in edges.values() if c > 1)
    unpaired = sum(1 for (i, j) in edges if (j, i) not in edges)

    P = np.asarray(positions, dtype=np.float64)
    F = np.asarray(faces, dtype=np.int64)
    a, b, c = P[F[:, 0]], P[F[:, 1]], P[F[:, 2]]
    signed_volume = float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)
    return duplicated, unpaired, signed_volume


def validate_obj(filepath="mymodel.obj"):
    if not os.path.exists(filepath):
        print(f"Error: File '{filepath}' tidak ditemukan.")
        return False

    positions = []
    faces = []
    num_uvs = 0
    num_normals = 0
    non_triangles = 0
    missing_uv_faces = 0

    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            tag = parts[0]

            if tag == "v":
                positions.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif tag == "vt":
                num_uvs += 1
            elif tag == "vn":
                num_normals += 1
            elif tag == "f":
                face_vertices = parts[1:]
                if len(face_vertices) != 3:
                    non_triangles += 1
                    continue
                faces.append([int(fv.split("/")[0]) - 1 for fv in face_vertices])

                # Periksa apakah face menyertakan vt (format v/vt atau v/vt/vn)
                for fv in face_vertices:
                    tokens = fv.split("/")
                    if len(tokens) < 2 or not tokens[1]:
                        missing_uv_faces += 1
                        break

    num_triangles = len(faces)
    P = np.asarray(positions)

    print("=" * 60)
    print(f"HASIL VALIDASI OBJ: {filepath}")
    print("=" * 60)
    print(f"- Jumlah Vertices (v) : {len(positions)}")
    print(f"- Jumlah UVs (vt)     : {num_uvs}")
    print(f"- Jumlah Normal (vn)  : {num_normals}")
    print(f"- Jumlah Segitiga (f) : {num_triangles} {'[OK]' if num_triangles >= 200 else '[ERROR: < 200]'}")
    print(f"- Face non-segitiga   : {non_triangles} {'[OK]' if non_triangles == 0 else '[ERROR: Harus triangulated!]'}")
    print(f"- Face tanpa UV       : {missing_uv_faces} {'[OK]' if missing_uv_faces == 0 else '[ERROR: Ada face tanpa UV]'}")

    if len(P):
        for name, k in (("X", 0), ("Y", 1), ("Z", 2)):
            lo, hi = P[:, k].min(), P[:, k].max()
            print(f"- Bounding Box {name}      : [{lo:.3f}, {hi:.3f}] (rentang: {hi - lo:.3f})")

    duplicated, unpaired, signed_volume = check_winding(positions, faces)
    print("- Winding:")
    print(f"    edge berarah ganda    : {duplicated} {'[OK]' if duplicated == 0 else '[ERROR: winding tidak konsisten]'}")
    print(f"    edge tanpa pasangan   : {unpaired} {'[OK, mesh tertutup]' if unpaired == 0 else '[INFO: mesh punya tepi terbuka]'}")
    print(f"    signed volume         : {signed_volume:.4f} {'[OK, normal CCW menunjuk keluar]' if signed_volume > 0 else '[ERROR: inside-out]'}")

    print("-" * 60)
    ok = (
        num_triangles >= 200
        and non_triangles == 0
        and num_uvs > 0
        and missing_uv_faces == 0
        and duplicated == 0
        and signed_volume > 0
    )
    if ok:
        print("STATUS: VALID. Memenuhi syarat Lab 1 (>= 200 segitiga, UV lengkap, triangulated, winding CCW konsisten).")
    else:
        print("STATUS: BELUM VALID. Periksa catatan di atas.")
    return ok


if __name__ == "__main__":
    filepath = sys.argv[1] if len(sys.argv) > 1 else "mymodel.obj"
    sys.exit(0 if validate_obj(filepath) else 1)
