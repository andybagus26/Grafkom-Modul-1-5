@tool
extends Path3D
## Module 4 -- Catmull-Rom camera fly-through, built the same way twice:
##   1) sampled by hand with the identical formula as code/Module4/spline.py
##      and baked into this Path3D's Curve3D (the "from scratch" artifact,
##      reproduced inside the engine);
##   2) for the Lab 3 decision-with-prediction task, compare against Godot's
##      own Curve3D authored directly from the 5 control points (built-in
##      cubic interpolation) -- predict whether the two paths visibly differ
##      before overlaying them.
##
## @tool: the path is built in the editor too, so you can see it there.
## While playing: the camera flies the lap and always faces `look_target`
## (the temple); press C to switch between PathCamera and OverviewCamera.
##
## 2026-09-29 fixes: the JSON is now inside the project (res://data/), since
## res://../ points outside the project folder; samples_per_segment is 10, as
## spline.py uses (5 control points -> 41 samples); PathFollow3D's own
## rotation is off and the camera looks at the temple instead of along the path.

@export var control_points_json: String = "res://data/camera_path.json"
@export var seconds_per_lap: float = 12.0
@export var samples_per_segment: int = 10
@export var look_target: Vector3 = Vector3(0, 2, 0)          # the temple, world space
@export var overview_camera_path: NodePath = ^"../OverviewCamera"

var _follow: PathFollow3D
var _camera: Camera3D
var _t := 0.0


func _ready() -> void:
	var control_points := _load_control_points(control_points_json)
	curve = Curve3D.new()
	for p in _sample_catmull_rom(control_points, samples_per_segment):
		curve.add_point(p)

	_follow = get_node_or_null("PathFollow3D")
	_camera = get_node_or_null("PathFollow3D/PathCamera")


func _process(delta: float) -> void:
	if Engine.is_editor_hint():
		return  # build the path in the editor, but only fly it while playing
	if _follow == null or curve == null or curve.get_baked_length() <= 0.0:
		return
	_t = fmod(_t + delta / seconds_per_lap, 1.0)
	_follow.progress_ratio = _t
	if _camera != null:
		_camera.look_at(look_target, Vector3.UP)


func _unhandled_input(event: InputEvent) -> void:
	if Engine.is_editor_hint():
		return
	if event is InputEventKey and event.pressed and event.keycode == KEY_C:
		var overview := get_node_or_null(overview_camera_path) as Camera3D
		if _camera == null or overview == null:
			return
		if _camera.current:
			overview.make_current()
		else:
			_camera.make_current()


func _load_control_points(path: String) -> Array:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null:
		push_warning("camera_path.json not found at %s -- using a built-in fallback path" % path)
		return [Vector3(8, 3, 0), Vector3(5.657, 3, 5.657), Vector3(0, 3, 8),
				Vector3(-5.657, 3, 5.657), Vector3(-8, 3, 0)]
	var data: Dictionary = JSON.parse_string(file.get_as_text())
	var points: Array = []
	for p in data.get("control_points", []):
		points.append(Vector3(p[0], p[1], p[2]))
	return points


## Same formula as spline.py's catmull_rom_point + sample_path (clamped ends).
func _sample_catmull_rom(control_points: Array, per_segment: int) -> Array:
	var pts: Array = [control_points[0]]
	pts.append_array(control_points)
	pts.append(control_points[control_points.size() - 1])

	var out: Array = []
	var n_segments := pts.size() - 3
	for seg in range(n_segments):
		var p0: Vector3 = pts[seg]
		var p1: Vector3 = pts[seg + 1]
		var p2: Vector3 = pts[seg + 2]
		var p3: Vector3 = pts[seg + 3]
		var steps := per_segment if seg < n_segments - 1 else per_segment + 1
		for i in range(steps):
			var t := float(i) / float(per_segment)
			out.append(_catmull_rom_point(p0, p1, p2, p3, t))
	return out


func _catmull_rom_point(p0: Vector3, p1: Vector3, p2: Vector3, p3: Vector3, t: float) -> Vector3:
	var t2 := t * t
	var t3 := t2 * t
	var term1 := p1 * 2.0
	var term2 := (p2 - p0) * t
	var term3 := (p0 * 2.0 - p1 * 5.0 + p2 * 4.0 - p3) * t2
	var term4 := (-p0 + p1 * 3.0 - p2 * 3.0 + p3) * t3
	return (term1 + term2 + term3 + term4) * 0.5
