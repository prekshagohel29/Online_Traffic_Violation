---
license: cc-by-4.0
task_categories:
- object-detection
- image-classification
tags:
- computer-vision
- helmet-detection
- safety-equipment
- bike-helmet
- coco
- pascal-voc
---

# Bike Helmet Detection Dataset

This repository contains multiple computer vision datasets for bike helmet detection.

## 1. Bike Helmet Detection (COCO Format)
- **Location**: Root folders (`train/`, `valid/`, `test/`)
- **Total Images**: 1376
- **Splits**:
  - `train/`: 1185 images and `_annotations.coco.json`
  - `valid/`: 127 images and `_annotations.coco.json`
  - `test/`: 64 images and `_annotations.coco.json`
- **Format**: COCO

## 2. Bikes Helmets Dataset (Pascal VOC Format)
- **Location**: `helmet_voc/` folder
- **Total Images**: 764
- **Format**: Pascal VOC (images under `images/` and xml annotations under `annotations/`)
- **License**: CC BY 4.0

## 3. Google Search Helmet Images
- **Location**: `google_search_helmets/` folder
- **Total Images**: 595
- **Format**: Unannotated images (raw images)
- **License**: Unknown / Web Collection

## 4. Harvested Helmet Images
- **Location**: `harvested_helmets/` folder
- **Total Images**: 4989
- **Format**: Unannotated images (raw images)
- **License**: Unknown / Web Collection (harvested programmatically)

## 5. Harvested Bicycle Helmet Images
- **Location**: `harvested_bicycle_helmets/` folder
- **Total Images**: 62
- **Format**: Unannotated images (raw images)
- **License**: Unknown / Web Collection (harvested programmatically)
