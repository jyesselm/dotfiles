# CLAUDE.md structure (the modal template)

Order matters — Claude reads top-down, so put the highest-value content first.
Fill only the sections that apply. Commands are always a fenced bash block with `#` comments.

```markdown
# <Project name> — <one-line purpose (WHAT + WHY)>

<2-4 lines: what it does, the stack, and the single most important thing to know.
For a monorepo, note the subsystem layout and where to start Claude.>

## Commands
\`\`\`bash
<install>            # e.g. uv sync   /   pip install -e .   /   cmake -B build
<format> && <lint>   # e.g. ruff format . && ruff check .
<typecheck>          # e.g. mypy src/   (omit if not used)
<test>               # e.g. python3 -m pytest -q   /   ctest --test-dir build
<single test>        # e.g. pytest tests/test_x.py::test_y    <-- include this; it's the highest-value line
\`\`\`

## Architecture / Layout
- \`src/<pkg>/\` — <what lives here>
- \`tests/\`     — <runner, how it mirrors src>
- \`data/raw/\`  — **NEVER edit; generated/external**
<only include non-obvious structure; skip what's self-evident from the tree>

## Code style
@~/.claude/standards/python-style.md          <-- import shared standard, don't restate it
- <only project-specific deltas that aren't in the import and aren't a linter's job>

## Conventions & gotchas
- **ALWAYS** <imperative rule Claude would otherwise get wrong>
- **NEVER** <forbidden action, e.g. commit raw data, edit generated files>
- <non-obvious behavior, required env var, reproducibility note>
```

---

## Filled example — scientific Python + C++ research codebase

```markdown
# rna-fold — RNA secondary-structure prediction (Python + C++)

Python analysis pipeline over a C++ folding core (pybind11). Optimize for reproducibility:
every result must regenerate from code + committed fixtures alone.

## Commands
\`\`\`bash
conda env create -f environment.yml && conda activate rna-fold   # setup
cmake -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build  # build C++ core
ruff format . && ruff check . && python3 -m pytest -q            # python gate
ctest --test-dir build                                           # C++ tests
pytest tests/test_rmsd.py::test_pseudoknot -q                    # single test
\`\`\`

## Architecture
- \`python/rna_fold/\` — analysis, plotting, the pybind11 bindings
- \`cpp/\` — folding algorithms (the hot path); changes here require re-running the FULL python suite
- \`data/raw/\` — **NEVER edit or commit**; documented in \`data/README.md\`
- \`data/fixtures/\` — small committed datasets used by reproducibility tests
- \`results/\` — regenerated from code + fixtures; never hand-edited

## Code style
@~/.claude/standards/python-style.md
@~/.claude/standards/cpp-style.md

## Conventions & gotchas
- **ALWAYS** set \`np.random.seed(42)\` at the top of reproducibility tests.
- **NEVER** assert float equality — use \`np.allclose(x, y, rtol=1e-5)\`.
- **CRITICAL**: after any \`cpp/\` change, re-run \`python3 -m pytest -q\` (the bindings are the contract).
- Serialize arrays with \`np.save\`/HDF5, not pickle (cross-version stability).
```

Note: this user keeps the agent pipeline (planner→coder→reviewer, verifiers) in the GLOBAL
`~/.claude/CLAUDE.md`, which loads in every session — do NOT repeat it in a project file.
