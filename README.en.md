# Aquaplus Dungeon Travelers 2 — RU localization tools (EN)

Russian text for **Dungeon Travelers 2: The Royal Library & The Monster Seal**
(PC, ENG 1.0). The repository contains tooling and documentation only — no game
files, fonts or translation. Everything is built from your own legal copy.

## Documentation

| Document | Russian | English |
|---|---|---|
| Project map: inventory, formats, Android | [PROJECT_MAP_RU](docs/PROJECT_MAP_RU.md) | [PROJECT_MAP_EN](docs/PROJECT_MAP_EN.md) |
| Full reverse-engineering report | [ENGINE_RU](docs/ENGINE_RU.md) | [ENGINE_EN](docs/ENGINE_EN.md) |
| Engine map: action → address/class, opcodes | [ENGINE_ACTIONS_RU](docs/ENGINE_ACTIONS_RU.md) | [ENGINE_ACTIONS_EN](docs/ENGINE_ACTIONS_EN.md) |

## Done

- 112 dialogue scripts translated to Russian; line breaks come from the translation.
- The **3-byte speaker ID** at the start of every text chunk is preserved
  (otherwise the engine eats the first letters and breaks name plates).
- Names/descriptions translated: 20 `Data\ENG\Parameter\*.bin` files (strings
  appended at EOF, table pointers patched; originals in `Parameter_orig`).
- Cyrillic embedded into `Font1.pck` / `Font2.pck`; character codes preserved.
- Text layout fixed with a static patch of `DT2_en.exe` (`.rufix` section,
  per-line cursor inside `FindGlyph`, 22 px margin), no DLL/ASI.

Known limits: some speaker plates stay Latin (the name is a separate script
string); intro credits and the menu logo are baked video/textures; `Parameter`
coverage is partial; glyph widths are set by the patch stub (field `+8` of
`UI.tex/UI2.tex` is not the advance — verified with in-memory markers).

## Install

1. Back up `Data\ENG` and `DT2_en.exe`.
2. Extract the Russian archive into the game folder, overwriting files.
3. Run `DT2_en.exe`.

## Build

```
python tools/pack_ru.py       # dialogues -> Data\ENG\Script (speaker IDs kept)
python tools/pack_param.py    # names/descriptions -> Data\ENG\Parameter (originals in Parameter_orig)
python tools/inject_ru.py     # Cyrillic into Font1.pck / Font2.pck
python tools/patch_static.py  # static patch of DT2_en.exe (.rufix)
```

| File | Role |
|---|---|
| `tools/translit.py` | Cyrillic → ASCII code table shared by the packers |
| `tools/port_pc.py` | PCK library (`parse`/`build`) used by `pack_ru.py`; not a build step |
| `tools/hookfont.cpp` | dev DLL hook and the reference `g_w[256]` table |
| `tools/injector.cpp`, `tools/build_all.bat` | 32-bit injector build (debug only) |

## Requirements

- Windows, Python 3 (Pillow, numpy); MSVC Build Tools (x86) for the dev DLL only.
- Game: PC 1.0 (`DT2_en.exe`, 2,697,728 bytes); the patch is bound to its addresses.
- Translation files (not in the repo): `перевод/translation_template.ru.csv`,
  `перевод/parameter.ru.tsv`; font `C:\Windows\Fonts\arialbd.ttf`.

## Legal

Game assets belong to their owners; the translation was made by the project
contributors. Game assets are not distributed. Code is MIT (see LICENSE).
