# Voice Dictation Tool

A Python voice plugin for the Kimi K3 model. You talk, it listens, streams a short reply from `kimi-k3`, and speaks it back.

The microphone and speaker stay on your machine. Moonshot only receives the transcript. Kimi K3 has no speech API, so this plugin adds the voice loop around the [chat completions endpoint](https://platform.kimi.ai/docs/api/chat).

The same folder is a Kimi Code plugin and a downloadable skill.

## Setup

```powershell
cd C:\Users\newleaf888\kimi-voice
copy .env.example .env
```

Put your Moonshot key in `MOONSHOT_API_KEY` inside `.env`. The plugin loads `.env` automatically (existing environment variables win):

```text
MOONSHOT_API_KEY=your-key
```

Optional: set `KIMI_LANG` to a BCP-47 tag (e.g. `zh-CN`) to select the speech language. Leave it empty to use the system default voice.

## Talk

```powershell
python skills/voice-dictation-tool/scripts/voice.py
```

Typed conversation, no microphone:

```powershell
python skills/voice-dictation-tool/scripts/voice.py --text
```

Say **stop**, **quit**, or **goodbye** to end.

## Install in Kimi Code

```text
/plugins install C:\Users\newleaf888\kimi-voice
/reload
/skill:voice-dictation-tool
```

Or `/voice-dictation-tool:talk` to start a spoken turn.

Build a zip you can hand someone:

```powershell
$env:PYTHONPATH = "skills/voice-dictation-tool"
python -m voice_dictation_tool.pack
```

That writes `dist/voice-dictation-tool.zip`. Install the unzipped folder with `/plugins install`, or copy `skills/voice-dictation-tool` to `~/.kimi/skills/voice-dictation-tool`.

## Tests

```powershell
python -m unittest discover -s tests -v
```

## What the loop does

1. Listen with the Windows speech recognizer (or read a typed line).
2. Send the transcript to `kimi-k3` with streaming on and `reasoning_effort` set to `low`.
3. Speak each finished sentence as it arrives. Reasoning text is kept for the next turn and is not spoken.
4. Repeat until you say stop.
