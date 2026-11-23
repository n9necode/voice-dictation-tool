import bootstrap  # noqa: F401

import unittest

from voice_dictation_tool.session import converse, take_turn
from voice_dictation_tool.speech import LineListener, ListSpeaker
from voice_dictation_tool.stream import StreamPiece, new_history


class FakeClient:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def stream(self, messages):
        self.calls.append([dict(message) for message in messages])
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        for piece in reply:
            yield piece


def words(text, reasoning=""):
    pieces = []
    if reasoning:
        pieces.append(StreamPiece("reasoning", reasoning))
    pieces.append(StreamPiece("content", text))
    return pieces


class SessionTests(unittest.TestCase):
    def test_speaks_sentences_and_stores_reasoning(self):
        client = FakeClient([words("Hello there. How are you?", reasoning="quiet")])
        speaker = ListSpeaker()
        history = new_history()
        reply = take_turn(client, history, "hi", speaker)
        self.assertEqual(speaker.spoken, ["Hello there.", "How are you?"])
        self.assertEqual(reply, "Hello there. How are you?")
        self.assertEqual(history[-1]["reasoning_content"], "quiet")
        self.assertNotIn("quiet", " ".join(speaker.spoken))

    def test_stop_does_not_call_the_model(self):
        client = FakeClient([])
        speaker = ListSpeaker()
        result = converse(client, LineListener(["stop"]), speaker, max_turns=3)
        self.assertEqual(client.calls, [])
        self.assertEqual(speaker.spoken, ["Okay. Talk to you later."])
        self.assertTrue(result["turns"][0]["stopped"])

    def test_second_turn_includes_the_first_reply(self):
        client = FakeClient([words("Four."), words("Six.")])
        speaker = ListSpeaker()
        result = converse(
            client,
            LineListener(["what is two plus two", "add two more", "goodbye"]),
            speaker,
        )
        self.assertEqual([turn["reply"] for turn in result["turns"]], [
            "Four.",
            "Six.",
            "Okay. Talk to you later.",
        ])
        second_call = client.calls[1]
        self.assertEqual(second_call[-1]["content"], "add two more")
        self.assertEqual(second_call[-2]["role"], "assistant")
        self.assertEqual(second_call[-2]["content"], "Four.")

    def test_failed_turn_does_not_keep_a_user_line(self):
        client = FakeClient([RuntimeError("down")])
        history = new_history()
        with self.assertRaises(RuntimeError):
            take_turn(client, history, "hello", ListSpeaker())
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["role"], "system")


if __name__ == "__main__":
    unittest.main()
