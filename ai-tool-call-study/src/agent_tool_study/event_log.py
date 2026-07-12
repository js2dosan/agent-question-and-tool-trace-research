from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict


class EventLogger:
    def __init__(self, path: Path, trial_id: str) -> None:
        self.path = path
        self.trial_id = trial_id
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event_type: str, **payload: Any) -> None:
        event: Dict[str, Any] = {
            "trial_id": self.trial_id,
            "event_type": event_type,
            "timestamp_unix": time.time(),
            **payload,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
