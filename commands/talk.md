---
description: Start a spoken conversation with Kimi K3
---

The user wants to talk out loud with Kimi K3. Follow the voice-dictation-tool skill.

Prefer the `voice-dictation-tool` MCP tools (`listen`, `speak`, `ask`, `converse`). If those tools are not available, run `python skills/voice-dictation-tool/scripts/voice.py` from the plugin root and pass one JSON object on stdin.

Speak only the reply. Never read reasoning aloud. End when the user says stop, quit, or goodbye.

$ARGUMENTS
