from pathlib import Path
import pytest
import cv2

@pytest.mark.skipif(not Path('models/plates/manifest.json').exists(),reason='Run scripts.fetch_plate_models first')
def test_real_neural_ocr_with_explicit_manual_crop():
    from backend.plates import PlateReader
    reader=PlateReader();assert reader.ready,reader.error
    image=cv2.imread('samples/plate-example.png')
    # This known test crop is manually annotated. It does not test localization accuracy.
    crop=cv2.cvtColor(image[180:218,300:405],cv2.COLOR_BGR2RGB)
    result=reader.ocr.run_one(crop,return_confidence=True)
    assert result.plate=='5AU5341'
    assert len(result.char_probs)>=len(result.plate)
    readings,crops=reader.read(image)
    assert len(readings)==len(crops)
    assert all(r['status']=='unreviewed_suggestion' for r in readings)
