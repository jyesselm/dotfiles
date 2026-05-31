---
description: Run test suite with coverage and report results
---

Run the project test suite and provide a comprehensive report.

## Input: $ARGUMENTS

Optional arguments:
- `--file <path>`: Run tests for specific file
- `--coverage`: Include coverage report
- `--verbose`: Show all test output
- `--fix`: Auto-fix failing tests if possible

## Process

1. **Detect** test framework:
   - Look for pytest.ini, pyproject.toml, setup.cfg
   - Check for tests/, test/, or *_test.py files

2. **Run** tests:
   ```bash
   # Standard run
   pytest -v --tb=short

   # With coverage
   pytest --cov=src --cov-report=term-missing --cov-fail-under=80

   # Specific file
   pytest tests/test_specific.py -v
   ```

3. **Report** results in structured format

## Output Format

```
## Test Results

**Status**: PASS/FAIL
**Tests**: X passed, Y failed, Z skipped
**Duration**: X.Xs

### Failed Tests
| Test | Error | Location |
|------|-------|----------|
| test_name | AssertionError: ... | file.py:42 |

### Coverage Report (if requested)
| Module | Coverage |
|--------|----------|
| src/module.py | 95% |

**Overall Coverage**: X%

### Recommendations
- [Suggestion for improving tests]
```

## Common Fixes

If tests fail:
1. Read the specific test file
2. Understand what's being tested
3. Check if it's a real bug or outdated test
4. Fix appropriately

## Rules

- Never skip tests to make suite pass
- Report flaky tests separately
- Suggest missing test cases
