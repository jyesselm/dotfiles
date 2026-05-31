---
description: Analyze task complexity and create an implementation plan
---

Analyze the requested task and create a structured implementation plan.

## Input: $ARGUMENTS

Task description from user.

## Analysis Framework

### 1. Task Classification
- **Research**: Literature review, data analysis design
- **Development**: New feature, bug fix, refactor
- **Documentation**: Protocols, papers, notes
- **DevOps**: CI/CD, deployment, infrastructure

### 2. Complexity Assessment
| Level | Scope | Files | Dependencies |
|-------|-------|-------|--------------|
| Small | Single function | 1-2 | None |
| Medium | Module/feature | 3-5 | Minor |
| Large | Cross-module | 5-10 | Several |
| XL | Architecture | 10+ | Major |

### 3. Research Needed
- [ ] Existing code to understand?
- [ ] External docs to read?
- [ ] Similar implementations to reference?

## Output Format

```
## Task: [One-line summary]

### Classification
- Type: [research/dev/docs/devops]
- Complexity: [small/medium/large/xl]
- Priority: [high/medium/low]

### Understanding
[2-3 sentences on what this task involves]

### Prerequisites
- [ ] [What needs to be understood first]

### Implementation Plan

#### Phase 1: [Name]
- [ ] Step 1.1
- [ ] Step 1.2
*Checkpoint: [How to verify]*

#### Phase 2: [Name]
- [ ] Step 2.1
*Checkpoint: [How to verify]*

### Files to Touch
| File | Action | Purpose |
|------|--------|---------|
| path/file.py | create/modify | reason |

### Risks
- [Potential issue]: [Mitigation]

### Definition of Done
- [ ] Code complete
- [ ] Tests pass
- [ ] Documentation updated (if needed)
```

## Rules

- Break large tasks into phases
- Each phase should be completable in one session
- Include verification checkpoints
- Identify blockers early
