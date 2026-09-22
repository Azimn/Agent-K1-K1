from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROUTINES = [
    {
        "name": "K1-K1 Pulse",
        "schedule": "every 1h",
        "skill": "k1k1-life",
        "continuity": True,
        "delivery": "local",
        "prompt": (
            "Wake for one bounded K1-K1 life cycle. Run the persistent pulse first. "
            "Inspect open commitments and concerns. Complete at most one genuinely useful unit of internal or "
            "explicitly authorized work, inspect the outcome, and update persistent state only when warranted. "
            "Do not manufacture activity. If nothing useful is available, return [SILENT]."
        ),
    },
    {
        "name": "K1-K1 Night Reflection",
        "schedule": "30 1 * * *",
        "skill": "k1k1-life",
        "continuity": True,
        "delivery": "local",
        "prompt": (
            "Review recent durable memories, actions, commitments, relationships, and open concerns. "
            "Reconcile stale or duplicate concerns. Add a self-model claim only if repeated behavioral evidence "
            "supports it. Preserve uncertainty and never invent autobiographical events. Return [SILENT] unless "
            "there is something the user actually needs to see."
        ),
    },
    {
        "name": "K1-K1 Daily Brief",
        "schedule": "0 8 * * *",
        "skill": "k1k1-assistant",
        "continuity": True,
        "delivery": "configured",
        "prompt": (
            "Prepare a compact daily brief using K1-K1's actual persistent state. Include unresolved commitments, "
            "time-sensitive concerns, completed useful work since the previous brief, and anything that genuinely "
            "deserves attention. Do not invent urgency or progress. If there is nothing substantive, say so briefly."
        ),
    },
]


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=check)


def hermes_prefix(profile: str) -> list[str]:
    return ["hermes", "-p", profile]


def existing_cron_text(profile: str) -> str:
    proc = run(hermes_prefix(profile) + ["cron", "list"], check=False)
    return (proc.stdout or "") + "\n" + (proc.stderr or "")


def ensure_config(profile: str, root: Path) -> list[str]:
    values = {
        "terminal.cwd": str(root),
        "cron.max_parallel_jobs": "1",
        "cron.allow_agent_scheduling": "false",
        "cron.mirror_delivery": "true",
        "cron.script_timeout_seconds": "1800",
        "goals.max_turns": "12",
        "loops.max_ticks": "48",
        "loops.self_paced_floor_seconds": "60",
        "loops.self_paced_ceiling_seconds": "900",
        "agent.clarify_timeout": "300",
        "skills.create_dir": str(root / "local" / "learned_skills"),
        "plugins.hook_callback_timeout": "5",
    }
    changed = []
    for key, value in values.items():
        proc = run(hermes_prefix(profile) + ["config", "set", key, value], check=False)
        if proc.returncode != 0:
            raise RuntimeError(f"Failed to set {key}: {proc.stderr or proc.stdout}")
        changed.append(key)

    plugin = run(
        hermes_prefix(profile)
        + ["plugins", "enable", "k1k1-state", "--no-allow-tool-override"],
        check=False,
    )
    if plugin.returncode != 0:
        raise RuntimeError(f"Failed to enable k1k1-state plugin: {plugin.stderr or plugin.stdout}")
    changed.append("plugins.enabled:k1k1-state")
    return changed


def initialize_runtime(root: Path) -> dict:
    runtime = root / "runtime" / "k1k1_runtime.py"
    knowledge = root / "runtime" / "knowledge_library.py"
    seed = root / "resources" / "seed_agenda.json"

    init = run([sys.executable, str(runtime), "init"])
    seeded = run([sys.executable, str(runtime), "seed-agenda", str(seed)])
    knowledge_init = run([sys.executable, str(knowledge), "init"])

    for path in (
        root / "local" / "learned_skills",
        root / "local" / "work",
    ):
        path.mkdir(parents=True, exist_ok=True)

    return {
        "state": init.stdout.strip(),
        "seed": seeded.stdout.strip(),
        "knowledge": knowledge_init.stdout.strip(),
    }


def create_routines(profile: str, root: Path, deliver: str) -> dict[str, str]:
    current = existing_cron_text(profile)
    results: dict[str, str] = {}

    for routine in ROUTINES:
        name = routine["name"]
        if name.lower() in current.lower():
            results[name] = "already present"
            continue

        target = deliver if routine["delivery"] == "configured" else routine["delivery"]
        cmd = hermes_prefix(profile) + [
            "cron",
            "create",
            routine["schedule"],
            routine["prompt"],
            "--name",
            name,
            "--skill",
            routine["skill"],
            "--deliver",
            target,
            "--workdir",
            str(root),
        ]
        if routine["continuity"]:
            cmd.append("--continuity")

        proc = run(cmd, check=False)
        if proc.returncode != 0:
            raise RuntimeError(f"Failed to create {name}: {proc.stderr or proc.stdout}")
        results[name] = "created"

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Activate Agent K1-K1 autonomous Hermes routines")
    parser.add_argument("--profile", default="agent-k1k1")
    parser.add_argument(
        "--deliver",
        default="local",
        help="Delivery target for the daily brief, such as local or telegram",
    )
    parser.add_argument(
        "--install-gateway",
        action="store_true",
        help="Install/restart the Hermes user gateway after activation",
    )
    args = parser.parse_args()

    if not shutil.which("hermes"):
        raise SystemExit("Hermes CLI not found on PATH.")

    root = Path(__file__).resolve().parent.parent
    runtime_result = initialize_runtime(root)
    config_result = ensure_config(args.profile, root)
    routines = create_routines(args.profile, root, args.deliver)

    gateway = "unchanged"
    if args.install_gateway:
        proc = run(["hermes", "gateway", "install"], check=False)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr or proc.stdout)
        restart = run(["hermes", "gateway", "restart"], check=False)
        gateway = "restarted" if restart.returncode == 0 else "installed; restart reported an error"

    status = run(hermes_prefix(args.profile) + ["cron", "status"], check=False)
    print(
        json.dumps(
            {
                "profile": args.profile,
                "root": str(root),
                "runtime": runtime_result,
                "config_keys": config_result,
                "routines": routines,
                "gateway": gateway,
                "cron_status": (status.stdout or status.stderr).strip(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
