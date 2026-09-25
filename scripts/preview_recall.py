from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


def load_plugin():
    root = Path(__file__).resolve().parent.parent
    plugin_path = root / "plugins" / "k1k1-state" / "__init__.py"
    spec = importlib.util.spec_from_file_location("k1k1_state_plugin", plugin_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load k1k1-state plugin")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description="Preview K1-K1 contextual recall")
    parser.add_argument("query")
    args = parser.parse_args()

    plugin = load_plugin()
    result = plugin.contextual_recall(args.query)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
