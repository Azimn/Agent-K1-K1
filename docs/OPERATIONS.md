# Operations

## First installation

From a machine with a working Hermes installation:

```bash
python scripts/install.py --start-gateway
```

This creates the isolated `agent-k1k1` profile, installs the distribution, initializes local state, enables contextual recall, and creates bounded schedules.

## Check status

```bash
hermes -p agent-k1k1 cron status
hermes -p agent-k1k1 cron list
python runtime/k1k1_runtime.py status
```

## Chat

```bash
agent-k1k1 chat
```

If the profile alias is unavailable, use the profile form supported by the installed Hermes version.

## Preview recall

```bash
python scripts/preview_recall.py "continue the project we discussed"
```

This shows which persistent records the plugin would make available.

## Knowledge

Add sourced information with:

```bash
python runtime/knowledge_library.py add \
  --title "Example" \
  --source "https://example.com" \
  --source-type web \
  --summary "Concise reusable summary" \
  --confidence 0.8 \
  --tag example
```

Search it with:

```bash
python runtime/knowledge_library.py search "example"
```

## Backups

The most valuable long-term files will be under `local/`.

Back up the K1-K1 profile's `local/k1k1_state/`, `local/knowledge_library/`, and `local/learned_skills/` directories.

Do not copy Pretorius state into these paths.

## Updating

Distribution updates should preserve user-owned `local/` data.

After a substantial update run:

```bash
python -m unittest discover -s tests -v
python scripts/readiness.py
```
