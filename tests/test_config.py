import bootstrap  # noqa: F401

import unittest

from voice_dictation_tool.config import Settings
from voice_dictation_tool.errors import ConfigError


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

    def test_lang_defaults_to_empty(self):
        self.assertEqual(Settings.from_env({}).lang, "")

    def test_lang_from_env(self):
        self.assertEqual(Settings.from_env({"KIMI_LANG": "zh-CN"}).lang, "zh-CN")

    def test_dotenv_parser(self):
        import tempfile
        from pathlib import Path

        from voice_dictation_tool.config import _parse_dotenv

        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text(
                "# comment\nKEY1=value1\nKEY2=\"quoted\"\n\nKEY3='single'\n",
                encoding="utf-8",
            )
            self.assertEqual(
                _parse_dotenv(env_file),
                {"KEY1": "value1", "KEY2": "quoted", "KEY3": "single"},
            )


if __name__ == "__main__":
    unittest.main()
