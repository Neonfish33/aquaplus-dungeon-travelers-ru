# Aquaplus Dungeon Travelers 2 — RU localization tools (EN)

Tools and technical notes for the Russian text build of
**Dungeon Travelers 2: The Royal Library & The Monster Seal** (PC, ENG 1.0).

This repository contains **no game files, fonts, scripts or translation** —
only code and documentation. Everything is built from your own legal copy.

## What was done

Full engine reverse-engineering report (RU): [docs/ENGINE_RU.md](docs/ENGINE_RU.md)


- 112 dialogue scripts translated to Russian (full project translation);
  line breaks from the translation are preserved.
- The 3-byte speaker ID at the start of each text chunk is preserved: without it
  the engine ate the first letters and name plates broke.
- Item/skill/class names and descriptions translated: 13
  `Data\ENG\Parameter\*.bin` files (strings appended at EOF, table pointers
  patched; originals kept in `Parameter_orig`).
- Cyrillic embedded into the engine font atlases; character codes preserved.
- Root cause of overlapping letters and inconsistent left margin found: the
  engine advances glyphs using the original English metrics. Fixed with a static
  patch of `DT2_en.exe` (`.rufix` section, per-line cursor inside `FindGlyph`,
  22 px left margin), no DLL/ASI.

Known limitations: some speaker name plates stay in Latin (the name comes from a
separate script string), baked video/texture text (intro subtitles, menu logo)
is not translated, `Parameter` coverage is partial. Glyph widths are set by the
patch stub: field `+8` in the `UI.tex/UI2.tex` tables turned out not to be the
advance (verified with in-memory markers) — the engine computes the step in code.

Details and addresses: [docs/REVERSE_EN.md](docs/REVERSE_EN.md)
(Russian: [docs/REVERSE_RU.md](docs/REVERSE_RU.md)).

## Installing the result

1. Back up `Data\ENG` and `DT2_en.exe`.
2. Extract the Russian build into the game folder, overwriting files.
3. Run `DT2_en.exe`.

## Building the patch (from your copy)

```
python tools/pack_ru.py            # dialogue translation -> Data\ENG\Script (speaker IDs kept)
python tools/pack_param.py         # names/descriptions -> Data\ENG\Parameter (originals in Parameter_orig)
python tools/inject_ru.py          # inject Cyrillic into Font1.pck / Font2.pck
python tools/patch_static.py       # static patch of DT2_en.exe (adds .rufix section)
```

`tools/translit.py` — Cyrillic-to-ASCII code table used by the packers.
`tools/port_pc.py` — PCK parse/build library (`parse`/`build`) used by
`pack_ru.py`. Not a build step: the early draft ported Vita scripts, while the
final text is packed from the translation CSV.
`tools/build_all.bat` builds 32-bit `hookfont.dll`/`injector.exe`
(the DLL hook variant used during development; not needed for the release).

## Requirements

- Windows, Python 3 (Pillow, numpy), MSVC Build Tools (x86) for building.
- Game: PC version 1.0 (`DT2_en.exe`, 2,697,728 bytes). The patch is bound to
  this build's addresses.

## Legal

The game and its assets belong to their owners. The text translation was made by
the project contributors. This repository contains neither game assets nor the
translation. Do not redistribute archives containing game assets.

## Code license

MIT (see LICENSE).
