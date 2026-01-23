from __future__ import annotations

import json
from pathlib import Path


def write_fnet(fnet: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(fnet, indent=2, sort_keys=True) + "\n")

