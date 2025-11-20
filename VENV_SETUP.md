# Virtual Environment Setup Guide

## Why Use Virtual Environments?

Virtual environments (venv) isolate your Python dependencies per project:
- ✅ Avoid dependency conflicts between projects
- ✅ Keep global Python installation clean
- ✅ Ensure reproducible builds
- ✅ Easy to reset if something breaks

## Quick Start

### Create Virtual Environment

From project root:

```bash
cd /Users/yuyu/workspace/crypto-dashboard
python3 -m venv venv
```

This creates a `venv/` directory with isolated Python installation.

### Activate Virtual Environment

**macOS/Linux**:
```bash
source venv/bin/activate
```

**Windows**:
```cmd
venv\Scripts\activate
```

**Windows PowerShell**:
```powershell
venv\Scripts\Activate.ps1
```

Your prompt should show `(venv)` when activated.

### Install Dependencies

With venv activated:

```bash
# Upgrade pip first
pip install --upgrade pip

# Install development tools
pip install pre-commit flake8 black isort pytest pytest-asyncio

# Install service-specific dependencies
cd <service-directory>
pip install -r requirements.txt
```

### Deactivate Virtual Environment

When done:

```bash
deactivate
```

## Working with Virtual Environments

### Daily Workflow

1. **Always activate venv before working**:
   ```bash
   cd /Users/yuyu/workspace/crypto-dashboard
   source venv/bin/activate
   ```

2. **Work on your code** (run tests, start services, etc.)

3. **Deactivate when switching projects**:
   ```bash
   deactivate
   ```

### Check Which Python You're Using

```bash
which python   # Should show path inside venv/
python --version  # Should show 3.13.x
```

### List Installed Packages

```bash
pip list
```

### Freeze Dependencies

Save exact versions:

```bash
pip freeze > requirements_pinned.txt
```

## IDE Integration

### VS Code

Add to `.vscode/settings.json`:

```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
    "python.terminal.activateEnvironment": true
}
```

VS Code will automatically activate venv in terminal.

### PyCharm

1. File → Settings → Project → Python Interpreter
2. Add Interpreter → Existing Environment
3. Select: `/Users/yuyu/workspace/crypto-dashboard/venv/bin/python`

## Troubleshooting

### "Command not found" after installing

Make sure venv is activated:
```bash
source venv/bin/activate
which pip  # Should show path inside venv/
```

### Wrong Python version

Check your Python 3.13 installation:
```bash
python3 --version  # Should be 3.13.x
which python3
```

### Corrupted venv

Delete and recreate:
```bash
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Permission errors

Don't use `sudo` with pip in venv! Just:
```bash
pip install <package>
```

## Best Practices

1. ✅ **One venv per project** - Keep it in project root
2. ✅ **Always activate** - Before running anything
3. ✅ **Add to .gitignore** - Don't commit venv/ (already done)
4. ✅ **Document dependencies** - Keep requirements.txt updated
5. ✅ **Pin versions** - Use requirements_pinned.txt for reproducibility
6. ❌ **Never** - Use system Python for project work
7. ❌ **Never** - Install project dependencies globally

## Quick Reference

```bash
# Create
python3 -m venv venv

# Activate (macOS/Linux)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Deactivate
deactivate

# Upgrade pip
pip install --upgrade pip

# Install from requirements
pip install -r requirements.txt

# Freeze dependencies
pip freeze > requirements_pinned.txt

# Delete (if needed)
rm -rf venv
```

## Setup Script

The `scripts/setup_local.sh` automatically:
- ✅ Creates venv if not exists
- ✅ Activates venv
- ✅ Installs development tools
- ✅ Installs pre-commit hooks

Just run:
```bash
./scripts/setup_local.sh
```

Then activate venv in future sessions:
```bash
source venv/bin/activate
```

