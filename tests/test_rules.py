import pytest
from backend.rules import validate_config, evaluate, capability, Tracker


def track(points):
    return {
        "id": 1,
        "class": "car",
        "history": [{"p": p, "t": t} for p, t in points],
        "emitted": [],
    }


def base(**kwargs):
    return validate_config(
        {"lane": [[0, 0], [1, 0], [1, 1], [0, 1]], "resolution": [1000, 1000], **kwargs}
    )


def test_no_uncalibrated_speed_or_specialist_rules():
    c = base(enabled=["speeding"])
    assert not next(x for x in capability(c) if x["rule"] == "speeding")["enabled"]
    assert not any(
        x["enabled"]
        for x in capability({})
        if x["rule"] in ("helmet_absence", "triple_riding")
    )
    assert evaluate(track([([0.5, 0.1], 0), ([0.5, 0.9], 1)]), c) == []


def test_red_requires_timestamped_red_and_transition():
    c = base(
        enabled=["red_light"],
        stop_line=[[0, 0.5], [1, 0.5]],
        signal_mode="manual",
        context_confirmed=True,
    )
    moving = track([([0.5, 0.3], 1), ([0.5, 0.7], 1.5)])
    assert evaluate(moving, c, None) == []
    assert evaluate(moving, c, {"state": "green", "timestamp": 0.5}) == []
    assert evaluate(moving, c, {"state": "red", "timestamp": -10}) == []
    assert evaluate(moving, c, {"state": "red", "timestamp": 1.2}) == []
    assert (
        evaluate(moving, c, {"state": "red", "timestamp": 0.5})[0]["rule"]
        == "red_light"
    )
    assert (
        evaluate(
            track([([0.5, 0.6], 1), ([0.5, 0.8], 1.5)]),
            c,
            {"state": "red", "timestamp": 0.5},
        )
        == []
    )


def test_wrong_way_duration_jitter_and_gap():
    c = base(enabled=["wrong_way"], direction=[[0.1, 0.5], [0.9, 0.5]])
    assert (
        evaluate(track([([0.7, 0.5], 0), ([0.5, 0.5], 1), ([0.3, 0.5], 2)]), c)[0][
            "rule"
        ]
        == "wrong_way"
    )
    assert (
        evaluate(track([([0.7, 0.5], 0), ([0.69, 0.5], 1), ([0.7, 0.5], 2)]), c) == []
    )
    assert (
        evaluate(track([([0.7, 0.5], 0), ([0.5, 0.5], 1), ([0.3, 0.5], 10)]), c) == []
    )


def test_restricted_entry_and_duplicate_suppression():
    c = base(
        enabled=["restricted_zone"],
        restricted_zone=[[0.4, 0.4], [1, 0.4], [1, 1], [0.4, 1]],
        context_confirmed=True,
    )
    tr = track([([0.2, 0.6], 0), ([0.6, 0.6], 0.5)])
    assert len(evaluate(tr, c)) == 1
    assert evaluate(tr, c) == []
    assert evaluate(track([([0.6, 0.6], 0), ([0.7, 0.7], 0.5)]), c) == []


def test_stationary_dwell_and_jitter():
    c = base(
        enabled=["no_parking"],
        parking_zone=[[0, 0], [1, 0], [1, 1], [0, 1]],
        parking_excludes_traffic=True,
        dwell_seconds=10,
    )
    tr = track([([0.5, 0.5], 0), ([0.5, 0.5], 1)])
    assert evaluate(tr, c) == []
    for t in range(2, 12):
        tr["history"].append({"p": [0.5001, 0.5001], "t": t})
        events = evaluate(tr, c)
    assert events[0]["rule"] == "no_parking"


def test_calibrated_speed_with_source_times():
    c = base(
        enabled=["speeding"],
        line_a=[[0, 0.3], [1, 0.3]],
        line_b=[[0, 0.7], [1, 0.7]],
        distance_m=20,
        speed_limit=30,
        measurement_validated=True,
    )
    tr = track([([0.5, 0.2], 0), ([0.5, 0.4], 0.5)])
    assert evaluate(tr, c) == []
    tr["history"].append({"p": [0.5, 0.8], "t": 1.5})
    event = evaluate(tr, c)[0]
    assert event["values"]["speed_kmh"] == 72


def test_tracker_expiry_occlusion_and_class_association():
    tracker = Tracker()
    detection = {"class": "car", "confidence": 0.9, "box": [0.1, 0.1, 0.2, 0.2]}
    first = tracker.update([detection], 0)[0]["id"]
    assert tracker.update([], 0.5) == []
    assert tracker.update([detection], 1)[0]["id"] == first
    assert tracker.update([detection], 5)[0]["id"] != first


def test_invalid_calibration():
    for c in (
        {"stop_line": [[0, 0], [0, 0]]},
        {"confidence": float("nan")},
        {"enabled": ["helmet_absence"]},
        {"signal": {"state": "red"}},
    ):
        with pytest.raises(ValueError):
            validate_config(c)
