---
description: Analyze experimental data (DMS, SHAPE, sequences)
---

Set up and execute data analysis for RNA experimental data.

## Input: $ARGUMENTS

- Data file path or directory
- Analysis type: `dms`, `shape`, `sequence`, `structure`
- Optional: output format, comparison conditions

## Analysis Types

### DMS Analysis
```python
# Standard DMS processing pipeline
import pandas as pd
import numpy as np
from pathlib import Path

def load_dms_data(path: str) -> pd.DataFrame:
    """Load and validate DMS reactivity data."""
    ...

def normalize_dms(data: pd.DataFrame, method: str = "boxplot") -> pd.DataFrame:
    """Normalize DMS reactivities using boxplot method."""
    ...

def qc_dms(data: pd.DataFrame) -> dict:
    """Quality control checks for DMS data."""
    checks = {
        "coverage_ok": data["depth"].min() > 1000,
        "mutation_rate_ok": data["mut_rate"].mean() < 0.1,
        "signal_noise_ok": data["signal_noise"].mean() > 2,
    }
    return checks
```

### SHAPE Analysis
Similar pipeline with 2-8% normalization

### Sequence Analysis
- Motif finding
- Conservation analysis
- Structure prediction

## Workflow

1. **Load** data and validate format
2. **QC** - Check data quality
3. **Process** - Normalize, filter
4. **Analyze** - Run requested analysis
5. **Visualize** - Generate plots
6. **Export** - Save results

## Output

```
## Data Summary
- File: [path]
- Sequences: N
- Conditions: [list]

## Quality Control
| Metric | Value | Status |
|--------|-------|--------|
| Coverage | X | PASS/FAIL |
| Mut Rate | X% | PASS/FAIL |

## Results
[Analysis-specific results]

## Figures Generated
- [figure1.png]: Description
- [figure2.png]: Description

## Interpretation
[Biological interpretation of results]

## Next Steps
- [ ] Suggested follow-up analysis
```

## Common Issues

- Low coverage: Need more sequencing depth
- High mutation rate: Check for degradation
- Poor correlation: Check experimental conditions
