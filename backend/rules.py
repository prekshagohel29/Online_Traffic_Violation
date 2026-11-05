"""Experimental, calibrated movement rules. No pixel-only speed or inferred signals."""

import math
from copy import deepcopy

RULES = [
    "wrong_way",
    "restricted_zone",
    "red_light",
    "speeding",
    "no_parking",
    "stop_line",
]
CLASSES = ["person", "bicycle", "car", "motorcycle", "bus", "truck"]


def number(value, low, high, label):
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not low <= value <= high
    ):
        raise ValueError(f"{label} must be between {low} and {high}")
    return value


def points(value, count, label):
    if not isinstance(value, list) or len(value) != count:
        raise ValueError(f"{label} requires {count} points")
    for p in value:
        if not isinstance(p, list) or len(p) != 2:
            raise ValueError("Each point needs x,y")
        for v in p:
            number(v, 0, 1, label)
    if count == 2 and math.dist(*value) < 0.01:
        raise ValueError("Line is too short")
    return value


def validate_config(raw):
    if not isinstance(raw, dict):
        raise ValueError("Configuration must be an object")
    c = deepcopy(raw)
    for key in ("stop_line", "line_a", "line_b", "direction"):
        if c.get(key):
            points(c[key], 2, key)
    for key in ("lane", "restricted_zone", "parking_zone"):
        if c.get(key):
            if not 3 <= len(c[key]) <= 20:
                raise ValueError(f"{key} needs 3–20 points")
            points(c[key], len(c[key]), key)
    defaults = {
        "min_duration": 2,
        "min_displacement": 0.08,
        "max_gap": 1.5,
        "dwell_seconds": 30,
        "stationary_radius": 0.015,
        "distance_m": 0,
        "speed_limit": 50,
        "confidence": 0.45,
        "signal_tolerance": 0.3,
        "signal_max_age": 2,
        "crossing_direction": 1,
    }
    ranges = {
        "min_duration": (0.5, 30),
        "min_displacement": (0.01, 1),
        "max_gap": (0.1, 5),
        "dwell_seconds": (10, 3600),
        "stationary_radius": (0.001, 0.1),
        "distance_m": (0, 1000),
        "speed_limit": (1, 200),
        "confidence": (0.1, 0.95),
        "signal_tolerance": (0, 3),
        "signal_max_age": (0.1, 10),
        "crossing_direction": (-1, 1),
    }
    for key, default in defaults.items():
        c[key] = number(c.get(key, default), *ranges[key], key)
    if c["crossing_direction"] not in (-1, 1):
        raise ValueError("Crossing direction must be -1 or 1")
    enabled = c.get("enabled", [])
    if not isinstance(enabled, list) or any(x not in RULES for x in enabled):
        raise ValueError("Unknown rule")
    c["enabled"] = enabled
    if c.get("classes") and (
        not isinstance(c["classes"], list)
        or any(x not in CLASSES for x in c["classes"])
    ):
        raise ValueError("Unsupported class")
    for flag in (
        "context_confirmed",
        "parking_excludes_traffic",
        "measurement_validated",
    ):
        if flag in c and not isinstance(c[flag], bool):
            raise ValueError(f"{flag} must be true/false")
    if c.get("signal_mode", "unknown") not in ("unknown", "manual"):
        raise ValueError("Only timestamped manual signals are available")
    if "signal" in c:
        raise ValueError(
            "Signal state is session-scoped; send timestamped observations"
        )
    if c.get("resolution"):
        points_value = c["resolution"]
        if not isinstance(points_value, list) or len(points_value) != 2:
            raise ValueError("Resolution requires width,height")
        for n in points_value:
            number(n, 100, 4096, "Resolution")
    c["viewpoint"] = str(c.get("viewpoint", ""))[:150]
    return c


def capability(config, model_ready=True):
    c = config or {}
    dependencies = {
        "wrong_way": bool(c.get("lane") and c.get("direction")),
        "restricted_zone": bool(
            c.get("restricted_zone") and c.get("context_confirmed")
        ),
        "red_light": bool(
            c.get("stop_line")
            and c.get("lane")
            and c.get("signal_mode") == "manual"
            and c.get("context_confirmed")
        ),
        "speeding": bool(
            c.get("line_a")
            and c.get("line_b")
            and c.get("distance_m", 0) > 0
            and c.get("measurement_validated")
        ),
        "no_parking": bool(c.get("parking_zone") and c.get("parking_excludes_traffic")),
        "stop_line": bool(
            c.get("stop_line") and c.get("lane") and c.get("context_confirmed")
        ),
    }
    result = []
    for key, ready in dependencies.items():
        ready = ready and bool(c.get("resolution"))
        enabled = key in c.get("enabled", []) and ready and model_ready
        reason = (
            "Model unavailable"
            if not model_ready
            else (
                "Required geometry/context missing"
                if not ready
                else (
                    "Disabled by operator"
                    if not enabled
                    else "Experimental: human review required"
                )
            )
        )
        result.append(
            {
                "rule": key,
                "enabled": enabled,
                "reason": reason,
                "version": "movement-1",
                "thresholds": {
                    k: c.get(k)
                    for k in (
                        "min_duration",
                        "min_displacement",
                        "max_gap",
                        "confidence",
                    )
                },
            }
        )
    for key in ("triple_riding", "seatbelt", "phone_use"):
        result.append(
            {
                "rule": key,
                "enabled": False,
                "reason": "Suitable licensed and evaluated specialist weights not provisioned",
                "version": None,
            }
        )
    result.append(
        {
            "rule": "helmet_absence",
            "enabled": False,
            "reason": "Research head classifier needs published head boxes; live rider association and enforcement accuracy are not established",
            "version": "research-head-1",
        }
    )
    result.append(
        {
            "rule": "plate_detector",
            "enabled": False,
            "reason": "Experimental plate detector/OCR readiness appears in worker health. Arbitrary-camera performance is unvalidated; readings require review",
            "version": "intel-barrier-0106+cct-xs-v2",
        }
    )
    for key in ("drunk_driving", "no_license", "insurance_puc", "overweight"):
        result.append(
            {
                "rule": key,
                "enabled": False,
                "reason": "Manual or authorized external-data workflow only",
                "version": None,
            }
        )
    return result


def inside(p, poly):
    if not poly:
        return False
    x, y = p
    result = False
    for a, b in zip(poly, poly[1:] + poly[:1]):
        if (a[1] > y) != (b[1] > y) and x < (b[0] - a[0]) * (y - a[1]) / (
            b[1] - a[1]
        ) + a[0]:
            result = not result
    return result


def side(p, line):
    a, b = line
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


def crosses(a, b, line, direction=0):
    s1, s2 = side(a, line), side(b, line)
    # Segment intersection, with a directional sign change and jitter margin.
    if abs(s1) < 0.002 or abs(s2) < 0.002 or s1 * s2 >= 0:
        return False
    if direction and not (s1 * direction < 0 and s2 * direction > 0):
        return False
    return side(line[0], [a, b]) * side(line[1], [a, b]) <= 0


def evaluate(track, config, signal=None):
    history = track["history"]
    events = []
    if len(history) < 2 or track["class"] == "person":
        return events
    c = config
    old, new = history[-2], history[-1]
    a, b = old["p"], new["p"]
    t = new["t"]
    if new["t"] - old["t"] > c.get("max_gap", 1.5):
        return events
    enabled = {x["rule"] for x in capability(c) if x["enabled"]}
    if track["class"] not in c.get(
        "classes", ["car", "motorcycle", "bus", "truck", "bicycle"]
    ):
        return []

    def emit(rule, explanation, values):
        if rule not in track.setdefault("emitted", []):
            track["emitted"].append(rule)
            events.append(
                {
                    "rule": rule,
                    "explanation": explanation,
                    "values": values,
                    "source_time": t,
                    "track_id": track["id"],
                }
            )

    if "wrong_way" in enabled and inside(b, c["lane"]):
        recent = [
            h
            for h in history
            if t - h["t"] <= max(10, c["min_duration"] * 2)
            and inside(h["p"], c["lane"])
        ]
        if len(recent) >= 3:
            first = recent[0]
            dx = b[0] - first["p"][0]
            dy = b[1] - first["p"][1]
            d = c["direction"]
            vx = d[1][0] - d[0][0]
            vy = d[1][1] - d[0][1]
            displacement = math.hypot(dx, dy)
            duration = t - first["t"]
            alignment = (dx * vx + dy * vy) / max(
                0.0001, displacement * math.hypot(vx, vy)
            )
            if (
                duration >= c["min_duration"]
                and displacement >= c["min_displacement"]
                and alignment < -0.7
            ):
                emit(
                    "wrong_way",
                    "Tracked movement opposed the configured lane direction over the minimum duration.",
                    {
                        "displacement_normalized": displacement,
                        "duration_seconds": duration,
                        "direction_cosine": alignment,
                    },
                )
    if (
        "restricted_zone" in enabled
        and not inside(a, c["restricted_zone"])
        and inside(b, c["restricted_zone"])
    ):
        emit(
            "restricted_zone",
            "Vehicle entered an operator-configured restricted zone for this class.",
            {"from": a, "to": b, "context_confirmed": True},
        )
    if (
        c.get("stop_line")
        and crosses(a, b, c["stop_line"], c.get("crossing_direction", 1))
        and inside(b, c.get("lane", []))
    ):
        if "stop_line" in enabled:
            emit(
                "stop_line",
                "Vehicle crossed the configured line in the prohibited direction; contextual restriction was enabled by the operator.",
                {"from": a, "to": b},
            )
        if "red_light" in enabled and signal and signal.get("state") == "red":
            stamp = signal.get("timestamp", -999)
            if (
                0 <= t - stamp <= c["signal_max_age"]
                and stamp <= old["t"] - c["signal_tolerance"]
            ):
                emit(
                    "red_light",
                    "Stop-line crossing during a timestamped MANUAL red signal; lane and movement restriction configured.",
                    {"signal": signal, "from": a, "to": b, "manual_signal": True},
                )
    if "speeding" in enabled:
        if crosses(a, b, c["line_a"]):
            track["speed_start"] = t
        if crosses(a, b, c["line_b"]) and "speed_start" in track:
            dt = t - track.pop("speed_start")
            if dt > 0.1:
                speed = c["distance_m"] / dt * 3.6
                if c["speed_limit"] < speed < 200:
                    emit(
                        "speeding",
                        "Measured transit between operator-validated distance lines exceeded the camera limit.",
                        {
                            "speed_kmh": speed,
                            "distance_m": c["distance_m"],
                            "elapsed_seconds": dt,
                            "limit_kmh": c["speed_limit"],
                        },
                    )
    if "no_parking" in enabled:
        if not inside(b, c["parking_zone"]):
            track.pop("stationary", None)
        else:
            anchor = track.setdefault("stationary", {"p": b, "t": t})
            if math.dist(anchor["p"], b) > c["stationary_radius"]:
                track["stationary"] = {"p": b, "t": t}
            elif t - anchor["t"] >= c["dwell_seconds"]:
                emit(
                    "no_parking",
                    "Vehicle remained stationary in a configured prohibited zone beyond its dwell threshold; stopped-traffic exclusion is operator-confirmed.",
                    {"dwell_seconds": t - anchor["t"], "anchor": anchor["p"]},
                )
    return events


class Tracker:
    """Greedy class-aware IoU/centroid association; short occlusion tolerance, no re-ID claim."""

    def __init__(self, state=None):
        self.state = deepcopy(state or {"next": 1, "tracks": []})

    def update(self, detections, t, max_gap=1.5):
        tracks = [
            tr
            for tr in self.state["tracks"]
            if 0 <= t - tr["history"][-1]["t"] <= max_gap
        ]
        unmatched = set(range(len(tracks)))
        active = []
        for det in sorted(detections, key=lambda d: -d["confidence"]):
            x, y, w, h = det["box"]
            p = [x + w / 2, y + h]
            options = []
            for i in unmatched:
                tr = tracks[i]
                if tr["class"] != det["class"]:
                    continue
                tx, ty, tw, th = tr["box"]
                inter = max(0, min(x + w, tx + tw) - max(x, tx)) * max(
                    0, min(y + h, ty + th) - max(y, ty)
                )
                iou = inter / max(0.0001, w * h + tw * th - inter)
                distance = math.dist(p, tr["history"][-1]["p"])
                if iou > 0.1 or distance < 0.08:
                    options.append((iou - distance, i))
            if options:
                _, idx = max(options)
                unmatched.remove(idx)
                tr = tracks[idx]
            else:
                tr = {
                    "id": self.state["next"],
                    "class": det["class"],
                    "history": [],
                    "emitted": [],
                }
                self.state["next"] += 1
            tr.update(box=det["box"], confidence=det["confidence"])
            tr["history"] = (tr["history"] + [{"p": p, "t": t}])[-300:]
            active.append(tr)
        self.state["tracks"] = (active + [tracks[i] for i in unmatched])[:200]
        return active
