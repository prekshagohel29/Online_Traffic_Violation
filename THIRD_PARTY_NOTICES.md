# Third-party provenance

- Original project: https://github.com/prekshagohel29/traffic_violation_system,
  base `77e5dff4699c7514ac13d43149acc019da57b203`. No new licence is asserted over
  the friend's original work. Review repository rights before public distribution.
- React / React DOM / React Router: MIT; original package notices remain in npm
  dependencies/build licence output. React is the only frontend framework used.
- Flask / Werkzeug: BSD-3-Clause; SQLAlchemy: MIT; HTTPX: BSD-3-Clause.
- OpenCV Zoo YOLOX model and YOLOX implementation provenance: Apache-2.0,
  https://github.com/opencv/opencv_zoo/tree/main/models/object_detection_yolox and
  https://github.com/Megvii-BaseDetection/YOLOX. Preserve model-directory licence
  and attribution on redistribution. Weight SHA/source in ASSET_MANIFEST.json.
- OpenCV runtime: Apache-2.0; Tesseract: Apache-2.0 (optional Windows dependency,
  installed in the prepared container image).
- Prerecorded sample: Taurus Media Technik, Munich rush hour, CC0; source and
  checksums in MODEL_SETUP.md/ASSET_MANIFEST.json. No identifiable owner is inferred.
- AI City Challenge specialist data is NOT included, downloaded, trained on or
  sublicensed. Its access/licence terms need explicit review before use.

Dependency package licence files and `frontend/build/static/js/*.LICENSE.txt`
should accompany redistribution. No Ultralytics code/AGPL weights were added.

## Additional models and showcase data

- Intel Open Model Zoo vehicle-license-plate-detection-barrier-0106, Apache-2.0:
  https://github.com/openvinotoolkit/open_model_zoo/tree/master/models/intel/vehicle-license-plate-detection-barrier-0106.
  OpenVINO runtime is Apache-2.0. Exact detector sources, official SHA-384 and
  downloaded SHA-256 are retained by scripts/fetch_plate_models.py and
  models/plates/manifest.json; license text is included alongside the models.
- fast-plate-ocr/CCT-XS v2 global, MIT:
  https://github.com/ankandrew/fast-plate-ocr. ONNX Runtime is MIT. Included plate
  example photo originates in the MIT fast-alpr repository's assets/test_image.png;
  only the photo is used, not its separately licensed detector weights.
- Bike Helmet Detection dataset: original supplied notice credits Syed Salman
  Reza (https://github.com/syed-reza98), Roboflow source
  https://universe.roboflow.com/vehicle-tracking-wxxxy/bike-helmet-detection-2vdjo-dki1r,
  and declares Public Domain. The cute-face Hugging Face mirror declares CC BY 4.0:
  https://huggingface.co/datasets/cute-face/bike-helmet-dataset.
  Preserve all three included README notices, dataset links and the pinned revision
  in samples/showcase/manifest.json. Twelve images are included unchanged; four
  additional traffic frames are extracted from the separately attributed CC0 clip.
- The educational HOG/logistic head classifier was trained in this project using
  published boxes from the pinned helmet dataset; training recipe, measured limits
  and dataset attribution accompany its small NPZ weights. Overlay images are
  annotated derivatives for comparison, not original source labels or identifications.

No government personal records were obtained. All demonstration owner/vehicle
associations are fictional. Dataset imagery is not evidence identifying its subjects
as the fictional account holders.
