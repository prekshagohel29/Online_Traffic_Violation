# Models, data and measured limits

## Real vehicle analysis

`python -m scripts.fetch_assets` downloads OpenCV Zoo YOLOX COCO,
`object_detection_yolox_2022nov.onnx`, 35,858,002 bytes, Apache-2.0.
SHA-256: `c5c2d13e59ae883e6af3b45daea64af4833a4951c92d116ec270d9ddbe998063`.
Source: https://github.com/opencv/opencv_zoo/tree/main/models/object_detection_yolox.

OpenCV 5.0.0.93/NumPy 2.5.4 CPU inference uses two threads. Input is 640×640 RGB
with a top-left letterbox; boxes are mapped back to source coordinates. Used
classes: person, bicycle, car, motorcycle, bus and truck. The bounded IoU/centroid
tracker has expiry/occlusion tolerance; fragmented tracks remain a limitation.
No generic object class is treated as a helmet or an offence.

The worker loads/checks models once, evaluates calibrated temporal rules, and
saves private checksummed snapshots plus pending candidates. Plate readings do
not automatically assign an owner. Movement rules require camera geometry and
explicit context, unknown signals disable red-light decisions, and uncalibrated
pixel displacement is never presented as speed. These are experimental rules
requiring human review, not measured field enforcement accuracy.

The CC0 20.114-second Munich clip is by Taurus Media Technik, via Wikimedia:
https://commons.wikimedia.org/wiki/File:Video_Codec_Test_rush_hour_1080p25.y4m.webm.
SHA-256: `bb587147edb58630b0025b1e86cc2bdfe85fc7caf1f2c8f179e4226749963e76`.
Practice zones are deliberate test configuration, not claims of an actual offence.

## Trained plate localization and neural OCR

Run `python -m scripts.fetch_plate_models`. `models/plates/manifest.json` records
the source, bytes and checksum of every model/config/license asset.

- Intel Open Model Zoo `vehicle-license-plate-detection-barrier-0106` FP32 uses
  MobileNetV2+SSD through OpenVINO 2026.4.1, BGR NHWC 300×300 input. Apache-2.0.
  [Official model scope](https://docs.openvino.ai/2023.3/omz_models_model_vehicle_license_plate_detection_barrier_0106.html):
  frontal Chinese barrier-camera views, minimum plate width 96px.
- CCT-XS v2 global OCR via fast-plate-ocr 1.1.0/ONNX Runtime 1.31.1. MIT.
  https://github.com/ankandrew/fast-plate-ocr. RGB plate crops, raw text, normalized
  suggestion, character scores and private crop are preserved for review.
- A manually annotated crop from the included MIT project example reads
  `5AU5341` in the real OCR regression. This checks OCR integration, **not plate
  localization accuracy**. The Intel detector does not reliably localize that
  rear-view sample at the configured threshold; Indian/BH accuracy is unvalidated.
- Low-quality/unreadable readings remain uncertain. An OCR failure cannot fail
  the main traffic job. Optional Tesseract contour OCR is a fallback when the
  neural runtime is unavailable; Windows Tesseract is not required for neural OCR.

Multi-frame plate consensus and a representative Indian/BH exact-match corpus
are still outstanding. Never treat model scores as proof of registration/ownership.

## Public helmet examples and reproducible research training

Dataset: https://huggingface.co/datasets/cute-face/bike-helmet-dataset,
revision `29338f31e9985da07bc6992dde0633676c7b6415`.
Mirror card: CC BY 4.0. Original included notice credits Syed Salman Reza and
declares Public Domain. All notices, attribution and source links are retained
under `samples/showcase/`. COCO labels: `With Helmet`, `Without Helmet`; the
`rider-helmet-bike` parent category is not used as a head label.

`python -m scripts.fetch_showcase` fetches 12 test photographs and extracts four
CC0 traffic frames using decoded timestamps. `manifest.json` records image hashes,
source revision and published annotations. `python -m scripts.seed_showcase`
creates local dataset assets, five fictional vehicle profiles and linked positive,
negative, pending and memo examples. These annotations are not application output;
the example registration/owner association never identifies a pictured person.

`python -m scripts.train_helmet_classifier` reproducibly downloads 240 training,
64 validation and 64 test images, extracts **published head boxes**, computes
64×64 HOG features and trains balanced logistic classification. Training uses
horizontal flips and excludes matching source filenames from held-out splits.
Validation chooses the epoch; test data is not used for model selection. Exact
source-video separation cannot be established from this image-only dataset.

Measured held-out result, positive class `Without Helmet`:

| Training crops (with flips) | Validation | Test | Precision | Recall | Accuracy |
|---:|---:|---:|---:|---:|---:|
| 1,234 | 150 | 186 | 54.7% | 75.8% | 71.0% |

TP 47, FP 39, FN 15, TN 85. Full report/hash:
`artifacts/helmet-classifier-report.json`; weights: `models/helmet-head-classifier.npz`.
This research artifact is retained for reference. The comparison UI and HTTP
endpoint were removed from the college release; it is not loaded by the API.
Scores in the research report are uncalibrated.

This classifier **cannot localize heads, associate riders to motorcycles, or
establish a live helmet offence**. Its false positives are material. Automatic
helmet, triple-riding, seatbelt and phone-use enforcement remain disabled. Completing
them requires suitable view-specific localization/association, temporal positive
evidence, and representative event-level evaluation. Manual review cases remain
available; the capability registry does not silently enable incomplete rules.

## Timing versus accuracy

`python -m scripts.benchmark` measures real detection/tracking timing, not accuracy.
Last YOLOX CPU run: 39 sampled frames, 396 detections, 75 fragmented tracks,
mean 559.49ms/frame, median 552.75ms, p95 615.98ms, 1.79 inference FPS on an
Intel i5-1340P Windows machine. Plate OCR was added later, so this is a vehicle
detector benchmark, not the complete pipeline's OCR-inclusive throughput.
No held-out event-level movement-rule accuracy is claimed.
