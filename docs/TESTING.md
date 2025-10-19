# Testing Guide

This document provides comprehensive information about testing the Kindle Scribe Sync system.

## Table of Contents

- [Overview](#overview)
- [Test Structure](#test-structure)
- [Running Tests](#running-tests)
- [Test Types](#test-types)
- [Writing Tests](#writing-tests)
- [Test Configuration](#test-configuration)
- [CI/CD Integration](#cicd-integration)
- [Performance Testing](#performance-testing)
- [Troubleshooting](#troubleshooting)

## Overview

The Kindle Scribe Sync system includes a comprehensive testing suite with:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **End-to-End Tests**: Test complete workflows
- **Performance Tests**: Benchmark system performance
- **Security Tests**: Check for security vulnerabilities
- **Code Quality Tests**: Ensure code standards

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                 # Pytest configuration and shared fixtures
├── unit/                       # Unit tests
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_file_watcher.py
│   ├── test_pdf_converter.py
│   ├── test_kindle_sync.py
│   └── test_sync_processor.py
├── integration/                # Integration tests
│   ├── __init__.py
│   ├── test_config_integration.py
│   └── test_file_processing_integration.py
├── e2e/                        # End-to-end tests
│   ├── __init__.py
│   └── test_complete_workflow.py
├── fixtures/                   # Test fixtures and mock data
│   ├── __init__.py
│   ├── sample_data.py
│   └── mock_objects.py
└── utils/                      # Testing utilities
    ├── __init__.py
    ├── test_helpers.py
    └── test_runner.py
```

## Running Tests

### Using the Test Script

The easiest way to run tests is using the provided script:

```bash
# Run all tests
./scripts/run-tests.sh

# Run specific test types
./scripts/run-tests.sh --type unit
./scripts/run-tests.sh --type integration
./scripts/run-tests.sh --type e2e

# Run with coverage
./scripts/run-tests.sh --coverage

# Run quick tests (unit tests, no slow tests)
./scripts/run-tests.sh --quick

# Run CI-appropriate tests
./scripts/run-tests.sh --ci

# Run with specific markers
./scripts/run-tests.sh --markers "unit,not slow"

# Generate test report
./scripts/run-tests.sh --report test-results.md
```

### Using Make

```bash
# Run all tests
make test

# Run specific test types
make test-unit
make test-integration
make test-e2e

# Run with coverage
make test-coverage

# Run quick tests
make test-quick

# Run CI tests
make test-ci
```

### Using Pytest Directly

```bash
# Run all tests
pytest

# Run specific test files
pytest tests/unit/test_config.py

# Run with markers
pytest -m "unit"
pytest -m "integration"
pytest -m "e2e"
pytest -m "not slow"

# Run with coverage
pytest --cov=src --cov-report=html

# Run with verbose output
pytest -v

# Run specific test functions
pytest tests/unit/test_config.py::TestConfig::test_config_initialization
```

## Test Types

### Unit Tests

Unit tests test individual components in isolation using mocks and fixtures.

**Location**: `tests/unit/`

**Examples**:
- Configuration loading and validation
- File watcher event handling
- PDF conversion logic
- Email sending functionality

**Running**:
```bash
pytest tests/unit/ -v
```

### Integration Tests

Integration tests test how components work together with real file operations.

**Location**: `tests/integration/`

**Examples**:
- Configuration with real files
- File processing workflows
- Component interactions

**Running**:
```bash
pytest tests/integration/ -v
```

### End-to-End Tests

E2E tests test complete workflows from start to finish.

**Location**: `tests/e2e/`

**Examples**:
- Complete markdown to Kindle workflow
- Complete PDF to Obsidian workflow
- File watcher with real file operations

**Running**:
```bash
pytest tests/e2e/ -v
```

**Note**: E2E tests are marked as `slow` and may take longer to run.

## Writing Tests

### Test Structure

```python
import pytest
from unittest.mock import Mock, patch
from src.module import ClassToTest

class TestClassToTest:
    """Test cases for ClassToTest."""

    def test_method_success(self, fixture_name):
        """Test successful method execution."""
        # Arrange
        instance = ClassToTest()

        # Act
        result = instance.method()

        # Assert
        assert result is not None
        assert result == expected_value

    def test_method_with_error(self):
        """Test method error handling."""
        # Arrange
        instance = ClassToTest()

        # Act & Assert
        with pytest.raises(ValueError):
            instance.method_with_error()

    @pytest.mark.slow
    def test_slow_method(self):
        """Test that takes a long time."""
        # Test implementation
        pass
```

### Using Fixtures

```python
@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        "obsidian": {"vault_path": "/tmp/test"},
        "kindle": {"email": "test@kindle.com"}
    }

def test_with_fixture(sample_config):
    """Test using a fixture."""
    config = Config(sample_config)
    assert config.get_obsidian_vault_path() == Path("/tmp/test")
```

### Using Mocks

```python
@patch('src.module.external_dependency')
def test_with_mock(mock_dependency):
    """Test with mocked external dependency."""
    mock_dependency.return_value = "mocked_value"

    result = function_under_test()

    assert result == "expected_result"
    mock_dependency.assert_called_once()
```

### Test Markers

Use markers to categorize tests:

```python
@pytest.mark.unit
def test_unit_functionality():
    """Unit test."""
    pass

@pytest.mark.integration
def test_integration_functionality():
    """Integration test."""
    pass

@pytest.mark.e2e
def test_e2e_functionality():
    """End-to-end test."""
    pass

@pytest.mark.slow
def test_slow_functionality():
    """Slow test."""
    pass

@pytest.mark.network
def test_network_functionality():
    """Test requiring network."""
    pass
```

## Test Configuration

### Pytest Configuration

The `pytest.ini` file configures pytest behavior:

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*

addopts =
    --verbose
    --tb=short
    --strict-markers
    --cov=src
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-fail-under=80

markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow running tests
    network: Tests requiring network access
    ocr: Tests requiring OCR functionality
    email: Tests requiring email functionality
```

### Test Dependencies

Install test dependencies:

```bash
pip install -r requirements-test.txt
```

### System Dependencies

For tests requiring OCR and PDF processing:

**Ubuntu/Debian**:
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-eng poppler-utils
```

**macOS**:
```bash
brew install tesseract poppler
```

## CI/CD Integration

### GitHub Actions

The project includes GitHub Actions workflows for automated testing:

- **Unit Tests**: Run on every push and PR
- **Integration Tests**: Run after unit tests pass
- **E2E Tests**: Run on main branch pushes and scheduled runs
- **Security Tests**: Run on every push
- **Code Quality**: Run on every push
- **Docker Tests**: Run on every push

### Local CI Simulation

Run CI-appropriate tests locally:

```bash
make test-ci
# or
./scripts/run-tests.sh --ci
```

This runs:
- Unit tests with coverage
- Integration tests
- Code quality checks
- Security checks

## Performance Testing

### Benchmarking

Run performance tests:

```bash
pytest --benchmark-only
```

### Performance Markers

Mark slow tests:

```python
@pytest.mark.slow
def test_performance_critical_function():
    """Test that measures performance."""
    # Performance test implementation
    pass
```

### Performance Assertions

```python
def test_function_performance():
    """Test that function runs within time limit."""
    import time

    start_time = time.time()
    result = function_under_test()
    execution_time = time.time() - start_time

    assert execution_time < 1.0  # Should complete within 1 second
    assert result is not None
```

## Troubleshooting

### Common Issues

**Import Errors**:
```bash
# Ensure you're in the project root
cd /path/to/kindle-sync

# Install dependencies
pip install -r requirements-test.txt
```

**Missing System Dependencies**:
```bash
# Install OCR and PDF tools
sudo apt-get install tesseract-ocr poppler-utils
```

**Permission Errors**:
```bash
# Make test script executable
chmod +x scripts/run-tests.sh
```

**Test Failures**:
```bash
# Run with verbose output
pytest -v

# Run specific failing test
pytest tests/unit/test_config.py::TestConfig::test_specific_method -v

# Run with debugging
pytest --pdb
```

### Test Debugging

**Debug Mode**:
```bash
pytest --pdb  # Drop into debugger on failure
pytest -s     # Don't capture output
pytest -vv    # Extra verbose
```

**Test Isolation**:
```bash
pytest -x     # Stop on first failure
pytest --lf   # Run last failed tests only
pytest --ff   # Run failed tests first
```

### Coverage Issues

**Low Coverage**:
```bash
# Generate detailed coverage report
pytest --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html
```

**Coverage Configuration**:
```ini
# In pytest.ini
[tool:pytest]
cov-fail-under = 80
```

### Performance Issues

**Slow Tests**:
```bash
# Skip slow tests
pytest -m "not slow"

# Run only slow tests
pytest -m "slow"
```

**Memory Issues**:
```bash
# Run with memory profiling
pytest --memray
```

## Best Practices

### Test Organization

1. **One test class per module**
2. **Descriptive test names**
3. **Arrange-Act-Assert pattern**
4. **Use fixtures for common setup**
5. **Mock external dependencies**

### Test Data

1. **Use fixtures for test data**
2. **Create realistic test scenarios**
3. **Test edge cases and error conditions**
4. **Use factories for complex objects**

### Assertions

1. **Use specific assertions**
2. **Test both success and failure cases**
3. **Verify side effects**
4. **Check error messages**

### Performance

1. **Mark slow tests appropriately**
2. **Use timeouts for long-running tests**
3. **Profile performance-critical code**
4. **Mock expensive operations**

## Contributing

When adding new tests:

1. **Follow existing patterns**
2. **Add appropriate markers**
3. **Update documentation**
4. **Ensure CI passes**
5. **Maintain coverage requirements**

For more information, see the [Contributing Guide](CONTRIBUTING.md).
