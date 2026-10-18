import struct, re

EXE = 'DT2_en.exe'
CLEAN = 'DT2_en.clean.exe'
d = bytearray(open(CLEAN, 'rb').read())

pe = struct.unpack_from('<I', d, 0x3c)[0]
nsec = struct.unpack_from('<H', d, pe + 6)[0]
szopt = struct.unpack_from('<H', d, pe + 20)[0]
sec_tab = pe + 24 + szopt
opt = pe + 24
size_hdr = struct.unpack_from('<I', d, opt + 60)[0]
size_img = struct.unpack_from('<I', d, opt + 56)[0]
img_base = struct.unpack_from('<I', d, opt + 28)[0]
sec_align = struct.unpack_from('<I', d, opt + 32)[0]
file_align = struct.unpack_from('<I', d, opt + 36)[0]
print('nsec %d  sec_tab %X  hdr %X  img %X  base %X align %X/%X' % (nsec, sec_tab, size_hdr, size_img, img_base, sec_align, file_align))
assert sec_tab + (nsec + 1) * 40 <= size_hdr, 'no room for section header'

def sec(i):
    o = sec_tab + i * 40
    vs, va, rs, ro = struct.unpack_from('<IIII', d, o + 8)
    return o, vs, va, rs, ro

def align(x, a):
    return (x + a - 1) & ~(a - 1)

max_end = max(va + align(max(vs, rs), sec_align) for _, vs, va, rs, ro in (sec(i) for i in range(nsec)))
new_va = align(max_end, sec_align)
new_off = align(len(d), file_align)

src = open('hookfont.cpp', encoding='utf-8').read()
w = [int(x) for x in re.search(r'g_w\[256\] = \{(.*?)\};', src, re.S).group(1).replace('\n', '').split(',') if x.strip()]
assert len(w) == 256

B = img_base + new_va
CUR, LASTX, Y = B + 0xE0, B + 0xE4, B + 0xE8
MARG = B + 0xEC
SCRATCH = B + 0xF0
TAB = B + 0x200

code = bytearray()
code += b'\x60'
code += b'\x8b\x74\x24\x28'
code += b'\x8b\x7c\x24\x2c'
code += b'\x8b\x5c\x24\x30'
code += b'\x3b\x1d' + struct.pack('<I', Y)
jne = len(code); code += b'\x75\x00'
code += b'\x3b\x3d' + struct.pack('<I', LASTX)
ja = len(code); code += b'\x77\x00'
reset = len(code)
code += b'\xc7\x05' + struct.pack('<I', CUR) + struct.pack('<i', 22)
code += b'\x89\x1d' + struct.pack('<I', Y)
cont = len(code)
code += b'\xa1' + struct.pack('<I', CUR)
code += b'\x89\x44\x24\x2c'
code += b'\x8b\xce'
code += b'\x81\xe1\xff\x00\x00\x00'
code += b'\x0f\xb6\x0c\x0d' + struct.pack('<I', TAB)
code += b'\x01\x0d' + struct.pack('<I', CUR)
code += b'\x89\x3d' + struct.pack('<I', LASTX)
code += b'\x61'
code += b'\x8b\x54\x24\x08'          # mov edx,[esp+8]
code += b'\x83\xec\x08'              # sub esp,8
code += b'\x33\xc0'                  # xor eax,eax
code += b'\x53'                      # push ebx
jmp = len(code); code += b'\xe9\x00\x00\x00\x00'

code[jne + 1] = reset - (jne + 2)
code[ja + 1] = cont - (ja + 2)
struct.pack_into('<i', code, jmp + 1, 0x44795A - (B + jmp + 5))

blob = bytearray(0x1000)
blob[0:len(code)] = code
struct.pack_into('<iiii', blob, 0xE0, 0, 0, -1, 0)
blob[0x200:0x300] = bytes(min(v, 255) for v in w)

d += b'\x00' * (new_off - len(d))
d += blob

h = sec_tab + nsec * 40
d[h:h+8] = b'.rufix\x00\x00'
struct.pack_into('<IIII', d, h + 8, 0x1000, new_va, 0x1000, new_off)
struct.pack_into('<II', d, h + 24, 0, 0)
struct.pack_into('<I', d, h + 36, 0xE0000060)
struct.pack_into('<H', d, pe + 6, nsec + 1)
struct.pack_into('<I', d, opt + 56, align(new_va + 0x1000, sec_align))

FG = 0x447950
fg_off = None
for i in range(nsec):
    o, vs, va, rs, ro = sec(i)
    if va <= FG - img_base < va + max(vs, rs):
        fg_off = ro + (FG - img_base - va)
        break
assert fg_off
d[fg_off] = 0xE9
struct.pack_into('<i', d, fg_off + 1, B - (FG + 5))

open(EXE, 'wb').write(bytes(d))
print('new section RVA %X  stub VA %08X  table %08X  code %d' % (new_va, B, TAB, len(code)))
