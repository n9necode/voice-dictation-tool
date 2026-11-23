---
name: kimi-voice
description: Spoken conversation with the Kimi K3 model. Listens through the microphone, streams a short reply from kimi-k3, and speaks it back. Use when the user wants to talk out loud, dictate, hear a reply, or install the Voice Dictation Tool skill.
---

# Voice Dictation Tool

Talk with Kimi K3 the way you would talk with a person. Speech stays on this machine. Only the transcript goes to the Moonshot API.

## Setup

Set `MOONSHOT_API_KEY`. The model is `kimi-k3`. Voice replies use `reasoning_effort=low` so they start quickly.

Optional: `KIMI_MODEL`, `KIMI_REASONING_EFFORT` (`low`, `high`, `max`), `MOONSHOT_BASE_URL`, `KIMI_TIMEOUT`.

## Talk

From the plugin root:

```bash
python skills/kimi-voice/scripts/voice.py
```

Type instead of using the microphone:

```bash
python skills/kimi-voice/scripts/voice.py --text
```

Say "stop", "quit", or "goodbye" as the whole utterance to end.

## Tools

Use the `kimi-voice` MCP tools when they are available. Otherwise pass one JSON object to the script. On PowerShell:

```powershell
'{"tool":"ask","text":"What is 1+1?","speak":true}' | python skills/kimi-voice/scripts/voice.py
```

| Tool | Input | Result |
| --- | --- | --- |
| `listen` | `{"timeout": 12}` | transcript, not sent to Kimi yet |
| `speak` | `{"text": "..."}` | plays that text |
| `ask` | `{"text": "...", "speak": true}` | one kimi-k3 reply |
| `converse` | `{"turns": 1}` or `{"lines": ["hello", "stop"]}` | listen, reply, speak |

Speak the reply only. Never speak `reasoning_content` or the API key. Keep replies to one or two spoken sentences unless the user asks for more.

## Install

Kimi Code: `/plugins install` this folder, then `/reload`. Load it with `/skill:kimi-voice` or `/kimi-voice:talk`.

Skill download: unzip `dist/kimi-voice.zip` and install that folder the same way. Copy `skills/kimi-voice` to `~/.kimi/skills/kimi-voice` if you only need the skill files.
