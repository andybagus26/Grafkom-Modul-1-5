"""Quaternions from scratch: construction, slerp, and a gimbal-lock
demonstration comparing Euler angles against quaternions.

No library (no scipy.spatial.transform, no numpy-quaternion) -- everything
is a 4-tuple (w, x, y, z) and plain trig/arithmetic, per the from-scratch
rule (MASTER Sec 3.2 item 2).
"""
from __future__ import annotations

import math


def quat_from_axis_angle(axis, angle_deg):
    ax, ay, az = axis
    norm = math.sqrt(ax * ax + ay * ay + az * az)
    ax, ay, az = ax / norm, ay / norm, az / norm
    half = math.radians(angle_deg) / 2.0
    s = math.sin(half)
    return (math.cos(half), ax * s, ay * s, az * s)


def quat_dot(q0, q1):
    return sum(a * b for a, b in zip(q0, q1))


def quat_scale(q, s):
    return tuple(c * s for c in q)


def quat_add(q0, q1):
    return tuple(a + b for a, b in zip(q0, q1))


def quat_negate(q):
    return tuple(-c for c in q)


def slerp(q0, q1, t: float):
    """Spherical linear interpolation between two unit quaternions."""
    cos_theta = quat_dot(q0, q1)
    if cos_theta < 0.0:  # take the short way round
        q1 = quat_negate(q1)
        cos_theta = -cos_theta
    cos_theta = max(-1.0, min(1.0, cos_theta))
    if cos_theta > 0.9995:  # nearly identical: linear interpolation is safe
        result = quat_add(quat_scale(q0, 1.0 - t), quat_scale(q1, t))
    else:
        theta = math.acos(cos_theta)
        sin_theta = math.sin(theta)
        coeff0 = math.sin((1.0 - t) * theta) / sin_theta
        coeff1 = math.sin(t * theta) / sin_theta
        result = quat_add(quat_scale(q0, coeff0), quat_scale(q1, coeff1))
    n = math.sqrt(sum(c * c for c in result))
    return tuple(c / n for c in result)


def quat_to_axis_angle(q):
    w, x, y, z = q
    w = max(-1.0, min(1.0, w))
    angle = 2.0 * math.degrees(math.acos(w))
    s = math.sqrt(max(0.0, 1.0 - w * w))
    if s < 1e-8:
        return (0.0, 0.0, 1.0), angle
    return (x / s, y / s, z / s), angle


def euler_xyz_to_matrix(pitch_deg, yaw_deg, roll_deg):
    """Intrinsic X (pitch) -> Y (yaw) -> Z (roll), a common engine order."""
    p, y, r = (math.radians(a) for a in (pitch_deg, yaw_deg, roll_deg))
    cx, sx = math.cos(p), math.sin(p)
    cy, sy = math.cos(y), math.sin(y)
    cz, sz = math.cos(r), math.sin(r)
    rx = [[1, 0, 0], [0, cx, -sx], [0, sx, cx]]
    ry = [[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]
    rz = [[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]

    def matmul(a, b):
        return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]

    return matmul(matmul(rz, ry), rx)


def _axis_matrix(axis: str, angle_deg: float):
    a = math.radians(angle_deg)
    c, s = math.cos(a), math.sin(a)
    return {
        "x": [[1, 0, 0], [0, c, -s], [0, s, c]],
        "y": [[c, 0, s], [0, 1, 0], [-s, 0, c]],
        "z": [[c, -s, 0], [s, c, 0], [0, 0, 1]],
    }[axis]


def _matmul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def euler_to_matrix(order: str, pitch_deg, yaw_deg, roll_deg):
    """General Euler composition. `order` is the matrix product written left
    to right, e.g. "zyx" = Rz(roll) @ Ry(yaw) @ Rx(pitch) (this module's
    default), "xzy" = Rx(pitch) @ Rz(roll) @ Ry(yaw), "yxz" = Godot 4's default.
    pitch is about x, yaw about y, roll about z."""
    angle = {"x": pitch_deg, "y": yaw_deg, "z": roll_deg}
    m = _axis_matrix(order[0], angle[order[0]])
    for ax in order[1:]:
        m = _matmul(m, _axis_matrix(ax, angle[ax]))
    return m


def _max_diff(m1, m2):
    return max(abs(m1[i][j] - m2[i][j]) for i in range(3) for j in range(3))


def alt_order_lock_demo():
    """Lab 2: order Rx(pitch) Rz(roll) Ry(yaw). The *middle* factor is now Rz,
    so the prediction is that ROLL locks at 90 deg and only (pitch - yaw) is
    observable. Returns:
      roll90_pitch_minus_yaw : diff between two (pitch, yaw) pairs with the same
                               pitch - yaw at roll=90  -> ~0 (LOCKED)
      roll90_pitch_plus_yaw  : same but with pitch + yaw held -> > 0
      yaw90_same_pairs       : the original lock test (yaw=90, pitch - roll
                               held) under the NEW order -> > 0 (yaw does NOT lock)
    """
    m = lambda p, y, r: euler_to_matrix("xzy", p, y, r)
    roll90_minus = _max_diff(m(20.0, 10.0, 90.0), m(15.0, 5.0, 90.0))
    roll90_plus = _max_diff(m(20.0, 10.0, 90.0), m(15.0, 15.0, 90.0))
    yaw90 = _max_diff(m(20.0, 90.0, 10.0), m(15.0, 90.0, 5.0))
    return roll90_minus, roll90_plus, yaw90


def running_example_slerp():
    """Module 4 running example: slerp 40% from identity to a 90 deg yaw
    (about +Y) quaternion."""
    identity = (1.0, 0.0, 0.0, 0.0)
    yaw90 = quat_from_axis_angle((0, 1, 0), 90.0)
    return slerp(identity, yaw90, 0.4)


def gimbal_lock_demo():
    """This engine applies intrinsic X(pitch) then Y(yaw) then Z(roll)
    (matrix = Rz(roll) @ Ry(yaw) @ Rx(pitch)) -- for that order, the *middle*
    axis (yaw) is the one that locks: at yaw = +90 deg, the pitch and roll
    axes both end up rotating the model about the same world axis, so only
    their *difference* (pitch - roll) is observable, not each independently.
    We show this by picking three (pitch, roll) pairs that all keep
    pitch - roll = 10 deg fixed while yaw = 90 deg, and confirming the
    resulting matrices are identical even though pitch and roll each change.
    """
    m1 = euler_xyz_to_matrix(20.0, 90.0, 10.0)   # pitch=20, roll=10 -> diff=10
    m2 = euler_xyz_to_matrix(15.0, 90.0, 5.0)    # pitch=15, roll=5  -> diff=10
    m3 = euler_xyz_to_matrix(10.0, 90.0, 0.0)    # pitch=10, roll=0  -> diff=10
    max_diff_12 = max(abs(m1[i][j] - m2[i][j]) for i in range(3) for j in range(3))
    max_diff_13 = max(abs(m1[i][j] - m3[i][j]) for i in range(3) for j in range(3))
    return max_diff_12, max_diff_13


if __name__ == "__main__":
    q = running_example_slerp()
    print(f"slerp(identity, yaw90, t=0.4) = ({q[0]:.4f}, {q[1]:.4f}, {q[2]:.4f}, {q[3]:.4f})")
    axis, angle = quat_to_axis_angle(q)
    print(f"  -> axis {tuple(round(c,3) for c in axis)}, angle {angle:.2f} deg (expect 36.00 deg = 0.4 x 90)")

    d12, d13 = gimbal_lock_demo()
    print(f"gimbal lock: max|M(20,90,10) - M(15,90,5)| = {d12:.2e}")
    print(f"gimbal lock: max|M(20,90,10) - M(10,90,0)| = {d13:.2e}")
    print("  -> both ~0: at yaw=90, only (pitch-roll) matters -- one DOF is lost")

    print("\n-- alternative order: M = Rx(pitch) @ Rz(roll) @ Ry(yaw) --")
    r_minus, r_plus, y90 = alt_order_lock_demo()
    print(f"roll=90, pitch-yaw held : max|M(20,10,90) - M(15,5,90)|  = {r_minus:.2e}  <- LOCKED")
    print(f"roll=90, pitch+yaw held : max|M(20,10,90) - M(15,15,90)| = {r_plus:.2e}")
    print(f"yaw=90,  pitch-roll held: max|M(20,90,10) - M(15,90,5)|  = {y90:.2e}  <- yaw is NOT the lock axis here")

    g = lambda p, y, r: euler_to_matrix("yxz", p, y, r)
    print("\n-- Godot 4 default order YXZ: M = Ry(yaw) @ Rx(pitch) @ Rz(roll) --")
    print(f"yaw=90,   pitch-roll held: {_max_diff(g(20, 90, 10), g(15, 90, 5)):.2e}  <- NOT locked")
    print(f"pitch=90, yaw-roll held  : {_max_diff(g(90, 20, 10), g(90, 15, 5)):.2e}  <- LOCKED (middle axis = x)")
