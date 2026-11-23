import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "skills" / "kimi-voice"
ROOT = Path(__file__).resolve().parents[1]
for entry in (SKILL, ROOT):
    text = str(entry)
    if text not in sys.path:
        sys.path.insert(0, text)
