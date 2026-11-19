@tool
extends Path3D
## Module 4, Lab 3 item 2 -- the rig WALKS ALONG THE SPLINE past the temple.
## Takes the same Catmull-Rom samples as CameraPath (the 41 points baked by
## spline_camera.gd), flattens them to the ground and pulls them in to
## `radius_scale` x the camera radius (8 m -> 5 m), so the walker passes between
## the flying camera and the temple and stays in shot.
##
## The root speed along the path is NOT a free parameter: it is
## stride_per_cycle * cycle_rate, the stride the leg animation already encodes
## (the foot-slide fix from Lab 2, applied on a curve). progress is arc length,
## so constant progress-per-second = constant ground speed = no sliding.

@export var camera_path: NodePath = ^"../CameraPath"
@export var radius_scale: float = 0.625
@export var stride_per_cycle: float = 1.0
@export var cycle_rate: float = 1.0

var _follow: PathFollow3D
var _figure: Node3D
var _printed := false


func _ready() -> void:
	_follow = PathFollow3D.new()
	_follow.loop = false
	add_child(_follow)
	_figure = Node3D.new()
	_figure.set_script(load("res://scripts/foot_slide_demo.gd"))
	_figure.set("drive_root", false)
	_figure.set("print_gap", false)
	_figure.set("stride_per_cycle", stride_per_cycle)
	_figure.set("cycle_rate", cycle_rate)
	# the stick figure faces +x; PathFollow3D's forward is -z -> turn it +90 deg about y
	_figure.rotation.y = PI / 2
	_follow.add_child(_figure)
	_build_curve.call_deferred()   # CameraPath bakes its curve in its own _ready


func _build_curve() -> void:
	var src := get_node_or_null(camera_path) as Path3D
	if src == null or src.curve == null:
		push_warning("path_walker: no camera curve at %s" % camera_path)
		return
	curve = Curve3D.new()
	for i in src.curve.point_count:
		var p := src.curve.get_point_position(i)
		curve.add_point(Vector3(p.x * radius_scale, 0.0, p.z * radius_scale))


func speed() -> float:
	return stride_per_cycle * cycle_rate


func _process(delta: float) -> void:
	if Engine.is_editor_hint() or curve == null or curve.get_baked_length() <= 0.0:
		return
	var length := curve.get_baked_length()
	_follow.progress = fmod(_follow.progress + speed() * delta, length)
	if not _printed:
		_printed = true
		print("[pathwalker] ground path %d points, length %.2f m, speed = stride*rate = %.2f m/s, lap %.1f s" % [
			curve.point_count, length, speed(), length / speed()])
