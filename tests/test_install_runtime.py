"""Small installer checks without network, GPU work or personal queue data."""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile, ZipInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from install_runtime import download, extract_archive
from studio_environment import configure_environment


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def archive(self, filename, content=b"fixture"):
        archive = self.root / "fixture.zip"
        with ZipFile(archive, "w") as package:
            package.writestr(filename, content)
        return archive

    def test_extracts_normal_nested_file(self):
        destination = self.root / "installed"
        extract_archive(self.archive("code/hello.txt"), destination)
        self.assertEqual((destination / "code/hello.txt").read_bytes(), b"fixture")

    def test_rejects_escape_before_writing_any_files(self):
        archive = self.root / "fixture.zip"
        with ZipFile(archive, "w") as package:
            package.writestr("normal.txt", b"safe")
            package.writestr("../escaped.txt", b"unsafe")
        with self.assertRaises(ValueError):
            extract_archive(archive, self.root / "installed")
        self.assertFalse((self.root / "escaped.txt").exists())
        self.assertFalse((self.root / "installed/normal.txt").exists())

    def test_rejects_windows_path_and_backslash_escape(self):
        for name in ("C:/escaped.txt", "..\\escaped.txt", "code/file:stream"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                extract_archive(self.archive(name), self.root / "installed")

    def test_rejects_symbolic_link(self):
        archive = self.root / "fixture.zip"
        entry = ZipInfo("linked")
        entry.create_system = 3
        entry.external_attr = (stat.S_IFLNK | 0o777) << 16
        with ZipFile(archive, "w") as package:
            package.writestr(entry, "../outside")
        with self.assertRaises(ValueError):
            extract_archive(archive, self.root / "installed")

    def test_does_not_overwrite_existing_files(self):
        destination = self.root / "installed"
        destination.mkdir()
        existing = destination / "hello.txt"
        existing.write_bytes(b"keep")
        with self.assertRaises(FileExistsError):
            extract_archive(self.archive("hello.txt"), destination)
        self.assertEqual(existing.read_bytes(), b"keep")

    def test_download_verifies_and_reuses_cache(self):
        source = self.root / "source.bin"
        source.write_bytes(b"verified fixture")
        expected = hashlib.sha256(source.read_bytes()).hexdigest()
        destination = self.root / "cache/download.bin"
        download(source.as_uri(), destination, expected)
        source.unlink()
        download(source.as_uri(), destination, expected)
        self.assertEqual(destination.read_bytes(), b"verified fixture")

    def test_rejects_tampered_download(self):
        source = self.root / "source.bin"
        source.write_bytes(b"unexpected")
        destination = self.root / "cache/download.bin"
        with self.assertRaises(ValueError):
            download(source.as_uri(), destination, "0" * 64)
        self.assertFalse(destination.exists())

    def test_rejects_tampered_cached_file(self):
        destination = self.root / "download.bin"
        destination.write_bytes(b"keep for inspection")
        with self.assertRaises(ValueError):
            download("https://invalid.example/unused", destination, "0" * 64)
        self.assertEqual(destination.read_bytes(), b"keep for inspection")

    def test_blender_setting_and_environment_priority(self):
        settings = self.root / "local_data/settings.json"
        settings.parent.mkdir()
        settings.write_text(json.dumps({"blender": "C:/Custom/blender.exe"}), encoding="utf-8")
        with patch.dict(os.environ):
            os.environ.pop("ASSET_BLENDER", None)
            configure_environment(self.root)
            self.assertEqual(os.environ["ASSET_BLENDER"], "C:/Custom/blender.exe")
            os.environ["ASSET_BLENDER"] = "C:/Override/blender.exe"
            configure_environment(self.root)
            self.assertEqual(os.environ["ASSET_BLENDER"], "C:/Override/blender.exe")


if __name__ == "__main__":
    unittest.main()
