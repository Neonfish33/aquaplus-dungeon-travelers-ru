import os
import re
import struct
import sys
import shutil

PC_SCRIPT = os.environ.get("DT2_PC_SCRIPT", os.path.join("Data", "ENG", "Script"))
PC_PARAM = os.environ.get("DT2_PC_PARAM", os.path.join("Data", "ENG", "Parameter"))
VITA = os.environ.get("DT2_VITA", "")
VITA_SCRIPT = os.path.join(VITA, "Script") if VITA else ""
VITA_PARAM = os.path.join(VITA, "Parameter") if VITA else ""


def parse(d):
    assert d[:8] == b"Filename", d[:8]
    if d[8:0x14] == b" " * 12:
        T = 0x18
    else:
        T = 0xC
    Q = d.find(b"Pack    ")
    m = Q + 0x14 if d[Q + 4:Q + 0x14] == b" " * 16 else Q + 8
    hsz = struct.unpack_from("<I", d, m)[0]
    cnt = struct.unpack_from("<I", d, m + 4)[0]
    et = m + 8
    ents = [struct.unpack_from("<II", d, et + 8 * k) for k in range(cnt)]
    names = []
    for k in range(cnt):
        o = struct.unpack_from("<I", d, T + 4 * k)[0]
        names.append(d[T + o:d.find(b"\x00", T + o, T + o + 0x40)].decode("latin1"))
    return T, Q, m, et, hsz, cnt, ents, names


def build(templ, T, Q, m, et, hsz, cnt, ents, names, blobs, align=0x10):
    hdr = bytearray(templ[:Q + hsz])
    cur = Q + hsz
    for k in range(cnt):
        off = (cur + align - 1) & ~(align - 1) if align > 1 else cur
        struct.pack_into("<II", hdr, et + 8 * k, off, len(blobs[k]))
        cur = off + len(blobs[k])
    out = bytearray(hdr)
    for k in range(cnt):
        off = struct.unpack_from("<I", hdr, et + 8 * k)[0]
        if len(out) < off:
            out += b"\x00" * (off - len(out))
        out[off:off + len(blobs[k])] = blobs[k]
    return bytes(out)


def vita_blobs(path):
    d = open(path, "rb").read()
    if d[8:0x14] == b" " * 12:
        T = 0x18
    else:
        T = 0xC
    Q = d.find(b"Pack    ")
    m = Q + 0x14 if d[Q + 4:Q + 0x14] == b" " * 16 else Q + 8
    cnt = struct.unpack_from("<I", d, m + 4)[0]
    et = m + 8
    ents = [struct.unpack_from("<II", d, et + 8 * k) for k in range(cnt)]
    names = []
    for k in range(cnt):
        o = struct.unpack_from("<I", d, T + 4 * k)[0]
        names.append(d[T + o:d.find(b"\x00", T + o, T + o + 0x40)].decode("latin1"))
    return {n: d[o:o + s] for n, (o, s) in zip(names, ents)}


def convert_pck(templbytes, vb, align=0x10):
    T, Q, m, et, hsz, cnt, ents, names = parse(templbytes)
    blobs = [vb.get(n, templbytes[o:o + s]) for n, (o, s) in zip(names, ents)]
    return build(templbytes, T, Q, m, et, hsz, cnt, ents, names, blobs, align=align)


def main():
    indir = sys.argv[1] if len(sys.argv) > 1 else PC_SCRIPT
    vidir = VITA_SCRIPT if "Script" in indir or indir == PC_SCRIPT else VITA_PARAM
    outdir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(indir), os.path.basename(indir) + "_ru")
    os.makedirs(outdir, exist_ok=True)
    n_ok = n_skip = 0
    for f in sorted(os.listdir(indir)):
        src = os.path.join(indir, f)
        if not os.path.isfile(src):
            continue
        vp = None
        for cand in os.listdir(vidir):
            if cand.lower() == f.lower():
                vp = os.path.join(vidir, cand)
                break
        if vp is None:
            shutil.copyfile(src, os.path.join(outdir, f))
            n_skip += 1
            continue
        data = open(src, "rb").read()
        try:
            vb = vita_blobs(vp)
            new = convert_pck(data, vb)
        except Exception as e:
            print("  ERR %s: %s" % (f, e))
            shutil.copyfile(src, os.path.join(outdir, f))
            n_skip += 1
            continue
        open(os.path.join(outdir, f), "wb").write(new)
        n_ok += 1
    print("converted %d, copied %d -> %s" % (n_ok, n_skip, outdir))


if __name__ == "__main__":
    main()
