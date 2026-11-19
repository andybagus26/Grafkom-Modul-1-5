"""
ppm_io.py
Baca/tulis citra Netpbm biner (P5 grayscale, P6 RGB, maxval 255) tanpa library citra.
Infrastruktur (bukan inti penilaian).
"""

import numpy as np


def _tokens(data):
    """Generator token header Netpbm; melewati komentar '#'. Mengembalikan (token, offset_setelahnya)."""
    i, n = 0, len(data)
    while i < n:
        c = data[i:i + 1]
        if c == b"#":
            while i < n and data[i:i + 1] not in (b"\n", b"\r"):
                i += 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < n and not data[j:j + 1].isspace() and data[j:j + 1] != b"#":
                j += 1
            yield data[i:j], j
            i = j


def read_ppm(path):
    """Mengembalikan array uint8 (H, W, 3) untuk P6 atau (H, W) untuk P5."""
    with open(path, "rb") as f:
        data = f.read()
    tok = _tokens(data)
    magic, _ = next(tok)
    w, _ = next(tok)
    h, _ = next(tok)
    maxval, end = next(tok)
    if magic not in (b"P5", b"P6") or int(maxval) != 255:
        raise ValueError(f"{path}: hanya P5/P6 maxval 255 yang didukung ({magic!r}, {maxval!r})")
    w, h = int(w), int(h)
    ch = 3 if magic == b"P6" else 1
    pix = np.frombuffer(data, dtype=np.uint8, count=w * h * ch, offset=end + 1)
    return pix.reshape((h, w, 3) if ch == 3 else (h, w)).copy()


def write_ppm(path, img):
    """Menulis uint8 (H, W, 3) sebagai P6 atau (H, W) sebagai P5."""
    img = np.ascontiguousarray(img, dtype=np.uint8)
    magic = b"P6" if img.ndim == 3 else b"P5"
    with open(path, "wb") as f:
        f.write(magic + f"\n{img.shape[1]} {img.shape[0]}\n255\n".encode("ascii"))
        f.write(img.tobytes())
