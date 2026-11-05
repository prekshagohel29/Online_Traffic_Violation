import pytest
from backend.camera_sources import validate_sources
def test_gateway_allowlist_accepts_only_fixed_rtsp_destinations():
    assert validate_sources('{"junction":"rtsp://192.168.1.50:554/authorized"}')['junction'].startswith('rtsp:')
    for url in ['http://169.254.169.254/latest/meta-data','rtsp://169.254.169.254/','rtsp://127.0.0.1/','rtsp://camera.example.com/','https://192.168.1.50/redirect','rtsp://[::1]/','rtsp://224.0.0.1/']:
        import json
        with pytest.raises(ValueError): validate_sources(json.dumps({'bad':url}))
