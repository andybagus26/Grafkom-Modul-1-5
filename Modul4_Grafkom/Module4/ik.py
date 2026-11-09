"""Analytic 2-bone inverse kinematics (law of cosines) -- from scratch.

Given two link lengths and a target point, find the two joint angles that
place the end effector on the target, using the same (length, local_angle)
convention as fk.py so the result can be plugged straight back into
forward_kinematics as a check.
"""
from __future__ import annotations

import math

from fk import Bone, forward_kinematics


class UnreachableTarget(Exception):
    pass


def solve_two_bone_ik(l1: float, l2: float, target: tuple[float, float], elbow_up: bool = True):
    """Return (theta1_deg, theta2_deg) -- theta1 is the shoulder angle from
    the +x axis, theta2 is the elbow angle relative to the first link
    (matching fk.py's local-angle convention).

    elbow_up=True  -> +arccos branch (the module's running example)
    elbow_up=False -> -arccos branch, the mirror "elbow down" solution
    """
    tx, ty = target
    d = math.hypot(tx, ty)
    if d > l1 + l2 or d < abs(l1 - l2):
        raise UnreachableTarget(
            f"target at distance {d:.3f} is outside [{abs(l1 - l2):.3f}, {l1 + l2:.3f}]"
        )

    # Elbow angle from the law of cosines: d^2 = l1^2 + l2^2 - 2 l1 l2 cos(pi - theta2)
    # => cos(theta2) = (d^2 - l1^2 - l2^2) / (2 l1 l2)
    cos_theta2 = (d * d - l1 * l1 - l2 * l2) / (2 * l1 * l2)
    cos_theta2 = max(-1.0, min(1.0, cos_theta2))  # clamp for float safety
    theta2 = math.degrees(math.acos(cos_theta2))  # elbow-up: positive bend
    if not elbow_up:
        theta2 = -theta2  # elbow-down: mirror across the shoulder-target line

    # Shoulder angle = angle to target minus the angle the elbow bend adds.
    angle_to_target = math.degrees(math.atan2(ty, tx))
    theta2_rad = math.radians(theta2)
    adjust = math.degrees(math.atan2(l2 * math.sin(theta2_rad), l1 + l2 * math.cos(theta2_rad)))
    theta1 = angle_to_target - adjust

    return theta1, theta2


def running_example():
    """Module 4 running example: lengths 3 and 2, target (4, 1)."""
    l1, l2 = 3.0, 2.0
    target = (4.0, 1.0)
    theta1, theta2 = solve_two_bone_ik(l1, l2, target)
    # Verify: plug the solved angles back into forward kinematics.
    positions, _ = forward_kinematics([Bone(l1, theta1), Bone(l2, theta2)])
    hand = positions[-1]
    return theta1, theta2, hand, target


if __name__ == "__main__":
    theta1, theta2, hand, target = running_example()
    print(f"target       = ({target[0]:.3f}, {target[1]:.3f})")
    print(f"theta1 (shoulder) = {theta1:.2f} deg")
    print(f"theta2 (elbow)    = {theta2:.2f} deg")
    print(f"FK(theta1,theta2) = ({hand[0]:.3f}, {hand[1]:.3f})  <- should match target")
    err = math.hypot(hand[0] - target[0], hand[1] - target[1])
    print(f"position error    = {err:.2e}")

    print("\n-- both solutions for the same target (4, 1) --")
    for label, up in (("elbow-up  ", True), ("elbow-down", False)):
        t1, t2 = solve_two_bone_ik(3.0, 2.0, target, elbow_up=up)
        pos, _ = forward_kinematics([Bone(3.0, t1), Bone(2.0, t2)])
        e, h = pos[1], pos[2]
        print(f"{label}: theta1={t1:7.2f}  theta2={t2:7.2f}  "
              f"elbow=({e[0]:.3f}, {e[1]:.3f})  hand=({h[0]:.3f}, {h[1]:.3f})")
