import sys, pymupdf
from PIL import Image
pdf, prefix, start, n = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
d = pymupdf.open(pdf)
ims = []
for i in range(start, min(start + n, d.page_count)):
    pm = d[i].get_pixmap(dpi=70)
    ims.append(Image.frombytes('RGB', (pm.width, pm.height), pm.samples))
w, h = ims[0].size
cols = 4
rows_ = (len(ims) + cols - 1) // cols
S = Image.new('RGB', (w * cols, h * rows_), 'white')
for k, im in enumerate(ims):
    S.paste(im, ((k % cols) * w, (k // cols) * h))
S.save(prefix)
