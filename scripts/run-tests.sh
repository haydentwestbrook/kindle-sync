#!/bin/bash

# Kindle Scribe Sync - Test Runner Script
# This script provides various options for running tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
TEST_TYPE="all"
VERBOSE=false
COVERAGE=false
QUICK=false
CI=false
REPORT_FILE=""
MARKERS=""

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -t, --type TYPE         Type of tests to run (unit|integration|e2e|all) [default: all]
    -m, --markers MARKERS   Pytest markers to filter tests (e.g., "unit,not slow")
    -v, --verbose           Enable verbose output
    -c, --coverage          Generate coverage report
    -q, --quick             Run quick tests only (unit tests, no slow tests)
    --ci                    Run CI-appropriate tests (unit + integration, no E2E)
    -r, --report FILE       Output file for test report
    -h, --help              Show this help message

Examples:
    $0 --type unit --coverage
    $0 --quick --verbose
    $0 --ci --report test-results.txt
    $0 --markers "unit,not slow" --coverage
    $0 --type e2e --verbose

EOF
}

# Function to check dependencies
check_dependencies() {
    print_status "Checking dependencies..."

    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed"
        exit 1
    fi

    # Check pip
    if ! command -v pip3 &> /dev/null; then
        print_error "pip3 is required but not installed"
        exit 1
    fi

    # Check pytest
    if ! python3 -c "import pytest" &> /dev/null; then
        print_warning "pytest not found, installing test dependencies..."
        pip3 install -r requirements-test.txt
    fi

    print_success "Dependencies check completed"
}

# Function to install system dependencies
install_system_dependencies() {
    print_status "Installing system dependencies..."

    # Detect OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y tesseract-ocr tesseract-ocr-eng poppler-utils
        elif command -v yum &> /dev/null; then
            sudo yum install -y tesseract poppler-utils
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y tesseract poppler-utils
        else
            print_warning "Package manager not found, skipping system dependencies"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install tesseract poppler
        else
            print_warning "Homebrew not found, skipping system dependencies"
        fi
    else
        print_warning "Unsupported OS, skipping system dependencies"
    fi

    print_success "System dependencies installation completed"
}

# Function to run tests
run_tests() {
    local cmd="python3 -m pytest"

    # Add test path based on type
    case $TEST_TYPE in
        "unit")
            cmd="$cmd tests/unit/"
            ;;
        "integration")
            cmd="$cmd tests/integration/"
            ;;
        "e2e")
            cmd="$cmd tests/e2e/"
            ;;
        "all")
            cmd="$cmd tests/"
            ;;
        *)
            print_error "Invalid test type: $TEST_TYPE"
            exit 1
            ;;
    esac

    # Add markers if specified
    if [[ -n "$MARKERS" ]]; then
        cmd="$cmd -m \"$MARKERS\""
    fi

    # Add verbose flag
    if [[ "$VERBOSE" == true ]]; then
        cmd="$cmd -v"
    fi

    # Add coverage if requested
    if [[ "$COVERAGE" == true ]]; then
        cmd="$cmd --cov=src --cov-report=term-missing --cov-report=html"
    fi

    # Add quick test markers
    if [[ "$QUICK" == true ]]; then
        cmd="$cmd -m \"unit and not slow\""
    fi

    # Add CI markers
    if [[ "$CI" == true ]]; then
        cmd="$cmd -m \"unit or integration\""
    fi

    # Add JUnit XML output
    cmd="$cmd --junitxml=test-results.xml"

    print_status "Running command: $cmd"

    # Execute the command
    if eval $cmd; then
        print_success "Tests completed successfully"
        return 0
    else
        print_error "Tests failed"
        return 1
    fi
}

# Function to generate report
generate_report() {
    if [[ -n "$REPORT_FILE" ]]; then
        print_status "Generating test report..."

        # Create report content
        cat > "$REPORT_FILE" << EOF
# Kindle Scribe Sync - Test Report

Generated on: $(date)

## Test Configuration
- Test Type: $TEST_TYPE
- Verbose: $VERBOSE
- Coverage: $COVERAGE
- Quick Mode: $QUICK
- CI Mode: $CI
- Markers: $MARKERS

## Test Results
EOF

        # Add test results if available
        if [[ -f "test-results.xml" ]]; then
            echo "- Test results XML: test-results.xml" >> "$REPORT_FILE"
        fi

        if [[ -f "htmlcov/index.html" ]]; then
            echo "- Coverage report: htmlcov/index.html" >> "$REPORT_FILE"
        fi

        print_success "Test report generated: $REPORT_FILE"
    fi
}

# Function to cleanup
cleanup() {
    print_status "Cleaning up temporary files..."

    # Remove temporary files
    rm -f test-results.xml
    rm -rf .pytest_cache
    rm -rf htmlcov
    rm -rf .coverage

    print_success "Cleanup completed"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            TEST_TYPE="$2"
            shift 2
            ;;
        -m|--markers)
            MARKERS="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -c|--coverage)
            COVERAGE=true
            shift
            ;;
        -q|--quick)
            QUICK=true
            shift
            ;;
        --ci)
            CI=true
            shift
            ;;
        -r|--report)
            REPORT_FILE="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_status "Starting Kindle Scribe Sync test suite..."

    # Check dependencies
    check_dependencies

    # Install system dependencies if needed
    if [[ "$TEST_TYPE" == "all" || "$TEST_TYPE" == "integration" || "$TEST_TYPE" == "e2e" ]]; then
        install_system_dependencies
    fi

    # Run tests
    if run_tests; then
        print_success "All tests passed!"

        # Generate report
        generate_report

        # Cleanup
        cleanup

        exit 0
    else
        print_error "Some tests failed!"

        # Generate report even on failure
        generate_report

        # Cleanup
        cleanup

        exit 1
    fi
}

# Trap to ensure cleanup on exit
trap cleanup EXIT

# Run main function
main "$@"
