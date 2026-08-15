#!/usr/bin/env python3
"""Render a viewable half-res PPM/PNG preview from an ML MLV raw video file.

No dependencies (pure stdlib). Decodes ML's 14-bit raw_pixblock packing
(ml/src/raw.h:72 — 8 pixels in 14 bytes, LSB-first bitfields), half-res
demosaic of the RGGB bayer quad, gray-world white balance, gamma 2.2.

Usage: mlv_preview.py file.mlv [frame_index ...]   (default: frame 0)
Writes <file>_frameNN.ppm next to the input (and .png if ImageMagick/ffmpeg exists).
"""
import shutil, struct, subprocess, sys

def blocks(f):
    pos = 0
    f.seek(0, 2); end = f.tell()
    while pos < end:
        f.seek(pos)
        hdr = f.read(8)
        if len(hdr) < 8: return
        magic, size = hdr[:4], struct.unpack('<I', hdr[4:])[0]
        if size < 8 or pos + size > end: return
        yield magic, size, pos
        pos += size

def main():
    path = sys.argv[1]
    wanted = sorted(int(a) for a in sys.argv[2:]) or [0]
    f = open(path, 'rb')
    xres = yres = None
    vidf = {}
    for magic, size, pos in blocks(f):
        if magic == b'RAWI':
            f.seek(pos + 16)
            xres, yres = struct.unpack('<HH', f.read(4))
        elif magic == b'VIDF':
            f.seek(pos + 16)
            frameno, = struct.unpack('<I', f.read(4))
            f.seek(pos + 28)
            frame_space, = struct.unpack('<I', f.read(4))
            vidf[frameno] = pos + 32 + frame_space
    assert xres and yres, 'no RAWI block'
    stride = xres * 14 // 8          # bytes per bayer row (240 pixblocks at 1920)
    ow, oh = xres // 2, yres // 2

    for want in wanted:
        if want not in vidf:
            print(f'frame {want} not in file (has {min(vidf)}..{max(vidf)})'); continue
        base = vidf[want]
        # decode all pixels of the two rows of each quad, half-res demosaic
        px = [0.0] * (ow * oh * 3)
        black, white = 2400.0, 15000.0
        f.seek(base)
        raw = f.read(stride * yres)
        for oy in range(oh):
            r0 = (2 * oy) * stride
            r1 = r0 + stride
            row_even, row_odd = [], []
            for row, out in ((r0, row_even), (r1, row_odd)):
                for b in range(stride // 14):
                    v = int.from_bytes(raw[row + b*14 : row + b*14 + 14], 'little')
                    out += [(v >> 2) & 0x3FFF,                                # a
                            (((v)       & 3)   << 12) | ((v >> 20) & 0xFFF),  # b
                            (((v >> 16) & 0xF) << 10) | ((v >> 38) & 0x3FF),  # c
                            (((v >> 32) & 0x3F)<< 8)  | ((v >> 56) & 0xFF),   # d
                            (((v >> 48) & 0xFF)<< 6)  | ((v >> 74) & 0x3F),   # e
                            (((v >> 64) & 0x3FF)<<4)  | ((v >> 92) & 0xF),    # f
                            (((v >> 80) & 0xFFF)<<2)  | ((v >> 110) & 3),     # g
                            (v >> 96) & 0x3FFF]                               # h
            o = oy * ow * 3
            for ox in range(ow):
                x2 = 2 * ox
                px[o + 3*ox]     = row_even[x2]                               # R
                px[o + 3*ox + 1] = (row_even[x2+1] + row_odd[x2]) / 2         # G
                px[o + 3*ox + 2] = row_odd[x2+1]                              # B
        # gray-world WB on linear values, then gamma
        sums = [0.0, 0.0, 0.0]
        for i, v in enumerate(px): sums[i % 3] += max(v - black, 0)
        gains = [sums[1] / s if s else 1.0 for s in sums]
        out = bytearray()
        for i, v in enumerate(px):
            lin = max(v - black, 0) * gains[i % 3] / (white - black)
            out.append(round(255 * min(1.0, lin) ** (1 / 2.2)))
        ppm = path.rsplit('.', 1)[0] + f'_frame{want:02d}.ppm'
        with open(ppm, 'wb') as o:
            o.write(f'P6\n{ow} {oh}\n255\n'.encode()); o.write(out)
        print('wrote', ppm)
        for conv in (['magick', ppm, ppm[:-4] + '.png'],
                     ['convert', ppm, ppm[:-4] + '.png'],
                     ['ffmpeg', '-y', '-loglevel', 'error', '-i', ppm, ppm[:-4] + '.png']):
            if shutil.which(conv[0]):
                subprocess.run(conv, check=False)
                print('wrote', ppm[:-4] + '.png'); break

if __name__ == '__main__':
    main()
