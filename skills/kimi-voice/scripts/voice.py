#!/usr/bin/env python3
"""Skill entry point. A JSON object on stdin runs one tool; otherwise talk."""

from __future__ import annotations

import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT))

from kimi_voice.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
