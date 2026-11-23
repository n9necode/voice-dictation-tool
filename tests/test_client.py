import bootstrap  # noqa: F401

import io
import unittest
import urllib.error

from kimi_voice.client import KimiClient, build_request
from kimi_voice.config import Settings
from kimi_voice.errors import ConfigError, KimiAPIError


SECRET = "secret-key-should-not-leak"


class _Body:
    def __init__(self, lines):
        self._lines = iter(lines)

    def __iter__(self):
        return self._lines

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class ClientTests(unittest.TestCase):
    def test_request_targets_kimi_k3(self):
        settings = Settings(api_key=SECRET, model="kimi-k3", reasoning_effort="low")
        request = build_request(settings, [{"role": "user", "content": "hi"}])
        self.assertEqual(request.full_url, "https://api.moonshot.ai/v1/chat/completions")
        self.assertEqual(request.get_header("Authorization"), f"Bearer {SECRET}")
        payload = request.data.decode("utf-8")
        self.assertIn('"model": "kimi-k3"', payload)
        self.assertIn('"reasoning_effort": "low"', payload)
        self.assertIn('"stream": true', payload)

    def test_missing_key_does_not_call_the_network(self):
        called = []

        def opener(request, timeout):
            called.append(request)
            raise AssertionError("network")

        client = KimiClient(Settings.from_env({}), opener=opener)
        with self.assertRaises(ConfigError):
            list(client.stream([{"role": "user", "content": "hi"}]))
        self.assertEqual(called, [])

    def test_stream_yields_before_done(self):
        lines = [
            b'data: {"choices":[{"delta":{"content":"One. "}}]}\n',
            b'data: {"choices":[{"delta":{"content":"Two."}}]}\n',
            b"data: [DONE]\n",
        ]

        def opener(request, timeout):
            return _Body(lines)

        client = KimiClient(Settings(api_key="k"), opener=opener)
        pieces = list(client.stream([{"role": "user", "content": "hi"}]))
        self.assertEqual([piece.text for piece in pieces], ["One. ", "Two."])

    def test_http_error_hides_the_api_key(self):
        def opener(request, timeout):
            raise urllib.error.HTTPError(
                request.full_url,
                401,
                "Unauthorized",
                None,
                io.BytesIO(b'{"error":"invalid key"}'),
            )

        client = KimiClient(Settings(api_key=SECRET), opener=opener)
        with self.assertRaises(KimiAPIError) as caught:
            list(client.stream([{"role": "user", "content": "hi"}]))
        self.assertNotIn(SECRET, str(caught.exception))
        self.assertIn("401", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
