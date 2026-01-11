---
description: How to run tests and checks locally
---

# Run Local Tests

This workflow runs the local test suite to verify code changes before pushing.

## 1. Run Python Tests

Run the full Python test suite using the included runner script.

```bash
# Activate virtual environment if not already active
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate

# Run all tests
python run_tests.py all
```

// turbo
## 2. Run Type Checks

Run static type checking with MyPy.

```bash
.\run_type_check.bat
```

## 3. Verify Frontend Build (Optional)

If you made changes to the `web_dashboard` or frontend code, verify it builds.

```bash
npm run build
```

## 4. Run Specific Tests (Optional)

To run a specific category of tests (faster than running all):

```bash
# Run only portfolio display bug tests
python run_tests.py portfolio_display

# Run only integration tests
python run_tests.py integration
```

## 5. Web Dashboard Tests

The web dashboard has its own virtual environment and test suite.

### Backend (Flask)

```bash
# Use the web_dashboard venv
.\web_dashboard\venv\Scripts\python -m pytest tests/test_flask_routes.py
```

### Frontend (TypeScript)

```bash
cd web_dashboard
npm test
```
