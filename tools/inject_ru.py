import os
import sys
import struct
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import port_pc
import numpy as np
from PIL import Image, ImageFont, ImageDraw

FONT = r"C:\Windows\Fonts\arialbd.ttf"
LOW = "abcdefghijklmnopqrstuvwxyz"
LOWR = "абцдефгчижклмнопярстювшхуз"
UP = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
UPR = "АБЦДЕФГЧИЖКЛМНОПЯРСТЮВШХУЗ"
SYM = "#=&}{|>"
SYMR = "ыйэщъьЭ"
MAP = {}
for a, b in zip(LOW, LOWR):
    MAP[a] = b
for a, b in zip(UP, UPR):
    MAP[a] = b
MAP["#"] = "ы"
MAP["="] = "й"
MAP["&"] = "э"
MAP["{"] = "щ"
MAP["|"] = "ъ"
MAP["}"] = "ь"
MAP[">"] = "Э"


def bbox(arr, thr=20):
    ys, xs = np.where(arr > thr)
    if len(xs) == 0:
        return None
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def render(ch, size):
    y0 = size
    fnt = ImageFont.truetype(FONT, size)
    tmp = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(tmp).text((size, y0), "Н", fill=255, font=fnt)
    bbh = tmp.getbbox()
    baseline = bbh[3]
    im = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(im).text((size, y0), ch, fill=255, font=fnt)
    bb = im.getbbox()
    if bb is None:
        return None, 0
    base_in = baseline - bb[1]
    return im.crop(bb), base_in


def tex_magic_len(b, texoff):
    return 20 if b[texoff + 4:texoff + 0x14] == b" " * 16 else 8


def parse_font(b):
    ml = 20 if b[8:0x14] == b" " * 12 else 8
    texoff = struct.unpack_from("<I", b, ml)[0]
    f1 = struct.unpack_from("<I", b, ml + 4)[0]
    n = (texoff - 0x20) // 12
    codes = [struct.unpack_from("<I", b, 0x20 + 12 * k)[0] for k in range(n)]
    tml = tex_magic_len(b, texoff)
    tb = texoff + tml
    W = H = dataoff = None
    for off in range(tb, tb + 0x40, 4):
        v = struct.unpack_from("<I", b, off)[0]
        w = v & 0xFFFF
        h = v >> 16
        if 0 < w <= 8192 and 0 < h <= 8192 and abs((len(b) - (off + 4)) - w * h * 4) < 65536:
            W, H, dataoff = w, h, off + 4
            break
    return f1, n, codes, W, H, dataoff


def inject(blob, verbose=False):
    f1, n, codes, W, H, dataoff = parse_font(blob)
    out = bytearray(blob)
    cols = W // f1
    size = max(8, int(round(f1 * 0.68)))
    target_base = int(round(f1 * 0.68))
    done = 0
    for k in range(n):
        code = codes[k]
        if not (0x20 <= code <= 0x7E):
            continue
        ch = MAP.get(chr(code))
        if not ch:
            continue
        col = k % cols
        row = k // cols
        gx = col * f1
        gy = row * f1
        cell = np.frombuffer(bytes(blob[dataoff + ((gy + yy) * W + gx + xx) * 4 + 3] for yy in range(f1) for xx in range(f1)), dtype=np.uint8).reshape(f1, f1)
        ob = bbox(cell)
        if ob is None:
            continue
        ox = ob[0]
        g, base_in = render(ch, size)
        if g is None:
            continue
        # clear the cell
        for yy in range(f1):
            ro = dataoff + ((gy + yy) * W + gx) * 4
            for xx in range(f1):
                o = ro + xx * 4
                out[o] = out[o + 1] = out[o + 2] = out[o + 3] = 0
        pa = np.asarray(g).astype(np.uint8)
        gh, gw = pa.shape
        top = target_base - base_in
        for yy in range(gh):
            ty = gy + top + yy
            if ty < 0 or ty >= H:
                continue
            for xx in range(gw):
                tx = gx + ox + xx
                if tx >= W:
                    break
                a = int(pa[yy, xx])
                o = dataoff + (ty * W + tx) * 4
                out[o] = a
                out[o + 1] = a
                out[o + 2] = a
                out[o + 3] = a
        done += 1
    if verbose:
        print("  injected %d glyphs size=%d base=%d" % (done, size, target_base))
    return bytes(out)


def main():
    for fn in ("Font1.pck", "Font2.pck"):
        p = os.path.join("Data", "ENG", fn)
        if not os.path.exists(p + ".orig2"):
            shutil.copyfile(p, p + ".orig2")
        d = open(p + ".orig2", "rb").read()
        T, Q, m, et, hsz, cnt, ents, names = port_pc.parse(d)
        blobs = [inject(d[o:o + s], verbose=True) for (o, s) in ents]
        new = port_pc.build(d, T, Q, m, et, hsz, cnt, ents, names, blobs)
        open(p, "wb").write(new)
        print("wrote", fn)


if __name__ == "__main__":
    main()



