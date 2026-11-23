import bootstrap  # noqa: F401

import unittest

from voice_dictation_tool.stream import (
    assistant_message,
    flush_sentence,
    is_stop,
    iter_pieces,
    take_sentences,
)


class StreamTests(unittest.TestCase):
    def test_stop_phrases(self):
        self.assertTrue(is_stop("stop"))
        self.assertTrue(is_stop("Goodbye."))
        self.assertTrue(is_stop("再见"))
        self.assertFalse(is_stop("please stop talking about that"))

    def test_decimal_stays_one_sentence(self):
        ready, rest = take_sentences("It costs 3.14 dollars.")
        self.assertEqual(ready, [])
        self.assertEqual(flush_sentence(rest), "It costs 3.14 dollars.")

    def test_two_english_sentences(self):
        ready, rest = take_sentences("Hello there. How are you?")
        self.assertEqual(ready, ["Hello there."])
        self.assertEqual(flush_sentence(rest), "How are you?")

    def test_chinese_sentences(self):
        ready, rest = take_sentences("你好。我是 Kimi。")
        self.assertEqual(ready, ["你好。", "我是 Kimi。"])
        self.assertEqual(rest, "")

    def test_chunks_join_before_splitting(self):
        pending = ""
        spoken = []
        for chunk in ("Hel", "lo. ", "Done."):
            pending += chunk
            ready, pending = take_sentences(pending)
            spoken.extend(ready)
        tail = flush_sentence(pending)
        if tail:
            spoken.append(tail)
        self.assertEqual(spoken, ["Hello.", "Done."])

    def test_sse_keeps_reasoning_separate_from_speech(self):
        lines = [
            'data: {"choices":[{"delta":{"reasoning_content":"think"}}]}\n',
            'data: {"choices":[{"delta":{"content":"Hi."}}]}\n',
            "data: [DONE]\n",
            'data: {"choices":[{"delta":{"content":"ignored"}}]}\n',
        ]
        pieces = list(iter_pieces(lines))
        self.assertEqual([(piece.kind, piece.text) for piece in pieces], [
            ("reasoning", "think"),
            ("content", "Hi."),
        ])

    def test_assistant_message_keeps_reasoning_for_the_next_turn(self):
        message = assistant_message("Hi.", "think")
        self.assertEqual(
            message,
            {"role": "assistant", "content": "Hi.", "reasoning_content": "think"},
        )
        self.assertNotIn("reasoning_content", assistant_message("Hi.", ""))


if __name__ == "__main__":
    unittest.main()
