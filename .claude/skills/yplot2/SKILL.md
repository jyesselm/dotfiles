---
name: yplot2
description: Make publication figures for the Yesselman lab with yplot2 — the lab's house plotting engine (a layout+style layer over matplotlib/seaborn). Use whenever writing or editing figure code for a lab paper/analysis: multipanel figures, violins/box/kde/heatmaps/hexbin, scatter+regression, RNA pop_avg reactivity plots, or embedding structure PNGs. ALWAYS reach for yplot2 instead of hand-rolling matplotlib styling or copying a per-paper plotting.py.
argument-hint: [plot-type | figure | catalog]
---

# yplot2 — the lab's house plotting engine

`yplot2` is a thin **layout + style layer** over matplotlib + seaborn. It gives every
figure a consistent house look (bundled Arimo font, uniform linewidths/fonts), a
fixed-width multipanel canvas in inches, and one-command reproducibility. You draw with
the plot functions (or raw matplotlib/seaborn) into axes yplot2 lays out and styles.

## The golden rule
**Never hand-roll matplotlib styling and never copy a paper's `plotting.py`.** If you
find yourself writing `publication_style_ax()`, `format_small_plot()`, `figsize=(2.0,1.5)`,
`fig.subplots_adjust(...)`, or per-figure hex colors — STOP and use yplot2. That habit is
exactly what this library exists to kill. `import yplot2 as yp`.

## The one pattern (start every figure script from this)
```python
import matplotlib
matplotlib.use("Agg")            # headless/deterministic; drop for interactive
import yplot2 as yp

yp.use_style()                   # push house style into rcParams (ONCE, at top)

# 1) lay out a 7-inch-wide canvas — panels come back named A, B, C, ...
fig, panels = yp.figure7(rows=1, cols=3)     # or figure7(2, 2, row_heights=[1.0, 2.0])

# 2) draw into each panel with a yplot2 wrapper (house-styled automatically)
yp.violin(panels["A"], df, x="cond", y="reactivity")
yp.regplot(panels["B"], df["x"], df["y"])
yp.scatter(panels["C"], a, b)

# 3) panel labels + save with provenance (stamps source + git SHA into the file)
yp.add_labels(fig, [p.get_position() for p in panels.values()], fig.get_size_inches())
yp.save(fig, "figures/figure_2.png", source="figures/figure_2.py",
        data_hashes={"df": "<sha or version>"})
```
That is the whole workflow: `use_style` → `figure7` → draw → `save`.

## Plot-type → function (pick the wrapper; it applies house style for you)
| You want | Call | Notes |
|---|---|---|
| Violin (distributions by category) | `yp.violin(ax, df, x=, y=, hue=)` | strip overlay is **opt-in**: `strip=True` (auto-subsamples large N) |
| Box | `yp.box(ax, df, x=, y=, hue=)` | `strip=False` default |
| KDE / density | `yp.kde(ax, df, x=, y=, hue=)` | |
| 2-D histogram heatmap | `yp.heatmap2d(ax, x, y)` | numpy+imshow, styled colorbar, seaborn-free |
| Hexbin density | `yp.hexbin(ax, x, y)` | native mpl, seaborn-free |
| Scatter + regression + R² | `yp.regplot(ax, x, y)` / `yp.regplot_density(ax, x, y)` | |
| Scatter / line / bar / errorbar / hist | `yp.scatter/line/bar/barh/errorbar/hist(ax, ...)` | |
| RNA reactivity (pop-avg) | `yp.pop_avg(ax, seq, struct, react)` / `yp.stacked_pop_avg(df)` | nucleotide-colored |
| Lollipop | `yp.lollipop(ax, x, y1, y2)` | |
| Sequence/structure x-axis | `yp.sequence_x_axis(ax, seq)` / `yp.structure_x_axis(ax, struct)` / `yp.sequence_structure_x_axis(...)` | |
| Text/annotation on a panel | `yp.text(ax, s, pos="top left")` / `yp.annotate(ax, s, xy=..., coords="axes"\|"data")` | |
| Distance label / line / arrow on an image | `yp.line_annotation(ax, xy0, xy1)` / `yp.distance_label(ax, xy0, xy1, "8 Å")` | axes-fraction or data coords, never pixels |
| Log axis with a real "0" | `eps,pos,xp = yp.compute_eps_and_transform(x); yp.log_axis_with_zero(ax, eps, pos)` | |
| Colorbar / legend | `yp.add_colorbar(...)` / `yp.add_legend(...)` / `yp.add_legend_above(...)` | |

The full, current, machine-readable list of plot capsules (with tags, expected data
shape, and thumbnails) is at **`<yplot2-repo>/catalog/CATALOG.md`** and
`catalog/catalog.json`. When unsure which plot fits a data shape, read that catalog and
pick an existing one instead of inventing a new figure.

## The escape hatch (this is a feature, use it freely)
Panels are **live matplotlib `Axes`** — draw anything into them. For a plot type yplot2
doesn't wrap, draw with raw matplotlib/seaborn, then call `yp.finish(ax)` to re-assert
house chrome (spines, ticks, fonts):
```python
import seaborn as sns
sns.swarmplot(ax=panels["A"], data=df, x="g", y="v")   # not wrapped by yplot2
yp.finish(panels["A"])                                  # <-- house-style it
```
`finish(ax)` styles chrome only and leaves your data artists alone. (The yplot2 wrappers
already call it for you — you only need it for raw seaborn/mpl.)

## Layout — sizing is solved, stop hardcoding it
- `yp.figure7(rows, cols, ...)` → a 7-inch-wide figure; panel sizes are DERIVED from
  rows/cols + margins + gutters. Never write `figsize=(...)` or subplot_adjust again.
- Variable row heights: `yp.figure7(2, 1, row_heights=[1.0, 2.0])` (e.g. a tall image row
  over a short plot row).
- Single quick panel: `fig, ax = yp.subplots(subplotsize=(2, 1.5))`.
- Structure PNG + plots: size the image panel from its real aspect ratio with
  `yp.coord_from_image(path, left, bottom, column_width=..)` (no pixel fudging), place with
  `yp.create_figure`, load with `yp.load_image`, annotate with `yp.distance_label`.
- Absolute inch positioning when you need it: `yp.Coord(left, bottom, width, height)` +
  `yp.right_of/below/above/left_of`, then `yp.create_figure((w,h), coords)`.

## House style & palettes
- `yp.use_style()` sets the rcParams default; `with yp.style(): ...` scopes it.
- Nucleotide colors: `yp.palette("nucleotide")` (A=red, C=blue, G=orange, T/U=green),
  `yp.colors_for_sequence(seq)`. Never inline hex per figure — add named palettes to the
  registry instead.
- Journal presets: `yp.use_preset("nature"|"cell"|"science"|"pnas"|...)`.
- Override per call: e.g. `yp.apply_style(ax, axis_linewidth=1.0, x_axis_label_fontsize=9)`.

## Reproducibility (non-negotiable for paper figures)
- Always finish a figure with `yp.save(fig, path, source="<this script>", data_hashes=...)`.
  It enforces dpi + white background, stamps provenance (source, git SHA, version, data
  hashes) into the file metadata, and is byte-deterministic. Do NOT use bare `fig.savefig`.
- Put figure logic in scripts or notebooks under a `figures/` dir; regenerate the whole
  paper with `python -m yplot2.build figures/` (runs `.py` and executes `.ipynb` clean).
  "Raw data" here = the analysis-ready dataframe, not the fastq/BAM pipeline.

## Anti-patterns → do this instead
- `publication_style_ax(ax)` / `format_small_plot(ax)` → `yp.finish(ax)` (or a wrapper).
- `figsize=(2.0, 1.5)` / `fig.subplots_adjust(...)` → `yp.figure7(...)` / `yp.subplots(...)`.
- `sns.violinplot(...)` then hand-styling → `yp.violin(...)`.
- inline `palette={"A": "red", ...}` → `yp.palette("nucleotide")`.
- `plt.savefig(path, dpi=300)` → `yp.save(fig, path, source=...)`.
- seaborn with `hue=None` + `palette=` (deprecated) — the yplot2 wrappers handle this; if
  you must call seaborn raw, pass `hue=x, legend=False`.

## Adding a new plot type (when nothing in the catalog fits)
Add a capsule under `yplot2/plots/statistical/` (or the right category folder) following
an existing wrapper: lazy seaborn import, explicit palette + `hue_order`, `finish(ax)`,
`@catalog(tags=..., data_shape=..., kind="panel")`, plus a `demo_<name>()`. Add any new
`tags`/`data_shape` token to `yplot2/vocab.py` in the same change (the decorator validates
against it). Run `python -m yplot2.catalog_build.build` to refresh the catalog + gallery.

## Repo
Source: `~/local/code/python/developing/yplot2`. Install: `pip install -e ".[dev,stats]"`
(the `stats` extra provides seaborn — `import yplot2` itself stays seaborn-free). For
notebook regen add `[repro]`.
