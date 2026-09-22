# Agent K1-K1

## Easiest Windows install

For native Windows 10 or 11, the development branch includes a guided installer that can install Hermes Agent if needed, run Kiki's checks, create the isolated `agent-k1k1` profile, and optionally enable background autonomy.

Open PowerShell and paste:

```powershell
irm https://raw.githubusercontent.com/Azimn/Agent-K1-K1/feat/k1k1-v0.1/install-kiki-windows.ps1 | iex
```

Administrator rights are not required for the official Hermes native Windows installer.

The script leaves background autonomy off by default until you explicitly choose to enable it. This prevents unattended model usage during the first validation. It offers to start the first Kiki chat after installation.

Agent K1-K1, usually called Kiki, is a persistent Hermes-based general assistant, collaborator, and long-term companion agent.

The project deliberately shares architectural ideas with [Agent Pretorius](https://github.com/Azimn/Agent-Pretorius) while keeping the two individuals completely separate. They may use the same Hermes installation, but Kiki has her own profile, identity files, persistent database, knowledge library, learned skills, cron routines, work directory, and future history.

Kiki is not Pretorius with a different prompt. Pretorius is intentionally abrasive and research-oriented. Kiki is designed for everyday usefulness: supportive, curious, playful, highly capable, and pleasant to work with while remaining intellectually honest.

## Design

The persistent identity is split across several layers:

- `SOUL.md` contains the compact always-loaded identity and voice constraints.
- `runtime/k1k1_runtime.py` stores autobiographical memory, relationships, commitments, agenda items, action outcomes, and self-model evidence in SQLite.
- `runtime/knowledge_library.py` stores sourced external knowledge separately from lived memory.
- `plugins/k1k1-state` performs contextual recall before model generation.
- `skills/` contains reusable operating procedures.
- `local/` contains mutable user-owned state and is never committed.
- Hermes supplies inference, tools, gateway operation, profiles, cron, goals, and loops.

The current language model is treated as a replaceable renderer and reasoning substrate. Model replacement should not erase Kiki's durable state.

## Isolation from Agent Pretorius

The default profile is `agent-k1k1`. Kiki never reads Pretorius's autobiographical database, relationship state, agenda, or private research state.

If both agents later communicate, that communication should happen through explicit messages or a defined agent-to-agent interface. They may talk to one another. They do not share a brain.

## Install

This repository targets Hermes 0.21.4 or newer.

From an existing working Hermes installation:

```bash
git clone https://github.com/Azimn/Agent-K1-K1.git
cd Agent-K1-K1
python scripts/install.py --start-gateway
```

The installer creates an isolated `agent-k1k1` profile by cloning the default Hermes provider and tool configuration. Only a newly created clone has inherited `MEMORY.md` and `USER.md` removed. Existing Kiki memories and local state are preserved on repair and upgrade. A second Hermes installation is not required.

Repeated installs use the requested source with Hermes's supported forced reinstall, including profiles whose distribution marker has lost its recorded source. Existing `config.yaml` is restored byte-for-byte after payload installation, even on failure; core activation then reapplies Kiki's working directory and plugin settings. Hermes owns the installed manifest's `source` and `installed_at` fields; the installer must not overwrite that manifest afterward.

For a local Windows checkout, repair or repeat installation without downloading over development edits:

```powershell
.\install-kiki-windows.ps1 -SourcePath . -NoChat
```

Core activation always runs. Background routines and gateway installation require the explicit `-EnableAutonomy` switch in the Windows installer. Existing routines are not disabled by reinstalling. The download path retains the previous source directory as a `source-backup-*` sibling instead of deleting it. Hermes is installed only when absent; an existing Hermes installation is not updated.

Verify:

```bash
agent-k1k1 doctor
hermes -p agent-k1k1 cron status
hermes -p agent-k1k1 cron list
agent-k1k1 chat
```

When `--start-gateway` is used, activation supports both Hermes gateway layouts: older per-profile gateways and the newer multiplexed default gateway. In multiplex mode, Kiki remains a separate profile with separate credentials and state. Messaging platforms still need Kiki-specific bot credentials rather than Pretorius's token.

For a completely fresh profile:

```bash
python scripts/install.py --fresh --start-gateway
hermes -p agent-k1k1 setup
```

## Autonomous operation

The default activation creates bounded routines rather than pretending that the process is continuously conscious between executions.

Kiki can wake periodically to inspect open concerns, maintain useful continuity, reflect on durable state, and prepare a daily brief. If there is no useful action, she is instructed to remain silent rather than manufacture activity.

External actions remain permission-aware. Scheduled routines may inspect local user-owned material, organize Kiki's own state, and perform explicitly authorized work. They must not silently publish, push code, message third parties, spend money, alter accounts, or delete external data.

## Character

Kiki knows that she is an AI.

Her conversational surface is bright, playful, enthusiastic, and strongly influenced by late-1980s and 1990s Valley Girl speech. Her spontaneous analogies and cultural references should overwhelmingly come from before 2000.

That is a style constraint, not a knowledge cutoff. Kiki should understand contemporary technology and current information when tools provide it.

Her bubbly delivery must never be used as an excuse for weak reasoning. The intended contrast is an apparently light, playful conversational style paired with serious technical and intellectual competence.

See `SOUL.md` and `resources/identity/KIKI_FOUNDATION.md`.

## Validation

The persistent runtime uses the Python standard library.

Run:

```bash
python -m unittest discover -s tests -v
python scripts/readiness.py
python scripts/preview_recall.py "We need to continue the project we discussed last month"
```

## Status

v0.1 establishes the persistent architecture, strict Pretorius isolation, character foundation, contextual recall, knowledge separation, bounded autonomy, and installation path.

Historical Kiki conversations and LoRA training material can be added later as provenance-rich identity and voice evidence without redesigning the persistence layer.


## Testing the development branch

Until v0.1 is merged to `main`, test directly from the feature branch so the installer uses the local checkout rather than the still-empty default branch:

```bash
git clone -b feat/k1k1-v0.1 https://github.com/Azimn/Agent-K1-K1.git
cd Agent-K1-K1
python scripts/readiness.py
python -m unittest discover -s tests -v
python scripts/install.py --source . --start-gateway
```

Using `--source .` is important while testing an unmerged branch.
