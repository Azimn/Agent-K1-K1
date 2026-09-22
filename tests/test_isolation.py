from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class IsolationTests(unittest.TestCase):
    def test_no_pretorius_mutable_paths(self):
        targets = [
            ROOT / "runtime" / "k1k1_runtime.py",
            ROOT / "runtime" / "knowledge_library.py",
            ROOT / "plugins" / "k1k1-state" / "__init__.py",
            ROOT / "scripts" / "activate.py",
        ]
        text = "\n".join(path.read_text(encoding="utf-8").lower() for path in targets)
        self.assertNotIn("local/pretorius", text)
        self.assertNotIn("pretorius.db", text)
        self.assertNotIn("pretorius_state", text)

    def test_profile_identity(self):
        profile = (ROOT / "profile.yaml").read_text(encoding="utf-8")
        distribution = (ROOT / "distribution.yaml").read_text(encoding="utf-8")
        self.assertIn("Agent K1-K1", profile)
        self.assertIn("name: agent-k1k1", distribution)


if __name__ == "__main__":
    unittest.main()
