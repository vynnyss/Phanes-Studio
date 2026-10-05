"""Install the pinned external OptCuts engine and retain its license files."""
import json
import sys

from install_runtime import ROOT, SOURCES, download, extract_archive, file_hash


def install():
    source = SOURCES["uvgami"]
    destination = ROOT / "runtime/tools/uvgami-v2.1.0/optcuts"
    executable = destination / "bin/optcuts.exe"
    if not executable.is_file():
        archive = ROOT / "runtime/cache/setup/optcuts-engine-1.21.9-windows.zip"
        download(source["url"], archive, source["sha256"])
        extract_archive(archive, destination)
    if file_hash(executable) != source["binary_sha256"]:
        raise ValueError("Motor OptCuts diferente da versão validada; instalação preservada")
    if not (destination / "LICENSE.txt").is_file() or not (destination / "licenses/GPL-3.0.txt").is_file():
        raise ValueError("Licenças do motor UVgami ausentes")
    return {"engine": str(executable), "version": source["engine_version"], "verified": True}


if __name__ == "__main__":
    try:
        print(json.dumps(install(), ensure_ascii=False))
    except Exception as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
