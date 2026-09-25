from __future__ import annotations

import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PATH = ROOT / "plugins" / "k1k1-state" / "__init__.py"


def load_plugin():
    spec = importlib.util.spec_from_file_location("k1k1_state_plugin_test", PLUGIN_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class K1K1StatePluginTests(unittest.TestCase):
    def test_autobiographical_write_lands_in_k1k1_db(self):
        plugin = load_plugin()
        with tempfile.TemporaryDirectory() as tmp:
            plugin.DB_PATH = Path(tmp) / "k1k1.db"
            plugin.KNOWLEDGE_DB_PATH = Path(tmp) / "knowledge.db"

            result = plugin.write_autobiographical_memory(
                "Our persistent-memory test phrase is purple cassette.",
                kind="shared_event",
                salience=0.8,
                confidence=1.0,
                tags=["memory-test"],
            )
            self.assertTrue(result["success"])

            conn = sqlite3.connect(plugin.DB_PATH)
            try:
                row = conn.execute(
                    "SELECT kind, summary, source FROM memories WHERE id=?",
                    (result["id"],),
                ).fetchone()
            finally:
                conn.close()

            self.assertEqual(row[0], "shared_event")
            self.assertIn("purple cassette", row[1])
            self.assertEqual(row[2], "hermes:k1k1_remember")

    def test_old_relevant_memory_remains_eligible(self):
        plugin = load_plugin()
        with tempfile.TemporaryDirectory() as tmp:
            plugin.DB_PATH = Path(tmp) / "k1k1.db"
            plugin.KNOWLEDGE_DB_PATH = Path(tmp) / "knowledge.db"

            anchor = plugin.write_autobiographical_memory(
                "Ancient shared test: purple cassette belongs to our continuity.",
                kind="shared_event",
                salience=0.01,
                confidence=1.0,
            )
            self.assertTrue(anchor["success"])

            for idx in range(170):
                result = plugin.write_autobiographical_memory(
                    f"Unrelated recent filler memory number {idx}.",
                    kind="experience",
                    salience=1.0,
                    confidence=1.0,
                )
                self.assertTrue(result["success"])

            recall = plugin.contextual_recall("What was the purple cassette test?")
            selected_ids = {item["id"] for item in recall["selected"]}
            self.assertIn(anchor["id"], selected_ids)

    def test_pre_llm_context_routes_autobiographical_memory(self):
        plugin = load_plugin()
        with tempfile.TemporaryDirectory() as tmp:
            plugin.DB_PATH = Path(tmp) / "k1k1.db"
            plugin.KNOWLEDGE_DB_PATH = Path(tmp) / "knowledge.db"
            injected = plugin.inject_k1k1_state(user_message="Please remember this shared event.")
            self.assertIsNotNone(injected)
            self.assertIn("k1k1_remember", injected["context"])
            self.assertIn("not Kiki's autobiographical store", injected["context"])


if __name__ == "__main__":
    unittest.main()
