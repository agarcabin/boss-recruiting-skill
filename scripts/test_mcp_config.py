import tempfile
import unittest
from pathlib import Path

import mcp_config


class McpConfigTests(unittest.TestCase):
    def installed_root(self, folder):
        root = Path(folder) / "skill"
        (root / "runtime" / "win-x64" / "python").mkdir(parents=True)
        (root / "scripts").mkdir(parents=True)
        (root / "runtime" / "win-x64" / "python" / "python.exe").write_bytes(b"")
        (root / "scripts" / "recruiting_mcp.py").write_text("", encoding="utf-8")
        return root

    def test_registers_once_and_preserves_existing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = self.installed_root(folder)
            config = Path(folder) / "config.toml"
            first = mcp_config.ensure(config, root)
            self.assertEqual(first["state"], "registered")
            text = config.read_text(encoding="utf-8")
            self.assertIn("[mcp_servers.recruiting]", text)
            self.assertIn("BOSS_SKILL_ROOT", text)
            second = mcp_config.ensure(config, root)
            self.assertEqual(second["state"], "existing")
            self.assertEqual(text, config.read_text(encoding="utf-8"))

    def test_does_not_touch_existing_recruiting_section(self):
        with tempfile.TemporaryDirectory() as folder:
            root = self.installed_root(folder)
            config = Path(folder) / "config.toml"
            original = '[mcp_servers.recruiting]\ncommand = "custom"\n'
            config.write_text(original, encoding="utf-8")
            result = mcp_config.ensure(config, root)
            self.assertEqual(result["state"], "existing")
            self.assertEqual(config.read_text(encoding="utf-8"), original)

    def test_inline_and_commented_sections_are_handled(self):
        with tempfile.TemporaryDirectory() as folder:
            root = self.installed_root(folder)
            config = Path(folder) / "config.toml"
            config.write_text("[mcp_servers]\nrecruiting = { command = 'x' }\n", encoding="utf-8")
            self.assertEqual(mcp_config.ensure(config, root)["state"], "existing")
            config.write_text("# [mcp_servers.recruiting]\n", encoding="utf-8")
            self.assertEqual(mcp_config.ensure(config, root)["state"], "existing_disabled")
            self.assertEqual(config.read_text(encoding="utf-8"), "# [mcp_servers.recruiting]\n")

    def test_invalid_toml_is_not_rewritten(self):
        with tempfile.TemporaryDirectory() as folder:
            root = self.installed_root(folder)
            config = Path(folder) / "config.toml"
            config.write_text("[broken\n", encoding="utf-8")
            self.assertEqual(mcp_config.ensure(config, root)["state"], "skipped")
            self.assertEqual(config.read_text(encoding="utf-8"), "[broken\n")


if __name__ == "__main__":
    unittest.main()
