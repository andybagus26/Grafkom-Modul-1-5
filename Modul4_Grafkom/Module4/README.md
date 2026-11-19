# Module 4 -- Animation, Kinematics & Game Engine (reference repo)

Course: *Grafika Komputer / Computer Graphics* (`25MP7716G030`), S1 Informatika
semester 5. Companion to `../../Module4_EN.tex`. **Feeds the capstone game
track.**

**Rule:** forward kinematics, inverse kinematics, the Catmull-Rom spline
sampler, quaternion slerp, and the foot-slide diagnosis are **pure Python
standard library** (no engine, no animation library) -- built from the maths
first. `godot_project/` reproduces the same four primitives *inside* Godot 4
(GDScript) as the "real tool" reconciliation step, using the identical
formulas and the identical running-example numbers.

**Conventions** (pinned at the top of `fk.py`): a chain is a list of
`(length, local_angle_deg)` pairs; `local_angle_deg` is relative to the
*parent* link's direction (so composing a chain is just summing angles, the
2D analogue of a `Node3D` hierarchy in Godot). Angles in degrees everywhere in
this module's public API (converted to radians internally) -- match the
running example values in the `.tex` without a units slip.

## Quick start

```bash
cd code/Module4
python fk.py                # E1: the 2-bone arm, shoulder=30deg, elbow=60deg
python ik.py                 # E2: solve for target (4,1), verify via FK
python spline.py             # E3: Catmull-Rom q(0.5); samples camera_path.json
python quaternion.py         # E4: slerp 40% + the gimbal-lock demonstration
python foot_slide_bug.py     # diagnose-and-fix: buggy (2.5 m gap) vs fixed (0 m)
python tests.py              # -> ALL CHECKS PASSED (40 ok)
```

The Godot reference project is opened in the Godot 4 editor from
`godot_project/project.godot` (see "Known deviations" below -- it was authored
on a host with no Godot binary and has not been opened in the editor).

## Unit table

| File | Job | Reproduces |
|---|---|---|
| `fk.py` | forward kinematics for an n-bone planar chain | Running example (shoulder/elbow/hand) |
| `ik.py` | analytic 2-bone IK (law of cosines) + FK-based verification | IK running example, target (4,1) |
| `spline.py` | Catmull-Rom point evaluation + full-path sampler + `camera_path.json` loader | Spline running example, q(0.5)=(3,1) |
| `quaternion.py` | quaternion construction, slerp, axis-angle extraction, Euler-vs-quaternion gimbal-lock demo | Slerp running example; gimbal-lock invariance |
| `foot_slide_bug.py` | root-motion-speed vs. animation-stride-rate mismatch, diagnosed from the growing displacement gap | Lab 2 diagnose-and-fix |
| `data/camera_path.json` | 5 control points, a semicircular flyover of the temple (radius 8, height 3) | Case Study camera path |
| `tests.py` | every running example + the IK-reachability exception + the gimbal-lock invariance, asserted exactly | MASTER Sec 11.2 |
| `godot_project/` | the same four primitives (arm FK/IK, spline camera, gimbal-lock cubes, foot-slide walker) inside Godot 4, plus a procedural temple blockout | Lab 3 "ship" deliverable |

## What `python tests.py` asserts

- **E1** -- FK: shoulder `(0,0)`, elbow `(2.598, 1.500)` at global angle
  `30 deg`, hand `(2.598, 3.500)` at global angle `90 deg`.
- **E2** -- IK: target `(4,1)`, lengths `3, 2` -> `theta1 = -13.18 deg`,
  `theta2 = 70.53 deg`; plugging the solution back through `fk.py` reproduces
  the target to float precision. An out-of-reach target raises
  `UnreachableTarget` rather than silently clamping.
- **E3** -- Catmull-Rom: control points `(0,0),(2,0),(4,2),(6,2)`,
  `q(0.5) = (3.0, 1.0)` on the `P1`-`P2` segment. `camera_path.json` has 5
  points; the clamped-end sampler starts and ends exactly on the first/last
  control point.
- **E4** -- `slerp(identity, yaw90, t=0.4) = (0.9511, 0, 0.3090, 0)`, i.e. a
  `36 deg` rotation about `+Y` (`0.4 x 90 = 36`, the expected linear-in-angle
  result for two rotations sharing an axis); `t=0`/`t=1` return the endpoints
  exactly. The gimbal-lock demo: at `yaw=90 deg`, three different
  `(pitch, roll)` pairs that all keep `pitch - roll = 10 deg` produce
  *bit-identical* rotation matrices -- one degree of freedom is provably gone.
- **Foot-slide** -- at a scripted speed of `1.5 m/s` against a `1.0 m/s`
  animation stride, the foot-plant gap grows to `2.5 m` after 5 s and
  increases every second; at the corrected speed (`1.0 m/s`) the gap is `0`
  at every sample.

## Notes on fixes applied while verifying

- The first draft of `gimbal_lock_demo()` pinned **pitch** at `90 deg` and
  varied `(yaw, roll)` holding their **sum** constant, on the assumption that
  gimbal lock always "feels like" the first axis. Running it showed matrix
  differences of `0.09`-`0.17`, not `~0` -- **not** locked. The actual lock
  axis depends on the composition order: this engine applies
  `M = Rz(roll) @ Ry(yaw) @ Rx(pitch)`, so it is the **middle** axis (`yaw`)
  that locks, and the invariant combination at `yaw=90 deg` is
  `pitch - roll`, not `pitch + roll`. Fixed and re-verified to `~1e-16`. This
  is exactly the kind of "which axis, which sign, which order" trap
  Sec.\,Pitfalls warns about, and it is kept in the module as evidence that
  the derivation, not the intuition, is what should be trusted.
- No other fixes were needed; every other running example matched its
  hand-derivation on the first run.

## Known deviations from the course plan

1. **No Godot binary on the authoring host.** `godot_project/` (`project.godot`,
   `scenes/Main.tscn`, five `.gd` scripts) is hand-authored, syntactically
   reviewed GDScript/text-`.tscn`, but has **not been opened in the Godot 4
   editor or run**. All geometry is built procedurally in each script's
   `_ready()` (capsule/box/cylinder primitive meshes) specifically so the
   `.tscn` itself stays small and free of hand-typed mesh/material
   sub-resources -- the most failure-prone part of hand-writing Godot's scene
   format blind. **Resolved 2026-09-29:** opened and run in Godot 4.7.2
   (see item 4 and "Verified").
2. **No external rigged asset.** Rather than depend on a downloaded CC0
   `character.glb` (a network dependency this authoring host cannot verify),
   the FK/IK arm and the foot-slide walker are built from Godot's built-in
   primitive meshes (`CapsuleMesh`, `BoxMesh`, `CylinderMesh`) -- "a bone is
   just a node in a transform hierarchy" stays literally true without an
   imported skeleton. Students who rig a real free/AI model get full credit
   for the richer version; the primitive-mesh project is the documented
   fallback (MASTER Sec 3.2 item 1/5).
3. **Temple case-study artifact.** `temple_blockout.gd` procedurally builds a
   stacked-box temple silhouette (matching Module 1/3's "deterministic
   generator, no binary asset" rule) rather than importing
   `Module3/data/pusaka_model.obj` across a project boundary. A student's own
   textured model from Module 3 is a straightforward drop-in (`.obj`/`.glb`
   import + `MeshInstance3D`).
4. **Godot project fixes after the first real run (2026-09-29, Godot 4.7.2).**
   - **Nothing showed in the editor**, only when playing: every mesh is built
     in `_ready()`, which the editor does not run. All five scripts are now
     `@tool`, with `Engine.is_editor_hint()` guards so nothing animates,
     walks or reacts to keys in the editor. The meshes still have no owner, so
     they are never saved into `Main.tscn`.
   - **Wrong camera:** `OverviewCamera` was `current`, so the spline camera never
     showed. `PathCamera` is now current; press **C** to switch.
   - **Camera faced along the path**, not at the temple: `PathFollow3D`
     `rotation_mode = 0` and `spline_camera.gd` calls `look_at(look_target)`.
   - **Path circled the wrong centre:** the temple sat at (0, 0, −6) while the
     path is centred on the origin. The temple is now at the origin; the arm
     (−7.5, 0, 3.6), walker lane (z = 4.6) and gimbal cubes (z = 6.5) were
     moved so nothing overlaps (they all used to sit at the origin, inside it).
   - **Path file outside the project:** `res://../data/camera_path.json` is
     above the project root, so the built-in fallback points were used. The
     project now has its own copy, `godot_project/data/camera_path.json` —
     **keep it identical to `data/camera_path.json`**. For an exported build,
     add `*.json` to Project → Export → Resources → "Filters to export
     non-resource files".
   - **41 samples like `spline.py`:** `samples_per_segment` was 20 (81 points);
     it is now 10, as the module text says.
   - **The walker:** the capsule is now a stick figure whose legs actually swing
     (the script's own comment always described a leg-swing); footfall markers
     are children of the walker, so they land under its feet wherever the
     node is placed; the walk restarts every `loop_seconds` (8 s).

## Verified

| Item | Status | Date | Toolchain |
|---|---|---|---|
| `Module4_EN.tex` compiles | **yes** -- Tectonic 0.17.0, no overfull hbox > 14 pt, 25 pp | 2026-09-06 | Windows 11 |
| `python tests.py` | **ALL CHECKS PASSED (40 ok)** | 2026-09-06 | Python 3.11.9 (stdlib only) |
| `fk.py` / `ik.py` / `spline.py` / `quaternion.py` / `foot_slide_bug.py` | **run green**, transcripts in `Module4_EN.tex` are the actual output | 2026-09-06 | same |
| `../../figures/make_figures_m4.py` | **run green** -- writes `m4_fig1_fk_ik_arm.pdf`, `m4_fig2_gimbal_lock.pdf`, `m4_fig3_spline_path.pdf` | 2026-09-06 | same |
| `godot_project/` | **authored, not editor-verified on this host** (no Godot binary) | 2026-09-06 | Godot 4.2+ (target) |
| student run (Lab 1–3) | `python3 tests.py` **64 ok**; project imports and runs headless with no errors; `tools/check.gd` reproduces FK/IK, gimbal lock, foot-slide (bug 0.5 m/s, fix 0), path walker (slide 3 mm / 3 m); scene rendered with `--write-movie`; Web export in `build/web/` | 2026-11-09 | macOS 27.2 arm64, Python 3.14.7, Godot 4.7.2.stable (Homebrew); Web build opened in Chrome 156 (WebGL2) |
| `godot_project/` after the item-4 fixes | **runs with no errors or warnings** (headless, 300 frames); a headless check script confirms: `PathCamera` current, curve 41 points (8,3,0) → (−8,3,0), path camera faces the temple (dot 1.0000), footfall gap 0.62 m at t = 1.25 s (= 1.5·t − 1.0·t); the editor reopens `Main.tscn` with the `@tool` scripts and no errors. Not checked by eye in the windowed editor | 2026-09-29 | Godot 4.7.2 stable (win64) |
