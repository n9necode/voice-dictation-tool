#!/usr/bin/env python3
"""MCP stdio server for the Voice Dictation Tool plugin."""

from __future__ import annotations

import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT))

from voice_dictation_tool.mcp_server import serve  # noqa: E402

if __name__ == "__main__":
    serve()
