#!/usr/bin/env python3
"""step_shrink.py -- round the real numbers in STEP files to 7 significant digits (<= 0.01 um on a 100 mm part)
and gzip them, so every .step.gz stays under ~45 MB for GitHub.  Usage: python3 step_shrink.py file.step ..."""
import gzip
import re
import sys

NUM = re.compile(rb'-?\d+\.\d{7,}(?:E[-+]?\d+)?')


def short(m):
    v = float(m.group(0))
    s = ('%.7G' % v).encode()
    if b'.' not in s and b'E' not in s:
        s += b'.'
    return s


for fn in sys.argv[1:]:
    data = open(fn, 'rb').read()
    out = NUM.sub(short, data)
    open(fn, 'wb').write(out)
    with gzip.open(fn + '.gz', 'wb', compresslevel=9) as f:
        f.write(out)
    print(fn, len(data) // 1000000, '->', len(out) // 1000000, 'MB')
