# Pre-commit Hooks Setup Guide

This guide explains how to set up and use pre-commit hooks to ensure code quality and consistency in the Kindle Sync project.

## Overview

Pre-commit hooks automatically run code quality checks before each commit, ensuring that:
- Code is properly formatted
- Linting rules are followed
- Security vulnerabilities are detected
- Tests pass
- Type checking is performed
- Secrets are not accidentally committed

## Quick Setup

### 1. Run the Setup Script

```bash
# Make the script executable and run it
chmod +x scripts/setup-precommit.sh
./scripts/setup-precommit.sh
```

This script will:
- Install pre-commit if not already installed
- Install all required dependencies
- Set up the pre-commit hooks
- Run initial checks on all files
- Update the secrets baseline

### 2. Manual Setup (Alternative)

If you prefer to set up manually:

```bash
# Install pre-commit
pip install pre-commit

# Install additional dependencies
pip install flake8-docstrings flake8-bugbear pylint pytest-cov pytest-benchmark ruff

# Install the hooks
pre-commit install

# Update secrets baseline
detect-secrets scan --baseline .secrets.baseline
```

## Configured Hooks

The following hooks are configured and will run automatically on commit:

### 🔧 Basic Checks
- **trailing-whitespace** - Removes trailing whitespace
- **end-of-file-fixer** - Ensures files end with newline
- **check-yaml** - Validates YAML syntax
- **check-json** - Validates JSON syntax
- **check-toml** - Validates TOML syntax
- **check-ast** - Validates Python syntax
- **check-merge-conflict** - Detects merge conflict markers
- **check-case-conflict** - Detects case conflicts in filenames
- **check-executables-have-shebangs** - Ensures executable files have shebangs
- **check-shebang-scripts-are-executable** - Ensures shebang scripts are executable
- **mixed-line-ending** - Ensures consistent line endings
- **pretty-format-json** - Formats JSON files
- **check-added-large-files** - Prevents large files from being committed
- **debug-statements** - Detects debug statements (pdb, ipdb, etc.)
- **check-docstring-first** - Ensures docstrings are at the beginning of files

### 🎨 Code Formatting
- **black** - Python code formatter (line length: 88)
- **isort** - Import sorter (profile: black)
- **pyupgrade** - Upgrades Python syntax to newer versions (py311+)
- **ruff** - Fast Python linter and formatter

### 🔍 Code Quality
- **flake8** - Python linter with additional plugins:
  - flake8-docstrings (docstring checking)
  - flake8-bugbear (bug detection)
- **pylint** - Comprehensive Python linter
- **mypy** - Static type checker (strict mode)

### 🧪 Testing
- **pytest** - Runs tests with coverage and benchmark support
  - Only runs on files in `tests/` directory
  - Stops on first failure
  - Short traceback format

### 🔒 Security
- **bandit** - Security linter for Python
  - Skips B101 (assert_used) and B601 (shell_injection_subprocess)
  - Excludes test files
  - Generates JSON report
- **detect-secrets** - Detects secrets and credentials
  - Uses baseline file to avoid false positives
  - Scans for various secret patterns

## Configuration Files

### `.pre-commit-config.yaml`
Main configuration file defining all hooks and their settings.

### `.flake8`
Flake8 configuration with:
- Line length: 88 (matching Black)
- Ignored rules: E203, W503, E501, W504, C901, B008, B006
- Excluded directories: build, dist, .git, __pycache__, etc.
- Per-file ignores for tests and __init__.py files

### `.pylintrc`
Comprehensive Pylint configuration with:
- Disabled rules: C0114, C0116, R0903, R0913, W0613
- Naming conventions: snake_case for functions/variables, PascalCase for classes
- Complexity limits and other quality thresholds

### `.secrets.baseline`
Baseline file for detect-secrets to avoid false positives on known safe strings.

## Usage

### Automatic Usage
Hooks run automatically when you commit:

```bash
git add .
git commit -m "Your commit message"
# Hooks run automatically here
```

### Manual Usage

Run all hooks on all files:
```bash
pre-commit run --all-files
```

Run hooks only on staged files:
```bash
pre-commit run
```

Run a specific hook:
```bash
pre-commit run black
pre-commit run flake8
pre-commit run mypy
```

### Skipping Hooks (Not Recommended)
```bash
git commit --no-verify -m "Skip hooks"
```

## Troubleshooting

### Common Issues

#### 1. Hook Failures
If a hook fails:
1. Fix the issues reported
2. Stage the fixed files: `git add <fixed-files>`
3. Commit again: `git commit -m "Your message"`

#### 2. Black/Isort Conflicts
If Black and isort have conflicts:
```bash
# Run isort first, then black
pre-commit run isort --all-files
pre-commit run black --all-files
```

#### 3. MyPy Errors
If MyPy reports type errors:
- Add type hints to functions
- Use `# type: ignore` for unavoidable issues
- Update the mypy configuration if needed

#### 4. Flake8 Errors
If Flake8 reports style issues:
- Fix the issues manually
- Or update `.flake8` to ignore specific rules

#### 5. Bandit False Positives
If Bandit reports false positives:
- Add `# nosec` comment for specific lines
- Update bandit configuration to skip specific tests

#### 6. Detect-secrets False Positives
If detect-secrets reports false positives:
```bash
# Update the baseline
detect-secrets scan --baseline .secrets.baseline
```

### Updating Hooks

To update hook versions:
```bash
pre-commit autoupdate
pre-commit install
```

### Removing Hooks

To remove pre-commit hooks:
```bash
pre-commit uninstall
```

## Best Practices

### 1. Fix Issues Immediately
Don't let hook failures accumulate. Fix them as they appear.

### 2. Use Meaningful Commit Messages
Even with automated checks, write clear commit messages.

### 3. Run Hooks Locally
Test your changes locally before pushing:
```bash
pre-commit run --all-files
```

### 4. Keep Dependencies Updated
Regularly update pre-commit and hook versions:
```bash
pre-commit autoupdate
```

### 5. Configure IDE Integration
Set up your IDE to use the same tools:
- Black formatter
- isort import sorter
- MyPy type checker
- Flake8 linter

## Integration with CI/CD

The same hooks can be run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run pre-commit
  uses: pre-commit/action@v3.0.0
```

## Customization

### Adding New Hooks
Edit `.pre-commit-config.yaml` to add new hooks:

```yaml
- repo: https://github.com/example/new-hook
  rev: v1.0.0
  hooks:
    - id: new-hook
      args: [--config, .new-hook-config]
```

### Modifying Existing Hooks
Update the configuration in `.pre-commit-config.yaml`:

```yaml
- id: flake8
  args: [--max-line-length=100]  # Override default
```

### Excluding Files
Add exclusions to specific hooks:

```yaml
- id: mypy
  exclude: ^tests/  # Exclude test files
```

## Support

For issues with pre-commit hooks:
1. Check the hook documentation
2. Review the configuration files
3. Run hooks manually to debug
4. Check the project's issue tracker

## Resources

- [Pre-commit Documentation](https://pre-commit.com/)
- [Black Documentation](https://black.readthedocs.io/)
- [isort Documentation](https://pycqa.github.io/isort/)
- [Flake8 Documentation](https://flake8.pycqa.org/)
- [MyPy Documentation](https://mypy.readthedocs.io/)
- [Pylint Documentation](https://pylint.pycqa.org/)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Detect-secrets Documentation](https://github.com/Yelp/detect-secrets)
