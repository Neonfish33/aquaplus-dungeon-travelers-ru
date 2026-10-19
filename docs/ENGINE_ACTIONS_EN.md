# Dungeon Travelers 2 — engine map: which function does what

Russian: [ENGINE_ACTIONS_RU.md](ENGINE_ACTIONS_RU.md)

A summary of the PC build internals: function addresses, classes, opcodes and
formats. Complements [PROJECT_MAP_EN.md](PROJECT_MAP_EN.md) and
[ENGINE_EN.md](ENGINE_EN.md).

> Historical reverse-engineering notes. Part of §3 was refined later: field
> `+8` of the `Parts` table does **not** define the text step (verified with
> in-memory markers — see §14 in `ENGINE_EN.md`). The final step is set by the
> `.rufix` patch stub.

---

## 1. Engine

- Developer — Sting, publisher — Aquaplus.
- Internal Sting "ig" engine (PSP EBOOT strings `igTexture`,
  `igPackedArchive`, `igStringHashTable`, `igFileContext`); on PC it lives in
  `dbdata.dll` (~9.6 MB).
- Middleware: CRIWARE (ADX audio, Sofdec/PMF video), DirectX 11 rendering;
  video on PC is decoded by FFmpeg (`av*.dll`, `sw*.dll`).
- Data — Aquaplus containers PCK (`Filename`/`Pack`) and SFS (PSP).

---

## 2. Formats

### 2.1 PCK (scripts, fonts, data)

```
"Filename" + spaces up to 0x14
+0x14: u32 data_off
+0x18: name offsets (u32, relative to +0x18)
... NUL-terminated names
data_off: "Pack" + spaces (magic 0x14)
+0x14: u32 hsz
+0x18: u32 count
+0x1C: count × (u32 absolute offset, u32 size)
data: from Q+hsz, 0x10 alignment, absolute offsets
```

Vita PCK differs only in magic (8 bytes instead of 20). Inner `*.adv.bin`
blobs are identical PC↔Vita except for text.

### 2.2 SFS (PSP `DATA0.SFS`)

- Header `STFS 2012 STING`, encrypted directory 0..0x16000.
- `ZLB\0` blocks: `+0x0C` name, `+0x28` usize, `+0x2C` csize,
  `+0x30` total, `+0x34` zlib. Next block: `align(cur+total, 0x800)`.

### 2.3 Font (`Font1.pck` / `Font2.pck`)

Chunks: `[id 20 bytes][size u32 @+0x14][data @+0x18]`, order
`Table` → `Texture`.

- **Table**: `u32 0x38`, `u32 count`, then `count × 12`:
  `[u32 code][float U][float V]`.
- **Texture**: `u16 w | u16 h`, then RGBA8888, RGB = A.
  `Font480`: 3136×672, cell 56; `Font600`: 3808×816, cell 68.

### 2.4 `Parts` metrics (absent in the files)

Format recovered from memory:
`data = [u32 count] + count × 0x20`, record = 8 floats:
`offsetX, offsetY, advanceX, advanceY, u0, v0, u1, v1`.

### 2.5 Textures

- `.tex` — `Texture` chunk container + header (format/bspp) + pixels.
- `.ptx` — magic `PTX@`, w/h u16 @+0x6/+0x8.
- `.ptg` (`PTG2`), `.ptp` (`PTP`) — grouped/palette textures.

---

## 3. Text RE: action → address

| Action | Address |
|---|---|
| Font class vtable | `0x65C280` |
| Font object constructor | `0x51B080` |
| Font load (metrics) | `0x51B480` |
| Chunk lookup by name | `0x447B30`; `Parts` — `0x51B840`; `Anime` — `0x51B8D0` |
| `CFont` parse (Table/Texture) | `0x4477A0` |
| Glyph quad build | `0x447950` (`FindGlyph`) |
| X-step wrapper | `0x464F70` → `[vtable+0xC]` |
| Y-step wrapper | `0x464FB0` → `[vtable+0x10]` |
| X-step method | `0x51B370`: `float[[obj+0xC]+code*0x20+8]` |
| Y-step method | `0x51B390`: `float[[obj+0xC]+code*0x20+0xC]` |
| Line draw | `0x4632C0` |
| Dialogue/message renderer | `0x465233` (later `0x465940`) |
| Font selection by code | `0x464FF0`: `<0x7D0` → `[0x6E5984]`, else `[0x6E59D0]` |
| Base size `base` | `0x4475E0` (`mov eax,[ecx+8]; ret`) |
| Ratio `ratio` | `0x4642D0`: 60/48/44/40/36/32 |

Historical model (not confirmed as the step source):

```
pen_delta = max(0, base - advX) * ratio * 0.5
```

Later verified: markers 999/888 in `advanceX` are loaded by the game, but the
steps do not change (space 18, `i` 11, `w` 45). The step is computed in the
layout code (`0x4634xx`); in the release it is set by the `.rufix` stub.

---

## 4. Script engine (commands/opcodes)

- `CScript`, `CScriptTask` — executor; a script is a command stream.
- Every opcode is a `CCommand_<N>` class; bases: `CCommandBase`,
  `CCommandPassiveBase`, `CCommandTurnBase`, `CCommandProbabilityBase`,
  `CCommandUniqueBase`.
- **142** commands, numbers **9..433** (`cmd_opcodes.txt`):

```
9,10,11,17,18,20,21,26,27,28,30,31,32,41,42,43,44,45,46,48,66,77,80,84,
101..108,113..123,128..131,139,146,161..174,178..205,210..221,228..233,235,
246,247,262,272,273,291,312,325..329,335..341,416..423,425..428,432,433
```

- `.adv` = stream (opcode + operands); each opcode has its own handler.

### 4.1 Class families (engine map)

| Family | Count | Examples |
|---|---|---|
| Game | 47 | CGame, CGameArticleItem/Equipment/SealScroll, CGameBustup |
| Action | 34 | CActionAttack, CActionDamageHPAnime, CActionAnimeBase |
| Window | 34 | CWindowBase, CWindowConfirm, CWindowEquipmentStatus |
| Menu | 34 | CMenuBase, CMenuClassChange, CMenuEquipment |
| Kernel | 18 | CAlloc, CFile, CGraphics, CMovie, CEventQueueBase |
| Battle | 16 | CBattle, CBattleAI, CBattleMenuAttack/Defense/Escape |
| Dungeon | 11 | CDungeon, CDungeonMap, CDungeonCamera, CDungeonStairs |
| Model | 9 | CModelAnime, CModelCamera, CModelMap, CModelUVAnime |
| Utility | 8 | CSprite, CSpriteParts, CPolygonBox, CDAT |
| Title | 7 | CTitle, CTitleCGGallery, CTitleEventRec |
| String | 5 | CString, CStringCursor, CStringHScroll |
| Script | 2 | CScript, CScriptTask |
| Command | 6 | CCommand*, CCommandBase |

---

## 5. Transliteration

```
а=a б=b ц=c д=d е=e ф=f г=g ч=h и=i ж=j к=k л=l м=m н=n о=o п=p
я=q р=r с=s т=t ю=u в=v ш=w х=x у=y з=z
ы=# й== ь=} э=& щ={ ъ=| Э=>
```

Markers `<C1>`, `<C9>` are ASCII and must not be re-encoded.

---

## 6. Android

- There is no native Android version of DT2.
- **Winlator (Android)** — PC build with our translation (Box86 + Wine + DXVK).
- **Vita3K (Android)** — Vita build (needs a separate text port).
- A native port needs the engine/source; the PCK/SFS/font/text formats above
  are enough to move assets between versions.
