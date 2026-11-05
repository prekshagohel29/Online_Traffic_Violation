"""Download a small attributed subset of a public dataset, never owner identities."""

import json, hashlib, urllib.request, zipfile, io, struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = "cute-face/bike-helmet-dataset"


def get(url, limit=20 * 1024 * 1024, headers=None):
    req = urllib.request.Request(
        url, headers={"User-Agent": "Preksha-college-demo/2.0", **(headers or {})}
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        content = r.read(limit + 1)
        if len(content) > limit:
            raise RuntimeError("Download exceeds bounded size")
        return content


def main():
    dest = ROOT / "samples" / "showcase"
    dest.mkdir(parents=True, exist_ok=True)
    revision = "29338f31e9985da07bc6992dde0633676c7b6415"
    files = []
    (dest / "repository.json").write_text(
        json.dumps({"revision": revision, "files": files}, indent=2)
    )
    base = f"https://huggingface.co/datasets/{REPO}/resolve/{revision}/"
    for name in ["README.md", "README.dataset.txt", "README.roboflow.txt"]:
        try:
            if not (dest / name).exists():
                (dest / name).write_bytes(get(base + name))
        except Exception:
            pass
    coco = (
        json.loads((dest / "test-annotations.json").read_text())
        if (dest / "test-annotations.json").exists()
        else json.loads(get(base + "test/_annotations.coco.json"))
    )
    (dest / "test-annotations.json").write_text(json.dumps(coco))
    categories = {x["id"]: x["name"] for x in coco["categories"]}
    chosen = []
    for image in coco["images"]:
        annotations = [a for a in coco["annotations"] if a["image_id"] == image["id"]]
        if not annotations:
            continue
        name = image["file_name"]
        url = base + "test/" + urllib.parse.quote(name)
        ident = "helmet-" + str(image["id"])
        path = dest / (ident + ".jpg")
        raw = path.read_bytes() if path.exists() else get(url, 5 * 1024 * 1024)
        path.write_bytes(raw)
        chosen.append(
            {
                "id": ident,
                "title": "Helmet safety dataset · image " + str(image["id"]),
                "category": "helmet_safety",
                "file": path.relative_to(ROOT).as_posix(),
                "source_url": "https://huggingface.co/datasets/" + REPO,
                "download_url": url,
                "revision": revision,
                "license": "CC BY 4.0",
                "attribution": "Syed Salman Reza, Bike Helmet Detection dataset (original declares Public Domain); cute-face/Hugging Face mirror declares CC BY 4.0. Source notices included.",
                "sha256": hashlib.sha256(raw).hexdigest(),
                "annotations": {
                    "image_width": image["width"],
                    "image_height": image["height"],
                    "labels": [
                        {"label": categories[a["category_id"]], "box_xywh": a["bbox"]}
                        for a in annotations
                    ],
                    "basis": "Published dataset annotations; not output of this application",
                },
            }
        )
        if len(chosen) >= 12:
            break
    import cv2

    cap = cv2.VideoCapture(str(ROOT / "samples/rush-hour.webm"))
    for index, seconds in enumerate([1.5, 4, 9, 14]):
        while True:
            ok, image = cap.read()
            if not ok or cap.get(cv2.CAP_PROP_POS_MSEC) >= seconds * 1000:
                break
        if not ok:
            continue
        ident = "traffic-" + str(index + 1)
        path = dest / (ident + ".jpg")
        cv2.imwrite(str(path), image)
        chosen.append(
            {
                "id": ident,
                "title": f"CC0 city traffic · {seconds:g} seconds",
                "category": "road_traffic",
                "file": path.relative_to(ROOT).as_posix(),
                "source_url": "https://commons.wikimedia.org/wiki/File:Video_Codec_Test_rush_hour_1080p25.y4m.webm",
                "license": "CC0",
                "attribution": "Taurus Media Technik, Munich rush-hour test sequence, via Wikimedia Commons",
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "annotations": {
                    "source_time_seconds": seconds,
                    "basis": "Prerecorded traffic frame. Any violation scenario added to this frame is fictional.",
                },
            }
        )
    cap.release()
    (dest / "manifest.json").write_text(json.dumps(chosen, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {"downloaded": len(chosen), "categories": categories, "revision": revision}
        )
    )


if __name__ == "__main__":
    main()
