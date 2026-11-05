"""Small Intel Apache-2.0 plate detector + MIT global OCR model, kept project-local."""

import hashlib, json, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fetch(url, path, sha384=None):
    if path.exists():
        data = path.read_bytes()
    else:
        with urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": "Preksha-project/2.0"}),
            timeout=90,
        ) as r:
            data = r.read(50 * 1024 * 1024)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    if sha384 and hashlib.sha384(data).hexdigest() != sha384:
        raise RuntimeError("Intel model checksum mismatch")
    return {
        "file": path.relative_to(ROOT).as_posix(),
        "url": url,
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }


def main():
    path = ROOT / "models/plates"
    path.mkdir(parents=True, exist_ok=True)
    items = []
    base = "https://storage.openvinotoolkit.org/repositories/open_model_zoo/2023.0/models_bin/1/vehicle-license-plate-detection-barrier-0106/FP32/"
    for ext, checksum in [
        (
            "xml",
            "5467807d2432f717edc7d1d121399c3bc62f483a8b7a444be844a2415a1a036979cff8fc652b6ab1e692d62ff6723c6e",
        ),
        (
            "bin",
            "4bc69a94aeab8c9141c1531e13bdd93224ba1048602d8f80c697f4e376700569677cd72e4a75c7e9dc2dbccef61582e2",
        ),
    ]:
        name = "vehicle-license-plate-detection-barrier-0106." + ext
        items.append(fetch(base + name, path / name, checksum))
    from fast_plate_ocr.inference.hub import download_model, AVAILABLE_ONNX_MODELS

    model, config = download_model("cct-xs-v2-global-model", save_directory=path)
    for p, url in zip([model, config], AVAILABLE_ONNX_MODELS["cct-xs-v2-global-model"]):
        items.append(fetch(url, p))
    items.append(
        fetch(
            "https://raw.githubusercontent.com/openvinotoolkit/open_model_zoo/master/LICENSE",
            path / "LICENSE-INTEL.txt",
        )
    )
    items.append(
        fetch(
            "https://raw.githubusercontent.com/ankandrew/fast-plate-ocr/master/LICENSE",
            path / "LICENSE-OCR.txt",
        )
    )
    sample = ROOT / "samples/plate-example.png"
    try:
        items.append(
            fetch(
                "https://raw.githubusercontent.com/ankandrew/fast-alpr/master/assets/test_image.png",
                sample,
            )
        )
    except Exception:
        pass
    (path / "manifest.json").write_text(json.dumps(items, indent=2))
    print(json.dumps({"assets": len(items), "directory": str(path)}))


if __name__ == "__main__":
    main()
