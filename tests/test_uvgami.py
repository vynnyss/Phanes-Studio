"""UV-only correspondence and queue/API rules in a disposable workspace."""
import hashlib
import gc
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import studio_service as service
from studio_api import create_api
from uvgami_transfer import transfer_uv


class UvgamiTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(gc.collect)
        self.root = Path(temporary.name)

    def test_corner_transfer_accepts_seam_duplicates_without_moving_originals(self):
        positions = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=float)
        faces = np.array([[0, 1, 2]])
        obj = self.root / "result.obj"
        obj.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 0\n"
                       "vt 0 0\nvt 1 0\nvt 0 1\nf 3/3 4/1 2/2\n", encoding="utf-8")
        original = positions.copy()
        uv, report = transfer_uv(positions, faces, obj)
        np.testing.assert_array_equal(positions, original)
        np.testing.assert_array_equal(uv, [[[0, 0], [1, 0], [0, 1]]])
        self.assertTrue(report["all_original_triangles_matched"])
        obj.write_text(obj.read_text(encoding="utf-8").replace("v 1 0 0", "v 2 0 0"), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "moved"):
            transfer_uv(positions, faces, obj)

    def test_missing_triangles_and_invalid_uv_indices_are_rejected(self):
        positions = np.eye(3)
        faces = np.array([[0, 1, 2]])
        obj = self.root / "result.obj"
        obj.write_text("v 1 0 0\nv 0 1 0\nv 0 0 1\nvt 0 0\nf 1/1 2/1 3/4\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "indices"):
            transfer_uv(positions, faces, obj)
        with self.assertRaisesRegex(ValueError, "incomplete"):
            transfer_uv(positions, np.vstack([faces, faces]), obj)

    def test_queue_import_review_and_api_preserve_relationships(self):
        data = self.root / "local_data/studio"
        engine = self.root / "engine.exe"
        engine.write_bytes(b"fixture")
        with patch.multiple(service, ROOT=self.root, DATA=data, DB=data / "studio.db", UVGAMI=engine):
            studio = service.Studio()  # No executor is started by unit tests.
            directory = self.root / "outputs/low"
            directory.mkdir(parents=True)
            model = directory / "model.glb"
            model.write_bytes(struct.pack("<4sII", b"glTF", 2, 20) + b"12345678")
            (directory / "optimized.blend").write_bytes(b"fixture-scene")
            studio.add_variant("low", "asset", "high", "LOW", "low", model, None, None, None)
            studio.add_variant("other", "other-asset", None, "Other", "low", model, None, None, None)
            studio.add_variant("high", "asset", None, "HIGH", "high", model, None, None, None)
            api = TestClient(create_api(studio))
            self.addCleanup(api.close)
            payload = {"variant_id": "low", "texture": 1024, "request_key": "uv-first"}
            first = api.post("/api/jobs/unwrap", json=payload)
            self.assertEqual(first.status_code, 200, first.text)
            identifier = first.json()["job_id"]
            self.assertEqual(api.post("/api/jobs/unwrap", json=payload).json()["job_id"], identifier)
            self.assertEqual(api.post("/api/jobs/unwrap", json=dict(payload, variant_id="other")).status_code, 400)
            self.assertEqual(api.post("/api/jobs/unwrap", json=dict(payload, texture=2048)).status_code, 400)
            self.assertEqual(api.post("/api/jobs/unwrap", json={"variant_id": "high"}).status_code, 400)
            job = studio.job(identifier)
            self.assertEqual(job["kind"], "unwrap")
            self.assertEqual(job["parent_id"], "low")
            self.assertEqual(Path(job["input"]).name, "optimized.blend")
            command = studio.command(job)
            self.assertIn("--engine", command)
            self.assertNotIn("--triangles", command)
            result = self.root / "outputs/result"
            result.mkdir()
            (result / "model.glb").write_bytes(model.read_bytes())
            metadata = {
                "result": "completed", "method": "uvgami-optcuts", "geometry_unchanged": True,
                "transfer": {"all_original_triangles_matched": True},
                "protected_file_hashes": {str(model): hashlib.sha256(model.read_bytes()).hexdigest()},
            }
            (result / "report.json").write_text(json.dumps(metadata), encoding="utf-8")
            imported = api.post("/api/models/import-unwrap", json={"variant_id": "low", "directory": str(result)})
            self.assertEqual(imported.status_code, 200, imported.text)
            variant = imported.json()
            self.assertEqual((variant["asset_id"], variant["parent_id"], variant["kind"]), ("asset", "low", "low"))
            self.assertEqual(variant["quality_status"], "unreviewed")
            review = api.post(f"/api/models/{variant['id']}/review", json={"state": "approved", "reason": "Explicit fixture decision"})
            self.assertEqual(review.json()["quality_status"], "approved")
            again = studio.import_unwrap("low", result)
            self.assertEqual(again["quality_status"], "approved")
            self.assertEqual(studio.variant("low")["quality_status"], "unreviewed")
            self.assertEqual(api.post(f"/api/models/{variant['id']}/review", json={"state": "approved", "reason": ""}).status_code, 400)
            self.assertEqual(api.post("/api/models/import-unwrap", json={"variant_id": "low", "directory": str(self.root.parent)}).status_code, 400)
            studio.review_variant("low", "rejected", "Explicit fixture rejection")
            self.assertEqual(api.post("/api/jobs/unwrap", json={"variant_id": "low"}).status_code, 400)
            studio.cancel(identifier)
            self.assertEqual(studio.job(identifier)["status"], "cancelled")


if __name__ == "__main__":
    unittest.main()
