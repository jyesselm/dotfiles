# Python Style Standards

Shared standard for `py-planner`, `py-coder`, and `py-reviewer`. Modern Python 3.10+. Clean, simple, testable.

## Non-Negotiables

| Rule | Target | Rationale |
|------|--------|-----------|
| Max nesting depth | ≤3 | early returns, extract helpers |
| Cyclomatic complexity | ≤10 | the real complexity signal; refactor above it |
| Function parameters | ≤4 | more → group into a `@dataclass` |
| One responsibility | always | if you need "and" to describe it, split it |

**Length is a smell, not a hard limit.** A function should be as short as it can be while telling one coherent story; a module as small as it can be while being about one thing. If a function runs long or a module sprawls, look for a missing abstraction. Never split a cohesive unit just to hit a number: ravioli code (many tiny functions you have to chase) reads worse than one honest function.

## Principles

- **One responsibility per function** — if you need "and" to describe it, split it
- **Simple > clever** — no comprehension chains, no nested ternaries
- **Early returns** — handle errors/edge cases first, then happy path
- **Flat is better** — prefer composition over deep nesting

## Human Readability (the prime directive)

Above all, write code a human can read quickly and trust. Code is read far more often than it is written, and the reader is usually a tired collaborator, a new trainee, or you in six months with no memory of this. Optimize for that reader, not for the machine and not for your own convenience while writing. If they would have to ask you what a piece of code does, it is not done.

- **Tell a story top-down.** A function's first lines should read as its high-level steps; push details into helpers defined below it. A reader should learn *what* a function does without reading *how*.
- **Minimize what the reader must hold in mind.** Keep scopes short and variables few. Declare a variable right before its first use, not at the top. Use early returns to peel off edge cases so the happy path stays flat. Avoid action at a distance: no hidden mutation of arguments, no surprising global state.
- **Make names do the work.** A precise name removes the need for a comment. Use one word per concept and the same word everywhere (`reactivity`, never `react`/`r`/`val` for the same thing). Names state intent and units, never type: `timeout_s`, `coverage_depth`, `is_paired`.
- **Surface the logic.** Give a complex sub-expression a name (an "explaining variable"), and lift a compound condition into a named predicate so the `if` reads like a sentence.
  ```python
  # dense: the reader has to decode the condition
  if seq and len(seq) >= min_len and not seq.strip("AUGC"):
      ...
  # readable: the condition names its intent
  if is_valid_rna(seq, min_len):
      ...
  ```
- **Comment the why, never the what.** The code already says what it does. Comments justify the non-obvious: a scientific rationale (cite the paper or equation), a unit, an assumption, a gotcha. Name magic numbers and explain them.
  ```python
  Z_95 = 1.96  # 95% CI half-width for a normal distribution; see Methods.
  ci_half_width = Z_95 * standard_error
  ```
- **Prefer boring and explicit over clever.** No nested ternaries, no multi-clause comprehensions that must be decoded, no one-liner that saves a line at the cost of a minute. If a line makes the reader pause to parse it, split it.
  ```python
  # clever: three operations crammed into one line
  return [f(x) for x in xs if x.ok and x.v > t][: n or len(xs)]
  # clear: each step is named and obvious
  usable = [x for x in xs if is_usable(x, threshold)]
  transformed = [transform(x) for x in usable]
  return transformed[:limit]
  ```
- **Replace flag parameters with intent.** A boolean argument forces the reader to look up what `True` means at the call site. Prefer two well-named functions, or a keyword-only argument with an enum.
- **Map code onto the science.** Analysis code should read like the method it implements: name variables after the quantities, make each step visible, and state units and the rationale for every threshold, normalization, and formula (with a reference).

**The reader test (run before finishing):** reread each function and ask, "could a new lab member follow this in one pass without asking me?" If not, the fix is almost always a clearer name, a flatter structure, an explaining variable, or a single why-comment, not more prose.

## Function Template

```python
def normalize_signal(
    signal: np.ndarray,
    method: str = "zscore",
) -> np.ndarray:
    """Normalize signal using specified method.

    Args:
        signal: Raw signal values.
        method: Normalization method ('zscore' or 'minmax').

    Returns:
        Normalized signal array.

    Raises:
        ValueError: If signal is empty or method unknown.
    """
    if signal.size == 0:
        raise ValueError("Signal cannot be empty")

    if method == "zscore":
        return (signal - signal.mean()) / signal.std()
    if method == "minmax":
        return (signal - signal.min()) / (signal.max() - signal.min())

    raise ValueError(f"Unknown method: {method}")
```

Type hints and a full docstring (Args/Returns/Raises) are required on **all** functions.

## Classes

- Protocols for interfaces, not ABCs unless you need default implementations
- `@dataclass` for data containers
- Factories for complex construction — `__init__` just assigns
- Composition over inheritance

## Module Organization

```
src/
  package/
    __init__.py          # Public API only
    models.py            # Data classes, protocols
    processing.py        # Core logic (~200 lines)
    io.py                # File I/O
    utils.py             # Shared helpers (if needed)
tests/
  test_processing.py     # Mirror src structure
```

## Tool Chain (MUST pass before finishing)

```bash
ruff check --fix .
ruff format .
mypy src/ --ignore-missing-imports
pytest --cov=src --cov-fail-under=90
```

Fix all ruff errors. Complexity must stay ≤10. Coverage must be ≥90%.
