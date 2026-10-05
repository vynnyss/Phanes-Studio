"""Read texture previews without changing a model or its source textures."""
import base64
from functools import lru_cache
import hashlib
from io import BytesIO
import json
import logging
from pathlib import Path
import struct
import tempfile
from urllib.parse import unquote, urlsplit

from PIL import Image


TEXTURE_LABELS = {"albedo": "Albedo", "normal": "Normal", "ao": "AO"}
TEXTURE_CSS = """
.texture-toolbar {
    justify-content: flex-end;
    gap: 6px !important;
}
.texture-toolbar > button {
    flex: 0 0 auto !important;
    min-width: 64px !important;
    padding: 6px 12px !important;
}
"""
LOGGER = logging.getLogger(__name__)


def read_glb_index(path):
    """Read JSON and locate binary data, without loading vertex buffers."""
    with path.open("rb") as stream:
        magic, version, length = struct.unpack("<4sII", stream.read(12))
        if magic != b"glTF" or version != 2 or length != path.stat().st_size:
            raise ValueError("Invalid GLB header")
        document = None
        binary = None
        while stream.tell() < length:
            size, kind = struct.unpack("<II", stream.read(8))
            offset = stream.tell()
            if offset + size > length:
                raise ValueError("Invalid GLB chunk")
            if kind == 0x4E4F534A:
                document = json.loads(stream.read(size))
            elif kind == 0x004E4942:
                binary = (offset, size)
                stream.seek(size, 1)
            else:
                stream.seek(size, 1)
        if document is None:
            raise ValueError("GLB JSON is missing")
        return document, binary


def image_bytes(path, document, binary, source):
    if "bufferView" in source:
        view = document["bufferViews"][source["bufferView"]]
        offset = view.get("byteOffset", 0)
        size = view["byteLength"]
        if binary is None or view["buffer"] != 0 or offset < 0 or size < 0 or offset + size > binary[1]:
            raise ValueError("Invalid image buffer view")
        with path.open("rb") as stream:
            stream.seek(binary[0] + offset)
            return stream.read(size)
    uri = source["uri"]
    if uri.startswith("data:"):
        header, data = uri.split(",", 1)
        if not header.endswith(";base64"):
            raise ValueError("Unsupported image data URI")
        return base64.b64decode(data, validate=True)
    parsed = urlsplit(uri)
    if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError("Only local texture files are supported")
    texture_path = (path.parent / unquote(parsed.path)).resolve()
    if not texture_path.is_relative_to(path.parent.resolve()):
        raise ValueError("Texture is outside the model directory")
    return texture_path.read_bytes()


def cache_image(content, channel, cache_directory):
    key = hashlib.sha256(content + channel.encode("ascii")).hexdigest()
    target = cache_directory / (key + ".png")
    if target.is_file():
        return str(target)
    with Image.open(BytesIO(content)) as image:
        # glTF AO occupies R even when sharing an ORM image with other maps.
        preview = image.convert("RGB").getchannel("R") if channel == "ao" else image.convert("RGBA")
        cache_directory.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=cache_directory, suffix=".png", delete=False) as temporary:
            temporary_path = Path(temporary.name)
        try:
            preview.save(temporary_path, format="PNG")
            temporary_path.replace(target)
        finally:
            temporary_path.unlink(missing_ok=True)
    return str(target)


@lru_cache(maxsize=32)
def embedded_maps(model_path, size, modified, cache_path):
    """The GLB stamp invalidates previews when an export is replaced."""
    path = Path(model_path)
    result = {channel: [] for channel in TEXTURE_LABELS}
    try:
        document, binary = read_glb_index(path)
        material_indices = sorted({
            primitive["material"]
            for mesh in document.get("meshes", [])
            for primitive in mesh.get("primitives", [])
            if "material" in primitive
        })
        for index in material_indices:
            material = document["materials"][index]
            name = material.get("name") or f"Material {index + 1}"
            slots = {
                "albedo": material.get("pbrMetallicRoughness", {}).get("baseColorTexture"),
                "normal": material.get("normalTexture"),
                "ao": material.get("occlusionTexture"),
            }
            for channel, slot in slots.items():
                if slot is None:
                    continue
                try:
                    texture = document["textures"][slot["index"]]
                    source = document["images"][texture["source"]]
                    content = image_bytes(path, document, binary, source)
                    preview = cache_image(content, channel, Path(cache_path))
                    if preview not in [item[0] for item in result[channel]]:
                        result[channel].append((preview, name))
                except (OSError, ValueError, KeyError, IndexError) as error:
                    LOGGER.warning("Cannot preview %s in %s: %s", channel, path, error)
    except (OSError, ValueError, KeyError, IndexError, struct.error) as error:
        LOGGER.warning("Cannot read textures from %s: %s", path, error)
    return result


def texture_maps(model_path, cache_directory):
    path = Path(model_path).resolve()
    stamp = path.stat()
    result = {
        channel: list(items)
        for channel, items in embedded_maps(str(path), stamp.st_size, stamp.st_mtime_ns,
                                           str(cache_directory)).items()
    }
    # Bake outputs can retain separate maps that the GLB exporter omitted.
    filenames = {
        "albedo": ("base_color.png", "albedo.png", "base_color_0.png"),
        "normal": ("normal.png",),
        "ao": ("ao.png", "ambient_occlusion.png"),
    }
    for channel, candidates in filenames.items():
        if result[channel]:
            continue
        for filename in candidates:
            source = path.parent / filename
            if not source.is_file() or not source.resolve().is_relative_to(path.parent):
                continue
            try:
                preview = cache_image(source.read_bytes(), channel, Path(cache_directory))
                result[channel].append((preview, TEXTURE_LABELS[channel]))
                break
            except (OSError, ValueError) as error:
                LOGGER.warning("Cannot preview %s: %s", source, error)
    return result
