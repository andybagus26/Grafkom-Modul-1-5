extends SceneTree
## Module 4 -- headless evidence for Lab 2 item 3, Lab 3 items 2-3, A4.
##   godot --headless --path godot_project --script res://tools/check.gd
## Loads Main.tscn, lets it run, then presses the keys a person would press
## (Space for IK, F for the foot-slide fix) by calling the same code paths, and
## prints numbers that can be compared with the Python output.

var _main: Node
var _frames := 0


func _initialize() -> void:
	_main = load("res://scenes/Main.tscn").instantiate()
	root.add_child(_main)


func _process(_delta: float) -> bool:
	_frames += 1
	if _frames == 5:
		_check_arm()
		_check_camera()
		_check_spine_prediction()
		_check_walker_fix()
		_check_path_walker()
		print("[check] DONE")
		return true   # quit
	return false


func _check_arm() -> void:
	var arm := _main.get_node("Arm")
	var a: Vector2 = arm.solve_two_bone_ik(3.0, 2.0, Vector2(4, 1))
	arm.set("_use_ik", true)
	arm._apply_fk(a.x, a.y)          # what [Space] does
	var t1 := deg_to_rad(a.x)
	var t2 := deg_to_rad(a.x + a.y)
	var hand := Vector2(3 * cos(t1) + 2 * cos(t2), 3 * sin(t1) + 2 * sin(t2))
	print("[check] IK hand error vs target (4,1) = %s  (python ik.py: 4.44e-16)" % String.num_scientific((hand - Vector2(4, 1)).length()))


func _check_camera() -> void:
	var cam := _main.get_node("CameraPath/PathFollow3D/PathCamera") as Camera3D
	var path := _main.get_node("CameraPath") as Path3D
	var c := path.curve
	print("[check] PathCamera current=%s  curve points=%d  first=%s last=%s" % [
		cam.current, c.point_count, c.get_point_position(0), c.get_point_position(c.point_count - 1)])
	# fly a quarter lap and check the camera faces the temple
	var follow := _main.get_node("CameraPath/PathFollow3D") as PathFollow3D
	follow.progress_ratio = 0.25
	cam.look_at(Vector3(0, 2, 0), Vector3.UP)
	var fwd := -cam.global_transform.basis.z
	var to_temple := (Vector3(0, 2, 0) - cam.global_position).normalized()
	print("[check] camera at %s faces temple: dot = %.4f" % [cam.global_position, fwd.dot(to_temple)])


## Lab 3 item 3: forced test of the written prediction.
## Spine joint, Godot default order YXZ: yaw = twist, pitch = bend forward,
## roll = lean sideways. Prediction: at pitch = 90 deg, twist and lean become
## the same motion (only yaw - roll is visible), so Euler cannot "bend 90, then
## lean 20 deg without twisting"; a quaternion composition can.
func _check_spine_prediction() -> void:
	var e := func(p: float, y: float, r: float) -> Basis:
		return Basis.from_euler(Vector3(deg_to_rad(p), deg_to_rad(y), deg_to_rad(r)), EULER_ORDER_YXZ)
	var diff := func(a: Basis, b: Basis) -> float:
		var m := 0.0
		for i in 3:
			var v: Vector3 = (a[i] - b[i]).abs()
			m = max(m, max(v.x, max(v.y, v.z)))
		return m
	var twist: Basis = e.call(90, 20, 0)     # bend 90 + twist 20
	var lean: Basis = e.call(90, 0, -20)     # bend 90 + lean -20
	print("[check] spine YXZ pitch=90: twist 20 vs lean -20 -> matrix diff %s (prediction: ~0, same pose)" % String.num_scientific(diff.call(twist, lean)))
	# A first version of this test claimed some pose was UNREACHABLE at pitch 90.
	# Wrong: gimbal lock never removes a pose (every orientation has some Euler
	# triple), it removes a DIRECTION OF MOTION. At YXZ pitch=90, yaw and roll
	# both turn about world Y and pitch turns about world X; a small turn about
	# world Z has no small Euler change. Measure exactly that.
	var A: Basis = e.call(90, 0, 0)                                # bent 90 deg
	var B: Basis = Basis(Vector3(0, 0, 1), deg_to_rad(10)) * A     # + 10 deg about world Z
	var eb: Vector3 = B.get_euler(EULER_ORDER_YXZ)
	print("[check] target = locked pose + 10 deg about world Z; its Euler YXZ = (pitch %.1f, yaw %.1f, roll %.1f) vs start (90, 0, 0)" % [
		rad_to_deg(eb.x), rad_to_deg(eb.y), rad_to_deg(eb.z)])
	var qa := A.get_rotation_quaternion()
	var qb := B.get_rotation_quaternion()
	var ea := Vector3(deg_to_rad(90), 0, 0)
	var max_dev := 0.0
	var e_steps: Array = []
	var q_steps: Array = []
	var prev_e := qa
	var prev_q := qa
	for i in range(1, 11):
		var t := i / 10.0
		var qe := Basis.from_euler(ea.lerp(eb, t), EULER_ORDER_YXZ).get_rotation_quaternion()
		var qs := qa.slerp(qb, t)
		max_dev = max(max_dev, rad_to_deg(qe.angle_to(qs)))
		e_steps.append(snappedf(rad_to_deg(prev_e.angle_to(qe)), 0.1))
		q_steps.append(snappedf(rad_to_deg(prev_q.angle_to(qs)), 0.1))
		prev_e = qe
		prev_q = qs
	print("[check] per-step rotation, Euler lerp : %s deg (sum %.1f)" % [e_steps, e_steps.reduce(func(x, y): return x + y)])
	print("[check] per-step rotation, quat slerp : %s deg (sum %.1f)" % [q_steps, q_steps.reduce(func(x, y): return x + y)])
	print("[check] max distance of the Euler-lerp path from the slerp path = %.1f deg" % max_dev)


func _check_walker_fix() -> void:
	var w := _main.get_node("Walker")
	var fixed: float = w.fixed_speed()
	for speed in [1.5, fixed]:
		var gaps: Array = []
		for t in range(0, 6):
			gaps.append(snappedf((speed - fixed) * t, 0.01))
		print("[check] walker speed %.2f m/s (stride*rate = %.2f): gap at t=0..5 s = %s" % [speed, fixed, gaps])


func _check_path_walker() -> void:
	var pw := _main.get_node("PathWalker") as Path3D
	var c := pw.curve
	var L := c.get_baked_length()
	# foot-slide on a curve = (root arc speed - animation speed) * t; measure the
	# root's actual travelled distance over 3 s of simulated frames at 60 fps
	var follow := pw.get_child(0) as PathFollow3D
	follow.progress = 0.0
	var prev := follow.global_position
	var travelled := 0.0
	for i in 180:
		pw._process(1.0 / 60.0)
		travelled += follow.global_position.distance_to(prev)
		prev = follow.global_position
	var anim := 1.0 * 1.0 * 3.0
	print("[check] path walker: path length %.2f m; 3.0 s -> root travelled %.3f m, animation stride %.3f m, slide %.3f m" % [
		L, travelled, anim, travelled - anim])
