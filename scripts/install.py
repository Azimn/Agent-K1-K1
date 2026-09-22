from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_SOURCE = "github.com/Azimn/Agent-K1-K1"


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=check)


def remove_inherited_memory(profile_home: Path) -> None:
    for name in ("MEMORY.md", "USER.md"):
        for path in (profile_home / name, profile_home / "memories" / name):
            if path.exists():
                path.unlink()


def install_payload(source: str, profile: str, profile_home: Path) -> None:
    """Reinstall the requested source, including distributions with lost provenance.

    Hermes 0.21.3 --force preserves user data but replaces config.yaml. Restore
    the existing config even on failure. Let Hermes write the resolved manifest;
    copying the source's distribution.yaml afterward erases its source metadata.
    """
    config = profile_home / "config.yaml"
    preserved = config.read_bytes() if config.exists() else None
    cmd = ["hermes", "profile", "install", source, "--name", profile, "--yes"]
    if profile_home.exists():
        cmd.append("--force")
    try:
        proc = run(cmd, check=False)
        if proc.returncode != 0:
            raise SystemExit(proc.stderr or proc.stdout)
    finally:
        if preserved is not None:
            config.write_bytes(preserved)


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

    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", args.profile) or args.profile == "default":
        raise SystemExit("Use a named profile ID, not default or a filesystem path.")
    default_home = (
        Path(os.environ["LOCALAPPDATA"]) / "hermes"
        if os.name == "nt" and os.environ.get("LOCALAPPDATA")
        else Path.home() / ".hermes"
    )
    hermes_home = Path(os.environ.get("HERMES_HOME", str(default_home))).expanduser()
    profile_home = hermes_home / "profiles" / args.profile
    if profile_home.is_symlink():
        raise SystemExit("Refusing to replace a symlinked profile.")
    if profile_home.exists():
        if not (profile_home / "distribution.yaml").exists() and not args.replace_existing:
            raise SystemExit(
                f"Profile '{args.profile}' already exists but is not a distribution. "
                "Choose another --profile name or re-run with --replace-existing."
            )
    elif not args.fresh:
        # Only a just-created clone has inherited memory. Never erase memories
        # from an existing Kiki profile on an upgrade or repair.
        create = run(["hermes", "profile", "create", args.profile, "--clone-from", "default", "--no-alias"], check=False)
        if create.returncode != 0:
            raise SystemExit(create.stderr or create.stdout)
        remove_inherited_memory(profile_home)

    install_payload(args.source, args.profile, profile_home)

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
    if args.skip_activation:
        cmd.append("--skip-routines")
    if args.start_gateway:
        cmd.append("--install-gateway")
    result = subprocess.run(cmd)
    if result.returncode == 0 and args.skip_activation:
        print(f"Installed and initialized Agent K1-K1 core at {profile_home}. Background routines remain off.")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
