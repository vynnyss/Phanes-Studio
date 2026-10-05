"""Texture and selection checks using disposable files, without a Studio queue."""
from functools import partial
from io import BytesIO
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from studio_textures import texture_maps


def png(color):
    stream = BytesIO()
    Image.new("RGB", (8, 8), color).save(stream, format="PNG")
    return stream.getvalue()


def write_glb(path, materials, colors, used=None):
    binary = bytearray()
    views = []
    for color in colors:
        content = png(color)
        views.append({"buffer": 0, "byteOffset": len(binary), "byteLength": len(content)})
        binary.extend(content)
        binary.extend(b"\0" * (-len(binary) % 4))
    document = {
        "asset": {"version": "2.0"}, "materials": materials,
        "meshes": [{"primitives": [{"material": index} for index in
                                   (range(len(materials)) if used is None else used)]}],
        "buffers": [{"byteLength": len(binary)}], "bufferViews": views,
        "images": [{"bufferView": index, "mimeType": "image/png"} for index in range(len(colors))],
        "textures": [{"source": index} for index in range(len(colors))],
    }
    encoded = json.dumps(document).encode("utf-8")
    encoded += b" " * (-len(encoded) % 4)
    path.write_bytes(
        struct.pack("<4sII", b"glTF", 2, 28 + len(encoded) + len(binary))
        + struct.pack("<II", len(encoded), 0x4E4F534A) + encoded
        + struct.pack("<II", len(binary), 0x004E4942) + binary
    )


class TextureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.model = self.root / "model.glb"
        self.cache = self.root / "cache"

    def test_embedded_maps_and_packed_ao_preserve_original(self):
        write_glb(self.model, [{
            "pbrMetallicRoughness": {"baseColorTexture": {"index": 0},
                                    "metallicRoughnessTexture": {"index": 2}},
            "normalTexture": {"index": 1}, "occlusionTexture": {"index": 2},
        }], [(200, 40, 60), (128, 128, 255), (35, 140, 220)])
        original = self.model.read_bytes()
        maps = texture_maps(self.model, self.cache)
        with Image.open(maps["albedo"][0][0]) as image:
            self.assertEqual(image.getpixel((0, 0)), (200, 40, 60, 255))
        with Image.open(maps["normal"][0][0]) as image:
            self.assertEqual(image.getpixel((0, 0)), (128, 128, 255, 255))
        with Image.open(maps["ao"][0][0]) as image:
            self.assertEqual(image.getpixel((0, 0)), 35)
        self.assertEqual(self.model.read_bytes(), original)

    def test_metallic_roughness_does_not_imply_ao(self):
        write_glb(self.model, [{"pbrMetallicRoughness": {
            "metallicRoughnessTexture": {"index": 0}}}], [(255, 50, 70)])
        self.assertFalse(texture_maps(self.model, self.cache)["ao"])

    def test_multiple_used_materials_and_cache_invalidation(self):
        materials = [{"name": name, "pbrMetallicRoughness": {"baseColorTexture": {"index": index}}}
                     for index, name in enumerate(("A", "B", "Unused"))]
        write_glb(self.model, materials, [(1, 2, 3), (4, 5, 6), (7, 8, 9)], used=[0, 1])
        maps = texture_maps(self.model, self.cache)
        self.assertEqual([item[1] for item in maps["albedo"]], ["A", "B"])
        write_glb(self.model, materials, [(9, 8, 7), (4, 5, 6), (7, 8, 9)], used=[0, 1])
        updated = texture_maps(self.model, self.cache)
        self.assertNotEqual(maps["albedo"][0][0], updated["albedo"][0][0])

    def test_separate_bake_maps_and_invalid_image(self):
        write_glb(self.model, [], [])
        (self.root / "base_color.png").write_bytes(png((180, 90, 20)))
        (self.root / "normal.png").write_bytes(b"invalid")
        (self.root / "ambient_occlusion.png").write_bytes(png((65, 65, 65)))
        with self.assertLogs("studio_textures", level="WARNING"):
            maps = texture_maps(self.model, self.cache)
        self.assertTrue(maps["albedo"])
        self.assertFalse(maps["normal"])
        self.assertTrue(maps["ao"])

    def test_external_texture_cannot_escape_directory(self):
        from studio_textures import image_bytes
        for uri in ("../secret.png", "file:///secret.png", "https://example.com/a.png"):
            with self.assertRaises(ValueError):
                image_bytes(self.model, {}, None, {"uri": uri})

    def test_selection_refresh_and_processing_clear_texture(self):
        import gradio as gr
        import studio_ui
        write_glb(self.model, [{"pbrMetallicRoughness": {"baseColorTexture": {"index": 0}}}],
                  [(240, 100, 40)])
        model = {
            "id": "fixture", "asset_id": "fixture", "name": "Fixture", "kind": "low",
            "parent_id": None, "model": str(self.model), "report": None,
            "quality_status": "unreviewed", "status": "completed",
        }

        class FixtureStudio:
            def history_entry(self, identifier):
                return model

            def variant(self, identifier):
                return model

            def history_entries(self):
                return [model]

            def reference_images(self):
                return []

        with patch.object(studio_ui, "ROOT", self.root):
            demo = studio_ui.build_demo(FixtureStudio())

        def callback(name):
            for block in demo.fns.values():
                function = block.fn.func if isinstance(block.fn, partial) else block.fn
                if function and function.__name__ == name:
                    return block.fn
            raise AssertionError(name)

        event = gr.SelectData(None, {"index": 0, "selected": True, "value": None})
        choose = callback("choose_gallery")
        selection = choose(["fixture"], event)
        self.assertEqual(len(selection), 13)
        self.assertTrue(selection[10]["interactive"])  # Albedo
        self.assertFalse(selection[12]["interactive"])  # No AO
        show = callback("show_texture")
        texture = show.func("fixture", channel="albedo")
        self.assertFalse(texture[0]["visible"])
        self.assertTrue(texture[1]["visible"])
        self.assertEqual(texture[3]["variant"], "primary")
        selected_refresh = callback("refresh").__closure__
        refresh = next(cell.cell_contents for cell in selected_refresh
                       if callable(cell.cell_contents) and cell.cell_contents.__name__ == "selected_refresh")
        self.assertTrue(all(update == gr.skip() for update in refresh("fixture", selection[6])))
        self.assertEqual(choose(["fixture"], event)[8]["visible"], "hidden")
        self.assertTrue(show.func("fixture", channel="3d")[0]["visible"])
        model.update(status="running", stage="export", output=str(self.root), error=None)
        processing = choose(["fixture"], event)
        self.assertEqual(processing[8]["visible"], "hidden")
        self.assertIsNone(processing[8]["value"])
        self.assertTrue(all(not update["interactive"] for update in processing[9:]))
        self.assertEqual(len(choose([], event)), 13)
        self.assertEqual(len(callback("choose_image")([], event)), 15)


if __name__ == "__main__":
    unittest.main()
