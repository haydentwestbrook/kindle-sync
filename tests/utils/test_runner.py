"""Test runner utilities and custom test execution."""

import os
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
import pytest
import time

from tests.utils.test_helpers import TestHelpers


class TestRunner:
    """Custom test runner with additional functionality."""
    
    def __init__(self, test_dir: Optional[Path] = None):
        self.test_dir = test_dir or Path(__file__).parent.parent
        self.results = {}
    
    def run_unit_tests(self, verbose: bool = True, coverage: bool = True) -> Dict[str, Any]:
        """Run unit tests."""
        cmd = ["python", "-m", "pytest", "tests/unit/"]
        
        if verbose:
            cmd.append("-v")
        
        if coverage:
            cmd.extend(["--cov=src", "--cov-report=term-missing"])
        
        return self._run_tests("unit", cmd)
    
    def run_integration_tests(self, verbose: bool = True) -> Dict[str, Any]:
        """Run integration tests."""
        cmd = ["python", "-m", "pytest", "tests/integration/", "-v" if verbose else ""]
        cmd = [c for c in cmd if c]  # Remove empty strings
        
        return self._run_tests("integration", cmd)
    
    def run_e2e_tests(self, verbose: bool = True) -> Dict[str, Any]:
        """Run end-to-end tests."""
        cmd = ["python", "-m", "pytest", "tests/e2e/", "-v" if verbose else ""]
        cmd = [c for c in cmd if c]  # Remove empty strings
        
        return self._run_tests("e2e", cmd)
    
    def run_all_tests(self, verbose: bool = True, coverage: bool = True) -> Dict[str, Any]:
        """Run all tests."""
        cmd = ["python", "-m", "pytest", "tests/"]
        
        if verbose:
            cmd.append("-v")
        
        if coverage:
            cmd.extend(["--cov=src", "--cov-report=term-missing", "--cov-report=html"])
        
        return self._run_tests("all", cmd)
    
    def run_specific_test(self, test_path: str, verbose: bool = True) -> Dict[str, Any]:
        """Run a specific test file or test function."""
        cmd = ["python", "-m", "pytest", test_path]
        
        if verbose:
            cmd.append("-v")
        
        return self._run_tests("specific", cmd)
    
    def run_tests_with_markers(self, markers: List[str], verbose: bool = True) -> Dict[str, Any]:
        """Run tests with specific markers."""
        cmd = ["python", "-m", "pytest", "tests/"]
        
        for marker in markers:
            cmd.extend(["-m", marker])
        
        if verbose:
            cmd.append("-v")
        
        return self._run_tests(f"markers_{'_'.join(markers)}", cmd)
    
    def run_performance_tests(self) -> Dict[str, Any]:
        """Run performance tests."""
        cmd = ["python", "-m", "pytest", "tests/", "-m", "slow", "--benchmark-only"]
        return self._run_tests("performance", cmd)
    
    def run_security_tests(self) -> Dict[str, Any]:
        """Run security tests."""
        cmd = ["python", "-m", "pytest", "tests/", "-m", "security"]
        return self._run_tests("security", cmd)
    
    def _run_tests(self, test_type: str, cmd: List[str]) -> Dict[str, Any]:
        """Run tests with the given command."""
        start_time = time.time()
        
        try:
            # Change to test directory
            original_cwd = os.getcwd()
            os.chdir(self.test_dir)
            
            # Run the tests
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Parse results
            test_result = {
                'test_type': test_type,
                'command': ' '.join(cmd),
                'return_code': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'execution_time': execution_time,
                'success': result.returncode == 0
            }
            
            # Parse pytest output for additional info
            if 'pytest' in cmd[1]:
                test_result.update(self._parse_pytest_output(result.stdout))
            
            self.results[test_type] = test_result
            return test_result
            
        except subprocess.TimeoutExpired:
            return {
                'test_type': test_type,
                'command': ' '.join(cmd),
                'return_code': -1,
                'stdout': '',
                'stderr': 'Test execution timed out',
                'execution_time': 300,
                'success': False,
                'error': 'timeout'
            }
        except Exception as e:
            return {
                'test_type': test_type,
                'command': ' '.join(cmd),
                'return_code': -1,
                'stdout': '',
                'stderr': str(e),
                'execution_time': time.time() - start_time,
                'success': False,
                'error': str(e)
            }
        finally:
            os.chdir(original_cwd)
    
    def _parse_pytest_output(self, output: str) -> Dict[str, Any]:
        """Parse pytest output for additional information."""
        info = {}
        
        # Extract test counts
        lines = output.split('\n')
        for line in lines:
            if 'passed' in line and 'failed' in line:
                # Parse line like "5 passed, 2 failed in 1.23s"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'passed':
                        info['passed'] = int(parts[i-1])
                    elif part == 'failed':
                        info['failed'] = int(parts[i-1])
                    elif part == 'skipped':
                        info['skipped'] = int(parts[i-1])
        
        # Extract coverage information
        if 'TOTAL' in output:
            coverage_lines = [line for line in lines if 'TOTAL' in line]
            if coverage_lines:
                total_line = coverage_lines[-1]
                if '%' in total_line:
                    # Extract coverage percentage
                    parts = total_line.split()
                    for part in parts:
                        if part.endswith('%'):
                            info['coverage'] = float(part[:-1])
                            break
        
        return info
    
    def get_test_summary(self) -> Dict[str, Any]:
        """Get a summary of all test results."""
        if not self.results:
            return {'message': 'No tests have been run yet'}
        
        total_tests = 0
        total_passed = 0
        total_failed = 0
        total_time = 0
        
        for result in self.results.values():
            total_time += result.get('execution_time', 0)
            total_passed += result.get('passed', 0)
            total_failed += result.get('failed', 0)
            total_tests += result.get('passed', 0) + result.get('failed', 0)
        
        return {
            'total_tests': total_tests,
            'total_passed': total_passed,
            'total_failed': total_failed,
            'total_time': total_time,
            'success_rate': (total_passed / total_tests * 100) if total_tests > 0 else 0,
            'test_types': list(self.results.keys())
        }
    
    def generate_report(self, output_file: Optional[Path] = None) -> str:
        """Generate a test report."""
        if not self.results:
            return "No test results available"
        
        report = []
        report.append("=" * 80)
        report.append("KINDLE SCRIBE SYNC - TEST REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Summary
        summary = self.get_test_summary()
        report.append("SUMMARY:")
        report.append(f"  Total Tests: {summary['total_tests']}")
        report.append(f"  Passed: {summary['total_passed']}")
        report.append(f"  Failed: {summary['total_failed']}")
        report.append(f"  Success Rate: {summary['success_rate']:.1f}%")
        report.append(f"  Total Time: {summary['total_time']:.2f}s")
        report.append("")
        
        # Detailed results
        report.append("DETAILED RESULTS:")
        report.append("-" * 40)
        
        for test_type, result in self.results.items():
            report.append(f"\n{test_type.upper()} TESTS:")
            report.append(f"  Command: {result['command']}")
            report.append(f"  Return Code: {result['return_code']}")
            report.append(f"  Execution Time: {result['execution_time']:.2f}s")
            report.append(f"  Success: {result['success']}")
            
            if 'passed' in result:
                report.append(f"  Passed: {result['passed']}")
            if 'failed' in result:
                report.append(f"  Failed: {result['failed']}")
            if 'coverage' in result:
                report.append(f"  Coverage: {result['coverage']:.1f}%")
            
            if result['stderr']:
                report.append(f"  Errors: {result['stderr'][:200]}...")
        
        report.append("")
        report.append("=" * 80)
        
        report_text = "\n".join(report)
        
        if output_file:
            output_file.write_text(report_text)
        
        return report_text


class TestSuiteRunner:
    """Run specific test suites with different configurations."""
    
    def __init__(self):
        self.runner = TestRunner()
    
    def run_quick_tests(self) -> Dict[str, Any]:
        """Run quick tests (unit tests only, no slow tests)."""
        return self.runner.run_tests_with_markers(["unit", "not slow"])
    
    def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run comprehensive tests (all tests with coverage)."""
        return self.runner.run_all_tests(verbose=True, coverage=True)
    
    def run_ci_tests(self) -> Dict[str, Any]:
        """Run tests suitable for CI/CD pipeline."""
        # Run unit and integration tests with coverage
        results = {}
        
        # Unit tests
        results['unit'] = self.runner.run_unit_tests(verbose=False, coverage=True)
        
        # Integration tests
        results['integration'] = self.runner.run_integration_tests(verbose=False)
        
        # Skip slow E2E tests in CI
        return results
    
    def run_development_tests(self) -> Dict[str, Any]:
        """Run tests suitable for development."""
        return self.runner.run_tests_with_markers(["unit", "integration"])
    
    def run_release_tests(self) -> Dict[str, Any]:
        """Run all tests for release validation."""
        return self.runner.run_all_tests(verbose=True, coverage=True)


def run_tests_from_command_line():
    """Run tests from command line with custom options."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Kindle Scribe Sync tests")
    parser.add_argument("--type", choices=["unit", "integration", "e2e", "all"], 
                       default="all", help="Type of tests to run")
    parser.add_argument("--markers", nargs="+", help="Pytest markers to filter tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--coverage", action="store_true", help="Generate coverage report")
    parser.add_argument("--report", help="Output file for test report")
    parser.add_argument("--quick", action="store_true", help="Run quick tests only")
    parser.add_argument("--ci", action="store_true", help="Run CI-appropriate tests")
    
    args = parser.parse_args()
    
    runner = TestRunner()
    suite_runner = TestSuiteRunner()
    
    if args.quick:
        result = suite_runner.run_quick_tests()
    elif args.ci:
        result = suite_runner.run_ci_tests()
    elif args.markers:
        result = runner.run_tests_with_markers(args.markers, args.verbose)
    elif args.type == "unit":
        result = runner.run_unit_tests(args.verbose, args.coverage)
    elif args.type == "integration":
        result = runner.run_integration_tests(args.verbose)
    elif args.type == "e2e":
        result = runner.run_e2e_tests(args.verbose)
    else:  # all
        result = runner.run_all_tests(args.verbose, args.coverage)
    
    # Generate report if requested
    if args.report:
        report_path = Path(args.report)
        runner.generate_report(report_path)
        print(f"Test report saved to: {report_path}")
    
    # Print summary
    print("\n" + "=" * 50)
    print("TEST EXECUTION COMPLETE")
    print("=" * 50)
    
    if isinstance(result, dict):
        print(f"Success: {result.get('success', False)}")
        print(f"Execution Time: {result.get('execution_time', 0):.2f}s")
        if 'passed' in result:
            print(f"Passed: {result['passed']}")
        if 'failed' in result:
            print(f"Failed: {result['failed']}")
    else:
        # Multiple results from suite runner
        for test_type, test_result in result.items():
            print(f"{test_type.upper()}: {'PASSED' if test_result.get('success') else 'FAILED'}")
    
    return result


if __name__ == "__main__":
    run_tests_from_command_line()
