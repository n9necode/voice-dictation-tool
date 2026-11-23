"""Tool entry points shared by the CLI, the skill script, and MCP."""

from __future__ import annotations

from voice_dictation_tool.client import KimiClient
from voice_dictation_tool.config import Settings
from voice_dictation_tool.errors import ConfigError, KimiVoiceError
from voice_dictation_tool.session import converse
from voice_dictation_tool.speech import LineListener, ListSpeaker, default_listener, default_speaker
from voice_dictation_tool.stream import new_history

TOOLS = ("listen", "speak", "ask", "converse")


def dispatch(payload: dict, *, client=None, listener=None, speaker=None, env=None) -> dict:
    if not isinstance(payload, dict):
        return {"ok": False, "error": "Tool input must be a JSON object."}
    name = payload.get("tool")
    if name not in TOOLS:
        return {
            "ok": False,
            "error": f"Unknown tool {name!r}. Use one of {', '.join(TOOLS)}.",
        }
    try:
        return _run(name, payload, client=client, listener=listener, speaker=speaker, env=env)
    except KimiVoiceError as exc:
        return {"ok": False, "error": str(exc)}


def _run(name: str, payload: dict, *, client, listener, speaker, env) -> dict:
    if name == "listen":
        ear = listener or default_listener()
        timeout = float(payload.get("timeout", 12))
        return {"ok": True, "text": ear.listen(timeout)}

    if name == "speak":
        text = payload.get("text", "")
        if not str(text).strip():
            raise ConfigError("speak requires text.")
        voice = speaker or default_speaker()
        voice.speak(str(text))
        return {"ok": True, "spoken": True}

    if name == "ask":
        text = str(payload.get("text", "")).strip()
        if not text:
            raise ConfigError("ask requires text.")
        model = client or KimiClient(Settings.from_env(env))
        voice = speaker if speaker is not None else (default_speaker() if payload.get("speak") else ListSpeaker())
        result = converse(
            model,
            LineListener([text]),
            voice,
            new_history(),
            max_turns=1,
        )
        reply = result["turns"][0]["reply"] if result["turns"] else ""
        return {"ok": True, "reply": reply}

    lines = payload.get("lines")
    ear = listener
    if ear is None:
        ear = LineListener(lines) if lines is not None else default_listener()
    voice = speaker or default_speaker()
    model = client or KimiClient(Settings.from_env(env))
    turns = payload.get("turns", 1)
    result = converse(
        model,
        ear,
        voice,
        new_history(),
        max_turns=None if turns is None else int(turns),
    )
    public_turns = [
        {"user": turn["user"], "reply": turn["reply"], "stopped": turn["stopped"]}
        for turn in result["turns"]
    ]
    return {"ok": True, "turns": public_turns}
