"""Fetch exact public model and permitted sample footage; verify before installation."""

import hashlib, urllib.request, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = [
    (
        "models/LICENSE-YOLOX.txt",
        "https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/object_detection_yolox/LICENSE",
        "sha256",
        "0ec3668d3274bcf29e8a29e9576d5a2cd96fc78d3c5bec4387355a796e5d9088",
    ),
    (
        "models/yolox.onnx",
        "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/object_detection_yolox/object_detection_yolox_2022nov.onnx",
        "sha256",
        "c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063",
    ),
    (
        "samples/rush-hour.webm",
        "https://upload.wikimedia.org/wikipedia/commons/a/a3/Video_Codec_Test_rush_hour_1080p25.y4m.webm",
        "sha1",
        "a80ae4df93bc2b24004ca1f850e4b1e3e666a603",
    ),
]


def main():
    manifest = []
    for relative, url, algorithm, expected in ASSETS:
        path = ROOT / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and (
            expected is None
            or hashlib.new(algorithm, path.read_bytes()).hexdigest() == expected
        ):
            print("Verified", relative)
        else:
            print("Downloading", relative)
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Preksha-Project/1.0 (educational local video inference)"
                },
            )
            with urllib.request.urlopen(req, timeout=90) as response:
                data = response.read(60 * 1024 * 1024)
            if expected and hashlib.new(algorithm, data).hexdigest() != expected:
                raise RuntimeError(f"Checksum failed: {relative}")
            path.write_bytes(data)
        manifest.append(
            {
                "file": relative,
                "url": url,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "bytes": path.stat().st_size,
            }
        )
    (ROOT / "ASSET_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
