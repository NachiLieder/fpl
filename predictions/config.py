import os
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = Path(os.environ.get("PREDICTIONS_DATA_DIR", ROOT / "data" / "predictions"))
