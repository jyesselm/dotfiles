---
description: Generate a quick Python script for one-off tasks
---

Create a focused Python script for quick data processing or analysis tasks.

## Input: $ARGUMENTS

Description of what the script should do.

## Template

```python
#!/usr/bin/env python3
"""
[Script description]

Usage:
    python script_name.py [arguments]
"""
from pathlib import Path
import argparse


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    # Add arguments here
    args = parser.parse_args()

    # Implementation here


if __name__ == "__main__":
    main()
```

## Standards

- Always include argparse for CLI
- Type hints on all functions
- Brief docstrings
- Handle errors gracefully
- Print progress for long operations

## Common Patterns

### File Processing
```python
from pathlib import Path

for path in Path(input_dir).glob("*.csv"):
    process_file(path)
```

### Data Loading
```python
import pandas as pd

df = pd.read_csv(path)
# or
import json
data = json.loads(path.read_text())
```

### Progress Tracking
```python
from tqdm import tqdm

for item in tqdm(items, desc="Processing"):
    process(item)
```

## Output

1. Generate the script
2. Save to current directory or specified path
3. Make executable: `chmod +x script.py`
4. Show usage example
