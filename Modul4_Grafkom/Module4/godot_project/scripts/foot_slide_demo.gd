@tool
extends Node3D
## Module 4 -- interactive version of code/Module4/foot_slide_bug.py.
## Moves a stick-figure "character" forward at `scripted_speed` while a
## separate, purely visual leg-swing animates at `cycle_rate` cycles/second
## with a stride of `stride_per_cycle` metres. When scripted_speed !=
## stride_per_cycle * cycle_rate the figure visibly slides past its own
## footfall markers, which are dropped on the ground every half-cycle so the
## gap is measurable, not just a vibe.
##
## 2026-09-29: @tool (the figure is visible, standing, in the editor); the
## capsule became a stick figure whose legs actually swing (the comment above
## always promised a leg-swing); markers are children of this node, so they
## land under the figure wherever the Walker node is placed; the walk restarts
## every `loop_seconds` so the figure stays in view.

@export var scripted_speed: float = 1.5
@export var stride_per_cycle: float = 1.0
@export var cycle_rate: float = 1.0
@export var loop_seconds: float = 8.0
## false = only animate the legs in place; a parent (path_walker.gd) moves the
## figure. Footfall markers are only meaningful when this node drives the root.
@export var drive_root: bool = true
## Print the root-vs-animation gap once per second (evidence for the report).
@export var print_gap: bool = true

var _buggy_speed := 0.0
var _last_print_s := -1

const LIMB_COLOR := Color(0.91, 0.96, 0.93)
const JOINT_COLOR := Color(0.83, 0.65, 0.22)
const LIMB_RADIUS := 0.035

var _body: Node3D          # the figure's root; moves along +x
var _hips: Node3D
var _thighs: Array[Node3D] = []
var _knees: Array[Node3D] = []
var _shoulders: Array[Node3D] = []
var _elbows: Array[Node3D] = []
var _markers: Node3D
var _t := 0.0
var _next_footfall_t := 0.0
var _step := 0


func _ready() -> void:
	_body = Node3D.new()
	add_child(_body)
	_build_stick_figure(_body)
	_markers = Node3D.new()
	add_child(_markers)
	_buggy_speed = scripted_speed
	_pose(0.0)


## The fix as a formula, not a guessed number: the root must move exactly as
## fast as the animation's feet do.
func fixed_speed() -> float:
	return stride_per_cycle * cycle_rate


## [F] toggles between the shipped (buggy) speed and the fixed speed.
func _unhandled_input(event: InputEvent) -> void:
	if Engine.is_editor_hint() or not drive_root:
		return
	if event is InputEventKey and event.pressed and event.keycode == KEY_F:
		scripted_speed = fixed_speed() if not is_equal_approx(scripted_speed, fixed_speed()) else _buggy_speed
		print("[walker] scripted_speed = %.2f m/s (%s); stride*rate = %.2f m/s" % [
			scripted_speed, "FIXED" if is_equal_approx(scripted_speed, fixed_speed()) else "BUGGY", fixed_speed()])
		_restart()


func _process(delta: float) -> void:
	if Engine.is_editor_hint():
		return  # stand still in the editor; walk only while playing
	_t += delta
	if not drive_root:
		_pose(TAU * cycle_rate * _t)   # legs only; the parent moves the figure
		return
	if _t > loop_seconds:
		_restart()
	_body.position.x = scripted_speed * _t
	_pose(TAU * cycle_rate * _t)  # one gait cycle every 1 / cycle_rate seconds
	if print_gap and int(_t) != _last_print_s and int(_t) <= 5:
		_last_print_s = int(_t)
		print("[walker] t=%.2fs root=%.2f m animation=%.2f m foot-slide=%+.2f m" % [
			_t, scripted_speed * _t, stride_per_cycle * cycle_rate * _t,
			(scripted_speed - stride_per_cycle * cycle_rate) * _t])

	# Drop a footfall marker every half-cycle of the *animation's own* stride,
	# so the accumulating gap between the marker trail and the body is the
	# visible evidence of foot-sliding.
	var half_cycle := 1.0 / (2.0 * cycle_rate)
	if _t >= _next_footfall_t:
		_drop_footfall(_t)
		_next_footfall_t += half_cycle


func _restart() -> void:
	_t = 0.0
	_last_print_s = -1
	_next_footfall_t = 0.0
	_step = 0
	for m in _markers.get_children():
		m.queue_free()


func _drop_footfall(t: float) -> void:
	var marker := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = Vector3(0.3, 0.02, 0.15)
	marker.mesh = box
	# Where the animation's own stride says the foot should be planted,
	# alternating left and right foot.
	var animated_x: float = stride_per_cycle * cycle_rate * t
	var side := 1.0 if _step % 2 == 0 else -1.0
	_step += 1
	marker.position = Vector3(animated_x, 0.01, 0.12 * side)
	var mat := StandardMaterial3D.new()
	var slide: float = scripted_speed * t - animated_x
	mat.albedo_color = Color(0.9, 0.2, 0.2) if abs(slide) > 0.05 else Color(0.2, 0.9, 0.3)
	marker.material_override = mat
	_markers.add_child.call_deferred(marker)


# ---------------------------------------------------------------- the figure
# About 1.8 m tall, facing +x: hips -> spine -> neck/head, neck -> shoulders ->
# upper arm -> forearm, hips -> thigh -> shin -> foot. Each joint is a Node3D
# whose rotation is local to its parent -- the same tree of local transforms
# as fk.py, in 3D.

func _build_stick_figure(root: Node3D) -> void:
	_hips = _joint(root, Vector3(0, 0.95, 0))
	_bone(_hips, 0.55, true)                                   # spine
	var neck := _joint(_hips, Vector3(0, 0.55, 0))
	_bone(neck, 0.07, true)
	var head := MeshInstance3D.new()
	var head_mesh := SphereMesh.new()
	head_mesh.radius = 0.12
	head_mesh.height = 0.24
	head.mesh = head_mesh
	head.position = Vector3(0, 0.19, 0)
	head.material_override = _material(LIMB_COLOR)
	neck.add_child(head)
	_crossbar(neck, 0.4)                                       # shoulders
	_crossbar(_hips, 0.24)                                     # pelvis
	for side in [1.0, -1.0]:
		var shoulder := _joint(neck, Vector3(0, 0, 0.2 * side))
		_bone(shoulder, 0.3)
		var elbow := _joint(shoulder, Vector3(0, -0.3, 0))
		_bone(elbow, 0.28)
		_shoulders.append(shoulder)
		_elbows.append(elbow)
		var thigh := _joint(_hips, Vector3(0, 0, 0.12 * side))
		_bone(thigh, 0.45)
		var knee := _joint(thigh, Vector3(0, -0.45, 0))
		_bone(knee, 0.45)
		var foot := MeshInstance3D.new()
		var foot_mesh := BoxMesh.new()
		foot_mesh.size = Vector3(0.2, 0.04, 0.08)
		foot.mesh = foot_mesh
		foot.position = Vector3(0.06, -0.47, 0)
		foot.material_override = _material(LIMB_COLOR)
		knee.add_child(foot)
		_thighs.append(thigh)
		_knees.append(knee)


## One gait cycle over phase 0..TAU: legs swing, the swinging knee bends, the
## arms swing opposite the legs, the hips bob a little. Rotating about z by
## +angle moves a downward limb toward +x (forward).
func _pose(phase: float) -> void:
	var s := sin(phase)
	for i in range(2):
		var sgn := 1.0 if i == 0 else -1.0
		var leg_phase := phase + (0.0 if i == 0 else PI)
		_thighs[i].rotation.z = 0.45 * sgn * s
		_knees[i].rotation.z = -0.63 * max(0.0, cos(leg_phase))
		_shoulders[i].rotation.z = -0.35 * sgn * s
		_elbows[i].rotation.z = 0.35
	_hips.position.y = 0.95 + 0.03 * abs(cos(phase))


func _joint(parent: Node3D, pos: Vector3) -> Node3D:
	var j := Node3D.new()
	j.position = pos
	parent.add_child(j)
	var ball := MeshInstance3D.new()
	var ball_mesh := SphereMesh.new()
	ball_mesh.radius = LIMB_RADIUS * 1.5
	ball_mesh.height = LIMB_RADIUS * 3.0
	ball.mesh = ball_mesh
	ball.material_override = _material(JOINT_COLOR)
	j.add_child(ball)
	return j


## A limb segment hanging down from `parent` (or pointing up when `up`).
func _bone(parent: Node3D, length: float, up: bool = false) -> void:
	var m := MeshInstance3D.new()
	var c := CylinderMesh.new()
	c.top_radius = LIMB_RADIUS
	c.bottom_radius = LIMB_RADIUS
	c.height = length
	m.mesh = c
	m.position = Vector3(0, length * 0.5 if up else -length * 0.5, 0)
	m.material_override = _material(LIMB_COLOR)
	parent.add_child(m)


## A horizontal bar across the body (shoulders, pelvis), along z.
func _crossbar(parent: Node3D, width: float) -> void:
	var m := MeshInstance3D.new()
	var c := CylinderMesh.new()
	c.top_radius = LIMB_RADIUS
	c.bottom_radius = LIMB_RADIUS
	c.height = width
	m.mesh = c
	m.rotation.x = PI / 2
	m.material_override = _material(LIMB_COLOR)
	parent.add_child(m)


func _material(color: Color) -> StandardMaterial3D:
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	return mat
