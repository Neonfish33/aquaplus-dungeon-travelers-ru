# Dungeon Travelers 2 — карта движка: что какое действие отвечает

English: [ENGINE_ACTIONS_EN.md](ENGINE_ACTIONS_EN.md)

Сводка по внутреннему устройству PC-версии: адреса функций, классы, опкоды,
форматы. Дополняет [PROJECT_MAP_RU.md](PROJECT_MAP_RU.md) и
[ENGINE_RU.md](ENGINE_RU.md).

> Исторические заметки реверса. Часть выводов §3 уточнена позже: поле `+8`
> таблицы `Parts` **не** задаёт шаг текста (проверено маркерами в памяти —
> см. §14 в `ENGINE_RU.md`). Итоговый шаг задаёт стаб патча `.rufix`.

---

## 1. Движок

- Разработчик — Sting, издатель — Aquaplus.
- Внутренний движок Sting «ig» (в PSP-EBOOT строки `igTexture`,
  `igPackedArchive`, `igStringHashTable`, `igFileContext`); на PC вынесен в
  `dbdata.dll` (~9.6 МБ).
- Промежуточное ПО: CRIWARE (ADX-аудио, Sofdec/PMF-видео), рендер DirectX 11,
  видео на PC декодирует FFmpeg (`av*.dll`, `sw*.dll`).
- Данные — контейнеры Aquaplus PCK (`Filename`/`Pack`) и SFS (PSP).

---

## 2. Форматы

### 2.1 PCK (скрипты, шрифты, данные)

```
"Filename" + пробелы до 0x14
+0x14: u32 data_off
+0x18: таблица смещений имён (u32, относительно +0x18)
... имена (null-terminated)
data_off: "Pack" + пробелы (магия 0x14)
+0x14: u32 hsz
+0x18: u32 count
+0x1C: count × (u32 offset_абс, u32 size)
данные: с Q+hsz, выравнивание 0x10, смещения абсолютные
```

Vita-PCK отличается магией (8 байт вместо 20). Саб-файлы `*.adv.bin` PC↔Vita
идентичны, кроме текста.

### 2.2 SFS (PSP `DATA0.SFS`)

- Заголовок `STFS 2012 STING`, зашифрованный каталог 0..0x16000.
- Блоки `ZLB\0`: `+0x0C` имя, `+0x28` usize, `+0x2C` csize, `+0x30` total,
  `+0x34` zlib. Следующий блок: `align(cur+total, 0x800)`.

### 2.3 Шрифт (`Font1.pck` / `Font2.pck`)

Чанки: `[id 20 байт][size u32 @+0x14][data @+0x18]`, порядок
`Table` → `Texture`.

- **Table**: `u32 0x38`, `u32 count`, затем `count × 12`:
  `[u32 code][float U][float V]`.
- **Texture**: `u16 w | u16 h`, далее RGBA8888, RGB = A.
  `Font480`: 3136×672, ячейка 56; `Font600`: 3808×816, ячейка 68.

### 2.4 `Parts` (метрики, в файле отсутствуют)

Формат восстановлен из памяти:
`data = [u32 count] + count × 0x20`, запись = 8 float:
`offsetX, offsetY, advanceX, advanceY, u0, v0, u1, v1`.

### 2.5 Текстуры

- `.tex` — чанк-контейнер `Texture` + заголовок (формат/bspp) + пиксели.
- `.ptx` — магия `PTX@`, w/h u16 @+0x6/+0x8.
- `.ptg` (`PTG2`), `.ptp` (`PTP`) — групповые/палитровые.

---

## 3. Реверс текста: действие → адрес

| Что | Адрес |
|---|---|
| vtable класса шрифта | `0x65C280` |
| Конструктор объекта шрифта | `0x51B080` |
| Загрузка шрифта (метрики) | `0x51B480` |
| Поиск чанка по имени | `0x447B30`; `Parts` — `0x51B840`; `Anime` — `0x51B8D0` |
| Разбор `CFont` (Table/Texture) | `0x4477A0` |
| Построение квада глифа | `0x447950` (`FindGlyph`) |
| Обёртка «шаг X» | `0x464F70` → `[vtable+0xC]` |
| Обёртка «шаг Y» | `0x464FB0` → `[vtable+0x10]` |
| Метод шага X | `0x51B370`: `float[[obj+0xC]+code*0x20+8]` |
| Метод шага Y | `0x51B390`: `float[[obj+0xC]+code*0x20+0xC]` |
| Отрисовка строки | `0x4632C0` |
| Рендерер диалогов/сообщений | `0x465233` (позже `0x465940`) |
| Выбор шрифта по коду | `0x464FF0`: `<0x7D0` → `[0x6E5984]`, иначе `[0x6E59D0]` |
| Базовое значение `base` | `0x4475E0` (`mov eax,[ecx+8]; ret`) |
| Коэффициент `ratio` | `0x4642D0`: 60/48/44/40/36/32 |

Историческая модель (не подтвердилась как источник шага):

```
pen_delta = max(0, base - advX) * ratio * 0.5
```

Позже проверено: маркеры 999/888 в `advanceX` игра загружает, но шаги не
меняются (space 18, `i` 11, `w` 45). Шаг считается в коде раскладки
(`0x4634xx`); в поставке его задаёт стаб `.rufix`.

---

## 4. Скриптовый движок (команды/опкоды)

- `CScript`, `CScriptTask` — исполнитель; скрипт = поток команд.
- Каждый опкод — класс `CCommand_<N>`; базы: `CCommandBase`,
  `CCommandPassiveBase`, `CCommandTurnBase`, `CCommandProbabilityBase`,
  `CCommandUniqueBase`.
- Всего **142** команды, номера **9..433** (`cmd_opcodes.txt`):

```
9,10,11,17,18,20,21,26,27,28,30,31,32,41,42,43,44,45,46,48,66,77,80,84,
101..108,113..123,128..131,139,146,161..174,178..205,210..221,228..233,235,
246,247,262,272,273,291,312,325..329,335..341,416..423,425..428,432,433
```

- `.adv` = поток (опкод + операнды); каждый опкод имеет отдельный обработчик.

### 4.1 Семейства классов (карта движка)

| Семейство | Кол-во | Примеры |
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

## 5. Транслитерация

```
а=a б=b ц=c д=d е=e ф=f г=g ч=h и=i ж=j к=k л=l м=m н=n о=o п=p
я=q р=r с=s т=t ю=u в=v ш=w х=x у=y з=z
ы=# й== ь=} э=& щ={ ъ=| Э=>
```

Маркеры `<C1>`, `<C9>` — ASCII, не перекодировать.

---

## 6. Android

- Нативной Android-версии DT2 нет.
- **Winlator (Android)** — PC-версия с нашим переводом (Box86 + Wine + DXVK).
- **Vita3K (Android)** — Vita-версия (потребуется отдельный порт текста).
- Для собственного порта нужен движок/исходники; форматы PCK/SFS/шрифта/текста
  выше достаточны для переноса ассетов.
