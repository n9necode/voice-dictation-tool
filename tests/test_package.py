import bootstrap  # noqa: F401

import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from kimi_voice.pack import pack_plugin

ROOT = Path(__file__).resolve().parents[1]


def frontmatter(text: str) -> dict:
    self_name, raw, _body = text.split("---", 2)
    del self_name
    data = {}
    for line in raw.strip().splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    return data


class PackageTests(unittest.TestCase):
    def test_skill_and_plugin_share_a_name(self):
        manifest = json.loads((ROOT / "kimi.plugin.json").read_text(encoding="utf-8"))
        skill = frontmatter((ROOT / "skills" / "kimi-voice" / "SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "kimi-voice")
        self.assertEqual(skill["name"], "kimi-voice")
        self.assertLessEqual(len(skill["description"]), 1024)
        self.assertIn("kimi-k3", skill["description"])
        script = ROOT / "skills" / "kimi-voice" / "scripts" / "mcp_server.py"
        self.assertTrue(script.is_file())
        command = manifest["mcpServers"]["kimi-voice"]
        self.assertTrue((ROOT / command["args"][0].lstrip("./")).is_file())

    def test_skill_zip_contains_the_download(self):
        with tempfile.TemporaryDirectory() as temp:
            dest = Path(temp) / "kimi-voice.zip"
            pack_plugin(ROOT, dest)
            with zipfile.ZipFile(dest) as archive:
                names = set(archive.namelist())
        self.assertIn("kimi.plugin.json", names)
        self.assertIn("skills/kimi-voice/SKILL.md", names)
        self.assertIn("skills/kimi-voice/kimi_voice/cli.py", names)
        self.assertNotIn("tests/test_config.py", names)


if __name__ == "__main__":
    unittest.main()
