from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CharacterContractTests(unittest.TestCase):
    def test_core_character_contract(self):
        soul = (ROOT / "SOUL.md").read_text(encoding="utf-8").lower()
        self.assertIn("k1-k1", soul)
        self.assertIn("artificial intelligence", soul)
        self.assertIn("helpfulness is part of your personality, not a command to agree with everything", soul)
        self.assertIn("before the year 2000", soul)
        self.assertIn("this is not a knowledge cutoff", soul)
        self.assertIn("agent pretorius is a separate agent", soul)
        self.assertIn("k1k1_remember", soul)
        self.assertNotIn("do not repeatedly tell the user", soul)

    def test_legacy_evidence_is_not_binding_canon(self):
        evidence = (
            ROOT / "resources" / "identity" / "LEGACY_KIKI_EVIDENCE.md"
        ).read_text(encoding="utf-8").lower()
        self.assertIn("historical evidence", evidence)
        self.assertIn("current explicit design", evidence)
        self.assertIn("the current authored design wins", evidence)


if __name__ == "__main__":
    unittest.main()
