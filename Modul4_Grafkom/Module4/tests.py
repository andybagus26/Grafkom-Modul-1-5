"""Module 4 test suite -- every from-scratch example checked against its
hand-worked number. Run: python tests.py -> ALL CHECKS PASSED (N ok)
"""
from __future__ import annotations

import math

from fk import Bone, forward_kinematics, running_example as fk_running_example, my_chain_example
from ik import solve_two_bone_ik, UnreachableTarget, running_example as ik_running_example
from spline import catmull_rom_point, sample_path, load_camera_path, running_example as spline_running_example
from quaternion import (
    quat_from_axis_angle, slerp, quat_to_axis_angle, gimbal_lock_demo,
    running_example_slerp, alt_order_lock_demo, euler_to_matrix, euler_xyz_to_matrix,
)
from spline import MY_CONTROL_POINTS
from foot_slide_bug import foot_slide_at, diagnose

_checks = 0


def check(name, got, want, tol=1e-6):
    global _checks
    ok = abs(got - want) <= tol if isinstance(want, (int, float)) else got == want
    status = "ok" if ok else "FAIL"
    print(f"[{status}] {name}: got={got!r} want={want!r}")
    assert ok, f"{name}: got {got!r}, want {want!r}"
    _checks += 1


def check_point(name, got, want, tol=1e-3):
    for g, w in zip(got, want):
        check(f"{name} ({w})", g, w, tol)


def test_fk():
    positions, angles = fk_running_example()
    shoulder, elbow, hand = positions
    check_point("E1 fk shoulder", shoulder, (0.0, 0.0))
    check_point("E1 fk elbow", elbow, (2.598, 1.500))
    check_point("E1 fk hand", hand, (2.598, 3.500))
    check("E1 fk elbow global angle", angles[0], 30.0)
    check("E1 fk hand global angle", angles[1], 90.0)


def test_my_chain():
    # Lab 2: own 3-bone chain, cross-checked against the hand calculation
    positions, angles = my_chain_example()
    check_point("my chain elbow", positions[1], (23.335, 23.335))
    check_point("my chain wrist", positions[2], (30.064, 48.449))
    check_point("my chain fingertip", positions[3], (39.564, 64.903))
    check("my chain fingertip global angle", angles[2], 60.0)


def test_ik():
    theta1, theta2, hand, target = ik_running_example()
    check("E2 ik theta1", theta1, -13.18, tol=0.01)
    check("E2 ik theta2", theta2, 70.53, tol=0.01)
    check_point("E2 ik FK-of-solution", hand, target, tol=1e-9)

    # Unreachable target must raise, not silently clamp.
    try:
        solve_two_bone_ik(1.0, 1.0, (10.0, 0.0))
    except UnreachableTarget:
        pass
    else:
        raise AssertionError("expected UnreachableTarget for a target outside [0,2]")
    print("[ok] unreachable target correctly raises UnreachableTarget")
    global _checks
    _checks += 1

    # Pitfall-driven fix: the elbow-down branch also reaches the target.
    t1, t2 = solve_two_bone_ik(3.0, 2.0, (4.0, 1.0), elbow_up=False)
    check("elbow-down theta2 mirrors elbow-up", t2, -70.53, tol=0.01)
    pos, _ = forward_kinematics([Bone(3.0, t1), Bone(2.0, t2)])
    check_point("elbow-down FK-of-solution", pos[-1], (4.0, 1.0), tol=1e-9)


def test_spline():
    q = spline_running_example()
    check_point("E3 catmull-rom q(0.5)", q, (3.0, 1.0))

    cps = load_camera_path()
    check("camera_path.json control point count", len(cps), 5)
    path = sample_path(cps, samples_per_segment=10)
    check_point("camera path starts at first control point", path[0], cps[0], tol=1e-9)
    check_point("camera path ends at last control point", path[-1], cps[-1], tol=1e-9)

    mine = sample_path(MY_CONTROL_POINTS, samples_per_segment=4)
    check("my path sample count", len(mine), 4 * (len(MY_CONTROL_POINTS) - 1) + 1)
    for k, cp in enumerate(MY_CONTROL_POINTS):
        check_point(f"my path passes through control point {k}", mine[4 * k], cp, tol=1e-9)


def test_quaternion():
    q = running_example_slerp()
    check_point("E4 slerp(id, yaw90, 0.4)", q, (0.9511, 0.0, 0.3090, 0.0), tol=1e-3)
    axis, angle = quat_to_axis_angle(q)
    check("E4 slerp result angle", angle, 36.0, tol=1e-2)

    # slerp at the endpoints must return the endpoints exactly.
    identity = (1.0, 0.0, 0.0, 0.0)
    yaw90 = quat_from_axis_angle((0, 1, 0), 90.0)
    check_point("slerp t=0 -> q0", slerp(identity, yaw90, 0.0), identity, tol=1e-9)
    check_point("slerp t=1 -> q1", slerp(identity, yaw90, 1.0), yaw90, tol=1e-9)

    d12, d13 = gimbal_lock_demo()
    check("gimbal lock: pitch/roll trade-off invisible (pair 1)", d12, 0.0, tol=1e-9)
    check("gimbal lock: pitch/roll trade-off invisible (pair 2)", d13, 0.0, tol=1e-9)

    # euler_to_matrix("zyx") must equal the original fixed-order function
    a, b = euler_to_matrix("zyx", 20, 35, 50), euler_xyz_to_matrix(20, 35, 50)
    check("euler_to_matrix('zyx') == euler_xyz_to_matrix", max(abs(a[i][j] - b[i][j]) for i in range(3) for j in range(3)), 0.0, tol=1e-12)

    # Alternative order Rx Rz Ry: roll locks, yaw does not.
    r_minus, r_plus, y90 = alt_order_lock_demo()
    check("alt order: roll=90 locks (pitch-yaw held)", r_minus, 0.0, tol=1e-9)
    assert r_plus > 1e-2 and y90 > 1e-2, "pitch+yaw, and yaw=90, must NOT be locked"
    print(f"[ok] alt order: pitch+yaw diff={r_plus:.3f}, yaw=90 diff={y90:.3f} (both clearly > 0)")
    _checks_inc()


def _checks_inc():
    global _checks
    _checks += 1


def test_foot_slide_bug():
    buggy = foot_slide_at(5.0, 1.5)
    fixed = foot_slide_at(5.0, 1.0)
    check("foot-slide bug, buggy speed, t=5s", buggy, 2.5)
    check("foot-slide bug, fixed speed, t=5s", fixed, 0.0, tol=1e-9)
    # the gap must grow monotonically over time in the buggy case
    samples = diagnose(1.5)
    diffs = [b[1] - a[1] for a, b in zip(samples, samples[1:])]
    assert all(d > 0 for d in diffs), "foot-slide gap should grow every second in the buggy case"
    print("[ok] foot-slide gap grows monotonically in the buggy case")
    global _checks
    _checks += 1


if __name__ == "__main__":
    test_fk()
    test_my_chain()
    test_ik()
    test_spline()
    test_quaternion()
    test_foot_slide_bug()
    print(f"\nALL CHECKS PASSED ({_checks} ok)")
