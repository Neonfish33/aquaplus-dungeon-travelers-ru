# Dungeon Travelers 2 (PC) — full engine reverse-engineering report

Russian: [ENGINE_RU.md](ENGINE_RU.md)

Everything below was disassembled, decompiled or measured on the live game.
Only facts and measurements; uncertain points are marked as observations.

Goal: Russian text in the PC 1.0 build and fixing glyph spacing.

---

## 1. Environment and binaries

- Game: `DT2_en.exe`, PE32 (x86), 2,697,728 bytes, ImageBase `0x400000`,
  ASLR off (`DllCharacteristics = 0x8100`).
- Sections:

| Section | RVA | VirtualSize | Raw | Flags |
|---|---|---|---|---|
| `.text` | `0x1000` | `0x19639D` | `0x400` | `0x60000020` R-X |
| `.rdata` | `0x198000` | `0xE6D08` | `0x196800` | `0xC0000040` R/W |
| `.data` | `0x27F000` | `0x401B3C74` (anomaly) | `0x27D600` | `0xC0000040` R/W |
| `_RDATA` | `0x40433000` | `0x5E0` | `0x28D000` | `0x40000040` R |
| `.rsrc` | `0x40434000` | `0x5318` | `0x28D600` | `0x40000040` R |

The anomalously large `.data` VirtualSize is a build artifact; the static patch
accounts for it (§10).

- Imports: `DINPUT8.dll`, `d3d11.dll`, `dbghelp.dll`, `IMM32`, `WINMM`,
  `XINPUT1_3`, FFmpeg (`avformat-58`, `avcodec-58`, `avutil-56`, `swscale-5`,
  `avfilter-7`).
- `dbdata.dll` — licensing/DRM (173 exports, `boost::archive`, `lm::License`,
  `HardwareBinding`, `MacInfo`), unrelated to text rendering.
- The exe embeds CRIWARE (ADX/Sofdec) and DirectX 11.

Tooling: Ghidra 12.1.4 (headless via `rea-agents`), capstone, pefile, Python;
runtime: DLL hooks + `ReadProcessMemory`/`WriteProcessMemory`, later a static
PE patch.

---

## 2. Containers and resources

### 2.1 PCK (scripts, fonts, some data)

```
0x00  "Filename" + spaces up to 0x14
0x14  u32 data_off        ; name table offset relative to 0x18
0x18  name table: count × u32 offset, then NUL-terminated names
       "Pack    " + spaces up to 0x14
       u32 hsz, u32 count
       count × (u32 absolute_offset, u32 size)
       data aligned to 0x10
```

- Data-table offsets are **absolute** from the file start.
- The Vita variant differs only in the 8-byte magic header; inner `*.adv.bin`
  blobs are structurally identical — the port is built on this.

### 2.2 Font `.fnt` (inside `Font1.pck` / `Font2.pck`)

```
0x00  "Table" + spaces (20 bytes)
0x14  u32 texoff
0x18  u32 f1        ; atlas cell size
0x20  glyph_count × 12 bytes: (u32 code, float U, float V)
texoff: "Texture" + spaces
        u32 packed W|H<<16, then RGBA8888
```

- Pixel format: 4 bytes per pixel, **RGB = A** (alpha channel used).
- `Font480`: 3136×672, `f1 = 56`, 672 glyphs, grid 56×12.
- `Font600`: 3808×816, `f1 = 68`, 672 glyphs (large text).
- `Font483`/`Font603`: 491/495 glyphs (CJK), `Debug.fnt`: 93 glyphs.
- There is no `Parts` chunk inside the font files.

### 2.3 `CSpriteParts` metrics (`Parts`)

```
u32 count
count × 0x20 bytes:
    float offsetX, offsetY, advanceX, advanceY, u0, v0, u1, v1
```

The array is indexed by **character code**. For the dialogue object `advanceX`
is 174…456 (original English glyph widths). Note: the field name does not mean
the engine uses it as the text step — in-memory marker tests (§14) show the
step does not depend on it.

### 2.4 Textures (for completeness)

- `.tex` — 20-byte header, then PNG or LZ77 + palette; format differs between
  PC and Vita.
- `.ptx` — `PTX@`, `u16 w` at +6, `u16 h` at +8 (480×480, 368×367).
- `.ptg` — `PTG2`; `.ptp` — `PTP\0`.

---

## 3. Engine classes (RTTI)

RTTI strings were found and vtables reconstructed:

- `Utility::CSpriteParts` — sprite/parts (metrics, UI, name plates).
- `String::CString` → `String::CStringBase` → `String::CStringCursor`,
  `String::CLineCursor` — text subsystem.

### 3.1 `CSpriteParts`

vtable `0x65C280`:

| Slot | Address | Purpose |
|---|---|---|
| +0x00 | `0x51B190` | destructor |
| +0x04 | `0x4475E0` | base-size getter (`[this+8]`) |
| +0x08 | `0x51B2E0` | draw (sprite quad) |
| +0x0C | `0x51B370` | advance X = `[[this+0xC]+code*0x20+8]` |
| +0x10 | `0x51B390` | advance Y = `+0x0C` |
| +0x14 | `0x51B480` | load: looks for `Texture`, `Parts`, `Anime` |
| +0x18 | `0x671C9C` | RTTI |
| +0x1C | `0x51B690` | — |
| +0x20 | `0x671D24` | RTTI |
| +0x24 | `0x51BA70` | — |
| +0x28 | `0x4F5490` | — |
| +0x2C | `0x51BBB0` | — |

Constructor `0x51B080` zeroes `+8/+C`, calls `0x42AF50` (kstring) and
`0x51B480`. Loader `0x51B480`:
- finds `Texture` → `[this+4]`;
- if `Parts` found → `[this+8] = count`, `[this+0xC] = array`;
- otherwise `count = 1` and defaults from texture dimensions.

### 3.2 Text: `CStringBase` / `CStringCursor`

`CStringBase` vtable `0x6506AC`: `+0x00 0x4631D0`, `+0x04 0x463290`,
`+0x08 0x4632C0` (draw), `+0x0C 0x4639A0`, `+0x10 0x464190`,
`+0x14 0x464150`, `+0x18 0x4641F0` (clear char record),
`+0x1C 0x4641C0` (per-char loop), `+0x20 0x66CEB0`, `+0x24 0x465300`.

`CStringCursor` vtable `0x6506D0`: `+0x00 0x465300`, `+0x04 0x463290`,
`+0x08 0x465410`, `+0x0C 0x4654A0`, `+0x10 0x4654E0`, `+0x14 0x464150`,
`+0x18 0x4641F0`, `+0x1C 0x4641C0`, `+0x20 0x66CF28`, `+0x24 0x4658E0`.

Constructors:
- `CStringBase` — `0x4630B0`: `[+0xC] = param_4*0x23/10` (max chars),
  `[+0x10]` — line count, `[+0x24]` — array of char-record pointers,
  size `([+0xC]+1) << 5` (0x20 per char).
- `CString` — `0x4665F0` (calls the base ctor).
- `CStringCursor` — `0x465230`/`0x465233`: fields `+0x54…+0x64`
  (flags/color/width), creates `CLineCursor` via `0x461500`.

Char record (0x20 bytes) as read by draw:
`+0x00 X`, `+0x04 Y`, `+0x08` (extra), `+0x0C` flag, `+0x10` char code,
`+0x14` color/attrs, `+0x1C` flag.

### 3.3 Text rendering

- `CStringBase::draw` — `0x4632C0`; `CStringCursor::draw` — `0x465940`.
- First the base size is fetched: `base = [CFont+8]` (`0x4475E0`).
- Then `FUN_004642D0` returns a ratio from `60/48/44/40/36/32`
  (depends on the current mode/scale).
- Per character:
  - if code `< 0x7D0` — font `[0x6E5984]`, else `[0x6E59D0]`
    (see `0x464FF0`); for codes ≥ 2000 the index is `code - 2000`;
  - call `FindGlyph(font, code, x, y, color, sx, sy)` (`0x447950`);
  - the X step is computed in the layout code (`0x4634xx`/`0x465940`);
    `advanceX` from `CSpriteParts` does not affect it (marker test, §14);
  - `FindGlyph` applies `pen = max(0, base - adv) * ratio` to x, where
    `advanceX` is used as the glyph "landing" metric.

X offset inside `FindGlyph`: `x = charX + origin + pen`.
That is why hooking `FindGlyph` gives full control over horizontal layout.

---

## 4. `FindGlyph` — the central text function

Address `0x447950`, thiscall: `ecx` = `CFont` object.

Stack arguments:

| Offset | Argument |
|---|---|
| `[esp+4]` | pointer to the output vertex buffer |
| `[esp+8]` | character code |
| `[esp+0xC]` | x (int) |
| `[esp+0x10]` | y (int) |
| `[esp+0x14]` | color |
| `[esp+0x18]` | sx |
| `[esp+0x1C]` | sy |

Prologue (10 bytes, `0x447950…0x447959`):

```
8B 54 24 08   mov  edx,[esp+8]
83 EC 08      sub  esp,8
33 C0         xor  eax,eax
53            push ebx
```

Continuation — `0x44795A` (`mov ebx,ecx; push esi; push edi; …`).
These 10 bytes must be executed when hooking (otherwise `edx` and the stack
break — this crashed the first static-patch version).

What the function does:
- looks up the code in the glyph table `[CFont+0x14]` (12-byte records:
  code, U, V), count in `[CFont+0x10]`;
- builds 4 quad vertices of size `cell * sx` in X and `cell * sy` in Y,
  where `cell = [CFont+0xC]`;
- UV: `u = entry.u`, `v = entry.v`, plus `[CFont+0x18]` / `[CFont+0x1C]`
  corrections (cell share in the atlas);
- writes coordinates and UV into the output buffer.

`CFont` fields:

| Offset | Value |
|---|---|
| `+0x04` | texture object |
| `+0x08` | cell (duplicated with +0x0C) |
| `+0x0C` | cell |
| `+0x10` | glyph count |
| `+0x14` | record array (code,U,V) |
| `+0x18` | `cell / textureW` |
| `+0x1C` | `cell / textureH` |
| `+0x20` | flag "first code < 0x80" |

`CFont` parser — `0x4477A0` (finds `Texture` via `0x447B30`, then `Table`;
copies records).

---

## 5. Script system

- `CScript` / `CScriptTask`, 142 `CCommand_<N>` classes (decimal numbers,
  range 9…433).
- Base classes: `CCommandBase`, `CCommandPassive`, `CCommandTurn`,
  `CCommandProbability`, `CCommandUnique`.
- Families (by RTTI): Game 47, Action 34, Window 34, Menu 34, Kernel 18,
  Battle 16, Dungeon 11, Model 9, Utility 8, Title 7, String 5, Script 2,
  Command 6.
- The opcode list is dumped to `cmd_opcodes.txt` (not in the repo, generated
  from exe RTTI).
- Dialogue text lives in `Data\ENG\Script\*.pck` → `*.adv.bin` blobs;
  character codes inside are the same as in the font (translit mapping, §6.2).

---

## 6. Russian text

### 6.1 Script port

`tools/port_pc.py`:
- parses the PC PCK template (names and offset table preserved);
- takes blobs by file name (Vita scripts are only a technical template);
- rebuilds the PCK with 0x10 alignment and absolute offsets.

Result: 112 files; all differ from the original PC scripts
(`BattleAI.bin` unchanged).

### 6.2 Cyrillic in the atlases

`tools/inject_ru.py`:
- renders Arial Bold into cells of codes `0x20…0x7E`;
- size `round(f1*0.68)` → 38 (Font480) and 46 (Font600),
  baseline `f1*0.68`;
- clears the cell before drawing; `Table` is unchanged.

Code mapping:

```
а a  б b  ц c  д d  е e  ф f  г g  ч h  и i  ж j  к k  л l  м m  н n
о o  п p  я q  р r  с s  т t  ю u  в v  ш w  х x  у y  з z
ы #  й =  ь }  э &  щ {  ъ |  Э >
```

Markers `<C1>`, `<C9>` are not re-encoded (engine control inserts).

---

## 7. Cause of the step defect

Observations:
- `advanceX` for codes comes from the English font table: e.g. `'o'`=230,
  `'w'`=174, `'u'`=392, `'l'`=286, `'H'`=224, space=456 (dialogue object,
  161 records).
- Deriving the step from `advanceX` (linear model `step ≈ base − adv*ratio`)
  matches only partially: with the same `advanceX=392` the step differed
  (31…32), with `174` — 34 and 45.
- Decisive test: markers 999/888 written into `advanceX` of both tables were
  loaded by the game, but the steps did not change (space 18, `e` 31, `i` 12).
  So the step is computed in the layout code, and `CSpriteParts` is not its
  source.

Result: our glyphs are wider than English ones, while the step stays
"English" → narrow letters spread out, wide ones stick together. A uniform
X scale (1.35/1.5) does not solve it: it stretches everything.

---

## 8. Runtime tooling (used during RE)

- ASI loader: `dinput8.dll` (Ultimate ASI Loader x86); the game imports
  `DINPUT8`, so `.asi` is picked up automatically.
- `hookfont.asi` — DLL with an inline hook of `FindGlyph` (10-byte prologue)
  and `CSpriteParts` vtable hooks.
- Injection into a live process — `injector.exe` (`VirtualAllocEx` +
  `CreateRemoteThread(LoadLibraryA)`), 32-bit.
- Diagnostics: glyph positions written to a static buffer directly from the
  hook (calling C functions from a naked hook is not allowed — crash), then
  dumped from a separate thread.
- Object reads: `[0x6E5984]` (952 records) and `[0x6E59D0]` (161 records);
  metrics array — `[obj+0xC]`, record 0x20.
- `WriteProcessMemory` works, but the engine reloads the values — so the fix
  was made at code/data level, not in memory.

---

## 9. Final fix (shipped)

Static patch `tools/patch_static.py`, no DLL:

1. A `.rufix` section is added (RVA `0x4043A000`, raw at EOF,
   flags `0xE0000060` RWX), `SizeOfImage` is increased.
2. `0x447950` receives `E9 rel32` to the stub.
3. The stub (98 bytes, hand-assembled, state in the same section):
   - `pushad`, read `code/x/y` from the stack;
   - if `y` changed **or** `x <= lastX` → new frame/line: `cursor = 22`;
   - `x = cursor` is written back to the stack;
   - `cursor += width[code & 0xFF]`;
   - executes the stolen prologue and `jmp 0x44795A`.
4. `width[256]` table (bytes): `round(ink*1.2)+2` from the Font480 atlas,
   minimums: `. , : ; ! ?` = 12, `-` = 14, quotes 9…11, brackets 12,
   space = 14.

The frame is detected by `x <= lastX` because the engine redraws the line every
frame with the same coordinates; without a reset the cursor would drift right
forever (verified experimentally).

---

## 10. Verification

- Patched exe runs without `dinput8.dll` and `.asi`.
- Dialogues: even spacing, text inside the box:
  "Меня зовут Фрид Эйнхард…", "Я положил книгу, которую держал в руке…",
  "Если ты слышал меня, то мог бы хотя бы ответить мне!".
- ~10 minutes of play without crashes.
- Failed variants and causes (history): calling a C function from a naked hook
  → crash; writing into zero windows of `.rdata`/`.data` → data corruption
  (0xC0000139); a section at the "wild" `.rsrc` RVA → wrong jump; skipping the
  stolen `FindGlyph` prologue → `edx` garbage and a crash at `0x4479D4`.

---

## 11. Limitations (facts)

- Some name plates (`Chief`, `Fried`) come from a separate source and stay
  English.
- `Data\ENG\Parameter` (menus, items, skills) was not translated at the time
  of this report (now partially done by `pack_param.py`).
- Long-line wrapping is computed by the engine with old metrics: text stays in
  the box, but the break point may be suboptimal.
- The patch is bound to one build's addresses (`DT2_en.exe`, 2,697,728 bytes).
- The Vita side (TEX formats, full/half-width limits) was not touched.

---

## 12. Address summary

| Address | Purpose |
|---|---|
| `0x447950` | `FindGlyph` (glyph vertices) |
| `0x4477A0` | `CFont::parse` |
| `0x447B30` | `Texture` chunk lookup |
| `0x4475E0` | base-size getter |
| `0x4630B0` | `CStringBase` ctor |
| `0x4632C0` | `CStringBase::draw` |
| `0x4639A0` | drawing/helper |
| `0x4641C0` | per-char loop |
| `0x4641F0` | clear char record |
| `0x464FF0` | font selection by code |
| `0x465230` | `CStringCursor` ctor |
| `0x465300` | `CStringCursor` method |
| `0x465410` | `CStringCursor` draw wrapper |
| `0x4654A0` | `CStringCursor` method |
| `0x4658E0` | `CStringCursor` method |
| `0x465940` | `CStringCursor::draw` |
| `0x4665F0` | `CString` ctor |
| `0x461500` | `CLineCursor` ctor |
| `0x51B080` | `CSpriteParts` ctor |
| `0x51B2E0` | `CSpriteParts` draw (UI/name plates) |
| `0x51B370` | advance X |
| `0x51B390` | advance Y |
| `0x51B480` | `CSpriteParts` load |
| `0x51B840` | `Parts` chunk lookup |
| `0x51B8D0` | `Anime` chunk lookup |
| `0x65C280` | `CSpriteParts` vtable |
| `0x6506AC` | `CStringBase` vtable |
| `0x6506D0` | `CStringCursor` vtable |
| `0x6E5984` | font object pointer (952 records) |
| `0x6E59D0` | font object pointer (161 records, dialogue) |
| `0x4479D4` | crash site if the prologue is skipped (`mov [edx+8],0`) |

---

## 13. Repository tools

| File | Purpose |
|---|---|
| `tools/port_pc.py` | PCK parse/build library (used by `pack_ru.py`) |
| `tools/pack_ru.py` | dialogue CSV → `Data\ENG\Script` (speaker ID preserved) |
| `tools/pack_param.py` | names/descriptions → `Data\ENG\Parameter` |
| `tools/translit.py` | Cyrillic → ASCII code table |
| `tools/inject_ru.py` | Cyrillic into Font1/Font2 atlases |
| `tools/patch_static.py` | static exe patch (`.rufix`) |
| `tools/hookfont.cpp` | dev DLL hook (reference cursor algorithm, `g_w[256]`) |
| `tools/injector.cpp` | DLL injection into a live process |
| `tools/build_all.bat` | x86 DLL/injector build |

---

## 14. Font metrics: what was verified (update)

- Font selection by code — `0x464FF0`: codes `< 0x7D0` → object `[0x6E5984]`
  (952 records, `Parts` from `Data\ENG\UI.tex`), codes `>= 0x7D0` →
  `[0x6E59D0]` (161 records, `Parts` from `Data\ENG\UI2.tex`).
- `0x51B370` (advX) = `fld [[this+0xC] + code*32 + 8]`; `0x51B390` (advY) —
  field `+0xC`. Wrappers: `0x464F70` (advX by code), `0x464FB0` (advY).
- Field `+8` is **not** the advance: after writing markers 999/888 into both
  files the game loaded them (verified by reading process memory), but the steps
  stayed the same (space 18, `e` 31, `i` 12). The step is computed in the layout
  code (`0x4634xx` / `0x465940`), not taken from these tables.
- Real engine steps (`FindGlyph` log, clean exe): space 18, `i`/`l` 11,
  `t` 22.5, `e` 31, `o` 32, `w` 45.
- Practical conclusion: widths are set by the patch stub (`.rufix`); line
  breaks in the translation are manual, so engine metrics do not affect
  wrapping.
