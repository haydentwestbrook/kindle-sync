"""Tests for retry mechanisms."""


import pytest

from src.core.exceptions import FileProcessingError
from src.core.retry import retry_on_file_error, retry_on_network_error, with_retry


class TestWithRetry:
    """Test retry decorator."""

    def test_successful_function_no_retry(self):
        """Test function that succeeds on first try."""

        @with_retry(max_attempts=3)
        def successful_function():
            return "success"

        result = successful_function()
        assert result == "success"

    def test_function_retries_on_failure(self):
        """Test function that retries on failure."""
        call_count = 0

        @with_retry(max_attempts=3, wait_min=0.01, wait_max=0.1)
        def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = failing_function()
        assert result == "success"
        assert call_count == 3

    def test_function_fails_after_max_attempts(self):
        """Test function that fails after max attempts."""
        call_count = 0

        @with_retry(max_attempts=2, wait_min=0.01, wait_max=0.1)
        def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            always_failing_function()

        assert call_count == 2

    def test_retry_only_on_specific_exceptions(self):
        """Test retry only on specific exceptions."""
        call_count = 0

        @with_retry(
            max_attempts=3, retry_exceptions=(ValueError,), wait_min=0.01, wait_max=0.1
        )
        def function_with_wrong_exception():
            nonlocal call_count
            call_count += 1
            raise TypeError("Wrong exception type")

        with pytest.raises(TypeError):
            function_with_wrong_exception()

        assert call_count == 1  # Should not retry

    def test_retry_with_exponential_backoff(self):
        """Test retry with exponential backoff."""
        call_count = 0

        @with_retry(max_attempts=3, wait_min=0.01, wait_max=0.1, backoff_factor=2.0)
        def function_with_backoff():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = function_with_backoff()

        assert result == "success"
        assert call_count == 3
        # Just verify that retries happened, timing is environment-dependent


class TestRetryOnNetworkError:
    """Test network-specific retry decorator."""

    def test_retry_on_connection_error(self):
        """Test retry on connection error."""
        call_count = 0

        @retry_on_network_error(max_attempts=3, wait_min=0.01, wait_max=0.1)
        def network_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Connection failed")
            return "success"

        result = network_function()
        assert result == "success"
        assert call_count == 2

    def test_retry_on_timeout_error(self):
        """Test retry on timeout error."""
        call_count = 0

        @retry_on_network_error(max_attempts=3, wait_min=0.01, wait_max=0.1)
        def timeout_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("Request timeout")
            return "success"

        result = timeout_function()
        assert result == "success"
        assert call_count == 2


class TestRetryOnFileError:
    """Test file-specific retry decorator."""

    def test_retry_on_file_not_found(self):
        """Test retry on file not found error."""
        call_count = 0

        @retry_on_file_error(max_attempts=3, wait_min=0.01, wait_max=0.1)
        def file_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise FileNotFoundError("File not found")
            return "success"

        result = file_function()
        assert result == "success"
        assert call_count == 2

    def test_retry_on_permission_error(self):
        """Test retry on permission error."""
        call_count = 0

        @retry_on_file_error(max_attempts=3, wait_min=0.01, wait_max=0.1)
        def permission_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise PermissionError("Permission denied")
            return "success"

        result = permission_function()
        assert result == "success"
        assert call_count == 2


class TestRetryWithCustomExceptions:
    """Test retry with custom exceptions."""

    def test_retry_with_custom_exception(self):
        """Test retry with custom exception."""
        call_count = 0

        @with_retry(
            max_attempts=3,
            retry_exceptions=(FileProcessingError,),
            wait_min=0.01,
            wait_max=0.1,
        )
        def custom_exception_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise FileProcessingError("Processing failed")
            return "success"

        result = custom_exception_function()
        assert result == "success"
        assert call_count == 2
