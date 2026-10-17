# DT2 (PC) — technical report

Everything below was verified on `DT2_en.exe` (PC, ENG 1.0, 2,697,728 bytes).
The report covers only what was done and measured.

## 1. Binary

- `DT2_en.exe` — PE32 (x86), ImageBase `0x400000`, ASLR disabled
  (DllCharacteristics `0x8100`), 5 sections: `.text` (RVA `0x1000`),
  `.rdata` (`0x198000`), `.data` (`0x27F000`, abnormally large VirtualSize),
  `_RDATA` (`0x40433000`), `.rsrc` (`0x40434000`).
- `dbdata.dll` — DRM/licensing (boost.serialization, lm::*), unrelated to text.
- Imports: DINPUT8, d3d11, FFmpeg (`av*`, `sw*`), CRIWARE inside.

## 2. Formats

### 2.1 PCK (scripts, font archives)

```
"Filename" + spaces up to 0x14
u32 data_off (name table offset relative to +0x18)
names (NUL-terminated), u32 offsets from +0x18
"Pack    " + spaces up to 0x14
u32 hsz, u32 count
count × (u32 absolute_offset, u32 size)
data, 0x10 alignment
```
Data-table offsets are absolute file offsets.

### 2.2 .fnt (font)

```
0x00: "Table" + spaces (20 bytes)
0x14: u32 texoff
0x18: u32 f1 (cell size: 56 for Font480, 68 for Font600)
0x20: glyph_count × 12 bytes: (u32 code, float U, float V)
texoff: "Texture" + spaces, then u32 W, u32 H, RGBA8888 (RGB = A)
```
Font480: 3136×672, cell 56, 672 glyphs. Font600: 3808×816, cell 68.

### 2.3 Part records (CSpriteParts)

```
u32 count; count × 0x20 bytes:
float offsetX, offsetY, advanceX, advanceY, u0, v0, u1, v1
```
Indexed by character code; `advanceX` derives from the English glyph width
(174…456 on the dialogue object).

## 3. Text port

- Source: Vita fan translation (Menori Co.), `Script/*.pck`, `*.adv.bin` blobs.
- PC and Vita scripts differ only in the 8-byte PCK header; `adv.bin` contents
  have the same structure.
- `tools/port_pc.py`: parses the PC template (names/offsets preserved),
  substitutes Vita blobs, rebuilds with 0x10 alignment.
- Result: 112 files; all 112 differ from the original PC scripts
  (`BattleAI.bin` unchanged).
- Translation text is translit-compatible (see 4.2).

## 4. Font and codes

### 4.1 Cyrillic injection

`tools/inject_ru.py`:
- reads `Font1.pck`/`Font2.pck` (originals kept as `.orig2`);
- for codes `0x20..0x7E` clears the cell and draws Cyrillic in Arial Bold
  (size = `round(f1*0.68)` → 38/46; baseline `f1*0.68`);
- writes texture pixels only; `Table` (codes/UV) is untouched.

### 4.2 Code mapping (translit)

```
а a  б b  ц c  д d  е e  ф f  г g  ч h  и i  ж j  к k  л l  м m  н n
о o  п p  я q  р r  с s  т t  ю u  в v  ш w  х x  у y  з z
ы #  й =  ь }  э &  щ {  ъ |  Э >
```
Service markers `<C1>`, `<C9>` are not re-encoded.

## 5. Text engine (addresses)

Classes (RTTI): `Utility::CSpriteParts`, `String::CString`,
`String::CStringBase`, `String::CStringCursor`, `String::CLineCursor`.

| Item | Address |
|---|---|
| vtable `CSpriteParts` | `0x65C280` |
| vtable `CStringBase` | `0x6506AC` |
| vtable `CStringCursor` | `0x6506D0` |
| ctor `CSpriteParts` | `0x51B080` |
| load `CSpriteParts` (Parts/Texture) | `0x51B480` |
| advance X / Y | `0x51B370` / `0x51B390` |
| `CFont::parse` (Table/Texture) | `0x4477A0` |
| `FindGlyph` | `0x447950` |
| draw `CStringBase` | `0x4632C0` |
| draw `CStringCursor` | `0x465940` |

`FindGlyph` (thiscall): `ecx` = CFont object, stack args:
`[esp+4]` output vertex buffer, `[esp+8]` code, `[esp+0xC]` x, `[esp+0x10]` y,
`[esp+0x14]` color, `[esp+0x18]` sx, `[esp+0x1C]` sy.
Prologue (10 bytes): `mov edx,[esp+8]` / `sub esp,8` / `xor eax,eax` / `push ebx`
(`0x447950..0x447959`), continuation at `0x44795A`.

`CFont` fields: `+0x8` cell, `+0xC` cell, `+0x10` glyph count, `+0x14`
pointer to records (code,U,V).

## 6. Root cause

The line advance comes from the **English** font metrics, not from our atlas.
Narrow Cyrillic letters got a wider step than needed, wide ones a narrower step,
producing both overlap and uneven gaps. Confirmed: with identical
`advanceX=392`, different codes produced different steps, i.e. the step follows
the original English glyph table.

## 7. Static exe patch

`tools/patch_static.py` (no DLLs):

1. Adds a `.rufix` section (RVA `0x4043A000`, raw data appended at EOF,
   characteristics `0xE0000060` — RWX, `SizeOfImage` increased).
2. Writes `E9 rel32` at `0x447950` jumping to the stub.
3. Stub (94 bytes, hand-assembled):
   - saves registers (`pushad`);
   - reads `code/x/y` from the stack;
   - if `y` changed **or** `x <= lastX` — new frame/line: `cursor = x`;
   - writes `x = cursor` back to the stack;
   - `cursor += width[code & 0xFF]`;
   - executes the stolen prologue (`mov edx,[esp+8]`, `sub esp,8`,
     `xor eax,eax`, `push ebx`) and jumps to `0x44795A`.
4. `width[256]` — bytes computed from our atlas:
   `round(ink*1.2)+2`; minimums for `. , : ; ! ?` = 12, `-` = 14,
   quotes 9–11, brackets 12, space = 14.

State (cursor/lastX/y) lives in the same section.

## 8. Verification

- The game runs with the patched exe without `dinput8.dll` or `.asi`.
- Dialogs: even spacing, no overlapping letters, lines stay inside the box
  (“Меня зовут Фрид Эйнхард…”, “Я положил книгу…”, “Если ты слышал меня…”).
- ~10 minutes of play without crashes.

## 9. Not done (fact)

- Name plates (`Chief`, `Fried`) come from another source and are untranslated.
- `Data\ENG\Parameter` (menus, items, skills) is untranslated.
- Long-line wrapping is still computed by the engine with old metrics: text
  stays inside the box, but the break point may be suboptimal.
- Vita-side porting (images/TEX, full/half-width) was not touched.
