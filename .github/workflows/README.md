# GitHub Actions Workflows

## CI Workflow

The `ci.yml` workflow runs on every push and pull request to `main` or `develop` branches.

### What it does:

1. **Linting with Flake8**
   - Uses the project's `.flake8` configuration
   - Checks all Python files for style violations
   - Fails the build on syntax errors or undefined names

2. **Basic Testing**
   - Runs pytest on all test files
   - Supports both `test_*.py` and `*_test.py` patterns
   - Gracefully skips if no tests exist

### Status Badge

Add this to your README.md:

```markdown
![CI](https://github.com/YOUR_USERNAME/crypto-dashboard/workflows/CI/badge.svg)
```

### Local Testing

Before pushing, you can run the same checks locally:

```bash
# Linting
flake8 . --config=.flake8

# Testing
pytest -v
```

Or use pre-commit hooks which run automatically on commit:

```bash
pre-commit run --all-files
```

### Configuration

- **Python Version**: 3.13
- **Flake8 Config**: `.flake8`
- **Pytest Config**: `pytest.ini`
- **Triggers**: Push and PR to main/develop branches

### Adding More Checks

To add more checks, edit `.github/workflows/ci.yml`:

```yaml
- name: Type checking with mypy
  run: |
    pip install mypy
    mypy .

- name: Security check with bandit
  run: |
    pip install bandit
    bandit -r . -f json -o bandit-report.json
```

