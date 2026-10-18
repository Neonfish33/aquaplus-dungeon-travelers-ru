# -*- coding: utf-8 -*-
import os, csv, re, struct, shutil, bisect
from translit import enc, unmapped

SRC = 'Data/ENG/Parameter'
BAK = 'Data/ENG/Parameter_orig'
TSV = 'перевод/parameter.ru.tsv'

if not os.path.isdir(BAK):
    shutil.copytree(SRC, BAK)

rows = {}
for r in csv.DictReader(open(TSV, encoding='utf-8'), delimiter='\t'):
    rows.setdefault(r['file'], []).append((int(r['offset']), r['text']))

stats = []
for fn in sorted(rows):
    src = os.path.join(BAK, fn)
    if not os.path.isfile(src):
        continue
    d = open(src, 'rb').read()
    n = len(d)
    starts = [0] + [m.end() for m in re.finditer(b'\x00', d)]
    starts = [s for s in starts if s < n]
    end_of = {}
    for s in starts:
        e = d.find(b'\x00', s)
        end_of[s] = n if e < 0 else e

    groups = {}
    for off, txt in rows[fn]:
        if not any(ord(ch) > 127 for ch in txt):
            continue
        i = bisect.bisect_right(starts, off) - 1
        if i < 0:
            continue
        s = starts[i]
        e = end_of[s]
        if off > e or e - s < 1:
            continue
        if not all(32 <= c < 127 for c in d[s:e]):
            continue
        groups.setdefault(s, []).append((off, txt))

    out = bytearray(d)
    remap = {}
    for s in sorted(groups):
        if s in remap:
            continue
        refs64 = [m.start() for m in re.finditer(re.escape(struct.pack('<Q', s)), d)]
        covered = set()
        for p in refs64:
            covered.update(range(p, p + 8))
        refs32 = [m.start() for m in re.finditer(re.escape(struct.pack('<I', s)), d) if m.start() % 4 == 0 and m.start() not in covered]
        if not refs64 and not refs32:
            continue
        joined = '\r\n'.join(t for _, t in sorted(groups[s]))
        rep = enc(joined) + b'\x00'
        new = len(out)
        out += rep
        remap[s] = new
        for p in refs64:
            struct.pack_into('<Q', out, p, new)
        for p in refs32:
            struct.pack_into('<I', out, p, new)

    if not remap:
        print('%-24s groups=%-4d  (no refs, kept)' % (fn, len(groups)))
        continue
    open(os.path.join(SRC, fn), 'wb').write(bytes(out))
    stats.append((fn, len(groups), len(remap), len(d), len(out)))

for st in stats:
    print('%-24s groups=%-4d repl=%-4d %d -> %d' % st)
print('unmapped chars:', sorted(unmapped))
