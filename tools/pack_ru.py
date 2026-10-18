import os, csv, sys, shutil
sys.path.insert(0, '.')
from port_pc import parse, build

SRC = 'Data/ENG/Script_orig'
DST = 'Data/ENG/Script'
CSV = 'перевод/translation_template.ru.csv'

from translit import enc, unmapped

rows = list(csv.DictReader(open(CSV, encoding='utf-8', newline='')))
per = {}
for r in rows:
    f, blob, off = r['id'].split('|')
    per.setdefault(f, {}).setdefault(blob, []).append((int(off), r['dst_ru']))

if os.path.isdir(DST) and not os.path.isdir('Data/ENG/Script_prev'):
    shutil.copytree(DST, 'Data/ENG/Script_prev')

total_blobs = changed = 0
used = set()
for fn, blobs in sorted(per.items()):
    srcp = os.path.join(SRC, fn)
    d = open(srcp, 'rb').read()
    T, Q, m, et, hsz, cnt, ents, names = parse(d)
    out_blobs = []
    for name, (off, size) in zip(names, ents):
        b = d[off:off + size]
        rows_here = blobs.get(name, [])
        if not rows_here:
            out_blobs.append(b)
            continue
        total_blobs += 1
        res = bytearray()
        pos = 0
        idx = 0
        rows_here.sort()
        while pos < len(b):
            end = b.find(b'\x00', pos)
            if end < 0:
                res += b[pos:]
                break
            chunk = []
            while idx < len(rows_here) and rows_here[idx][0] < end:
                if rows_here[idx][0] >= pos:
                    chunk.append(rows_here[idx][1])
                    used.add((fn, name, rows_here[idx][0]))
                idx += 1
            if chunk:
                pre = b''
                if pos + 3 <= end and not all(32 <= c < 127 for c in b[pos:pos + 3]):
                    pre = b[pos:pos + 3]
                res += pre + b'\n'.join(enc(t) for t in chunk) + b'\x00'
                changed += 1
            else:
                res += b[pos:end + 1]
            pos = end + 1
        out_blobs.append(bytes(res))
    new = build(d, T, Q, m, et, hsz, cnt, ents, names, out_blobs)
    open(os.path.join(DST, fn), 'wb').write(new)

print('files', len(per), 'blobs changed', changed, 'of', total_blobs)
print('rows used', len(used), 'of', len(rows))
print('unmapped chars:', sorted(unmapped))
