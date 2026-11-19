"""Catmull-Rom spline sampler -- from scratch, no library.

Standard (uniform, tau=0.5) Catmull-Rom: given four control points
P0, P1, P2, P3, the curve segment between P1 and P2 at parameter t in [0, 1]
is

    q(t) = 0.5 * [ 2*P1 + (-P0+P2)*t + (2P0-5P1+4P2-P3)*t^2
                   + (-P0+3P1-3P2+P3)*t^3 ]

This file implements that formula directly on 2D/3D point tuples and a
sampler over a full path of control points (used for the Module 4 camera
path, camera_path.json).
"""
from __future__ import annotations

import json
import os


def _add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _scale(a, s):
    return tuple(x * s for x in a)


def catmull_rom_point(p0, p1, p2, p3, t: float):
    t2 = t * t
    t3 = t2 * t
    term1 = _scale(p1, 2.0)
    term2 = _scale(_sub(p2, p0), t)
    term3 = _scale(_add(_add(_scale(p0, 2.0), _scale(p1, -5.0)), _add(_scale(p2, 4.0), _scale(p3, -1.0))), t2)
    term4 = _scale(_add(_add(_scale(p0, -1.0), _scale(p1, 3.0)), _add(_scale(p2, -3.0), _scale(p3, 1.0))), t3)
    total = _add(_add(term1, term2), _add(term3, term4))
    return _scale(total, 0.5)


def sample_path(control_points: list[tuple], samples_per_segment: int = 20):
    """Sample a full Catmull-Rom path through >=4 control points.

    The first and last control points are duplicated (clamped-end / "phantom
    point" convention) so the curve actually starts at control_points[0] and
    ends at control_points[-1].
    """
    pts = [control_points[0]] + list(control_points) + [control_points[-1]]
    out = []
    n_segments = len(pts) - 3
    for seg in range(n_segments):
        p0, p1, p2, p3 = pts[seg], pts[seg + 1], pts[seg + 2], pts[seg + 3]
        steps = samples_per_segment if seg < n_segments - 1 else samples_per_segment + 1
        for i in range(steps):
            t = i / samples_per_segment
            out.append(catmull_rom_point(p0, p1, p2, p3, t))
    return out


def load_camera_path(path=None):
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "camera_path.json")
    with open(path) as f:
        data = json.load(f)
    return [tuple(p) for p in data["control_points"]]


def running_example():
    """Module 4 running example: P0=(0,0) P1=(2,0) P2=(4,2) P3=(6,2);
    evaluate the P1-P2 segment at t=0.5."""
    p0, p1, p2, p3 = (0.0, 0.0), (2.0, 0.0), (4.0, 2.0), (6.0, 2.0)
    return catmull_rom_point(p0, p1, p2, p3, 0.5)


# Lab 2: my own control points (NOT camera_path.json) -- an S-shaped 2D path.
# TODO(student): change these to your own points if you like.
MY_CONTROL_POINTS = [(0.0, 0.0), (2.0, 3.0), (5.0, 3.0), (7.0, 0.0), (10.0, 1.0)]


if __name__ == "__main__":
    q = running_example()
    print(f"q(0.5) on segment P1->P2 = ({q[0]:.3f}, {q[1]:.3f})")

    cps = load_camera_path()
    path = sample_path(cps, samples_per_segment=10)
    print(f"camera_path.json: {len(cps)} control points -> {len(path)} sampled points")
    print(f"path start = ({path[0][0]:.3f}, {path[0][1]:.3f}, {path[0][2]:.3f})")
    print(f"path end   = ({path[-1][0]:.3f}, {path[-1][1]:.3f}, {path[-1][2]:.3f})")

    print(f"\n-- my own {len(MY_CONTROL_POINTS)} control points, 4 samples/segment --")
    mine = sample_path(MY_CONTROL_POINTS, samples_per_segment=4)
    for i, p in enumerate(mine):
        mark = "  <- control point" if p in MY_CONTROL_POINTS else ""
        print(f"  [{i:2d}] ({p[0]:6.3f}, {p[1]:6.3f}){mark}")
