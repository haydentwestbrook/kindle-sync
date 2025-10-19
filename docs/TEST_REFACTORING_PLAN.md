# Unit Test Refactoring Plan

## Overview

This document outlines a comprehensive plan to refactor the remaining 88 failing unit tests to align with the current codebase implementation. The tests were written for a different version of the codebase and need to be updated to reflect the actual API and functionality.

## Current Status

- **Total Tests**: 243
- **Passing**: 155 (64%)
- **Failing**: 88 (36%)
- **Recently Fixed**: 7 tests (HealthChecker, KindleSync, PDF Converter)

## Root Cause Analysis

The failing tests fall into several categories:

1. **API Mismatch**: Tests expect methods/attributes that don't exist in current implementation
2. **Configuration Format Changes**: Tests use outdated configuration structures
3. **Missing Dependencies**: Tests assume functionality that hasn't been implemented
4. **Async/Sync Confusion**: Tests mix async and sync patterns incorrectly
5. **Database Schema Mismatch**: Tests expect different database models/operations

## Refactoring Strategy

### Phase 1: Core Infrastructure Tests (Priority: High)

#### 1.1 Database Manager Tests
**Current Issues**: Tests expect methods like `add_processed_file`, `get_processed_file_by_hash`, `add_metric` that don't exist.

**Current API**:
```python
class DatabaseManager:
    def __init__(self, database_url: str, echo: bool = False)
    def create_tables(self)
    def get_session(self)
    def record_file_processing(self, ...)
    def record_file_operation(self, ...)
    def get_file_processing_history(self, file_path: str)
    def get_recent_files(self, days: int = 7)
    def get_files_by_status(self, status: ProcessingStatus)
    def add_to_queue(self, ...)
    def get_next_queue_item(self)
    def remove_from_queue(self, file_path: str)
    def get_queue_size(self)
    def record_metric(self, ...)
    def get_metrics(self, ...)
    def get_latest_metric(self, metric_name: str)
    def record_health_check(self, ...)
    def get_health_check_history(self, ...)
    def get_latest_health_check(self, check_name: str)
    def get_processing_statistics(self, days: int = 7)
    def cleanup_old_data(self, days: int = 30)
    def get_database_info(self)
```

**Refactoring Actions**:
- Update tests to use `record_file_processing` instead of `add_processed_file`
- Use `get_file_processing_history` instead of `get_processed_file_by_hash`
- Use `record_metric` instead of `add_metric`
- Fix session handling to use context manager properly
- Update database URL expectations to include `sqlite:///` prefix

#### 1.2 Async Processor Tests
**Current Issues**: Tests expect methods like `shutdown`, `kindle_sync` attribute, and different constructor signature.

**Current API**:
```python
class AsyncSyncProcessor:
    def __init__(self, config: Config, max_workers: int = 4)
    async def process_file_async(self, file_path: Path, ...)
    async def _process_file_with_retry(self, ...)
    async def _process_file_sync(self, ...)
    async def _process_markdown_file(self, ...)
    async def _process_pdf_file(self, ...)
    def _convert_markdown_to_pdf_sync(self, ...)
    def _convert_pdf_to_markdown_sync(self, ...)
    async def _send_pdf_to_kindle_async(self, ...)
    def _calculate_file_hash(self, file_path: Path)
    async def _record_processing_result(self, ...)
    async def _get_file_id(self, file_path: Path)
    async def add_to_queue(self, ...)
    async def process_queue(self, max_items: int = 10)
    def get_statistics(self)
    def get_health_status(self)
    async def cleanup(self)
```

**Refactoring Actions**:
- Remove tests for non-existent `shutdown` method
- Remove tests for non-existent `kindle_sync` attribute
- Update constructor calls to only pass `config` and `max_workers`
- Fix async test patterns to properly await async methods
- Update mock configurations to match actual dependencies

### Phase 2: Configuration and Core Tests (Priority: High)

#### 2.1 Config Tests
**Current Issues**: Tests expect different configuration structure and methods.

**Refactoring Actions**:
- Update test configurations to match current YAML structure
- Fix path resolution tests to handle new configuration format
- Update method expectations to match current Config API
- Add tests for new configuration methods we added

#### 2.2 File Watcher Tests
**Current Issues**: Tests expect different ObsidianFileWatcher API.

**Refactoring Actions**:
- Update tests to match current file watcher implementation
- Fix event handling tests to use correct callback signatures
- Update statistics and monitoring tests

### Phase 3: Email and Communication Tests (Priority: Medium)

#### 3.1 Email Receiver Tests
**Current Issues**: Tests expect different email handling API.

**Refactoring Actions**:
- Update IMAP connection tests
- Fix attachment handling tests
- Update email processing workflow tests

#### 3.2 Kindle Sync Tests
**Current Issues**: Some tests still failing due to configuration issues.

**Refactoring Actions**:
- Complete SMTP configuration fixes
- Update backup handling tests
- Fix email sending tests

### Phase 4: Database Models Tests (Priority: Medium)

#### 4.1 Database Models Tests
**Current Issues**: Tests expect different model structure.

**Refactoring Actions**:
- Update model creation tests
- Fix foreign key relationship tests
- Update timestamp and validation tests

### Phase 5: Monitoring and Metrics Tests (Priority: Low)

#### 5.1 Health Check Tests
**Current Issues**: Some async/sync issues remain.

**Refactoring Actions**:
- Fix remaining async method calls
- Update health check result format tests

#### 5.2 Metrics Tests
**Current Issues**: Tests expect different metrics API.

**Refactoring Actions**:
- Update metrics collection tests
- Fix Prometheus exporter tests

## Implementation Plan

### Week 1: Database and Core Infrastructure
- [ ] Refactor DatabaseManager tests (20 tests)
- [ ] Refactor AsyncSyncProcessor tests (10 tests)
- [ ] Update configuration tests (4 tests)

### Week 2: File Processing and Communication
- [ ] Refactor file watcher tests (25 tests)
- [ ] Complete email receiver tests (18 tests)
- [ ] Fix remaining KindleSync tests (1 test)

### Week 3: Models and Monitoring
- [ ] Refactor database models tests (5 tests)
- [ ] Fix health check tests (5 tests)
- [ ] Update metrics tests (remaining tests)

## Testing Strategy

### 1. Test-Driven Refactoring
- Start with understanding the current API
- Write tests that match current implementation
- Gradually improve implementation to meet test expectations

### 2. Incremental Approach
- Fix one test file at a time
- Run tests after each fix to ensure no regressions
- Commit changes frequently with descriptive messages

### 3. Mock Strategy
- Use proper mocking for external dependencies
- Mock database connections for unit tests
- Use real implementations for integration tests

## Quality Assurance

### 1. Test Coverage
- Maintain or improve current test coverage
- Add tests for new functionality
- Remove obsolete tests

### 2. Code Quality
- Follow existing code style and patterns
- Add proper docstrings and type hints
- Ensure tests are readable and maintainable

### 3. Performance
- Ensure tests run quickly
- Use appropriate fixtures and setup/teardown
- Avoid unnecessary I/O operations in tests

## Risk Mitigation

### 1. Breaking Changes
- Document all API changes
- Provide migration guide for test updates
- Maintain backward compatibility where possible

### 2. Test Reliability
- Use deterministic test data
- Avoid flaky tests with proper synchronization
- Add proper error handling in tests

### 3. Maintenance
- Keep tests up-to-date with code changes
- Regular test review and cleanup
- Document test patterns and conventions

## Success Metrics

### Primary Goals
- [ ] Reduce failing tests from 88 to 0
- [ ] Maintain or improve test coverage
- [ ] Ensure all tests run reliably

### Secondary Goals
- [ ] Improve test readability and maintainability
- [ ] Reduce test execution time
- [ ] Establish clear testing patterns and conventions

## Timeline

**Total Estimated Time**: 3 weeks
**Effort Level**: Medium-High
**Risk Level**: Medium

## Next Steps

1. **Immediate**: Start with DatabaseManager test refactoring
2. **Short-term**: Complete core infrastructure tests
3. **Medium-term**: Refactor remaining test modules
4. **Long-term**: Establish testing best practices and documentation

## Resources Required

- **Developer Time**: 3 weeks full-time equivalent
- **Testing Environment**: Local development setup
- **Documentation**: Update test documentation and patterns
- **Review Process**: Code review for all test changes

---

*This plan should be reviewed and updated as we progress through the refactoring process. The actual implementation may reveal additional issues or require adjustments to the approach.*
