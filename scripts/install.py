from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_SOURCE = "github.com/Azimn/Agent-K1-K1"


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=check)


def remove_inherited_memory(profile_home: Path) -> None:
    for name in ("MEMORY.md", "USER.md"):
        path = profile_home / "memories" / name
        if path.exists():
            path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Agent K1-K1 as an isolated Hermes profile")
    parser.add_argument("--profile", default="agent-k1k1")
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--deliver", default="local")
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Install a blank K1-K1 distribution without inheriting the current Hermes provider/tool config",
    )
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Allow replacement of an existing non-distribution profile while preserving its config",
    )
    parser.add_argument("--start-gateway", action="store_true")
    parser.add_argument(
        "--skip-activation",
        action="store_true",
        help="Install the isolated K1-K1 profile without creating cron routines or starting a gateway",
    )
    args = parser.parse_args()

    if not shutil.which("hermes"):
        raise SystemExit("Hermes CLI not found on PATH.")

    hermes_home = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))).expanduser()
    profile_home = hermes_home / "profiles" / args.profile
    distribution_marker = profile_home / "distribution.yaml"

    if profile_home.exists() and distribution_marker.exists():
        proc = run(["hermes", "profile", "update", args.profile, "--yes"], check=False)
        if proc.returncode != 0:
            raise SystemExit(proc.stderr or proc.stdout)
    elif profile_home.exists():
        if not args.replace_existing:
            raise SystemExit(
                f"Profile '{args.profile}' already exists but is not a distribution. "
                "Choose another --profile name or re-run with --replace-existing."
            )
        preserved_config = (
            (profile_home / "config.yaml").read_text(encoding="utf-8")
            if (profile_home / "config.yaml").exists()
            else None
        )
        remove_inherited_memory(profile_home)
        proc = run(
            [
                "hermes",
                "profile",
                "install",
                args.source,
                "--name",
                args.profile,
                "--alias",
                "--yes",
                "--force",
            ],
            check=False,
        )
        if proc.returncode != 0:
            raise SystemExit(proc.stderr or proc.stdout)
        if preserved_config is not None:
            (profile_home / "config.yaml").write_text(preserved_config, encoding="utf-8")
    elif args.fresh:
        proc = run(
            [
                "hermes",
                "profile",
                "install",
                args.source,
                "--name",
                args.profile,
                "--alias",
                "--yes",
            ],
            check=False,
        )
        if proc.returncode != 0:
            raise SystemExit(proc.stderr or proc.stdout)
        print(
            f"Installed Agent K1-K1 into a fresh profile at {profile_home}.\n"
            f"Run: hermes -p {args.profile} setup\n"
            f"Then run: {sys.executable} {profile_home / 'scripts' / 'activate.py'} "
            f"--profile {args.profile} --deliver {args.deliver}"
            + (" --install-gateway" if args.start_gateway else "")
        )
        return 0
    else:
        create = run(["hermes", "profile", "create", args.profile, "--clone"], check=False)
        if create.returncode != 0:
            raise SystemExit(create.stderr or create.stdout)

        preserved_config = (
            (profile_home / "config.yaml").read_text(encoding="utf-8")
            if (profile_home / "config.yaml").exists()
            else None
        )
        remove_inherited_memory(profile_home)

        proc = run(
            [
                "hermes",
                "profile",
                "install",
                args.source,
                "--name",
                args.profile,
                "--alias",
                "--yes",
                "--force",
            ],
            check=False,
        )
        if proc.returncode != 0:
            raise SystemExit(proc.stderr or proc.stdout)

        if preserved_config is not None:
            (profile_home / "config.yaml").write_text(preserved_config, encoding="utf-8")

    if args.skip_activation:
        print(f"Installed Agent K1-K1 profile at {profile_home}. Autonomous routines were not enabled.")
        return 0

    activate = profile_home / "scripts" / "activate.py"
    if not activate.exists():
        raise SystemExit(f"Installed profile is missing {activate}")

    cmd = [
        sys.executable,
        str(activate),
        "--profile",
        args.profile,
        "--deliver",
        args.deliver,
    ]
    if args.start_gateway:
        cmd.append("--install-gateway")
    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    raise SystemExit(main())
