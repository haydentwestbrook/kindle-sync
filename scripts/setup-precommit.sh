#!/bin/bash

# Setup Pre-commit Hooks for Kindle Sync
# This script installs and configures pre-commit hooks for code quality

set -e

echo "🔧 Setting up pre-commit hooks for Kindle Sync..."

# Check if we're in a virtual environment
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ Virtual environment detected: $VIRTUAL_ENV"
    PIP_CMD="pip"
elif [[ -f "venv/bin/activate" ]]; then
    echo "🔄 Activating virtual environment..."
    source venv/bin/activate
    PIP_CMD="pip"
else
    echo "⚠️  No virtual environment found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    PIP_CMD="pip"
fi

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "📦 Installing pre-commit..."
    $PIP_CMD install pre-commit
else
    echo "✅ pre-commit is already installed"
fi

# Install pre-commit hooks
echo "🔗 Installing pre-commit hooks..."
pre-commit install

# Install additional dependencies for enhanced hooks
echo "📦 Installing additional dependencies for enhanced hooks..."
$PIP_CMD install flake8-docstrings flake8-bugbear pylint pytest-cov pytest-benchmark ruff detect-secrets

# Update secrets baseline
echo "🔍 Updating secrets baseline..."
if [ -f ".secrets.baseline" ]; then
    detect-secrets scan --baseline .secrets.baseline
    echo "✅ Secrets baseline updated"
else
    echo "⚠️  No existing secrets baseline found. Run 'detect-secrets scan --baseline .secrets.baseline' to create one."
fi

# Run pre-commit on all files to ensure everything is working
echo "🧪 Running pre-commit on all files..."
pre-commit run --all-files

echo "✅ Pre-commit setup complete!"
echo ""
echo "📋 Available commands:"
echo "  pre-commit run --all-files    # Run all hooks on all files"
echo "  pre-commit run                # Run hooks on staged files"
echo "  pre-commit run <hook-id>      # Run specific hook"
echo "  pre-commit uninstall          # Remove pre-commit hooks"
echo ""
echo "🔍 Hook IDs available:"
echo "  - trailing-whitespace"
echo "  - end-of-file-fixer"
echo "  - check-yaml"
echo "  - black"
echo "  - isort"
echo "  - flake8"
echo "  - mypy"
echo "  - bandit"
echo "  - detect-secrets"
echo "  - pylint"
echo "  - pytest"
echo "  - pyupgrade"
echo "  - ruff"
echo ""
echo "💡 Tips:"
echo "  - Hooks will run automatically on git commit"
echo "  - Use 'git commit --no-verify' to skip hooks (not recommended)"
echo "  - Fix issues and re-stage files to commit successfully"
