# Agent Guidelines for LLM Micro-Cap Trading Bot

## Environment Setup
- **This is a Windows environment** - use Windows-specific commands and paths
- **Always activate virtual environment** before running any commands:
  ```bash
  .\venv\Scripts\activate
  ```
- **Use trading_data/funds/TEST directory** for development (not "trading_data/funds/Project Chimera" which is production)
- **Copy CSVs between funds** anytime: Copy files from `trading_data/funds/Project Chimera/` to `trading_data/funds/TEST/` for testing

## Build/Lint/Test Commands

### Type Checking
```bash
mypy trading_script.py
```

### Linting
```bash
ruff check trading_script.py
ruff check --fix trading_script.py  # Auto-fix issues
```

### Testing
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_financial_calculations.py -v

# Run tests with coverage
python -m pytest tests/ --cov=.

# Interactive test runner
python run_tests.py
```

### Development Mode
```bash
python dev_run.py --data-dir "trading_data/funds/TEST"
```

## Committing Code
- **ALWAYS run unit tests before committing**:
  ```bash
  python -m pytest tests/ -v
  ```
- **Run linting and type checking** before committing:
  ```bash
  ruff check trading_script.py
  mypy trading_script.py
  ```
- **Ensure all tests pass** before pushing changes
- **Use descriptive commit messages** that explain the "why" rather than just the "what"

## Code Style Guidelines

### Python Version & Requirements
- Python 3.11+ required
- Use `decimal.Decimal` for all financial calculations
- Handle timezone-aware datetimes properly

### Type Hints
- Strict typing enabled with mypy
- Use complete type annotations for all functions
- Avoid `Any` types except when necessary
- Use `Optional[T]` for nullable types

### Imports
- Use absolute imports
- Group imports: standard library, third-party, local modules
- isort configuration: `known-first-party = ["trading_script"]`

### Formatting
- Line length: 100 characters
- Use double quotes for strings
- Follow PEP 8 conventions

### Naming Conventions
- Functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_CASE`
- Private methods: `_leading_underscore`

### Error Handling
- Use specific exception types, not generic `Exception`
- Log all errors with context
- Provide meaningful error messages
- Handle edge cases gracefully (None values, empty data)

### Documentation
- Use comprehensive docstrings for modules and functions
- Include type hints in docstrings when helpful
- Document complex business logic

### Financial Calculations
- Always use `Decimal` for money values
- Handle currency conversion properly
- Validate decimal precision
- Use `or 0` pattern for None handling in P&L calculations

### Testing
- Write unit tests for all financial calculations
- Test edge cases and error conditions
- Use descriptive test names
- Mock external dependencies

### File Structure
- Keep modules focused on single responsibilities
- Use repository pattern for data access
- Separate business logic from presentation
- Follow existing modular architecture

### Security
- Never log or expose sensitive data
- Validate all user inputs
- Use secure practices for file operations
- Avoid exposing secrets in code

### Performance
- Cache expensive operations when appropriate
- Use efficient data structures
- Profile code before optimizing
- Consider memory usage for large datasets