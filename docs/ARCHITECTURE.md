# Agent K1-K1 architecture

## Goal

Agent K1-K1 is a persistent general assistant whose continuity does not depend on one chat transcript or one language model.

The architecture intentionally reuses successful patterns from Agent Pretorius while removing Pretorius-specific experimental machinery.

## Separation of concerns

Identity lives primarily in `SOUL.md` plus provenance-rich material under `resources/identity/`.

Autobiographical and relational state lives in `local/k1k1_state/k1k1.db`.

External sourced knowledge lives in `local/knowledge_library/knowledge.db`.

Reusable procedures live in distribution skills or, when learned through use, `local/learned_skills/`.

The active model provides language generation and reasoning but is not the sole storage location for identity or history.

## Contextual recall

The `k1k1-state` plugin retrieves a compact working set before an LLM call.

Candidates come from memories, relationships, commitments, agenda items, self-model claims, action outcomes, and external knowledge.

Selection uses lexical relevance plus class, salience, and confidence signals. It is intentionally simple and inspectable for v0.1.

A later learned relevance provider may replace or augment this selector if real usage demonstrates a recurring failure.

## Autonomy

Hermes cron provides low-frequency wake cycles.

Hermes goals, loops, proactive modes, or session heartbeats can support active-session work.

No component should pretend that scheduled execution is continuous consciousness.

Autonomy exists to produce useful continuity, not activity for its own sake.

## Isolation

Kiki defaults to the Hermes profile `agent-k1k1`.

All local mutable paths are K1-K1 specific.

Agent Pretorius may run under the same Hermes installation without sharing mutable state.

Future agent-to-agent communication should be explicit and transportable across machines.

## Model portability

A future model or LoRA can change the rendering of Kiki without requiring a migration of autobiographical memory, relationship history, knowledge, or skills.

Historical LoRA material should therefore be treated as identity and voice evidence rather than as the only place the character exists.
