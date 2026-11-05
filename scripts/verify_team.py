"""Check a complete team checkout; only Python's standard library is needed."""

import argparse, hashlib, json
from pathlib import Path


def digest(path):
    raw = path.read_bytes()
    try:
        raw = raw.decode("utf-8").replace("\r\n", "\n").encode()
    except UnicodeDecodeError:
        pass
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--strict", action="store_true", help="Compare original release fingerprints"
    )
    parser.add_argument(
        "--ready",
        action="store_true",
        help="Also require the downloaded detector model",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    spec = root / "integration/team_release.json"
    if not spec.is_file():
        raise SystemExit(
            "Missing integration/team_release.json. Complete the Member 1 upload."
        )
    manifest = json.loads(spec.read_text(encoding="utf-8"))
    errors = []
    for name, expected in manifest["required_files"].items():
        path = (root / name).resolve()
        if not path.is_relative_to(root):
            raise SystemExit("Unsafe path in release manifest")
        if not path.is_file():
            errors.append("Missing " + name)
        elif args.strict and digest(path) != expected:
            errors.append("Changed from release: " + name)
    for asset in manifest["downloaded_assets"]:
        path = root / asset["path"]
        if not path.is_file():
            if args.ready:
                errors.append("Run SETUP_MEMBER.cmd to download " + asset["path"])
            else:
                print(
                    "Setup will download "
                    + asset["path"]
                    + " using the pinned checksum."
                )
        elif hashlib.sha256(path.read_bytes()).hexdigest() != asset["sha256"]:
            errors.append("Model checksum mismatch: " + asset["path"])
    if errors:
        print("\n".join(errors))
        raise SystemExit(1)
    print(
        "All three members' required source/assets are present."
        + (" Release fingerprints match." if args.strict else "")
    )
    if args.ready:
        print("Detector model verified; source/model readiness check passed.")


if __name__ == "__main__":
    main()
