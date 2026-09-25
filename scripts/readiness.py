from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REQUIRED = [
    "distribution.yaml",
    "SOUL.md",
    "AGENTS.md",
    "config.yaml",
    "runtime/k1k1_runtime.py",
    "runtime/knowledge_library.py",
    "plugins/k1k1-state/__init__.py",
    "plugins/k1k1-state/plugin.yaml",
    "scripts/install.py",
    "scripts/activate.py",
    "scripts/preview_recall.py",
    "skills/k1k1-life/SKILL.md",
    "skills/k1k1-learning/SKILL.md",
    "skills/k1k1-assistant/SKILL.md",
    "resources/identity/KIKI_FOUNDATION.md",
    "resources/seed_agenda.json",
]


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    missing = [path for path in REQUIRED if not (root / path).exists()]

    checks: dict[str, object] = {
        "python": sys.version.split()[0],
        "python_ok": sys.version_info >= (3, 11),
        "hermes_found": bool(shutil.which("hermes")),
        "missing_required_files": missing,
    }

    if shutil.which("hermes"):
        proc = subprocess.run(["hermes", "--version"], text=True, capture_output=True)
        checks["hermes_version"] = (proc.stdout or proc.stderr).strip()

    with tempfile.TemporaryDirectory() as td:
        state_db = Path(td) / "k1k1.db"
        proc = subprocess.run(
            [
                sys.executable,
                str(root / "runtime" / "k1k1_runtime.py"),
                "--db",
                str(state_db),
                "init",
            ],
            text=True,
            capture_output=True,
        )
        checks["runtime_init_ok"] = proc.returncode == 0
        checks["runtime_init_output"] = (proc.stdout or proc.stderr).strip()

        knowledge_db = Path(td) / "knowledge.db"
        records_dir = Path(td) / "records"
        proc = subprocess.run(
            [
                sys.executable,
                str(root / "runtime" / "knowledge_library.py"),
                "--db",
                str(knowledge_db),
                "--records-dir",
                str(records_dir),
                "init",
            ],
            text=True,
            capture_output=True,
        )
        checks["knowledge_init_ok"] = proc.returncode == 0
        checks["knowledge_init_output"] = (proc.stdout or proc.stderr).strip()

    checks["isolation_ok"] = (
        "pretorius_state" not in (root / "runtime" / "k1k1_runtime.py").read_text(encoding="utf-8").lower()
        and "pretorius.db" not in (root / "plugins" / "k1k1-state" / "__init__.py").read_text(encoding="utf-8").lower()
    )

    ready = (
        checks["python_ok"]
        and not missing
        and checks["runtime_init_ok"]
        and checks["knowledge_init_ok"]
        and checks["isolation_ok"]
    )
    checks["ready"] = bool(ready)

    print(json.dumps(checks, indent=2))
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
