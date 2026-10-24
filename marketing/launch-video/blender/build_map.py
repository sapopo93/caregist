"""Blender scene: every CQC-registered location in England as a glowing dot.

One continuous 420-frame shot that Remotion cuts into three beats:
  1-150   reveal: dots sweep in north to south while the camera drifts
  151-270 Weekly Digest: West Midlands lights up, signal rings pulse
  271-420 Territory Brief: camera dives in, region dims, a shortlist rises

Run headless:
  /Applications/Blender.app/Contents/MacOS/Blender -b -P blender/build_map.py -- --render
"""

import json
import math
import random
import sys
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
POINTS = HERE.parent / "data" / "points.json"
OUT_DIR = HERE.parent / "renders" / "map"

SCALE = 0.01  # km -> scene units
DOT = 0.011
FOCUS_REGION = "West Midlands"
SHORTLIST_SIZE = 40
SIGNALS_NEW = 12
SIGNALS_RATING = 8

# Brand palette (linear-ish values chosen by eye under the Standard view transform).
CHARCOAL = (0.024, 0.019, 0.015, 1)
PARCHMENT = (0.91, 0.86, 0.78, 1)
SAGE = (0.21, 0.33, 0.19, 1)
AMBER = (0.66, 0.30, 0.04, 1)
CLAY = (0.53, 0.18, 0.08, 1)


def srgb(hex_value: str) -> tuple:
    h = hex_value.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i : i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, 1)


AMBER = srgb("#D4943A")
CLAY = srgb("#C1784F")
SAGE = srgb("#7E9B79")
PARCHMENT = srgb("#F5EFE4")
CHARCOAL = srgb("#2B2520")


def reset_scene() -> bpy.types.Scene:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, 420
    scene.render.fps = 30
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in {
        e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items
    } else "BLENDER_EEVEE"
    scene.view_settings.view_transform = "Standard"
    scene.render.film_transparent = False
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = CHARCOAL
    bg.inputs[1].default_value = 1.0
    scene.world = world
    return scene


def keyframe_value(node, frames_values):
    sock = node.outputs[0]
    for frame, value in frames_values:
        sock.default_value = value
        sock.keyframe_insert("default_value", frame=frame)
    fcurves = node.id_data.animation_data.action.fcurves if hasattr(node.id_data.animation_data.action, "fcurves") else []
    for fc in fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.easing = "EASE_IN_OUT"


def build_dots(points, focus_idx, shortlist_idx):
    verts, faces = [], []
    ny_vals, focus_vals, short_vals, rand_vals = [], [], [], []
    ys = [p[1] for p in points]
    y_min, y_max = min(ys), max(ys)
    rng = random.Random(7)
    focus_set, short_set = set(focus_idx), set(shortlist_idx)
    h = DOT / 2
    for i, (x, y, _region) in enumerate(points):
        cx, cy = x * SCALE, y * SCALE
        base = len(verts)
        verts += [(cx - h, cy - h, 0), (cx + h, cy - h, 0), (cx + h, cy + h, 0), (cx - h, cy + h, 0)]
        faces.append((base, base + 1, base + 2, base + 3))
        ny_vals.append(1 - (y - y_min) / (y_max - y_min))  # 0 = north, 1 = south
        focus_vals.append(1.0 if i in focus_set else 0.0)
        short_vals.append(1.0 if i in short_set else 0.0)
        rand_vals.append(rng.random())

    mesh = bpy.data.meshes.new("cqc_locations")
    mesh.from_pydata(verts, [], faces)
    for name, vals in (("ny", ny_vals), ("focus", focus_vals), ("shortlist", short_vals), ("rand", rand_vals)):
        attr = mesh.attributes.new(name, "FLOAT", "FACE")
        attr.data.foreach_set("value", vals)
    obj = bpy.data.objects.new("CQC Locations", mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(dot_material())
    return obj


def dot_material():
    mat = bpy.data.materials.new("Dots")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    n = nt.nodes.new
    out = n("ShaderNodeOutputMaterial")
    emit = n("ShaderNodeEmission")
    nt.links.new(emit.outputs[0], out.inputs["Surface"])

    def attr(name):
        a = n("ShaderNodeAttribute")
        a.attribute_type = "GEOMETRY"
        a.attribute_name = name
        return a.outputs["Fac"]

    def value(label, v):
        node = n("ShaderNodeValue")
        node.label = node.name = label
        node.outputs[0].default_value = v
        return node

    def math_node(op, a, b=None, clamp=False):
        m = n("ShaderNodeMath")
        m.operation = op
        m.use_clamp = clamp
        for i, src in enumerate((a, b)):
            if src is None:
                continue
            if isinstance(src, (int, float)):
                m.inputs[i].default_value = src
            else:
                nt.links.new(src, m.inputs[i])
        return m.outputs[0]

    def mix_color(fac, a, b):
        m = n("ShaderNodeMix")
        m.data_type = "RGBA"
        nt.links.new(fac, m.inputs["Factor"])
        for sock, src in ((m.inputs[6], a), (m.inputs[7], b)):
            if isinstance(src, tuple):
                sock.default_value = src
            else:
                nt.links.new(src, sock)
        return m.outputs[2]

    reveal = value("reveal", 0.0)  # 0..1.1 sweep north->south
    digest = value("digest", 0.0)  # focus region glow
    pulse = value("pulse", 0.0)  # animated 0..1 shimmer
    dim = value("dim", 0.0)  # dim everything outside the shortlist
    brief = value("brief", 0.0)  # shortlist glow

    ny, focus, short, rnd = attr("ny"), attr("focus"), attr("shortlist"), attr("rand")

    # Reveal: dot is visible once the sweep passes it, with a soft 0.08 edge.
    shown = math_node("SUBTRACT", reveal.outputs[0], ny)
    shown = math_node("DIVIDE", shown, 0.08, clamp=True)

    # Base brightness varies per dot so the map shimmers rather than looks flat.
    base_strength = math_node("ADD", math_node("MULTIPLY", rnd, 0.9), 0.6)

    # Colour: parchment -> amber for the focus region -> clay for the shortlist.
    focus_fac = math_node("MULTIPLY", focus, digest.outputs[0], clamp=True)
    col = mix_color(focus_fac, PARCHMENT, AMBER)
    short_fac = math_node("MULTIPLY", short, brief.outputs[0], clamp=True)
    col = mix_color(short_fac, col, CLAY)

    # Strength: focus region boosted and pulsing during the Digest beat.
    shimmer = math_node("SINE", math_node("ADD", math_node("MULTIPLY", rnd, 6.283), math_node("MULTIPLY", pulse.outputs[0], 6.283)))
    shimmer = math_node("ADD", math_node("MULTIPLY", shimmer, 0.5), 1.0)
    focus_boost = math_node("MULTIPLY", math_node("MULTIPLY", focus_fac, shimmer), 2.2)
    strength = math_node("ADD", base_strength, focus_boost)
    # Dim: everything except the shortlist fades toward 0.12 during the Brief beat.
    keep = math_node("MAXIMUM", short, math_node("SUBTRACT", 1.0, dim.outputs[0]))
    keep = math_node("ADD", math_node("MULTIPLY", keep, 0.88), 0.12)
    strength = math_node("MULTIPLY", strength, keep)
    strength = math_node("ADD", strength, math_node("MULTIPLY", short_fac, 5.0))
    strength = math_node("MULTIPLY", strength, shown)

    nt.links.new(col, emit.inputs["Color"])
    nt.links.new(strength, emit.inputs["Strength"])
    return mat


def emissive(name, color, strength=4.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = color
    emit.inputs["Strength"].default_value = strength
    nt.links.new(emit.outputs[0], out.inputs["Surface"])
    return mat, emit


def add_signal_rings(points, idx_list, color, start_frame):
    """Expanding rings over a few focus-region dots: illustrative weekly signals."""
    for k, i in enumerate(idx_list):
        x, y, _ = points[i]
        bpy.ops.mesh.primitive_torus_add(
            major_radius=0.05, minor_radius=0.0035, major_segments=48, minor_segments=6,
            location=(x * SCALE, y * SCALE, 0.002),
        )
        ring = bpy.context.active_object
        ring.name = f"signal_{k}"
        mat, emit = emissive(f"signal_mat_{k}", color, 0.0)
        ring.data.materials.append(mat)
        f0 = start_frame + k * 5
        for frame, scale, strength in ((f0, 0.1, 0.0), (f0 + 6, 0.6, 6.0), (f0 + 40, 2.4, 0.0)):
            ring.scale = (scale, scale, scale)
            ring.keyframe_insert("scale", frame=frame)
            emit.inputs["Strength"].default_value = strength
            emit.inputs["Strength"].keyframe_insert("default_value", frame=frame)
        # Hide outside its lifetime so a faded ring never renders as a dark outline.
        for frame, hidden in ((1, True), (f0, False), (f0 + 40, True)):
            ring.hide_render = hidden
            ring.keyframe_insert("hide_render", frame=frame)


def add_shortlist_beams(points, idx_list, start_frame):
    """Thin columns rising from shortlisted dots during the Brief beat."""
    mat, _ = emissive("beam", CLAY, 3.5)
    for k, i in enumerate(idx_list):
        x, y, _ = points[i]
        bpy.ops.mesh.primitive_cylinder_add(radius=0.0045, depth=1.0, vertices=8, location=(x * SCALE, y * SCALE, 0))
        beam = bpy.context.active_object
        beam.name = f"beam_{k}"
        beam.data.materials.append(mat)
        # Origin at base so scaling grows upward.
        beam.data.transform(__import__("mathutils").Matrix.Translation((0, 0, 0.5)))
        height = 0.10 + 0.22 * random.Random(i).random()
        f0 = start_frame + k * 2
        beam.scale = (1, 1, 0.0001)
        beam.keyframe_insert("scale", frame=f0)
        beam.scale = (1, 1, height)
        beam.keyframe_insert("scale", frame=f0 + 24)


def add_camera(focus_center):
    target = bpy.data.objects.new("CamTarget", None)
    bpy.context.scene.collection.objects.link(target)
    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens = 40
    cam = bpy.data.objects.new("Cam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    track = cam.constraints.new("TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"

    fx, fy = focus_center
    keys = [
        # frame, camera location, target location
        (1, (0.6, -9.2, 7.2), (0.2, -0.2, 0)),
        (150, (-0.4, -8.0, 6.0), (0.0, 0.0, 0)),
        (270, (fx - 0.2, fy - 5.2, 4.2), (fx, fy, 0)),
        (420, (fx + 0.45, fy - 2.7, 2.0), (fx, fy + 0.1, 0.05)),
    ]
    for frame, cam_loc, tgt_loc in keys:
        cam.location = cam_loc
        cam.keyframe_insert("location", frame=frame)
        target.location = tgt_loc
        target.keyframe_insert("location", frame=frame)
    for obj in (cam, target):
        action = obj.animation_data.action
        for fc in getattr(action, "fcurves", []):
            for kp in fc.keyframe_points:
                kp.interpolation = "BEZIER"


def animate_material(mat):
    nodes = mat.node_tree.nodes
    keyframe_value(nodes["reveal"], [(1, 0.0), (110, 1.12)])
    keyframe_value(nodes["digest"], [(150, 0.0), (180, 1.0)])
    keyframe_value(nodes["dim"], [(275, 0.0), (320, 1.0)])
    keyframe_value(nodes["brief"], [(285, 0.0), (330, 1.0)])
    pulse = nodes["pulse"].outputs[0]
    pulse.default_value = 0.0
    pulse.keyframe_insert("default_value", frame=150)
    pulse.default_value = 3.0
    pulse.keyframe_insert("default_value", frame=420)
    action = mat.node_tree.animation_data.action
    for fc in getattr(action, "fcurves", []):
        if 'pulse' in fc.data_path:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"


def setup_bloom(scene):
    """Soft glow on the dots. The compositor API moved in Blender 5, so try both."""
    try:
        tree = bpy.data.node_groups.new("Bloom", "CompositorNodeTree")
        scene.compositing_node_group = tree
        rl = tree.nodes.new("CompositorNodeRLayers")
        glare = tree.nodes.new("CompositorNodeGlare")
        out = tree.nodes.new("NodeGroupOutput")
        tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        tree.links.new(rl.outputs["Image"], glare.inputs[0])
        tree.links.new(glare.outputs[0], out.inputs[0])
        _configure_glare(glare)
        return "node_group"
    except Exception as exc:  # older API
        print("bloom: node-group API unavailable:", exc)
    scene.use_nodes = True
    tree = scene.node_tree
    rl = tree.nodes.get("Render Layers") or tree.nodes.new("CompositorNodeRLayers")
    comp = tree.nodes.get("Composite") or tree.nodes.new("CompositorNodeComposite")
    glare = tree.nodes.new("CompositorNodeGlare")
    tree.links.new(rl.outputs["Image"], glare.inputs[0])
    tree.links.new(glare.outputs[0], comp.inputs[0])
    _configure_glare(glare)
    return "scene_tree"


def _configure_glare(glare):
    for attr, val in (("glare_type", "BLOOM"), ("quality", "HIGH")):
        try:
            setattr(glare, attr, val)
        except Exception:
            pass
    for name, val in (("Threshold", 0.9), ("Strength", 0.9), ("Size", 0.6), ("Saturation", 1.0)):
        sock = glare.inputs.get(name)
        if sock is not None:
            try:
                sock.default_value = val
            except Exception:
                pass
    for attr, val in (("threshold", 0.9), ("size", 7), ("mix", 0.0)):
        if hasattr(glare, attr):
            try:
                setattr(glare, attr, val)
            except Exception:
                pass


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    data = json.loads(POINTS.read_text())
    points = [p for p in data["points"] if p[2] != "Unknown"]

    scene = reset_scene()
    focus_idx = [i for i, p in enumerate(points) if p[2] == FOCUS_REGION]
    rng = random.Random(42)
    shortlist_idx = rng.sample(focus_idx, SHORTLIST_SIZE)
    rest = [i for i in focus_idx if i not in set(shortlist_idx)]
    signals = rng.sample(rest, SIGNALS_NEW + SIGNALS_RATING)

    fx = sum(points[i][0] for i in focus_idx) / len(focus_idx) * SCALE
    fy = sum(points[i][1] for i in focus_idx) / len(focus_idx) * SCALE

    dots = build_dots(points, focus_idx, shortlist_idx)
    animate_material(dots.data.materials[0])
    add_signal_rings(points, signals[:SIGNALS_NEW], AMBER, 175)
    add_signal_rings(points, signals[SIGNALS_NEW:], SAGE, 200)
    add_shortlist_beams(points, shortlist_idx, 300)
    add_camera((fx, fy))
    print("bloom via", setup_bloom(scene))

    blend_path = HERE / "caregist_map.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print("saved", blend_path)

    if "--still" in args:
        frame = int(args[args.index("--still") + 1])
        scene.frame_set(frame)
        scene.render.filepath = str(OUT_DIR / f"still_{frame:04d}.png")
        bpy.ops.render.render(write_still=True)
    if "--render" in args:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = str(OUT_DIR / "frame_")
        bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    main()
