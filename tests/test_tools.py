import bootstrap  # noqa: F401

import unittest

from kimi_voice.speech import ListSpeaker
from kimi_voice.stream import StreamPiece
from kimi_voice.tools import dispatch


class FakeClient:
    def __init__(self, text):
        self.text = text
        self.calls = 0

    def stream(self, messages):
        self.calls += 1
        yield StreamPiece("content", self.text)


class ToolTests(unittest.TestCase):
    def test_ask_speaks_only_the_reply(self):
        speaker = ListSpeaker()
        client = FakeClient("Two.")
        result = dispatch(
            {"tool": "ask", "text": "1+1", "speak": True},
            client=client,
            speaker=speaker,
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["reply"], "Two.")
        self.assertEqual(speaker.spoken, ["Two."])
        self.assertEqual(client.calls, 1)

    def test_converse_can_run_from_typed_lines(self):
        speaker = ListSpeaker()
        result = dispatch(
            {"tool": "converse", "turns": 2, "lines": ["hello", "stop"]},
            client=FakeClient("Hi."),
            speaker=speaker,
        )
        self.assertEqual(
            [(turn["user"], turn["stopped"]) for turn in result["turns"]],
            [("hello", False), ("stop", True)],
        )

    def test_speak_requires_text(self):
        result = dispatch({"tool": "speak", "text": "  "}, speaker=ListSpeaker())
        self.assertFalse(result["ok"])
        self.assertIn("text", result["error"])

    def test_unknown_tool(self):
        result = dispatch({"tool": "sing"})
        self.assertFalse(result["ok"])
        self.assertIn("Unknown tool", result["error"])


if __name__ == "__main__":
    unittest.main()
