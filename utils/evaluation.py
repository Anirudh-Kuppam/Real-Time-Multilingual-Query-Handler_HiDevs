import json
from pathlib import Path


DATA_FILE = Path("data/evaluations.json")
DATA_FILE.parent.mkdir(parents=True, exist_ok=True)


# Basic local storage for demo purposes
def save_evaluation(entry: dict):
    data = []
    if DATA_FILE.exists():
        try:
            data = json.loads(DATA_FILE.read_text())
        except Exception:
            data = []
    data.append(entry)
    DATA_FILE.write_text(json.dumps(data, indent=2))


def load_evaluations():
    if not DATA_FILE.exists():
        return []
    return json.loads(DATA_FILE.read_text())