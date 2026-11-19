#!/usr/bin/env python3
"""
generate_texture.py
Membuat gambar tekstur prosedural PPM (P6 binary, 512x512) bermotif batu pilar kuno / brick.
Dibuat murni dengan pustaka standar Python (tanpa dependensi eksternal).
Lisensi: CC0 (Dibuat sendiri oleh Andy Bagus untuk Praktikum Grafkom Modul 3).
"""

import math

def generate_stone_texture(filename="texture.ppm", width=512, height=512):
    header = f"P6\n{width} {height}\n255\n".encode("ascii")
    pixel_bytes = bytearray(width * height * 3)

    brick_w = 64
    brick_h = 32
    mortar = 3

    idx = 0
    for y in range(height):
        # Selang-seling baris batu (staggered bricks)
        row = y // brick_h
        x_offset = (brick_w // 2) if (row % 2 == 1) else 0
        in_horizontal_mortar = (y % brick_h) < mortar

        for x in range(width):
            adjusted_x = (x + x_offset) % width
            in_vertical_mortar = (adjusted_x % brick_w) < mortar

            # Pola noise sederhana deterministik
            noise = (math.sin(x * 0.15) * math.cos(y * 0.15) * 15.0) + \
                    (math.sin(x * 0.05 + y * 0.03) * 20.0)

            if in_horizontal_mortar or in_vertical_mortar:
                # Warna semen / sela antar batu (abu-abu gelap)
                r = int(max(0, min(255, 65 + noise * 0.3)))
                g = int(max(0, min(255, 65 + noise * 0.3)))
                b = int(max(0, min(255, 70 + noise * 0.3)))
            else:
                # Warna batu pilar kuno (krem / marmer batu hangat)
                base_r = 195 + noise
                base_g = 180 + noise * 0.9
                base_b = 155 + noise * 0.8
                r = int(max(0, min(255, base_r)))
                g = int(max(0, min(255, base_g)))
                b = int(max(0, min(255, base_b)))

            pixel_bytes[idx] = r
            pixel_bytes[idx + 1] = g
            pixel_bytes[idx + 2] = b
            idx += 3

    with open(filename, "wb") as f:
        f.write(header)
        f.write(pixel_bytes)

    print(f"Tekstur berhasil dibuat ke '{filename}' (Ukuran: {width}x{height}, Format: PPM P6)")

if __name__ == "__main__":
    generate_stone_texture()
