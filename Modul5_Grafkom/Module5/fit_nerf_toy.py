"""Train the from-scratch VoxelGrid to reconstruct the toy Pusaka3D temple
from the 8-view capture.json dataset, then render a genuinely held-out
novel view and compare it to the analytic ground truth.

This is the from-scratch stand-in for `ns-train nerfacto` (see
Module5_EN.tex's Software section for the real nerfstudio command) --
matched against nerfstudio's renderer is not possible on this authoring
host (no GPU/COLMAP pipeline run here); matched against the *analytic*
ground truth (which generated the training images in the first place) is
the reconciliation this script performs instead. See README.md.
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np

from capture import data_dir, load_ppm, save_ppm
from nerf_toy import VoxelGrid, render_analytic, render_grid, train, ring_camera, psnr

RESOLUTION = 12
LR = 100.0
N_ITERS = 800
NOVEL_ANGLE_DEG = 22.5  # exactly between two training views (0 and 45) -- a fair held-out test


def load_capture(scene="pusaka", targets_from="ppm"):
    """Poses from poses.json; training images from the PPM files themselves
    (targets_from="ppm", the default -- what a real capture would give you), or
    re-rendered in float from the analytic scene (targets_from="analytic", the
    module's original behaviour, which never opened the PPMs)."""
    folder = data_dir(scene)
    with open(os.path.join(folder, "poses.json")) as f:
        manifest = json.load(f)
    views, targets = [], []
    for frame in manifest["frames"]:
        pos = np.array(frame["position"])
        c2w = np.array(frame["camera_to_world_rotation"])
        views.append((pos, c2w))
        if targets_from == "ppm":
            target = load_ppm(os.path.join(folder, frame["file"]))
        else:
            target = render_analytic(manifest["width"], manifest["height"], manifest["fov_deg"],
                                      pos, c2w, manifest["near"], manifest["far"], manifest["n_samples"],
                                      scene=manifest.get("scene", "pusaka"))
        targets.append(target)
    return manifest, views, targets


def main(scene="pusaka", targets_from="ppm", init=0.0):
    manifest, views, targets = load_capture(scene, targets_from)
    scene = manifest.get("scene", "pusaka")
    W, H, FOV = manifest["width"], manifest["height"], manifest["fov_deg"]
    near, far, n_samples = manifest["near"], manifest["far"], manifest["n_samples"]

    grid = VoxelGrid(resolution=RESOLUTION, seed=0, init_sigma_raw=init)
    print(f"[scene={scene}, targets from {targets_from}, sigma_raw init {init:g}] "
          f"Training a {RESOLUTION}^3 voxel grid on {len(views)} views "
          f"({W}x{H} px, {n_samples} samples/ray), lr={LR}, {N_ITERS} iters ...")
    history = train(grid, views, W, H, FOV, targets, near, far, n_samples, lr=LR, n_iters=N_ITERS, log_every=200)
    for it, mse in history:
        print(f"  iter {it:4d}   train MSE = {mse:.5f}")

    train_psnrs = []
    for (cam_pos, c2w), target in zip(views, targets):
        pred, _ = render_grid(grid, W, H, FOV, cam_pos, c2w, near, far, n_samples)
        train_psnrs.append(psnr(pred, target))
    print(f"mean training-view PSNR = {np.mean(train_psnrs):.2f} dB")

    novel_cam, novel_c2w = ring_camera(NOVEL_ANGLE_DEG, radius=manifest["radius"], height=manifest["camera_height"])
    novel_target = render_analytic(W, H, FOV, novel_cam, novel_c2w, near, far, n_samples, scene=scene)
    novel_pred, _ = render_grid(grid, W, H, FOV, novel_cam, novel_c2w, near, far, n_samples)
    novel_psnr = psnr(novel_pred, novel_target)
    print(f"held-out novel view ({NOVEL_ANGLE_DEG} deg, between two training views): PSNR = {novel_psnr:.2f} dB")

    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
    os.makedirs(out_dir, exist_ok=True)
    pre = ("" if scene == "pusaka" else f"{scene}_") + ("" if init == 0.0 else f"init{init:g}_")
    save_ppm(os.path.join(out_dir, f"{pre}novel_view_target.ppm"), novel_target)
    save_ppm(os.path.join(out_dir, f"{pre}novel_view_predicted.ppm"), novel_pred)
    diff = np.clip(np.abs(novel_pred - novel_target) * 4.0, 0, 1)
    save_ppm(os.path.join(out_dir, f"{pre}novel_view_diff_x4.ppm"), diff)
    print(f"wrote out/{pre}novel_view_target.ppm, out/{pre}novel_view_predicted.ppm, out/{pre}novel_view_diff_x4.ppm")
    np.savez(os.path.join(out_dir, f"{pre}grid.npz"), sigma_raw=grid.sigma_raw, color_raw=grid.color_raw)

    return grid, train_psnrs, novel_psnr


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="train the toy NeRF voxel grid on a capture")
    ap.add_argument("--scene", default="pusaka", choices=["pusaka", "andy"])
    ap.add_argument("--targets", default="ppm", choices=["ppm", "analytic"],
                    help="ppm = train on the captured image files (default); "
                         "analytic = the module's original float re-render")
    ap.add_argument("--init", type=float, default=0.0,
                    help="initial sigma_raw (module default 0; lab2_improve.py finds ~-1 fastest)")
    a = ap.parse_args()
    main(a.scene, a.targets, a.init)
