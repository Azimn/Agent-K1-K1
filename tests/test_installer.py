from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def load_installer():
    path = Path(__file__).resolve().parents[1] / "scripts" / "install.py"
    spec = importlib.util.spec_from_file_location("kiki_installer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InstallerTests(unittest.TestCase):
    def exercise(self, existing, marker=False, fresh=False, fail=False, recorded_source=False):
        installer = load_installer()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            profile = root / "profiles" / "agent-k1k1"
            config = b"model:\r\n  provider: llamacpp\r\n  default: existing-model\r\n"
            if existing:
                (profile / "memories").mkdir(parents=True)
                (profile / "config.yaml").write_bytes(config)
                (profile / "memories" / "USER.md").write_text("purple cassette")
                (profile / "local").mkdir()
                (profile / "local" / "state-sentinel").write_text("keep state")
                if marker:
                    (profile / "distribution.yaml").write_text(
                        "name: agent-k1k1\n" + ("source: previous-source\n" if recorded_source else "")
                    )
            calls = []

            def fake_run(cmd, check=True):
                calls.append(cmd)
                if cmd[1:3] == ["profile", "create"]:
                    self.assertIn("--clone-from", cmd)
                    self.assertIn("default", cmd)
                    (profile / "memories").mkdir(parents=True)
                    (profile / "config.yaml").write_bytes(config)
                    (profile / "memories" / "USER.md").write_text("inherited")
                elif cmd[1:3] == ["profile", "install"]:
                    self.assertEqual("--force" in cmd, existing or not fresh)
                    (profile / "scripts").mkdir(parents=True, exist_ok=True)
                    (profile / "scripts" / "activate.py").touch()
                    (profile / "config.yaml").write_text("distribution defaults")
                    (profile / "distribution.yaml").write_text("name: agent-k1k1\nsource: test-source\n")
                    if fail:
                        return subprocess.CompletedProcess(cmd, 1, "", "simulated failure")
                return subprocess.CompletedProcess(cmd, 0, "", "")

            argv = ["install.py", "--source", "test-source", "--skip-activation"]
            if fresh:
                argv.append("--fresh")
            if existing and not marker:
                argv.append("--replace-existing")
            with patch.dict(os.environ, {"HERMES_HOME": str(root)}), patch.object(sys, "argv", argv), \
                 patch.object(installer.shutil, "which", return_value="hermes"), \
                 patch.object(installer, "run", side_effect=fake_run), \
                 patch.object(installer.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as activate:
                if fail:
                    with self.assertRaises(SystemExit):
                        installer.main()
                    activate.assert_not_called()
                else:
                    self.assertEqual(installer.main(), 0)
                    self.assertIn("--skip-routines", activate.call_args.args[0])
            if existing or not fresh:
                self.assertEqual((profile / "config.yaml").read_bytes(), config)
            if existing:
                self.assertEqual((profile / "memories" / "USER.md").read_text(), "purple cassette")
                self.assertEqual((profile / "local" / "state-sentinel").read_text(), "keep state")
            else:
                self.assertFalse((profile / "memories" / "USER.md").exists())
            self.assertIn("source: test-source", (profile / "distribution.yaml").read_text())
            self.assertFalse(any(cmd[1:3] == ["profile", "update"] for cmd in calls))

    def test_half_installed_profile_preserves_state_and_records_source(self):
        self.exercise(existing=True, marker=True)

    def test_existing_non_distribution_preserves_state(self):
        self.exercise(existing=True)

    def test_valid_distribution_uses_requested_source_and_preserves_state(self):
        self.exercise(existing=True, marker=True, recorded_source=True)

    def test_fresh_profile(self):
        self.exercise(existing=False, fresh=True)

    def test_new_clone_removes_only_inherited_memory(self):
        self.exercise(existing=False)

    def test_failed_reinstall_restores_provider_config(self):
        self.exercise(existing=True, marker=True, fail=True)

