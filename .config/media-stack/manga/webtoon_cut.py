"""Re-cut webtoon CBZs (one tall strip per file) into phone-sized pages for paged readers (Panels).
usage: uv run --with pillow --with numpy python webtoon_cut.py <in.cbz> <out.cbz> [page_height=1560]
Stitches all strips into one column, then cuts near page_height, moving each cut to the quietest row
(a panel gutter) within the last quarter of the page so no bubble or panel is sliced. Output: JPEG pages, same width.
Whole series: for f in "mangas/<Source>/<Series>"/*.cbz; do ... "$f" "paged/<Source>/<Series>/$(basename "$f")"; done
Kavita's Manga library reads paged/ and excludes the original folder of each re-cut series (see README → Manga)."""
import io, sys, zipfile
from PIL import Image
import numpy as np

src, dst = sys.argv[1], sys.argv[2]
H = int(sys.argv[3]) if len(sys.argv) > 3 else 1560   # 720 wide at 9:19.5 (iPhone)
MIN_H, WINDOW = H // 2, H // 4

z = zipfile.ZipFile(src)
names = sorted(n for n in z.namelist() if n.lower().endswith((".jpg", ".jpeg", ".png", ".webp")))
imgs = [Image.open(io.BytesIO(z.read(n))).convert("RGB") for n in names]
W = max(i.width for i in imgs)
imgs = [i if i.width == W else i.resize((W, round(i.height * W / i.width))) for i in imgs]
strip = Image.new("RGB", (W, sum(i.height for i in imgs)))
y = 0
for i in imgs:
    strip.paste(i, (0, y)); y += i.height
arr = np.asarray(strip)
row_var = arr.std(axis=(1, 2)) + np.abs(np.diff(arr.mean(axis=(1, 2)), prepend=arr[0].mean()))

cuts, y = [0], 0
while strip.height - y > H:
    lo, hi = y + max(MIN_H, H - WINDOW), min(y + H, strip.height)
    k = lo + int(np.argmin(row_var[lo:hi]))        # quietest row = gutter
    y = k if row_var[k] < 8 else y + H
    cuts.append(y)
cuts.append(strip.height)

extra = [n for n in z.namelist() if n not in names]
with zipfile.ZipFile(dst, "w", zipfile.ZIP_STORED) as out:
    for n, (a, b) in enumerate(zip(cuts, cuts[1:]), 1):
        page = strip.crop((0, a, W, b))
        if b - a < H:                                   # pad the last page to full height
            canvas = Image.new("RGB", (W, H), tuple(int(v) for v in arr[b - 1].mean(axis=0)))
            canvas.paste(page, (0, 0)); page = canvas
        buf = io.BytesIO(); page.save(buf, "JPEG", quality=90)
        out.writestr(f"{n:03d}.jpg", buf.getvalue())
    for n in extra:
        out.writestr(n, z.read(n))
print(f"{src} -> {dst}: {len(imgs)} strips ({strip.height}px) -> {len(cuts)-1} pages of {W}x{H}")
