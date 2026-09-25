from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_library():
    path = ROOT / "runtime" / "knowledge_library.py"
    spec = importlib.util.spec_from_file_location("knowledge_library", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load knowledge library")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class KnowledgeTests(unittest.TestCase):
    def test_add_and_search(self):
        library = load_library()
        with tempfile.TemporaryDirectory() as td:
            conn = library.connect(Path(td) / "knowledge.db")
            args = type(
                "Args",
                (),
                {
                    "title": "Activation steering",
                    "source": "https://example.com/paper",
                    "source_type": "paper",
                    "summary": "Activation vectors can modify model behavior.",
                    "claim": ["A direction can be injected during inference."],
                    "confidence": 0.8,
                    "tag": ["steering"],
                },
            )()
            result = library.add_entry(conn, args, Path(td) / "records")
            self.assertTrue(result["ok"])
            found = library.search(conn, "activation steering", 5)
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0]["source_type"], "paper")
            conn.close()


if __name__ == "__main__":
    unittest.main()
