import bootstrap  # noqa: F401

import io
import json
import unittest

from kimi_voice.mcp_server import handle, read_message, serve, write_message


class McpTests(unittest.TestCase):
    def test_initialize_and_tool_list(self):
        started = handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        self.assertEqual(started["result"]["serverInfo"]["name"], "kimi-voice")
        self.assertIsNone(handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))
        listed = handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = [tool["name"] for tool in listed["result"]["tools"]]
        self.assertEqual(names, ["listen", "speak", "ask", "converse"])

    def test_tool_call_uses_the_injected_runner(self):
        def call_tool(name, arguments):
            return {"ok": True, "tool": name, "text": arguments.get("text")}

        response = handle(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "speak", "arguments": {"text": "hello"}},
            },
            call_tool,
        )
        self.assertFalse(response["result"]["isError"])
        body = json.loads(response["result"]["content"][0]["text"])
        self.assertEqual(body["text"], "hello")

    def test_framed_roundtrip(self):
        incoming = io.BytesIO()
        outgoing = io.BytesIO()
        write_message(
            incoming,
            {"jsonrpc": "2.0", "id": 7, "method": "ping"},
        )
        incoming.seek(0)

        def call_tool(name, arguments):
            raise AssertionError(name)

        serve(incoming, outgoing, call_tool)
        outgoing.seek(0)
        message = read_message(outgoing)
        self.assertEqual(message["id"], 7)
        self.assertEqual(message["result"], {})


if __name__ == "__main__":
    unittest.main()
