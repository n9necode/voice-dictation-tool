import bootstrap  # noqa: F401

import unittest

from kimi_voice.config import Settings
from kimi_voice.errors import ConfigError


class ConfigTests(unittest.TestCase):
    def test_voice_defaults_to_kimi_k3_and_low_effort(self):
        settings = Settings.from_env({})
        self.assertEqual(settings.model, "kimi-k3")
        self.assertEqual(settings.reasoning_effort, "low")
        self.assertEqual(settings.base_url, "https://api.moonshot.ai/v1")
        self.assertEqual(settings.api_key, "")

    def test_env_overrides(self):
        settings = Settings.from_env(
            {
                "MOONSHOT_API_KEY": "test-key",
                "MOONSHOT_BASE_URL": "https://example.test/v1/",
                "KIMI_MODEL": "kimi-k3",
                "KIMI_REASONING_EFFORT": "high",
                "KIMI_TIMEOUT": "15",
            }
        )
        self.assertEqual(settings.api_key, "test-key")
        self.assertEqual(settings.base_url, "https://example.test/v1")
        self.assertEqual(settings.reasoning_effort, "high")
        self.assertEqual(settings.timeout, 15)

    def test_bad_effort_is_rejected(self):
        with self.assertRaises(ConfigError):
            Settings.from_env({"KIMI_REASONING_EFFORT": "turbo"})

    def test_missing_key_is_a_clear_error(self):
        settings = Settings.from_env({})
        with self.assertRaises(ConfigError) as caught:
            settings.require_api_key()
        self.assertIn("MOONSHOT_API_KEY", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
