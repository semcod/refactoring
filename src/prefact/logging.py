"""Structured logging system for prefact.

This module provides enterprise-grade logging with:
- Structured JSON logging
- Configurable log levels
- Telemetry hooks for observability
- Proper exception handling
- Performance metrics logging
"""

import json
import logging
import sys
import traceback
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Union

from prefact.config import Config


class LogLevel(str, Enum):
    """Log levels for prefact."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class PprefactLogger:
    """Structured logger for prefact with enterprise features."""
    
    def __init__(
        self,
        name: str = "prefact",
        level: Union[LogLevel, str] = LogLevel.INFO,
        format_type: str = "json",
        output_file: Optional[Path] = None,
        enable_telemetry: bool = False
    ):
        self.name = name
        self.level = LogLevel(level)
        self.format_type = format_type
        self.output_file = output_file
        self.enable_telemetry = enable_telemetry
        
        # Setup Python logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, self.level.value))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Setup handlers
        self._setup_handlers()
        
        # Telemetry callbacks
        self.telemetry_callbacks: list[callable] = []
    
    def _setup_handlers(self) -> None:
        """Setup logging handlers."""
        if self.format_type == "json":
            formatter = JsonFormatter()
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler if specified
        if self.output_file:
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(self.output_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self._log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self._log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self._log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, error: Optional[Exception] = None, **kwargs) -> None:
        """Log error message."""
        if error:
            kwargs["error_type"] = type(error).__name__
            kwargs["error_message"] = str(error)
            kwargs["traceback"] = traceback.format_exc()
        self._log(LogLevel.ERROR, message, **kwargs)
    
    def critical(self, message: str, error: Optional[Exception] = None, **kwargs) -> None:
        """Log critical message."""
        if error:
            kwargs["error_type"] = type(error).__name__
            kwargs["error_message"] = str(error)
            kwargs["traceback"] = traceback.format_exc()
        self._log(LogLevel.CRITICAL, message, **kwargs)
    
    def _log(self, level: LogLevel, message: str, **kwargs) -> None:
        """Internal logging method."""
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level.value,
            "logger": self.name,
            "message": message,
            **kwargs
        }
        
        # Log to Python logger
        getattr(self.logger, level.value.lower())(json.dumps(log_record))
        
        # Send to telemetry if enabled
        if self.enable_telemetry:
            self._send_telemetry(log_record)
    
    def _send_telemetry(self, log_record: Dict[str, Any]) -> None:
        """Send log record to telemetry callbacks."""
        for callback in self.telemetry_callbacks:
            try:
                callback(log_record)
            except Exception:
                # Don't let telemetry errors break logging
                pass
    
    def add_telemetry_callback(self, callback: callable) -> None:
        """Add a telemetry callback."""
        self.telemetry_callbacks.append(callback)
    
    def log_scan_start(self, file_count: int, rule_ids: list[str]) -> None:
        """Log scan start event."""
        self.info(
            "scan_started",
            event_type="scan_start",
            file_count=file_count,
            rule_ids=rule_ids
        )
    
    def log_scan_complete(self, duration: float, issues_found: int, fixes_applied: int) -> None:
        """Log scan complete event."""
        self.info(
            "scan_completed",
            event_type="scan_complete",
            duration_seconds=duration,
            issues_found=issues_found,
            fixes_applied=fixes_applied
        )
    
    def log_rule_execution(self, rule_id: str, file_path: Path, duration: float, issues: int) -> None:
        """Log rule execution."""
        self.debug(
            "rule_executed",
            event_type="rule_execution",
            rule_id=rule_id,
            file_path=str(file_path),
            duration_ms=duration * 1000,
            issues_found=issues
        )
    
    def log_plugin_loaded(self, plugin_name: str, version: str) -> None:
        """Log plugin loaded event."""
        self.info(
            "plugin_loaded",
            event_type="plugin_loaded",
            plugin_name=plugin_name,
            version=version
        )
    
    def log_performance_metrics(self, metrics: Dict[str, Any]) -> None:
        """Log performance metrics."""
        self.info(
            "performance_metrics",
            event_type="performance",
            **metrics
        )


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Try to parse existing JSON
        try:
            data = json.loads(record.getMessage())
        except (json.JSONDecodeError, ValueError):
            data = {
                "message": record.getMessage(),
                "timestamp": datetime.utcnow().isoformat(),
                "level": record.levelname,
                "logger": record.name,
            }
        
        # Add standard logging fields
        data.update({
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        })
        
        return json.dumps(data)


class PprefactException(Exception):
    """Base exception for prefact."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.error_code = error_code
        self.context = context or {}
        self.timestamp = datetime.utcnow()


class ConfigurationError(PprefactException):
    """Raised when configuration is invalid."""
    pass


class RuleError(PprefactException):
    """Raised when a rule encounters an error."""
    
    def __init__(
        self,
        message: str,
        rule_id: str,
        file_path: Optional[Path] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.rule_id = rule_id
        self.file_path = file_path


class PluginError(PprefactException):
    """Raised when a plugin encounters an error."""
    
    def __init__(
        self,
        message: str,
        plugin_name: str,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.plugin_name = plugin_name


class CacheError(PprefactException):
    """Raised when cache operations fail."""
    pass


class PerformanceError(PprefactException):
    """Raised when performance issues are detected."""
    pass


# Global logger instance
_logger: Optional[PprefactLogger] = None


def get_logger() -> PprefactLogger:
    """Get the global logger instance."""
    if _logger is None:
        raise RuntimeError("Logger not initialized. Call setup_logging() first.")
    return _logger


def setup_logging(config: Config) -> PprefactLogger:
    """Setup logging from configuration."""
    global _logger
    
    # Get logging configuration
    log_config = config.get_rule_option("_logging", "config", {})
    
    level = log_config.get("level", "INFO")
    format_type = log_config.get("format", "json")
    output_file = None
    if log_config.get("file"):
        output_file = Path(log_config["file"])
    
    enable_telemetry = config.get_rule_option("_telemetry", "enabled", False)
    
    # Create logger
    _logger = PprefactLogger(
        level=level,
        format_type=format_type,
        output_file=output_file,
        enable_telemetry=enable_telemetry
    )
    
    # Setup telemetry if enabled
    if enable_telemetry:
        setup_telemetry(config)
    
    return _logger


def setup_telemetry(config: Config) -> None:
    """Setup telemetry callbacks."""
    logger = get_logger()
    
    # Prometheus telemetry
    if config.get_rule_option("_telemetry", "prometheus", False):
        try:
            from prefact.telemetry.prometheus import prometheus_callback
            logger.add_telemetry_callback(prometheus_callback)
        except ImportError:
            logger.warning("Prometheus telemetry requested but prometheus_client not installed")
    
    # Custom telemetry endpoint
    if config.get_rule_option("_telemetry", "endpoint"):
        endpoint = config.get_rule_option("_telemetry", "endpoint")
        api_key = config.get_rule_option("_telemetry", "api_key")
        
        def custom_callback(log_record: Dict[str, Any]) -> None:
            """Send log record to custom endpoint."""
            import requests
            
            try:
                requests.post(
                    endpoint,
                    json=log_record,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=5
                )
            except Exception:
                pass  # Silently fail telemetry
        
        logger.add_telemetry_callback(custom_callback)


# Context manager for logging operations
class LogContext:
    """Context manager for logging with additional context."""
    
    def __init__(self, logger: PprefactLogger, **context):
        self.logger = logger
        self.context = context
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.logger.error(
                "context_error",
                error=exc_val,
                **self.context
            )
    
    def log(self, level: LogLevel, message: str, **kwargs) -> None:
        """Log with context."""
        self.logger._log(level, message, **{**self.context, **kwargs})


# Decorator for logging function calls
def log_execution(logger: Optional[PprefactLogger] = None):
    """Decorator to log function execution."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            nonlocal logger
            if logger is None:
                logger = get_logger()
            
            start_time = datetime.utcnow()
            function_name = f"{func.__module__}.{func.__qualname__}"
            
            try:
                result = func(*args, **kwargs)
                duration = (datetime.utcnow() - start_time).total_seconds()
                
                logger.debug(
                    "function_executed",
                    function=function_name,
                    duration_seconds=duration,
                    success=True
                )
                
                return result
            except Exception as e:
                duration = (datetime.utcnow() - start_time).total_seconds()
                
                logger.error(
                    "function_failed",
                    function=function_name,
                    duration_seconds=duration,
                    success=False,
                    error=e
                )
                
                raise
        
        return wrapper
    return decorator


# Exception handler for unhandled exceptions
def handle_exception(exc_type, exc_value, exc_traceback):
    """Handle unhandled exceptions."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    logger = get_logger()
    logger.critical(
        "unhandled_exception",
        error=exc_value,
        exc_info=(exc_type, exc_value, exc_traceback)
    )


# Install exception handler
sys.excepthook = handle_exception
