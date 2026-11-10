"""Re-cut webtoon CBZs (one tall strip per file) into one-scene-per-page CBZs for paged readers.
usage: uv run --with pillow --with numpy python webtoon_cut.py <in.cbz> <out.cbz> [page_height=1560]
Stitches all strips into one column and cuts at gutters (solid rows at least MIN_GAP tall), so no panel or
bubble is sliced; only a gutterless stretch taller than four pages is cut at its quietest rows. Neighbouring scenes are grouped while they fit in page_height; a scene taller
than that gets its own tall page (the reader fits it to the screen). Pages are padded to page_height with the
gutter colour. Whole series: for f in "mangas/<Source>/<Series>"/*.cbz; do ... "$f" "paged/<Source>/<Series>/$(basename "$f")"; done
Kavita's Manga library reads paged/ and excludes the original folder of each re-cut series (see README → Manga)."""
import io, sys, zipfile
from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True   # some scanlated strips are truncated JPEGs
import numpy as np

src, dst = sys.argv[1], sys.argv[2]
H = int(sys.argv[3]) if len(sys.argv) > 3 else 1560   # 720 wide at 9:19.5 (iPhone)
QUIET, MIN_GAP, MARGIN = 8, 24, 32                     # row std below QUIET = solid (JPEG noise ~5); gutter = MIN_GAP+ solid rows
MAX_H, WINDOW = 4 * H, H // 4                          # a gutterless page taller than MAX_H is cut at its quietest rows

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
quiet = arr.std(axis=(1, 2)) < QUIET

# scenes = runs of non-quiet rows, where only gaps of MIN_GAP+ quiet rows separate them
edges = np.flatnonzero(np.diff(quiet.astype(int), prepend=1, append=1))   # starts/ends of content runs
runs = list(zip(edges[::2], edges[1::2]))
scenes = []
for a, b in runs:
    if scenes and a - scenes[-1][1] < MIN_GAP:
        scenes[-1] = (scenes[-1][0], b)
    else:
        scenes.append((a, b))

# group neighbouring scenes while the group fits one page
pages, cur = [], None
for a, b in scenes:
    if cur and b - cur[0] + 2 * MARGIN <= H:
        cur = (cur[0], b)
    else:
        if cur: pages.append(cur)
        cur = (a, b)
if cur: pages.append(cur)

# fallback for pages with no usable gutter (e.g. one continuous backdrop): cut at the quietest row of each window
row_std = arr.std(axis=(1, 2))
split = []
for a, b in pages:
    while b - a > MAX_H:
        lo, hi = a + H - WINDOW, a + H
        k = lo + int(np.argmin(row_std[lo:hi]))
        split.append((a, k)); a = k
    split.append((a, b))
pages = split

extra = [n for n in z.namelist() if n not in names]
with zipfile.ZipFile(dst, "w", zipfile.ZIP_STORED) as out:
    for n, (a, b) in enumerate(pages, 1):
        bg = tuple(int(v) for v in arr[max(a - 1, 0)].mean(axis=0))   # gutter colour above the scene
        a, b = max(a - MARGIN, 0), min(b + MARGIN, strip.height)
        page = strip.crop((0, a, W, b))
        if page.height < H:                                            # centre short pages on a full-height canvas
            canvas = Image.new("RGB", (W, H), bg)
            canvas.paste(page, (0, (H - page.height) // 2)); page = canvas
        buf = io.BytesIO(); page.save(buf, "JPEG", quality=90)
        out.writestr(f"{n:03d}.jpg", buf.getvalue())
    for n in extra:
        out.writestr(n, z.read(n))
tall = sum(1 for a, b in pages if b - a + 2 * MARGIN > H)
print(f"{src} -> {dst}: {len(imgs)} strips ({strip.height}px) -> {len(scenes)} scenes -> {len(pages)} pages ({tall} taller than {H})")
