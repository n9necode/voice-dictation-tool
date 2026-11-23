"""One spoken turn, and a short back-and-forth."""

from __future__ import annotations

from voice_dictation_tool.errors import ListenEnded
from voice_dictation_tool.stream import (
    assistant_message,
    flush_sentence,
    is_stop,
    new_history,
    take_sentences,
)

GOODBYE = "Okay. Talk to you later."


def take_turn(client, history: list[dict], user_text: str, speaker) -> str:
    """Append the user line, stream Kimi K3, and speak finished sentences."""
    history.append({"role": "user", "content": user_text})
    content: list[str] = []
    reasoning: list[str] = []
    pending = ""
    try:
        for piece in client.stream(history):
            if piece.kind == "reasoning":
                reasoning.append(piece.text)
                continue
            content.append(piece.text)
            pending += piece.text
            ready, pending = take_sentences(pending)
            for sentence in ready:
                speaker.speak(sentence)
        tail = flush_sentence(pending)
        if tail:
            speaker.speak(tail)
            pending = ""
        reply = "".join(content).strip()
        history.append(assistant_message(reply, "".join(reasoning)))
        return reply
    except Exception:
        if not content and not reasoning:
            history.pop()
        else:
            history.append(assistant_message("".join(content).strip(), "".join(reasoning)))
        raise


def converse(
    client,
    listener,
    speaker,
    history: list[dict] | None = None,
    *,
    max_turns: int | None = None,
) -> dict:
    """Listen, reply, and speak until stop, the listener ends, or max_turns."""
    transcript = history if history is not None else new_history()
    turns: list[dict] = []
    count = 0
    while max_turns is None or count < max_turns:
        try:
            heard = listener.listen()
        except ListenEnded:
            break
        heard = heard.strip()
        if not heard:
            continue
        if is_stop(heard):
            speaker.speak(GOODBYE)
            turns.append({"user": heard, "reply": GOODBYE, "stopped": True})
            break
        reply = take_turn(client, transcript, heard, speaker)
        turns.append({"user": heard, "reply": reply, "stopped": False})
        count += 1
    return {"history": transcript, "turns": turns}
