"""
Tracing decorators for automatic span creation.

Provides decorators to automatically create trace spans for functions and methods.
"""

import functools
import asyncio
from typing import Any, Callable, Optional, Dict, Union
from opentelemetry import trace
from loguru import logger


def trace_function(
    operation_name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
    record_exceptions: bool = True
):
    """
    Decorator to automatically create a trace span for a synchronous function.
    
    Args:
        operation_name: Name for the span (defaults to function name)
        attributes: Additional attributes to add to the span
        record_exceptions: Whether to record exceptions in the span
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            span_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            with tracer.start_as_current_span(span_name) as span:
                # Add function information as attributes
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                # Add custom attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("function.result_type", type(result).__name__)
                    return result
                    
                except Exception as e:
                    if record_exceptions:
                        span.record_exception(e)
                        span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    raise
                    
        return wrapper
    return decorator


def trace_async_function(
    operation_name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None,
    record_exceptions: bool = True
):
    """
    Decorator to automatically create a trace span for an asynchronous function.
    
    Args:
        operation_name: Name for the span (defaults to function name)
        attributes: Additional attributes to add to the span
        record_exceptions: Whether to record exceptions in the span
        
    Returns:
        Decorated async function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            span_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            with tracer.start_as_current_span(span_name) as span:
                # Add function information as attributes
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                span.set_attribute("function.is_async", True)
                
                # Add custom attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("function.result_type", type(result).__name__)
                    return result
                    
                except Exception as e:
                    if record_exceptions:
                        span.record_exception(e)
                        span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    raise
                    
        return wrapper
    return decorator


def trace_class_methods(
    operation_name_prefix: Optional[str] = None,
    exclude_methods: Optional[set] = None,
    include_private: bool = False
):
    """
    Class decorator to automatically trace all methods of a class.
    
    Args:
        operation_name_prefix: Prefix for operation names
        exclude_methods: Set of method names to exclude from tracing
        include_private: Whether to include private methods (starting with _)
        
    Returns:
        Decorated class
    """
    def decorator(cls):
        exclude_methods_set = exclude_methods or {
            '__init__', '__new__', '__del__', '__repr__', '__str__',
            '__hash__', '__eq__', '__ne__', '__lt__', '__le__', '__gt__', '__ge__'
        }
        
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            
            # Skip if not a method or should be excluded
            if not callable(attr) or attr_name in exclude_methods_set:
                continue
                
            # Skip private methods unless explicitly included
            if not include_private and attr_name.startswith('_'):
                continue
            
            # Skip if already decorated
            if hasattr(attr, '__wrapped__'):
                continue
            
            # Create operation name
            if operation_name_prefix:
                operation_name = f"{operation_name_prefix}.{attr_name}"
            else:
                operation_name = f"{cls.__name__}.{attr_name}"
            
            # Apply appropriate decorator based on whether it's async
            if asyncio.iscoroutinefunction(attr):
                setattr(cls, attr_name, trace_async_function(operation_name)(attr))
            else:
                setattr(cls, attr_name, trace_function(operation_name)(attr))
        
        return cls
    
    return decorator


def trace_database_operation(operation_type: str):
    """
    Decorator specifically for database operations.
    
    Args:
        operation_type: Type of database operation (SELECT, INSERT, UPDATE, DELETE)
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            span_name = f"db.{operation_type.lower()}"
            
            with tracer.start_as_current_span(span_name) as span:
                span.set_attribute("db.operation", operation_type)
                span.set_attribute("db.system", "sqlite")  # or detect from config
                
                # Add function information
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Add result information
                    if hasattr(result, '__len__'):
                        span.set_attribute("db.rows_affected", len(result))
                    
                    return result
                    
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    raise
                    
        return wrapper
    return decorator


def trace_http_request(method: str, url: str):
    """
    Decorator for HTTP requests.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        url: Request URL
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            span_name = f"http.{method.lower()}"
            
            with tracer.start_as_current_span(span_name) as span:
                span.set_attribute("http.method", method)
                span.set_attribute("http.url", url)
                span.set_attribute("function.name", func.__name__)
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Add response information if available
                    if hasattr(result, 'status_code'):
                        span.set_attribute("http.status_code", result.status_code)
                    
                    return result
                    
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    raise
                    
        return wrapper
    return decorator


def trace_file_operation(operation_type: str):
    """
    Decorator for file operations.
    
    Args:
        operation_type: Type of file operation (read, write, delete, etc.)
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            span_name = f"file.{operation_type.lower()}"
            
            with tracer.start_as_current_span(span_name) as span:
                span.set_attribute("file.operation", operation_type)
                span.set_attribute("function.name", func.__name__)
                
                # Try to extract file path from arguments
                if args and hasattr(args[0], 'name'):  # Path object
                    span.set_attribute("file.path", str(args[0]))
                elif args and isinstance(args[0], str):  # String path
                    span.set_attribute("file.path", args[0])
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Add file size if available
                    if hasattr(result, 'stat'):
                        span.set_attribute("file.size", result.stat().st_size)
                    
                    return result
                    
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                    raise
                    
        return wrapper
    return decorator
