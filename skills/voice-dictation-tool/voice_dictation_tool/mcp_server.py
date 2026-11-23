"""Minimal stdio MCP server so Kimi Code can call the voice tools."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable

from voice_dictation_tool import __version__
from voice_dictation_tool.tools import TOOLS, dispatch

PROTOCOL = "2024-11-05"

TOOL_SCHEMAS = {
    "listen": {
        "description": "Listen once through the microphone and return the transcript. Nothing is sent to Kimi until ask or converse.",
        "properties": {
            "timeout": {
                "type": "number",
                "description": "Seconds to wait for speech. Default 12.",
            }
        },
        "required": [],
    },
    "speak": {
        "description": "Speak text aloud on this machine. Do not pass reasoning or API keys.",
        "properties": {
            "text": {"type": "string", "description": "Words to speak."}
        },
        "required": ["text"],
    },
    "ask": {
        "description": "Send one utterance to kimi-k3 and return the spoken-style reply. Set speak true to play it.",
        "properties": {
            "text": {"type": "string", "description": "What the user said."},
            "speak": {
                "type": "boolean",
                "description": "Play the reply on the speakers. Default false.",
            },
        },
        "required": ["text"],
    },
    "converse": {
        "description": "Run a spoken back-and-forth. Pass lines to use text instead of the microphone. Say stop to end.",
        "properties": {
            "turns": {
                "type": "integer",
                "description": "Maximum user turns. Default 1. Null means continue until stop.",
            },
            "lines": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Typed utterances. Omit to use the microphone.",
            },
        },
        "required": [],
    },
}


def tool_list() -> list[dict]:
    listed = []
    for name in TOOLS:
        schema = TOOL_SCHEMAS[name]
        listed.append(
            {
                "name": name,
                "description": schema["description"],
                "inputSchema": {
                    "type": "object",
                    "properties": schema["properties"],
                    "required": schema["required"],
                },
            }
        )
    return listed


def handle(message: dict, call_tool: Callable[[str, dict], dict] | None = None) -> dict | None:
    """Answer one JSON-RPC message. Notifications return None."""
    if "id" not in message:
        return None
    method = message.get("method")
    request_id = message.get("id")
    if method == "initialize":
        return _result(
            request_id,
            {
                "protocolVersion": PROTOCOL,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "voice-dictation-tool", "version": __version__},
            },
        )
    if method == "ping":
        return _result(request_id, {})
    if method == "tools/list":
        return _result(request_id, {"tools": tool_list()})
    if method == "tools/call":
        params = message.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments") or {}
        runner = call_tool or _default_call
        try:
            body = runner(name, arguments)
        except Exception as exc:  # surface tool bugs as MCP errors, not a dead server
            body = {"ok": False, "error": str(exc)}
        failed = not body.get("ok", False)
        text = body.get("error") if failed else json.dumps(body)
        return _result(
            request_id,
            {
                "content": [{"type": "text", "text": text}],
                "isError": failed,
            },
        )
    return _error(request_id, -32601, f"Method not found: {method}")


def _default_call(name: str, arguments: dict) -> dict:
    if name not in TOOLS:
        return {"ok": False, "error": f"Unknown tool {name!r}."}
    return dispatch({"tool": name, **arguments})


def _result(request_id, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def read_message(reader) -> dict | None:
    headers: dict[str, str] = {}
    while True:
        line = reader.readline()
        if not line:
            return None
        if line in (b"\r\n", b"\n"):
            break
        decoded = line.decode("ascii", errors="replace").strip()
        if not decoded:
            break
        key, _, value = decoded.partition(":")
        headers[key.strip().lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    body = reader.read(length)
    if len(body) < length:
        return None
    return json.loads(body.decode("utf-8"))


def write_message(writer, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    writer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii"))
    writer.write(body)
    writer.flush()


def serve(reader=None, writer=None, call_tool: Callable[[str, dict], dict] | None = None) -> None:
    incoming = reader if reader is not None else sys.stdin.buffer
    outgoing = writer if writer is not None else sys.stdout.buffer
    while True:
        message = read_message(incoming)
        if message is None:
            return
        response = handle(message, call_tool)
        if response is not None:
            write_message(outgoing, response)
