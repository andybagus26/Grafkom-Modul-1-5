@tool
extends Node3D
## Module 4 -- forward & inverse kinematics for a 2-bone planar arm.
## (@tool: the arm and its IK target are also drawn in the editor.)
## Mirrors code/Module4/fk.py and ik.py exactly (same formulas, same running
## example numbers) so the two can be cross-checked by hand.
##
## Controls (when run in the Godot editor / an exported build):
##   [Space] toggles between the FK pose (shoulder=30 deg, elbow=60 deg)
##   and the IK pose (solved so the hand reaches ik_target).

@export var shoulder_length: float = 3.0
@export var elbow_length: float = 2.0
@export var shoulder_angle_deg: float = 30.0
@export var elbow_angle_deg: float = 60.0
@export var ik_target: Vector3 = Vector3(4, 1, 0)

var _shoulder_mesh: MeshInstance3D
var _elbow_mesh: MeshInstance3D
var _target_mesh: MeshInstance3D
var _use_ik := false


func _ready() -> void:
	_shoulder_mesh = _make_bone(shoulder_length, Color(0.2, 0.6, 1.0))
	_elbow_mesh = _make_bone(elbow_length, Color(1.0, 0.6, 0.1))
	add_child(_shoulder_mesh)
	add_child(_elbow_mesh)

	_target_mesh = MeshInstance3D.new()
	var sphere := SphereMesh.new()
	sphere.radius = 0.15
	sphere.height = 0.3
	_target_mesh.mesh = sphere
	_target_mesh.position = ik_target
	add_child(_target_mesh)

	_apply_fk(shoulder_angle_deg, elbow_angle_deg)


func _make_bone(length: float, color: Color) -> MeshInstance3D:
	var mesh_instance := MeshInstance3D.new()
	var capsule := CapsuleMesh.new()
	capsule.radius = 0.12
	capsule.height = length
	mesh_instance.mesh = capsule
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mesh_instance.material_override = mat
	return mesh_instance


func _unhandled_input(event: InputEvent) -> void:
	if Engine.is_editor_hint():
		return  # the Space toggle is for the running game, not the editor
	if event is InputEventKey and event.pressed and event.keycode == KEY_SPACE:
		_use_ik = not _use_ik
		if _use_ik:
			var angles := solve_two_bone_ik(shoulder_length, elbow_length, Vector2(ik_target.x, ik_target.y))
			_apply_fk(angles.x, angles.y)
		else:
			_apply_fk(shoulder_angle_deg, elbow_angle_deg)


## Same convention as fk.py: local_angle is relative to the parent link.
func _apply_fk(local_angle_1_deg: float, local_angle_2_deg: float) -> void:
	var global1 := local_angle_1_deg
	var global2 := global1 + local_angle_2_deg

	var rad1 := deg_to_rad(global1)
	var elbow_pos := Vector3(shoulder_length * cos(rad1), shoulder_length * sin(rad1), 0)

	var rad2 := deg_to_rad(global2)
	var hand_pos := elbow_pos + Vector3(elbow_length * cos(rad2), elbow_length * sin(rad2), 0)

	# Capsules are authored along +Y; rotate so each points from its start
	# joint to its end joint, and position it at the segment midpoint.
	_place_bone(_shoulder_mesh, Vector3.ZERO, elbow_pos)
	_place_bone(_elbow_mesh, elbow_pos, hand_pos)

	# Lab 2 item 3: print the same numbers fk.py / ik.py print.
	if not Engine.is_editor_hint():
		print("[arm] %s  theta1=%.2f  theta2=%.2f  elbow=(%.3f, %.3f)  hand=(%.3f, %.3f)" % [
			"IK" if _use_ik else "FK", local_angle_1_deg, local_angle_2_deg,
			elbow_pos.x, elbow_pos.y, hand_pos.x, hand_pos.y])


func _place_bone(mesh_instance: MeshInstance3D, from: Vector3, to: Vector3) -> void:
	var mid := (from + to) * 0.5
	var dir := (to - from).normalized()
	mesh_instance.position = mid
	if dir.length() > 0.0001:
		mesh_instance.basis = Basis(Quaternion(Vector3.UP, dir))


## Analytic 2-bone IK, law of cosines -- identical formula to ik.py.
func solve_two_bone_ik(l1: float, l2: float, target: Vector2) -> Vector2:
	var d := target.length()
	d = clamp(d, abs(l1 - l2) + 1e-6, l1 + l2 - 1e-6)  # clamp instead of raising, for interactive use

	var cos_theta2 := (d * d - l1 * l1 - l2 * l2) / (2.0 * l1 * l2)
	cos_theta2 = clamp(cos_theta2, -1.0, 1.0)
	var theta2 := rad_to_deg(acos(cos_theta2))

	var angle_to_target := rad_to_deg(atan2(target.y, target.x))
	var theta2_rad := deg_to_rad(theta2)
	var adjust := rad_to_deg(atan2(l2 * sin(theta2_rad), l1 + l2 * cos(theta2_rad)))
	var theta1 := angle_to_target - adjust

	return Vector2(theta1, theta2)
