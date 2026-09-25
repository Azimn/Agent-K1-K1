from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_runtime():
    path = ROOT / "runtime" / "k1k1_runtime.py"
    spec = importlib.util.spec_from_file_location("k1k1_runtime", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load runtime")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class RuntimeTests(unittest.TestCase):
    def test_schema_and_state_are_k1k1_specific(self):
        runtime = load_runtime()
        self.assertIn("k1k1_state", str(runtime.DEFAULT_DB))
        self.assertNotIn("pretorius_state", str(runtime.DEFAULT_DB).lower())

    def test_memory_round_trip(self):
        runtime = load_runtime()
        with tempfile.TemporaryDirectory() as td:
            conn = runtime.connect(Path(td) / "state.db")
            args = type(
                "Args",
                (),
                {
                    "occurred_at": None,
                    "kind": "experience",
                    "summary": "We discovered a useful workflow.",
                    "source": "test",
                    "salience": 0.8,
                    "confidence": 0.9,
                    "tag": ["workflow"],
                    "supersedes_id": None,
                },
            )()
            result = runtime.cmd_memory_add(conn, args)
            self.assertTrue(result["ok"])
            row = conn.execute("SELECT summary FROM memories").fetchone()
            self.assertEqual(row["summary"], "We discovered a useful workflow.")
            conn.close()

    def test_relationship_is_not_scalar_friendship_score(self):
        runtime = load_runtime()
        with tempfile.TemporaryDirectory() as td:
            conn = runtime.connect(Path(td) / "state.db")
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(relationships)").fetchall()
            }
            self.assertIn("evidence_json", columns)
            self.assertIn("commitments_json", columns)
            self.assertIn("unresolved_json", columns)
            self.assertNotIn("friendship_score", columns)
            conn.close()


if __name__ == "__main__":
    unittest.main()
