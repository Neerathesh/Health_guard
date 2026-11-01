"""Saves everything in one small JSON file next to the app (or where HEALTHGUARD_DATA points)."""
import copy
import json
import os
from pathlib import Path

DEFAULT = {
    "profile": {
        "onboarded": False,
        "name": "",
        "age": "",
        "blood_group": "",
        "step_goal": 8000,
        "water_goal": 8,
        "location": "",
        "sample": False,
    },
    "contacts": [],      # {"name": str, "phone": str}
    "vitals": [],        # {"ts": iso, "hr": int|None, "spo2": int|None, "steps": int|None, "sleep_min": int|None}
    "logs": [],          # {"ts": iso, "type": "BP"|"Weight"|"Sugar", "value": str}
    "medicines": [],     # {"id": int, "name": str, "dose": str, "time": "HH:MM"}
    "taken": {},         # {"YYYY-MM-DD": [medicine ids]}
    "water": {},         # {"YYYY-MM-DD": glasses}
}


def _path() -> Path:
    custom = os.environ.get("HEALTHGUARD_DATA")
    return Path(custom) if custom else Path(__file__).with_name("healthguard_data.json")


def load() -> dict:
    data = copy.deepcopy(DEFAULT)
    p = _path()
    if p.exists():
        try:
            saved = json.loads(p.read_text(encoding="utf-8"))
            for key, value in saved.items():
                if key == "profile" and isinstance(value, dict):
                    data["profile"].update(value)
                elif key in data:
                    data[key] = value
        except (json.JSONDecodeError, OSError):
            pass  # unreadable file: start fresh instead of crashing
    return data


def save(data: dict) -> None:
    p = _path()
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(p)
