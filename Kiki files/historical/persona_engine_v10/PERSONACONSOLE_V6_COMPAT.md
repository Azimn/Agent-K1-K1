# PersonaConsole_v6 compatibility notes

Persona Engine v10-compatible cartridges have been generated for the six PersonaConsole_v6 profile folders visible in the repository: `friendly`, `kiki`, `mentor`, `pretorius`, `quiet`, and `rival`.

The GitHub profile manifests use packed section files such as `identity.bin`, `drives.bin`, `today.bin`, `banks.bin`, and dialogue banks. The compatibility strategy is conservative:

1. Preserve each character as a `.snp` cartridge so the v10 engine can load and test it without code edits.
2. Keep all character-specific voice, body, world, sensory, avatar, and interpretation values inside the cartridge.
3. Provide `tools/convert_v6_profile.py` for future local conversion from the original PersonaConsole_v6 profile folder. It extracts printable strings from packed files as source hints, then writes a valid v10 `.snp` file.
4. Do not treat renderer speech or packed dialogue strings as canonical truth. They are source hints for authoring only.

Generated cartridges:

- `cartridges/friendly.snp`
- `cartridges/kiki.snp`
- `cartridges/mentor.snp`
- `cartridges/pretorius_v6.snp`
- `cartridges/quiet.snp`
- `cartridges/rival.snp`

The existing `cartridges/pretorius.snp` remains as the native v10 Pretorius test cartridge. `pretorius_v6.snp` is the compatibility copy aligned to the PersonaConsole_v6 profile set.
