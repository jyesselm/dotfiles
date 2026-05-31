# Python Style Standards

Shared standard for `py-planner`, `py-coder`, and `py-reviewer`. Modern Python 3.10+. Clean, simple, testable.

## Non-Negotiables

| Rule | Limit | Rationale |
|------|-------|-----------|
| Max indent levels | 3 | Use early returns, extract helpers |
| Function length | ~30 lines | Few exceptions for complex algorithms |
| Module size | 200-300 lines | Split large modules |
| Tiny functions | Avoid | Only if called 3+ times |
| Cyclomatic complexity | ≤10 | Refactor if higher |

## Principles

- **One responsibility per function** — if you need "and" to describe it, split it
- **Simple > clever** — no comprehension chains, no nested ternaries
- **Early returns** — handle errors/edge cases first, then happy path
- **Flat is better** — prefer composition over deep nesting

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
