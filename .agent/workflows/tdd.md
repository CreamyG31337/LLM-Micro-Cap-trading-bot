---
description: Workflow for implementing features using Test-Driven Development (Red-Green-Refactor)
---

# TDD Workflow

This workflow ensures robust code by writing tests *before* implementation.

## 1. Red Phase (Write Test)
**Goal**: Define the expected behavior.

- **Backend**: Create a new test file or add a function to `tests/`.
  - Example: `tests/test_scheduler.py`
  - Mock dependencies using `base_fixture` patterns.
- **Frontend**: Create a `*.test.ts` file next to the source.
  - Example: `web_dashboard/src/js/utils.test.ts`

**Action**: Run the test.
> It **MUST** fail. If it passes, verify your assumptions.

## 2. Green Phase (Implement)
**Goal**: Make the test pass.

- Write the *minimum* amount of code required.
- Do not worry about perfection or optimization yet.

**Action**: Run the test.
> It **MUST** pass.

## 3. Refactor Phase (Cleanup)
**Goal**: Improve code quality.

- Remove duplication.
- Improve naming.
- Optimize performance.

**Action**: Run the test.
> It **MUST** still pass.

## Commands
- **Backend Single Test**: `.\web_dashboard\venv\Scripts\python -m pytest tests/test_specific_file.py`
- **Frontend Single Test**: `cd web_dashboard && npx vitest run path/to/test.ts`
