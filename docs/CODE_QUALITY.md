# Code Quality Guidelines

## Overview

This project uses **pre-commit hooks** to automatically run code quality checks before every commit. The hooks include:
- **black** for code formatting
- **flake8** for linting
- **isort** for import sorting
- Additional checks for trailing whitespace, file endings, YAML/JSON validation, etc.

## Tools

### Black (Code Formatter)
- **Purpose**: Automatically formats Python code to a consistent style
- **Line Length**: 88 characters (PEP 8 default)
- **Target**: Python 3.13+
- **Config**: `pyproject.toml`

### Flake8 (Linter)
- **Purpose**: Checks code for style violations and potential errors
- **Config**: `.flake8`
- **Rules**: Relaxed to work well with Black

### isort (Import Sorter)
- **Purpose**: Automatically sorts and organizes imports
- **Profile**: Black-compatible
- **Config**: `pyproject.toml`

### Pre-commit
- **Purpose**: Runs all checks automatically before commits
- **Config**: `.pre-commit-config.yaml`

## Setup

### Install Pre-commit Hooks

**Important**: Always use a virtual environment!

1. **Create and activate virtual environment**:
```bash
cd /Users/yuyu/workspace/crypto-dashboard

# Create venv (if not exists)
python3 -m venv venv

# Activate venv
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate     # On Windows
```

2. **Install pre-commit**:
```bash
pip install pre-commit
```

3. **Install the git hooks**:
```bash
pre-commit install
```

That's it! Pre-commit hooks will now run automatically on every `git commit`.

**Remember**: Always activate venv before working:
```bash
source venv/bin/activate  # From project root
```

### First Time Setup (Optional)

Run hooks on all files to check everything:
```bash
pre-commit run --all-files
```

## Usage

### Automatic (Recommended)

Once installed, hooks run automatically when you commit:

```bash
git add .
git commit -m "Your commit message"
```

**What happens:**
1. Black formats your code
2. isort organizes imports
3. Flake8 checks for errors
4. Additional checks run (trailing whitespace, etc.)

If any hook fails:
- Files are automatically fixed (Black, isort)
- Or errors are shown (Flake8)
- Commit is blocked until issues are resolved

Simply re-run `git commit` after fixes.

### Manual (Skip Hooks)

To commit without running hooks (not recommended):
```bash
git commit --no-verify -m "Emergency commit"
```

### Run Hooks Manually

Run all hooks on all files:
```bash
pre-commit run --all-files
```

Run all hooks on specific files:
```bash
pre-commit run --files shared/auth/jwt_handler.py
```

Run a specific hook:
```bash
pre-commit run black --all-files
pre-commit run flake8 --all-files
```

### Update Hook Versions

Update to the latest hook versions:
```bash
pre-commit autoupdate
```

## Configuration Details

### Flake8 Relaxed Rules

The following rules are ignored to work well with Black:

- **E203**: Whitespace before ':' (conflicts with Black)
- **W503**: Line break before binary operator (conflicts with Black)  
- **E501**: Line too long (Black handles this)
- **E402**: Module level import not at top (useful for conditional imports)
- **E701**: Multiple statements on one line (sometimes useful)

**Max Line Length**: 88 (matches Black)
**Max Complexity**: 15 (reasonable for most functions)

### Excluded Files

Both tools exclude:
- Generated gRPC files (`*_pb2.py`, `*_pb2_grpc.py`, `*_pb2.pyi`)
- Virtual environments (`venv/`, `env/`, `.venv/`)
- Build artifacts (`build/`, `dist/`, `*.egg-info`)
- Cache directories (`__pycache__/`, `.pytest_cache/`)

### Per-File Rules

- **`__init__.py`**: Unused imports allowed (F401, F403)
- **`test_*.py`**: Star imports allowed (F401, F403, F405)

## Development Workflow

### Standard Workflow (Automatic)

1. **Make your changes**
2. **Stage files**:
   ```bash
   git add .
   ```

3. **Commit** (hooks run automatically):
   ```bash
   git commit -m "Your message"
   ```

4. **Fix any issues** if hooks fail and commit again

### Manual Quality Checks

Run hooks manually before committing:
```bash
pre-commit run --all-files
```

Run on specific files only:
```bash
pre-commit run --files path/to/file.py
```

### IDE Integration

#### VS Code

Add to `.vscode/settings.json`:
```json
{
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--config", "pyproject.toml"],
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.linting.flake8Args": ["--config", ".flake8"],
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.organizeImports": true
    }
}
```

**Note**: With pre-commit hooks, IDE formatting is optional but still useful for immediate feedback.

#### PyCharm

1. **Black**: 
   - Preferences → Tools → Black
   - Enable "On save"
   - Set path to `pyproject.toml`

2. **Flake8**:
   - Preferences → Tools → External Tools → Add
   - Program: `flake8`
   - Arguments: `$FilePath$ --config=.flake8`

**Note**: Pre-commit hooks will still run on commit regardless of IDE settings.

## Installation

**Always use virtual environment**:

1. **Create and activate venv** (from project root):
```bash
cd /Users/yuyu/workspace/crypto-dashboard
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate     # Windows
```

2. **Install tools**:
```bash
pip install --upgrade pip
pip install flake8 black isort pre-commit pytest pytest-asyncio
```

3. **Install git hooks**:
```bash
pre-commit install
```

4. **Pin versions** (optional):
```bash
pip freeze > requirements_dev.txt
```

## CI/CD Integration

Add to your CI/CD pipeline (GitHub Actions example):

```yaml
- name: Install pre-commit
  run: pip install pre-commit

- name: Run pre-commit hooks
  run: pre-commit run --all-files
```

Or use the official pre-commit action:

```yaml
- uses: pre-commit/action@v3.0.0
```

## Common Issues

### Pre-commit Hook Fails

If a hook fails during commit:

1. **Check the error message** - it tells you what failed
2. **Auto-fixed issues** (Black, isort) - just commit again:
   ```bash
   git add .
   git commit -m "Same message"
   ```
3. **Flake8 errors** - fix the code issues and commit again

### Skip Hooks Temporarily

Emergency commits without hooks:
```bash
git commit --no-verify -m "Emergency fix"
```

**Use sparingly!** Fix issues in the next commit.

### Import Order Issues

isort uses `profile = "black"` to prevent conflicts. If you see issues:
```bash
pre-commit run isort --all-files
```

### Line Too Long

Black handles line length automatically. If flake8 still complains:
- The line is in an excluded file (check `.flake8`)
- Or it's a string that Black can't break (add `# noqa: E501` at end)

### Trailing Commas

Black adds trailing commas for multi-line structures. This is intentional and improves git diffs.

### Hook Installation Issues

If hooks don't run:
```bash
# Reinstall hooks
pre-commit uninstall
pre-commit install

# Verify installation
pre-commit run --all-files
```

## Style Guide Summary

- **Line length**: 88 characters
- **Quotes**: Double quotes preferred by Black
- **Indentation**: 4 spaces
- **Imports**: Sorted and grouped (stdlib, third-party, local)
- **Trailing commas**: Yes (for multi-line)
- **Function/method spacing**: 2 blank lines
- **Class spacing**: 2 blank lines

## Benefits

1. **Automatic**: Runs on every commit without manual intervention
2. **Consistency**: All code looks the same
3. **No arguments**: Black is opinionated, no style debates
4. **Faster reviews**: Focus on logic, not formatting
5. **Error prevention**: Catches issues before they reach the repository
6. **Team enforcement**: Everyone uses the same quality standards
7. **CI/CD ready**: Same checks locally and in pipelines

## Hook Configuration

All hooks are configured in `.pre-commit-config.yaml`:

### Included Hooks

1. **Black** - Code formatting
2. **Flake8** - Linting with custom config
3. **isort** - Import sorting (Black-compatible)
4. **trailing-whitespace** - Removes trailing whitespace
5. **end-of-file-fixer** - Ensures files end with newline
6. **check-yaml** - Validates YAML files
7. **check-json** - Validates JSON files
8. **check-toml** - Validates TOML files
9. **check-added-large-files** - Prevents large files (>1MB)
10. **check-merge-conflict** - Detects merge conflict markers
11. **mixed-line-ending** - Fixes to LF line endings
12. **Python checks** - No blanket noqa, type annotations, etc.

### Excluded Files

Hooks automatically skip:
- Generated proto files (`*_pb2.py`, `*_pb2_grpc.py`)
- Virtual environments (`venv/`, `env/`, `.venv/`)
- Build artifacts (`build/`, `dist/`, `*.egg-info`)
- Cache directories (`__pycache__/`, `.pytest_cache/`)

### Updating Hooks

Keep hooks up to date:
```bash
pre-commit autoupdate
```

## Questions?

For more information:
- Black: https://black.readthedocs.io/
- Flake8: https://flake8.pycqa.org/
- isort: https://pycqa.github.io/isort/

