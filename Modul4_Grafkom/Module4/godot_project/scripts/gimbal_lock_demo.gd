@tool
extends Node3D
## Module 4 -- Euler (gimbal lock) vs Quaternion (slerp) side by side.
## (@tool: the cubes are drawn in the editor too, standing still there.)
## Mirrors code/Module4/quaternion.py's gimbal_lock_demo(): two cubes driven
## by Euler angles with yaw pinned at 90 deg fight each other for the same
## visual rotation (only pitch - roll is observable), while a third cube
## driven by slerp between two quaternions rotates smoothly with no lock.

var _euler_cube: MeshInstance3D
var _quat_cube: MeshInstance3D
var _t := 0.0


func _ready() -> void:
	_euler_cube = _make_cube(Vector3(-2, 1.5, 0), Color(0.9, 0.3, 0.2))
	_quat_cube = _make_cube(Vector3(2, 1.5, 0), Color(0.2, 0.7, 0.9))
	# FIX (Lab 2/3): Godot's default rotation_order is YXZ (= Ry @ Rx @ Rz),
	# whose MIDDLE axis is X -- so pinning yaw=90 there does NOT lock (diff
	# 8.65e-02, see quaternion.py). Use ZYX (= Rz @ Ry @ Rx), the same order
	# as quaternion.py, so yaw=90 really is the lock condition.
	_euler_cube.rotation_order = EULER_ORDER_ZYX
	if not Engine.is_editor_hint():
		_print_lock_evidence()


## Same numbers as `python quaternion.py`, computed by Godot's own Basis.
func _print_lock_evidence() -> void:
	var r := func(p: float, y: float, z: float, order: int) -> Basis:
		return Basis.from_euler(Vector3(deg_to_rad(p), deg_to_rad(y), deg_to_rad(z)), order)
	var d := func(a: Basis, b: Basis) -> float:
		var m := 0.0
		for i in 3:
			var v: Vector3 = (a[i] - b[i]).abs()
			m = max(m, max(v.x, max(v.y, v.z)))
		return m
	print("[gimbal] ZYX yaw=90 pitch-roll held : ", d.call(r.call(20, 90, 10, EULER_ORDER_ZYX), r.call(15, 90, 5, EULER_ORDER_ZYX)), "  (python: 1.11e-16, locked)")
	print("[gimbal] YXZ yaw=90 pitch-roll held : ", d.call(r.call(20, 90, 10, EULER_ORDER_YXZ), r.call(15, 90, 5, EULER_ORDER_YXZ)), "  (python: 8.65e-02, NOT locked)")
	print("[gimbal] YXZ pitch=90 yaw-roll held : ", d.call(r.call(90, 20, 10, EULER_ORDER_YXZ), r.call(90, 15, 5, EULER_ORDER_YXZ)), "  (python: 1.11e-16, locked)")


func _make_cube(pos: Vector3, color: Color) -> MeshInstance3D:
	var mesh_instance := MeshInstance3D.new()
	mesh_instance.mesh = BoxMesh.new()
	mesh_instance.position = pos
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mesh_instance.material_override = mat
	add_child(mesh_instance)
	return mesh_instance


func _process(delta: float) -> void:
	if Engine.is_editor_hint():
		return  # show the cubes in the editor, but only spin them while playing
	_t += delta

	# Euler cube: yaw pinned at 90 deg (the lock condition); pitch and roll
	# both swing but only their difference shows up on screen.
	var pitch := 20.0 * sin(_t)
	var roll := 20.0 * sin(_t) - 10.0  # pitch - roll = 10 deg, constant -> locked
	_euler_cube.rotation = Vector3(deg_to_rad(pitch), deg_to_rad(90.0), deg_to_rad(roll))

	# Quaternion cube: smooth slerp between two independent orientations,
	# never loses a degree of freedom.
	var q0 := Quaternion(Vector3.UP, deg_to_rad(0.0))
	var q1 := Quaternion(Vector3(1, 1, 0).normalized(), deg_to_rad(120.0))
	var s := (sin(_t) + 1.0) * 0.5
	_quat_cube.basis = Basis(q0.slerp(q1, s))
