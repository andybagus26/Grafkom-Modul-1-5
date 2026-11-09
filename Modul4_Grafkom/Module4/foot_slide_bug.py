"""Diagnose-and-fix: root-motion / animation-speed mismatch ("foot sliding").

A walk-cycle clip is *authored* to move the character forward by
STRIDE_PER_CYCLE metres over one full cycle (this is baked into the
animation -- e.g. read from the clip's root-motion curve, or, as here,
computed from the foot's forward excursion). The game code separately
drives the character's root node forward at SCRIPTED_SPEED m/s while the
animation plays at CYCLE_RATE cycles/s.

If SCRIPTED_SPEED != STRIDE_PER_CYCLE * CYCLE_RATE, the root moves faster
(or slower) than the legs are actually covering ground in the animation --
visually the feet slip against the floor ("foot sliding" / "ice skating").
We compute the two displacement curves (root vs. authored-animation) over
time and report the growing gap -- that gap, not a screenshot, is the
"evidence" a marker/automated test can check.
"""
from __future__ import annotations


STRIDE_PER_CYCLE = 1.0   # metres of forward travel the animation clip authored per cycle
CYCLE_RATE = 1.0         # cycles per second the AnimationPlayer plays the clip at


def root_motion_distance(scripted_speed: float, t: float) -> float:
    """Distance the root node has moved by time t, driven by a constant
    scripted speed (what a naive controller does)."""
    return scripted_speed * t


def animation_authored_distance(t: float, stride=STRIDE_PER_CYCLE, rate=CYCLE_RATE) -> float:
    """Distance the *feet* have actually walked by time t, according to the
    animation clip itself (stride length x number of cycles elapsed)."""
    return stride * rate * t


def foot_slide_at(t: float, scripted_speed: float) -> float:
    """The gap between where the root has moved to and where the animation's
    own foot contact says the character should be -- this gap is the visible
    sliding distance."""
    return root_motion_distance(scripted_speed, t) - animation_authored_distance(t)


def diagnose(scripted_speed: float, t_end: float = 5.0, dt: float = 1.0):
    """Report the foot-slide distance at each second up to t_end."""
    samples = []
    t = 0.0
    while t <= t_end + 1e-9:
        samples.append((t, foot_slide_at(t, scripted_speed)))
        t += dt
    return samples


if __name__ == "__main__":
    BUGGY_SPEED = 1.5   # scripted speed does not match the animation's own stride rate
    FIXED_SPEED = STRIDE_PER_CYCLE * CYCLE_RATE  # = 1.0 m/s: matches the animation exactly

    print("-- buggy: scripted_speed = 1.5 m/s, animation authors 1.0 m/s of travel --")
    for t, slide in diagnose(BUGGY_SPEED):
        print(f"  t={t:.0f}s  root={root_motion_distance(BUGGY_SPEED, t):.2f} m"
              f"  animation={animation_authored_distance(t):.2f} m"
              f"  foot-slide={slide:+.2f} m")

    print("\n-- fixed: scripted_speed set to STRIDE_PER_CYCLE * CYCLE_RATE = 1.0 m/s --")
    for t, slide in diagnose(FIXED_SPEED):
        print(f"  t={t:.0f}s  root={root_motion_distance(FIXED_SPEED, t):.2f} m"
              f"  animation={animation_authored_distance(t):.2f} m"
              f"  foot-slide={slide:+.2f} m")

    buggy_final = foot_slide_at(5.0, BUGGY_SPEED)
    fixed_final = foot_slide_at(5.0, FIXED_SPEED)
    print(f"\nfoot-slide after 5 s: buggy = {buggy_final:.2f} m, fixed = {fixed_final:.2f} m")
    assert abs(fixed_final) < 1e-9, "fix should zero the foot-slide gap"
    assert abs(buggy_final) > 2.0, "buggy case should show a large, visible gap"
