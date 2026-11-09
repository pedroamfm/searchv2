import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def save_json(data: Any, directory: str | Path, prefix: str) -> Path:
    target_directory = Path(directory)
    target_directory.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = target_directory / f"{prefix}_{timestamp}.json"
    filename.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return filename
