from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agency import Entry
from agency.content import render_entry


class ColorConversionTests(unittest.TestCase):
    def test_named_agent_color_is_converted_to_opencode_hex(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "agent"
            source.mkdir()
            (source / "agent.md").write_text(
                "---\nname: agent\ndescription: test\nmodel: claude-sonnet-4-20250514\ncolor: cyan\n---\nbody\n",
                encoding="utf-8",
            )
            rendered = render_entry(
                Entry("agent", source, "1.0.0", "agent", {"name": "agent"}),
                root / "target",
                None,
            )

        text = rendered["agents/agent.md"].decode()
        self.assertIn("color: '#06B6D4'", text)
        self.assertNotIn("color: cyan", text)


if __name__ == "__main__":
    unittest.main()
