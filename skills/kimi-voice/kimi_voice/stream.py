"""Pure helpers for streaming speech and Moonshot SSE events."""

from __future__ import annotations

import json
from dataclasses import dataclass

from kimi_voice.errors import KimiAPIError

STOP_PHRASES = {
    "stop",
    "quit",
    "exit",
    "goodbye",
    "good bye",
    "bye",
    "停止",
    "退出",
    "再见",
    "再見",
}

VOICE_SYSTEM = (
    "You are Kimi, an AI assistant from Moonshot AI, in a live spoken conversation. "
    "Reply in the user's language. Use one or two short sentences a person would say out loud. "
    "Do not use markdown, bullets, or code unless the user asks you to read something exactly. "
    "Moonshot AI is a proper noun and should not be translated."
)


@dataclass(frozen=True)
class StreamPiece:
    kind: str
    text: str


def new_history() -> list[dict]:
    return [{"role": "system", "content": VOICE_SYSTEM}]


def is_stop(text: str) -> bool:
    normalized = text.strip().lower().rstrip(".!?。！？")
    return normalized in STOP_PHRASES


def assistant_message(content: str, reasoning: str) -> dict:
    message = {"role": "assistant", "content": content}
    if reasoning:
        message["reasoning_content"] = reasoning
    return message


def take_sentences(buffer: str) -> tuple[list[str], str]:
    """Split completed sentences out of a streaming text buffer.

    A trailing sentence with no following character stays in the buffer so a
    later chunk can still extend it. Callers flush the remainder at the end.
    """
    sentences: list[str] = []
    start = 0
    index = 0
    while index < len(buffer):
        char = buffer[index]
        if char in "。！？\n" or (char in ".!?" and _is_boundary(buffer, index)):
            piece = buffer[start : index + 1].strip()
            if piece and piece not in "。！？.!?":
                sentences.append(piece)
            start = index + 1
        index += 1
    return sentences, buffer[start:]


def flush_sentence(buffer: str) -> str:
    return buffer.strip()


def _is_boundary(text: str, index: int) -> bool:
    char = text[index]
    previous = text[index - 1] if index else ""
    nxt = text[index + 1] if index + 1 < len(text) else ""
    if char == "." and previous.isdigit() and nxt.isdigit():
        return False
    if not nxt:
        return False
    return nxt.isspace() or nxt in "\"'”’)]}"


def iter_pieces(chunks):
    """Yield stream pieces as SSE lines arrive."""
    for raw in chunks:
        line = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
        line = line.strip()
        if not line or line.startswith(":"):
            continue
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            return
        try:
            event = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise KimiAPIError(0, f"Could not parse a stream event: {payload[:180]}") from exc
        yield from pieces_from_event(event)


def pieces_from_event(event: dict) -> list[StreamPiece]:
    choices = event.get("choices") or []
    if not choices:
        return []
    delta = choices[0].get("delta") or {}
    pieces: list[StreamPiece] = []
    reasoning = delta.get("reasoning_content") or ""
    content = delta.get("content") or ""
    if reasoning:
        pieces.append(StreamPiece("reasoning", reasoning))
    if content:
        pieces.append(StreamPiece("content", content))
    return pieces
