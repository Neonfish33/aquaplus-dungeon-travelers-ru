# Dungeon Travelers 2 — Russian text tools (EN)

Tools and technical notes for the Russian text build of
**Dungeon Travelers 2: The Royal Library & The Monster Seal** (PC, ENG 1.0).

This repository contains **no game files, fonts, scripts or translation** —
only code and documentation. Everything is built from your own legal copy.

## What was done

- 112 dialogue scripts translated to Russian (ported from the Vita fan translation).
- Cyrillic embedded into the engine font atlases; character codes preserved.
- Root cause of overlapping letters found and fixed: the engine advances glyphs
  using the original English font metrics. Fixed with a static patch of
  `DT2_en.exe`: a per-line cursor inside `FindGlyph`, no DLL/ASI.

Details and addresses: [docs/REVERSE_EN.md](docs/REVERSE_EN.md)
(Russian: [docs/REVERSE_RU.md](docs/REVERSE_RU.md)).

## Installing the result

1. Back up `Data\ENG` and `DT2_en.exe`.
2. Extract the Russian build into the game folder, overwriting files.
3. Run `DT2_en.exe`.

## Building the patch (from your copy)

```
python tools/port_pc.py            # port Vita scripts to PC (translation sources required)
python tools/inject_ru.py          # inject Cyrillic into Font1.pck / Font2.pck
python tools/patch_static.py       # static patch of DT2_en.exe (adds .rufix section)
```

`tools/build_all.bat` builds 32-bit `hookfont.dll`/`injector.exe`
(the DLL hook variant used during development; not needed for the release).

## Requirements

- Windows, Python 3 (Pillow, numpy), MSVC Build Tools (x86) for building.
- Game: PC version 1.0 (`DT2_en.exe`, 2,697,728 bytes). The patch is bound to
  this build's addresses.

## Legal

The game and its assets belong to their owners. The text translation is the work
of Menori Co. (Vita). This repository contains neither game assets nor the
translation. Do not redistribute archives containing game assets.

## Code license

MIT (see LICENSE).
