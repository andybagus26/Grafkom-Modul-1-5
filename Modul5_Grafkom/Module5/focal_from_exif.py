"""Lab 1 item 4 -- my phone's focal length in PIXELS, from a photo's EXIF,
then the pinhole ray through a pixel of my choosing (by hand in the report,
confirmed here with ray_generator.pixel_to_camera_dir).

    python focal_from_exif.py PHOTO.jpg [u v]
    python focal_from_exif.py --f35 26 --size 4032x3024 [u v]   (no photo at hand)

How f_px is estimated. Phones write FocalLengthIn35mmFilm (EXIF 0xA405): the
lens focal length that gives the SAME FIELD OF VIEW on a 36 x 24 mm frame. The
usual convention (and what phone makers use) matches the DIAGONAL field of
view, and the 36 x 24 frame's diagonal is sqrt(36^2 + 24^2) = 43.27 mm, so

    f_px = f35 * diag_px / 43.27            (diag_px = sqrt(W^2 + H^2))

The common shortcut f_px = f35 * W / 36 matches the WIDTH instead; it is exact
only for a 3:2 image and is ~4 % low for a phone's 4:3 photo. Both are printed.
If the photo has the real focal length (0x920A, mm) but no sensor size, it
cannot be converted alone -- that is why the 35 mm-equivalent tag is used.

This is still the pinhole model: a phone lens also has radial distortion
(k1, k2 ...) that this ignores -- see the report, Lab 1 item 3 (nerfstudio's
OPENCV camera model) for why a real pipeline must estimate it.
"""
from __future__ import annotations

import argparse
import math

import numpy as np

from ray_generator import pixel_to_camera_dir

DIAG_35 = math.hypot(36.0, 24.0)   # 43.267 mm


def read_exif(path):
    from PIL import Image
    with Image.open(path) as im:
        w, h = im.size
        exif = im.getexif()
        sub = exif.get_ifd(0x8769)          # Exif sub-IFD holds the lens tags
        f35 = sub.get(0xA405) or exif.get(0xA405)
        f_mm = sub.get(0x920A) or exif.get(0x920A)
        model = exif.get(0x0110)            # camera model
        orient = exif.get(0x0112, 1)
    if orient in (6, 8):                    # stored landscape, shown portrait
        w, h = h, w
    return dict(width=w, height=h, f35=float(f35) if f35 else None,
                f_mm=float(f_mm) if f_mm else None, model=model)


def focal_px(f35, w, h):
    return f35 * math.hypot(w, h) / DIAG_35, f35 * max(w, h) / 36.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("photo", nargs="?")
    ap.add_argument("u", nargs="?", type=float)
    ap.add_argument("v", nargs="?", type=float)
    ap.add_argument("--f35", type=float, help="35 mm-equivalent focal length if there is no photo")
    ap.add_argument("--size", help="WxH in pixels if there is no photo, e.g. 4032x3024")
    a = ap.parse_args()
    if a.photo and a.photo.lower().endswith((".jpg", ".jpeg", ".heic", ".png", ".tif", ".tiff")):
        info = read_exif(a.photo)
        print(f"photo: {a.photo}  model: {info['model']}  size: {info['width']}x{info['height']}  "
              f"focal: {info['f_mm']} mm  35mm-equiv: {info['f35']} mm")
        if info["f35"] is None:
            raise SystemExit("no FocalLengthIn35mmFilm tag in this photo -- pass --f35 and --size instead")
        f35, w, h = info["f35"], info["width"], info["height"]
    else:
        if a.photo is not None:                 # "python focal_from_exif.py --f35 26 --size .. u v"
            a.u, a.v = float(a.photo), a.u
        if a.f35 is None or a.size is None:
            raise SystemExit("give a photo, or --f35 and --size")
        f35 = a.f35
        w, h = (int(x) for x in a.size.lower().split("x"))
    f_diag, f_width = focal_px(f35, w, h)
    cx, cy = w / 2.0, h / 2.0
    u = a.u if a.u is not None else w * 0.75
    v = a.v if a.v is not None else h * 0.25
    print(f"f_px (diagonal FOV match) = {f35} * {math.hypot(w, h):.1f} / {DIAG_35:.2f} = {f_diag:.1f} px")
    print(f"f_px (width shortcut)     = {f35} * {max(w, h)} / 36 = {f_width:.1f} px   "
          f"({(f_width / f_diag - 1) * 100:+.1f} %)")
    hfov = 2 * math.degrees(math.atan(w / 2 / f_diag))
    print(f"horizontal field of view  = 2 atan({w}/2 / {f_diag:.1f}) = {hfov:.1f} deg")
    d = pixel_to_camera_dir(u, v, f_diag, f_diag, cx, cy)
    n = d / np.linalg.norm(d)
    print(f"principal point (cx, cy)  = ({cx:.1f}, {cy:.1f})   pixel (u, v) = ({u:.1f}, {v:.1f})")
    print(f"ray_generator: unnormalised ({d[0]:.4f}, {d[1]:.4f}, {d[2]:.4f})  "
          f"normalised ({n[0]:.4f}, {n[1]:.4f}, {n[2]:.4f})")


if __name__ == "__main__":
    main()
