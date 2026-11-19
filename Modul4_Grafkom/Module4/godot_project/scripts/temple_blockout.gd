@tool
extends Node3D
## Module 4 -- a self-contained, procedurally-built stand-in for the Pusaka3D
## temple (stacked boxes, same "deterministic generator, no binary asset"
## rule as Module 1/3's make_data.py / make_model.py), so this project has no
## external file dependency. Swap for an imported mymodel.obj / .glb for the
## graded, bring-your-own-building version.
##
## @tool: this also runs in the editor, so the temple is visible while you lay
## out the scene. The meshes have no owner, so they are never saved into
## Main.tscn -- they are rebuilt each time the scene opens or plays.

func _ready() -> void:
	# ground plane, so walkers and footfall markers stand on something
	var ground := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(40, 40)
	ground.mesh = plane
	var ground_mat := StandardMaterial3D.new()
	ground_mat.albedo_color = Color(0.22, 0.26, 0.22)
	ground.material_override = ground_mat
	add_child(ground)

	var tiers := [
		{"size": Vector3(6, 1, 6), "y": 0.5, "color": Color(0.55, 0.5, 0.45)},
		{"size": Vector3(4.5, 1, 4.5), "y": 1.5, "color": Color(0.5, 0.45, 0.4)},
		{"size": Vector3(3, 1.2, 3), "y": 2.6, "color": Color(0.45, 0.4, 0.38)},
		{"size": Vector3(1.6, 1.4, 1.6), "y": 3.9, "color": Color(0.4, 0.35, 0.35)},
	]
	for tier in tiers:
		var mesh_instance := MeshInstance3D.new()
		var box := BoxMesh.new()
		box.size = tier["size"]
		mesh_instance.mesh = box
		mesh_instance.position = Vector3(0, tier["y"], 0)
		var mat := StandardMaterial3D.new()
		mat.albedo_color = tier["color"]
		mesh_instance.material_override = mat
		add_child(mesh_instance)

	var spire := MeshInstance3D.new()
	var cone := CylinderMesh.new()
	cone.top_radius = 0.05
	cone.bottom_radius = 0.6
	cone.height = 1.2
	spire.mesh = cone
	spire.position = Vector3(0, 5.2, 0)
	var spire_mat := StandardMaterial3D.new()
	spire_mat.albedo_color = Color(0.75, 0.62, 0.2)
	spire.material_override = spire_mat
	add_child(spire)
