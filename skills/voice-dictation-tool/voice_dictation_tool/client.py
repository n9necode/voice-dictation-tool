"""Moonshot chat client for kimi-k3."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Iterator

from voice_dictation_tool.config import Settings
from voice_dictation_tool.errors import KimiAPIError
from voice_dictation_tool.stream import StreamPiece, iter_pieces


def build_request(settings: Settings, messages: list[dict]) -> urllib.request.Request:
    settings.require_api_key()
    body = {
        "model": settings.model,
        "messages": messages,
        "stream": True,
        "reasoning_effort": settings.reasoning_effort,
    }
    encoded = json.dumps(body).encode("utf-8")
    return urllib.request.Request(
        f"{settings.base_url}/chat/completions",
        data=encoded,
        headers={
            "Authorization": f"Bearer {settings.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )


class KimiClient:
    """Streams a Kimi K3 reply. Pass ``opener`` in tests to avoid the network."""

    def __init__(self, settings: Settings, opener=None):
        self.settings = settings
        self.opener = opener or urllib.request.urlopen

    def stream(self, messages: list[dict]) -> Iterator[StreamPiece]:
        request = build_request(self.settings, messages)
        try:
            context = self.opener(request, timeout=self.settings.timeout)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise KimiAPIError(exc.code, body) from None
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", exc)
            raise KimiAPIError(0, str(reason)) from None
        with context as response:
            yield from iter_pieces(response)
