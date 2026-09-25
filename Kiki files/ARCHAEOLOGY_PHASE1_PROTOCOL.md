# Kiki Archaeology Phase 1 Protocol

Checkpoint: `5e8ece86b5f26fcf1333762c8e5b3031ddde2149`

This document governs the first systematic archaeological pass over K1-K1 / Kiki historical material.

## Branch policy

The branch `feat/kiki-files-archive` is a frozen archaeological landmark. It marks the evidence set that existed when systematic Kiki archaeology began.

Ongoing archaeology belongs on `feat/kiki-archaeology-phase1` or later archaeology branches. Do not move the archive branch forward as ordinary development proceeds.

The checkpoint above is archaeological, not a cognitive-architecture milestone.

## Initial evidence priority

Phase 1 search priority is:

1. Genuine historical Kiki conversations and interaction records.
2. Original PersonaConsole v6 Kiki profile.
3. Original `corpus_kiki.txt`.
4. Original Kiki LoRA material, including datasets, adapters, or training artifacts.

This ordering is an archaeological presumption, not a permanent truth ranking. Reclassify material when direct inspection gives stronger provenance.

The rationale is that genuine interactions may show what Kiki actually did in context; a profile shows what Kiki was intended to be; a corpus shows what behavior someone attempted to reinforce; and LoRA artifacts may represent an additional transformation of earlier evidence.

## Absence is evidence

Absence must be recorded, not silently ignored.

If a characteristic appears repeatedly in persona specifications but rarely or never appears in genuine historical interactions, record that discrepancy.

If a characteristic repeatedly appears in genuine interactions despite not being prescribed by authored persona material, record that as a potentially emergent consistency.

Do not infer absence from a small or biased sample. Record the inspected corpus size, date range, source coverage, and relevant limitations.

## No automatic truth class

`current_identity/` is important authored evidence. It is not automatically historical truth.

`SOUL.md`, `KIKI_FOUNDATION.md`, and `LEGACY_KIKI_EVIDENCE.md` describe current intended identity and current interpretations of older material. Historical evidence is allowed to disagree with them.

Preserve disagreement. Do not edit historical artifacts to make them agree with current identity.

Later cognitive architecture may decide how different evidence classes influence present Kiki. Archaeology only records what the sources support.

## Evidence classes

Keep these classes distinct wherever possible:

- genuine historical interaction
- authored persona specification
- generated or converted persona artifact
- synthetic training example
- corpus or reinforcement material
- LoRA training artifact
- current autobiographical interaction
- derived analysis
- reconstruction

Do not promote one class into another without explicit evidence.

## Original versus reconstruction

An original artifact must be byte-identical to the recovered historical source when byte verification is possible.

A reconstructed equivalent may be useful, but it must be permanently labeled `reconstruction` and must never be represented as an original.

The unresolved `PersonaConsole_v5.zip` remains source-coordinate evidence only until its exact binary is obtained and verified. Do not reconstruct it in place.

## Recovery record

For each recovered artifact, record when available:

- source repository or storage location
- branch, tag, or commit
- original path
- source blob/hash
- recovery date
- byte hash after recovery
- artifact class
- whether Kiki actually experienced it
- whether it is synthetic, authored, generated, or transformed
- known derivation chain
- conflicts with other evidence
- uncertainty and missing context

## Comparative analysis rule

Do not evaluate an isolated quote as a stable trait.

When enough genuine interaction material is recovered, compare repeated behavior against authored specifications.

Specifically track:

- prescribed traits strongly present in interaction
- prescribed traits weakly present or absent in interaction
- recurring interaction traits not prescribed in specifications
- traits that appear only after a specific architecture/model/version change
- discontinuities associated with renderer/model changes
- stable linguistic or relational patterns surviving those changes

The objective is not to make historical Kiki conform to a present-day specification.

The objective is to discover what actually persisted across Kiki's history.
