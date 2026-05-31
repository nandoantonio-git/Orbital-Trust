#!/usr/bin/env python3
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from iot.pipeline import run_pipeline


def main() -> None:
    root = Path(__file__).parent.parent
    output_path = root / "data" / "payloads_BR-MT-001.json"
    payloads = run_pipeline(str(root / "data"), "BR-MT-001", "Sentinel-2")
    output_path.write_text(
        json.dumps(payloads, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Generated {output_path} with {len(payloads)} payloads")


if __name__ == "__main__":
    main()
