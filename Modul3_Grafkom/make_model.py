#!/usr/bin/env python3
"""
make_model.py
Satu perintah untuk menghasilkan semua aset turunan secara deterministik (tidak ada aset biner yang
perlu di-commit untuk model sendiri):
    mymodel.obj        <- generate_mymodel.py (pilar 432 segitiga, UV, winding CCW)
    texture.ppm        <- generate_texture.py (512x512, CC0, karya sendiri)
    web/mymodel.obj    salinan untuk viewer Three.js (GitHub Pages hanya menyajikan folder web/)
    web/texture.png    texture.ppm dikonversi ke PNG (browser tidak bisa memuat PPM)

    python3 make_model.py
"""

import os
import shutil
import struct
import zlib

import generate_mymodel
import generate_texture
from ppm_io import read_ppm


def write_png(path, rgb):
    """PNG RGB 8-bit tanpa library (zlib + struct): signature, IHDR, IDAT, IEND."""
    h, w, _ = rgb.shape
    raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(h))   # filter 0 per baris

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)))
        f.write(chunk(b"IDAT", zlib.compress(raw, 9)))
        f.write(chunk(b"IEND", b""))


def main():
    generate_mymodel.generate_pillar_obj("mymodel.obj")
    generate_texture.generate_stone_texture("texture.ppm")
    os.makedirs("web", exist_ok=True)
    shutil.copyfile("mymodel.obj", "web/mymodel.obj")
    write_png("web/texture.png", read_ppm("texture.ppm"))
    print("tulis web/mymodel.obj dan web/texture.png (untuk viewer Three.js)")


if __name__ == "__main__":
    main()
