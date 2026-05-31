---
description: Refactor Python code following project standards
---

Analyze and refactor Python code following established standards.

## Input: $ARGUMENTS

- File path or module name to refactor
- Optional: specific function/class to focus on

## Standards (from py-coder)

### Non-Negotiables
- Max 3 indent levels - use early returns
- Functions <= 30 lines, single responsibility
- All functions: docstrings + type hints
- Modules: 200-300 lines target
- Simple > clever
- No tiny 1-2 line functions unless frequently called
- Max cyclomatic complexity: **10**
- If higher, refactor into smaller functions

### Style Checklist
- [ ] Early returns for error cases
- [ ] Type hints on all functions
- [ ] Google-style docstrings
- [ ] Descriptive variable names
- [ ] No magic numbers (use constants)

## Process

1. **Read** the target file(s)
2. **Analyze** current structure:
   - Function lengths
   - Indent depth
   - Missing type hints
   - Missing docstrings
   - Code duplication
3. **Propose** specific changes
4. **Implement** refactoring
5. **Verify** with tools:
   ```bash
   ruff check --fix .
   ruff format .
   mypy src/
   ```

## Output Format

```
## Analysis

### Current Issues
- [file:line] Issue description
- ...

### Proposed Changes
1. [Change 1]: [Reason]
2. [Change 2]: [Reason]

## Refactored Code

[Show the refactored sections]

## Verification
- ruff: [pass/fail]
- mypy: [pass/fail]
- tests: [pass/fail]
```

## Rules

- Don't change behavior unless fixing a bug
- Preserve all existing tests
- One logical change per commit
- If extensive changes needed, break into phases
