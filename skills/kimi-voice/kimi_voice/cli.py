"""Command line for a spoken Kimi K3 session."""

from __future__ import annotations

import argparse
import json
import sys

from kimi_voice.client import KimiClient
from kimi_voice.config import Settings
from kimi_voice.errors import KimiVoiceError
from kimi_voice.session import converse
from kimi_voice.speech import (
    LineListener,
    PrintingSpeaker,
    PromptListener,
    TeeSpeaker,
    default_listener,
    default_speaker,
)
from kimi_voice.stream import new_history
from kimi_voice.tools import dispatch


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args and not sys.stdin.isatty():
        return run_json(sys.stdin.read())
    if args and args[0].startswith("{") and not args[0].startswith("--"):
        return run_json(args[0])

    parser = argparse.ArgumentParser(
        prog="kimi-voice",
        description="Talk with Kimi K3. Speech stays local; the transcript goes to the model.",
    )
    parser.add_argument(
        "--text",
        action="store_true",
        help="Type the conversation instead of using the microphone.",
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=None,
        help="Stop after this many user turns. Omit to talk until stop.",
    )
    parsed = parser.parse_args(args)
    try:
        if parsed.text:
            return run_text(parsed.turns)
        return run_voice(parsed.turns)
    except KimiVoiceError as exc:
        print(str(exc), file=sys.stderr)
        return 1


def run_json(raw: str) -> int:
    raw = raw.strip()
    if not raw:
        print(json.dumps({"ok": False, "error": "Expected a JSON tool object on stdin."}))
        return 1
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        print(json.dumps({"ok": False, "error": "Tool input was not valid JSON."}))
        return 1
    result = dispatch(payload)
    print(json.dumps(result))
    return 0 if result.get("ok") else 1


def run_text(turns: int | None) -> int:
    settings = Settings.from_env()
    client = KimiClient(settings)
    print("Kimi Voice (typed). Say stop to end.", flush=True)
    converse(
        client,
        PromptListener(),
        PrintingSpeaker(),
        new_history(),
        max_turns=turns,
    )
    return 0


def run_voice(turns: int | None) -> int:
    settings = Settings.from_env()
    client = KimiClient(settings)
    print("Kimi Voice. Speak after the prompt. Say stop to end.", flush=True)
    converse(
        client,
        default_listener(),
        TeeSpeaker(default_speaker()),
        new_history(),
        max_turns=turns,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
