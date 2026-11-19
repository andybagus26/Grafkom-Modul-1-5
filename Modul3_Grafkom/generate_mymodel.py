#!/usr/bin/env python3
"""
generate_mymodel.py
Script generator model 3D kustom untuk Andy Bagus (Praktikum Grafkom Modul 3).
Membangun model pilar/monumen parametrik bertingkat dengan format Wavefront OBJ
dan koordinat tekstur UV lengkap. Winding segitiga diatur Counter-Clockwise (CCW).
"""

import math

def generate_pillar_obj(filename="mymodel.obj", segments=24):
    """
    Menghasilkan model 3D pilar parametrik.
    segments: jumlah sudut melingkar (24 segmen x 8 tingkat cincin menghasilkan > 350 segitiga).
    """
    # Profil ketinggian (y) dan radius (r) pilar dari bawah ke atas
    profile = [
        (-1.2, 0.8),   # Dasar bawah (lebar)
        (-1.0, 0.8),   # Undakan dasar
        (-0.9, 0.5),   # Transisi ke badan pilar
        (-0.5, 0.45),  # Badan bawah
        ( 0.0, 0.4),   # Pinggang pilar (agak ramping)
        ( 0.5, 0.45),  # Badan atas
        ( 0.9, 0.5),   # Transisi ke kepala pilar
        ( 1.0, 0.8),   # Undakan kepala
        ( 1.2, 0.8),   # Puncak pilar (lebar)
    ]

    vertices = []
    uvs = []
    faces = []

    # 1. Generate vertex dan UV untuk setiap cincin melingkar
    # Kita buat duplikasi titik awal (u=0 dan u=1) pada sambungan UV agar tekstur tidak tertarik
    num_rings = len(profile)
    y_min = profile[0][0]
    y_max = profile[-1][0]

    for ring_idx, (y, r) in enumerate(profile):
        v_coord = (y - y_min) / (y_max - y_min)
        for seg in range(segments + 1):  # +1 untuk menutup jahitan UV (0.0 s/d 1.0)
            theta = (2.0 * math.pi * seg) / segments
            x = r * math.cos(theta)
            z = r * math.sin(theta)

            vertices.append((x, y, z))
            u_coord = seg / segments
            uvs.append((u_coord, v_coord))

    # Indexing vertex dalam grid (ring_idx, seg)
    def v_idx(ring, seg):
        # Index OBJ berbasis 1
        return ring * (segments + 1) + seg + 1

    # 2. Rajut sisi silinder (quad dibagi jadi 2 segitiga CCW)
    for ring in range(num_rings - 1):
        for seg in range(segments):
            # 4 titik pada satu quad:
            # D (atas kiri)    --- C (atas kanan)
            # |                    |
            # A (bawah kiri)  --- B (bawah kanan)
            a = v_idx(ring, seg)
            b = v_idx(ring, seg + 1)
            c = v_idx(ring + 1, seg + 1)
            d = v_idx(ring + 1, seg)

            # Winding CCW (dilihat dari luar):
            # theta naik dari +x ke +z (x = r cos, z = r sin). Dilihat dari LUAR pilar,
            # arah seg+1 itu ke KIRI, bukan ke kanan. Jadi A -> B -> C justru CW dari luar
            # (normal (B-A) x (C-A) menunjuk ke dalam). Versi lama memakai A->B->C dan
            # semua 384 segitiga sisi menghadap ke dalam (inside-out, ter-cull).
            # Urutan yang benar (CCW dari luar, normal keluar):
            # Segitiga 1: A -> C -> B
            # Segitiga 2: A -> D -> C
            faces.append(((a, a), (c, c), (b, b)))
            faces.append(((a, a), (d, d), (c, c)))

    # 3. Tutup Bawah (Bottom Cap pada ring 0, y = y_min)
    # Tambahkan titik pusat bawah
    center_bottom_v = len(vertices) + 1
    vertices.append((0.0, y_min, 0.0))
    center_bottom_uv = len(uvs) + 1
    uvs.append((0.5, 0.5))

    for seg in range(segments):
        p1 = v_idx(0, seg)
        p2 = v_idx(0, seg + 1)
        # Menghadap ke bawah: arah normal -y
        # CCW dari bawah: center -> p1 -> p2
        faces.append(((center_bottom_v, center_bottom_uv), (p1, p1), (p2, p2)))

    # 4. Tutup Atas (Top Cap pada ring terakhir, y = y_max)
    center_top_v = len(vertices) + 1
    vertices.append((0.0, y_max, 0.0))
    center_top_uv = len(uvs) + 1
    uvs.append((0.5, 0.5))

    top_ring = num_rings - 1
    for seg in range(segments):
        p1 = v_idx(top_ring, seg)
        p2 = v_idx(top_ring, seg + 1)
        # Menghadap ke atas: arah normal +y
        # CCW dari atas: center -> p2 -> p1
        faces.append(((center_top_v, center_top_uv), (p2, p2), (p1, p1)))

    # 5. Tulis file OBJ
    with open(filename, "w") as f:
        f.write("# Model 3D Pilar Parametrik (Andy Bagus - Modul 3)\n")
        f.write(f"# Segitiga: {len(faces)}\n\n")

        for vx, vy, vz in vertices:
            f.write(f"v {vx:.6f} {vy:.6f} {vz:.6f}\n")

        f.write("\n")
        for u, v in uvs:
            f.write(f"vt {u:.6f} {v:.6f}\n")

        f.write("\n")
        for (v1, vt1), (v2, vt2), (v3, vt3) in faces:
            f.write(f"f {v1}/{vt1} {v2}/{vt2} {v3}/{vt3}\n")

    print(f"Model berhasil digenerate ke '{filename}'!")
    print(f"- Jumlah vertex: {len(vertices)}")
    print(f"- Jumlah UV: {len(uvs)}")
    print(f"- Jumlah segitiga: {len(faces)}")
    return len(faces)

if __name__ == "__main__":
    generate_pillar_obj()
