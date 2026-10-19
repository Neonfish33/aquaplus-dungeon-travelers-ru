# Dungeon Travelers 2 (PC) — project map, RE summary and Android path

Russian: [PROJECT_MAP_RU.md](PROJECT_MAP_RU.md)

This document collects the project layout, reverse-engineering results, data
formats and realistic options for "restoring the engine" / porting to Android.

---

## 1. Project

Russian localization of **Dungeon Travelers 2: The Royal Library & The Monster
Seal** (PC, ENG 1.0, `DT2_en.exe`). No DLL/ASI: text, font, `Parameter` and a
static exe patch. Originals are kept nearby (`.orig`, `Parameter_orig`,
`DT2_en.clean.exe`).

Working folder example: `...\DungeonTravelers2_EN\`.

---

## 2. Files

### 2.1 Tools (working folder root; a subset is in the repo)

| File | Purpose |
|---|---|
| `patch_static.py` | static patch of `DT2_en.exe`: `.rufix` section, `FindGlyph` stub, width table |
| `pack_ru.py` | dialogues: CSV → `Data\ENG\Script` (PCK), keeps the 3-byte speaker ID |
| `pack_param.py` | names/descriptions → `Data\ENG\Parameter\*.bin` (strings at EOF, pointers patched) |
| `translit.py` | Cyrillic → ASCII code table shared by the packers |
| `inject_ru.py` | Cyrillic into `Font1.pck` / `Font2.pck` |
| `port_pc.py` | PCK parse/build library (`parse`/`build`) and early Vita→PC port |
| `hookfont.cpp` | dev DLL hook (reference cursor algorithm / `g_w[256]`) |
| `hooklog.cpp` | dev `FindGlyph` logger (code, x, y) |
| `injector.cpp` | 32-bit DLL injector |
| `build_all.bat`, `build_log.bat` | x86 tool builds (MSVC BuildTools) |
| `find_calls.py`, `font_parse.py`, `scan_font.py`, etc. | one-off research scripts |

### 2.2 Game data

| Path | Contents |
|---|---|
| `Data\ENG\Script\` | 112 PCK scripts (Russian text) |
| `Data\ENG\Script_orig\` | original English PCK |
| `Data\ENG\Script_prev\` | early port snapshot (archive) |
| `Data\ENG\Font1.pck`, `Font2.pck` | 480/600 fonts with Cyrillic (`*.orig`, `*.orig2`) |
| `Data\ENG\Parameter\` | 27 `.bin`: classes, items, skills, enemies, trophies |
| `Data\ENG\Parameter_orig\` | original `.bin` |
| `Data\ENG\UI.tex`, `UI2.tex` | UI atlases and metrics tables (`Parts`) |
| `DT2_en.exe` | patched exe (`.rufix`) |
| `DT2_en.clean.exe` | clean exe (logging/rollback) |

### 2.3 Translation and releases

| Path | Contents |
|---|---|
| `перевод\translation_template.ru.csv` | 35,521 rows: `id=file|blob|offset`, `src_en`, `dst_ru` |
| `перевод\parameter.ru.tsv` | 8,443 rows of names/descriptions |
| `перевод\scripts\` | text dumps of scripts |
| `перевод\check_translation.py` | markup/length checks |
| `dist\DT2_RU_v2.zip` | release (exe + 2 fonts + 112 scripts + 27 Parameter) |

---

## 3. RE summary

### 3.1 Binary

| Parameter | Value |
|---|---|
| Format | PE32, x86 (32-bit), ImageBase `0x400000`, ASLR off |
| Graphics | `d3d11.dll`, `dxgi.dll` (D3D11) |
| Input | `DINPUT8.dll`, `XINPUT1_3.dll` |
| Video | `avformat-58` / `avcodec-58` / `avutil-56` / `swscale-5` (ffmpeg) |
| Sections | `.text 0x1000`, `.rdata 0x198000`, `.data 0x27F000`, `_RDATA 0x40433000`, `.rsrc 0x40434000` |

### 3.2 Key addresses

| Address | Purpose |
|---|---|
| `0x447950` | `FindGlyph`: glyph draw (out, code, x, y, color, sx, sy) |
| `0x4477A0` | CFont parser (texture, cell, count, 12-byte entries, U/V) |
| `0x464FF0` | font selection: `<0x7D0` → `[0x6E5984]`, else `[0x6E59D0]` |
| `0x464F70` / `0x464FB0` | advX / advY by code |
| `0x51B370` / `0x51B390` | `fld [[this+0xC]+code*32+8/0xC]` (CSpriteParts advX/advY) |
| `0x4632C0` | `CStringBase::draw`; `0x465940` — `CStringCursor::draw` |
| `0x4634xx` | line layout/draw loop (`esi += 0x20` over glyph records) |
| `0x4651D0` | width-by-code wrapper (advX + rounding `0x588490`) |
| `0x6E5984`, `0x6E59D0` | font objects (CSpriteParts, vtable `0x65C280`) |
| `0x6E59B0` | font pointer array by size (60/48/44/40/36/32) |
| `0x65C280` | CSpriteParts vtable: `+0xC` advX, `+0x10` advY, `+0x14` load |

### 3.3 Text

- PCK: `Filename` / `Pack` headers, `(offset,size)` table, `*.adv.bin` blobs.
- Each text chunk starts with a **3-byte speaker ID** (`FF FF FF` = none).
  Replacing it with text makes the engine eat the first letters and breaks
  name plates. `pack_ru.py` preserves it.
- Strings are `NUL`-separated; line breaks in the translation are manual
  (`\n`), so engine metrics do not affect wrapping.
- Transliteration: Cyrillic is encoded with ASCII codes; Cyrillic glyphs live
  at those codes in the fonts (`translit.py`).

### 3.4 Fonts

- `Font1.pck` / `Font2.pck`: `Table` (12-byte records: code, U, V) and
  `Texture` (RGBA, RGB=A), 672 glyphs, cell 56/68.
- `UI.tex`: `Parts` 952 records of 32 B; `UI2.tex`: `Parts` 161 records.
  Record: `offsetX, offsetY, W, H, u0, v0, u1, v1`.
- **Field `+8` is not the advance**: markers 999/888 are loaded by the game but
  steps do not change (space 18, `i` 11, `w` 45). The step is computed in the
  layout code; the patch stub sets widths.

### 3.5 `Parameter`

- 27 `.bin`: record table + strings (names/descriptions) at the end.
- `pack_param.py` appends the translation at EOF and patches found 32/64-bit
  pointers; original data is not removed, so unpatched references stay valid.
- Coverage is partial: some strings were missing from `parameter.ru.tsv`.

### 3.6 Static `.rufix` patch

- New section RVA `0x4043A000`, flags `0xE0000060`, `SizeOfImage += 0x1000`.
- `0x447950` gets `E9 rel32`; the stub (98 bytes): `pushad`, read code/x/y,
  reset the cursor on a new line (`x <= lastX` or `y` change), 22 px left
  margin, `cursor += g_w[code]`, `popad`, stolen prologue, `jmp 0x44795A`.
- Width table `g_w[256]` from `hookfont.cpp` (ink × 1.2 + 2, punctuation
  minimums, space 14).
- No DLL/ASI; everything is inside the exe.

---

## 4. Still unknown

1. Exact advance formula in the layout (the step is not `Parts +8`).
2. Some speaker name plates stay Latin (name is a separate script string).
3. Intro credits and the menu logo are textures/video, not text.
4. Part of `Parameter` is untranslated (no rows in the TSV).
5. CG/WorldMap formats (`CG_EN.pck`) were not analyzed.

---

## 5. "Unpacking the game": what we can do

| Data | Tool | Status |
|---|---|---|
| PCK (scripts) | `port_pc.parse/build` | parse and build |
| Fonts | `font_parse.py`, `inject_ru.py` | Table/Texture parse, injection |
| UI atlases and metrics | `UI.tex`/`UI2.tex` Parts | parsed |
| `Parameter` | `pack_param.py` | table/string parse, pointer patch |
| Video/CG | ffmpeg `avformat` playlists | not analyzed |
| Audio | — | not analyzed |

---

## 6. Android path

The engine is **Win32 x86 + D3D11**. An APK needs ARM; there is no automatic
conversion.

### Option A. Winlator / Box86 + Wine + DXVK (realistic)

- 32-bit x86 via Box86, D3D11 → Vulkan via DXVK.
- The game is 2D with moderate load; chances are medium-to-good.
- This is a container, not a port; it can be packaged as an app-like shortcut.
- Test on the device: DXVK version, Box86, ffmpeg DLLs, input.

### Option B. Hybrid: emulator + HLE

- Take Wine/Box86 and replace subsystems (text/scripts) with native code.
- Requires recovering formats and entry points — weeks/months.

### Option C. Remake (Godot/Unity)

- Unpack assets (PCK/tex/parameter), reproduce battle and story.
- Months of work; native Android/PC and portability in return.

### What a "compiler for Android" would require

1. A static x86→ARM recompiler (no production-ready one exists; Box86 is an
   interpreter/JIT, not a compiler).
2. Or decompilation to C (Ghidra) + NDK: unrealistic for the whole engine, but
   possible for individual subsystems (text, scripts).
3. Practical minimum: an APK wrapper with Wine/Box86 and playable settings.

---

## 7. Legal

Game and assets belong to Aquaplus/Sting. The repository contains no game
assets, only tools and documentation; the release archive is built from a legal
copy.
