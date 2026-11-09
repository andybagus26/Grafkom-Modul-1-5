"""Generate the committed, deterministic "capture" dataset -- 8 synthetic
posed views of the toy Pusaka3D temple, ring-arranged like a COLMAP capture.
No RNG, no binary photo assets: everything here is produced by
nerf_toy.py's analytic scene, so it is exactly reproducible from source
(MASTER Sec 9.2's "deterministic input" rule). A real phone capture of the
student's own subject, run through nerfstudio/COLMAP, is the graded,
bring-your-own-input version this stands in for.
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np

from nerf_toy import render_analytic, ring_camera

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data", "pusaka_capture")


def data_dir(scene="pusaka"):
    """data/pusaka_capture (the module's scene) or data/andy_capture (mine)."""
    return os.path.join(HERE, "data", f"{scene}_capture")

WIDTH, HEIGHT, FOV_DEG = 20, 16, 50.0
NEAR, FAR, N_SAMPLES = 1.0, 5.0, 32
RING_ANGLES = [0, 45, 90, 135, 180, 225, 270, 315]
RADIUS, HEIGHT_CAM = 3.0, 1.0


def save_ppm(path, image):
    """8-bit binary PPM (P6), the same format code/Module1 and code/Module3
    already use -- one dependency-free image format across the whole
    course."""
    img8 = np.clip(image * 255.0 + 0.5, 0, 255).astype(np.uint8)
    h, w, _ = img8.shape
    with open(path, "wb") as f:
        f.write(f"P6\n{w} {h}\n255\n".encode("ascii"))
        f.write(img8.tobytes())


def load_ppm(path):
    """Read an 8-bit binary PPM (P6) written by save_ppm -> float image in [0,1]."""
    with open(path, "rb") as f:
        data = f.read()
    parts = data.split(maxsplit=4)          # P6, w, h, 255, pixels
    assert parts[0] == b"P6" and parts[3] == b"255", f"{path}: not an 8-bit P6 PPM"
    w, h = int(parts[1]), int(parts[2])
    pix = np.frombuffer(parts[4][: w * h * 3], dtype=np.uint8).reshape(h, w, 3)
    return pix.astype(float) / 255.0


def build_capture(scene="pusaka", angles=RING_ANGLES):
    out = data_dir(scene)
    os.makedirs(out, exist_ok=True)
    poses = []
    for angle in angles:
        cam_pos, c2w = ring_camera(angle, radius=RADIUS, height=HEIGHT_CAM)
        image = render_analytic(WIDTH, HEIGHT, FOV_DEG, cam_pos, c2w, NEAR, FAR, N_SAMPLES, scene=scene)
        fname = f"view_{angle:03d}.ppm"
        save_ppm(os.path.join(out, fname), image)
        poses.append({
            "file": fname,
            "angle_deg": angle,
            "position": cam_pos.tolist(),
            "camera_to_world_rotation": c2w.tolist(),
        })

    manifest = {
        "scene": scene,
        "width": WIDTH, "height": HEIGHT, "fov_deg": FOV_DEG,
        "near": NEAR, "far": FAR, "n_samples": N_SAMPLES,
        "radius": RADIUS, "camera_height": HEIGHT_CAM,
        "frames": poses,
        "_comment": f"Deterministic synthetic ring capture of the toy scene "
                    f"'{scene}' defined in nerf_toy.py -- COLMAP-style pose "
                    "manifest, no RNG, no binary photo assets.",
    }
    with open(os.path.join(out, "poses.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scene", default="pusaka", choices=["pusaka", "andy"],
                    help="pusaka = the module's temple; andy = temple + my candi bentar")
    args = ap.parse_args()
    manifest = build_capture(args.scene)
    print(f"wrote {len(manifest['frames'])} views to {os.path.relpath(data_dir(args.scene), HERE)}")
    for frame in manifest["frames"]:
        print(f"  {frame['file']}  angle={frame['angle_deg']:>3} deg  pos={[round(c,3) for c in frame['position']]}")
