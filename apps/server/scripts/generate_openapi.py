from __future__ import annotations

import json
from pathlib import Path

from task_orchestrator.api.app import app

OUTPUT_PATH = Path(__file__).resolve().parents[3] / "docs" / "api" / "openapi.json"


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT_PATH.relative_to(Path.cwd().parents[1])}")


if __name__ == "__main__":
    main()
