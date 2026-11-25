#!/usr/bin/env python3
"""Pixel-compare screenshots: diff.py <orig_dir> <new_dir> <diff_out>. Prints % of differing pixels per page."""
import os, sys
from PIL import Image, ImageChops
o, n, d = sys.argv[1:4]
for mode in ('desktop', 'mobile'):
    os.makedirs(os.path.join(d, mode), exist_ok=True)
    for f in sorted(os.listdir(os.path.join(o, mode))):
        if not f.endswith('.png') or not os.path.exists(os.path.join(n, mode, f)):
            continue
        a = Image.open(os.path.join(o, mode, f)).convert('RGB'); b = Image.open(os.path.join(n, mode, f)).convert('RGB')
        h = max(a.height, b.height)
        A = Image.new('RGB', (a.width, h), 'magenta'); A.paste(a); B = Image.new('RGB', (a.width, h), 'magenta'); B.paste(b.crop((0, 0, a.width, b.height)))
        diff = ImageChops.difference(A, B).convert('L').point(lambda v: 255 if v > 40 else 0)
        pct = 100 * sum(diff.histogram()[255:]) / (a.width * h)
        # first differing row band, to point at where to look
        bbox = diff.getbbox()
        Image.merge('RGB', (diff, Image.new('L', diff.size), Image.new('L', diff.size))).save(os.path.join(d, mode, f))
        print(f'{mode:8} {f:18} orig_h={a.height:6} new_h={b.height:6} diff={pct:5.2f}% bbox={bbox}')
