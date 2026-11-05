"""Measured smoke benchmark; not a labeled recognition-accuracy evaluation."""

import json, platform, os, time, statistics
from pathlib import Path
import cv2
from backend.vision import Detector, MODEL_VERSION
from backend.rules import Tracker


def main():
    cpu = platform.processor()
    if os.name == "nt":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            ) as key:
                cpu = winreg.QueryValueEx(key, "ProcessorNameString")[0]
        except OSError:
            pass
    detector = Detector("models/yolox.onnx")
    if not detector.ready:
        raise RuntimeError(detector.error)
    cap = cv2.VideoCapture("samples/rush-hour.webm")
    tracker = Tracker()
    timings = []
    counts = []
    rows = []
    seen = set()
    next_sample = 0
    start = time.perf_counter()
    while True:
        ok, im = cap.read()
        if not ok:
            break
        stamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
        if stamp < next_sample:
            continue
        next_sample = stamp + 0.5
        before = time.perf_counter()
        detections = detector.detect(im)
        elapsed = (time.perf_counter() - before) * 1000
        tracks = tracker.update(detections, stamp)
        for tr in tracks:
            seen.add(tr["id"])
        timings.append(elapsed)
        counts.append(len(detections))
        rows.append(
            {
                "source_seconds": stamp,
                "detections": len(detections),
                "tracks": len(tracks),
                "inference_ms": round(elapsed, 2),
            }
        )
        if len(rows) == 1:
            from backend.vision import annotate

            Path("artifacts").mkdir(exist_ok=True)
            cv2.imwrite(
                "artifacts/real-inference-sample.jpg",
                annotate(im, tracks, {}, stamp, 0),
            )
    cap.release()
    report = {
        "kind": "Unlabeled single-scene inference smoke benchmark; not event accuracy",
        "platform": platform.platform(),
        "python": platform.python_version(),
        "opencv": cv2.__version__,
        "cpu": cpu,
        "logical_cpus": os.cpu_count(),
        "configured_cv_threads": cv2.getNumThreads(),
        "model": MODEL_VERSION,
        "sample": "samples/rush-hour.webm",
        "sampled_frames": len(rows),
        "total_detections": sum(counts),
        "unique_track_ids": len(seen),
        "mean_inference_ms": round(statistics.mean(timings), 2),
        "median_inference_ms": round(statistics.median(timings), 2),
        "p95_inference_ms": round(sorted(timings)[int(0.95 * (len(timings) - 1))], 2),
        "measured_inference_fps": round(len(rows) / (sum(timings) / 1000), 2),
        "whole_run_seconds": round(time.perf_counter() - start, 2),
        "precision": None,
        "recall": None,
        "ocr_exact_match": None,
        "limitations": "No held-out labeled event/OCR corpus; sample is Munich traffic, not Indian registration evaluation",
        "frames": rows,
    }
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/inference-report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "frames"}, indent=2))


if __name__ == "__main__":
    main()
