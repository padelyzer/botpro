"""
BotPhia Comprehensive Error Handling System
==========================================

Centralized error management with custom exceptions, structured logging,
and recovery mechanisms for the trading platform.

Author: Senior Backend Developer
Phase: 1 - Days 5-7
"""

import logging
import traceback
import sys
from datetime import datetime
from typing import Dict, Any, Optional, Type, Union, Callable
from enum import Enum
import json
from pathlib import Path
import functools

# Custom Exception Hierarchy
# ==========================

class BotPhiaError(Exception):
    """Base exception for all BotPhia trading platform errors"""
    
    def __init__(self, message: str, error_code: str = None, context: Dict[str, Any] = None):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}
        self.timestamp = datetime.now().isoformat()
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization"""
        return {
            'error_type': self.__class__.__name__,
            'error_code': self.error_code,
            'message': self.message,
            'context': self.context,
            'timestamp': self.timestamp
        }

class TradingError(BotPhiaError):
    """Base class for trading-related errors"""
    pass

class CalculationError(BotPhiaError):
    """Errors in mathematical calculations"""
    pass

class DataValidationError(BotPhiaError):
    """Errors in data validation and integrity"""
    pass

class ApiError(BotPhiaError):
    """External API communication errors"""
    pass

class DatabaseError(BotPhiaError):
    """Database operation errors"""
    pass

class AuthenticationError(BotPhiaError):
    """Authentication and authorization errors"""
    pass

class ConfigurationError(BotPhiaError):
    """Configuration and setup errors"""
    pass

class NetworkError(BotPhiaError):
    """Network communication errors"""
    pass

class WebSocketError(BotPhiaError):
    """WebSocket communication errors"""
    pass

# Specific Trading Errors
# =======================

class InsufficientFundsError(TradingError):
    """Insufficient funds for trading operation"""
    pass

class InvalidOrderError(TradingError):
    """Invalid order parameters or conditions"""
    pass

class PositionNotFoundError(TradingError):
    """Position not found in database"""
    pass

class SymbolNotSupportedError(TradingError):
    """Trading symbol not supported"""
    pass

class RiskLimitExceededError(TradingError):
    """Risk management limits exceeded"""
    pass

class MarketClosedError(TradingError):
    """Market is closed for trading"""
    pass

# Specific Calculation Errors
# ===========================

class DivisionByZeroError(CalculationError):
    """Division by zero in calculations"""
    pass

class OverflowError(CalculationError):
    """Numeric overflow in calculations"""
    pass

class PrecisionError(CalculationError):
    """Precision requirements not met"""
    pass

class InvalidIndicatorError(CalculationError):
    """Invalid technical indicator calculation"""
    pass

# Specific Data Errors
# ===================

class InvalidDataFormatError(DataValidationError):
    """Invalid data format or structure"""
    pass

class MissingDataError(DataValidationError):
    """Required data is missing"""
    pass

class CorruptedDataError(DataValidationError):
    """Data corruption detected"""
    pass

class OutdatedDataError(DataValidationError):
    """Data is too old to be used"""
    pass

# Error Severity Levels
# ====================

class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"

class ErrorHandler:
    """
    Centralized error handling and logging system.
    
    Features:
    - Structured error logging
    - Error categorization and severity
    - Recovery mechanism suggestions
    - Error metrics and reporting
    - Context preservation
    """
    
    def __init__(self, log_file: str = "logs/error_handler.log"):
        """
        Initialize ErrorHandler.
        
        Args:
            log_file: Path to error log file
        """
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(exist_ok=True)
        
        # Setup structured logging
        self.logger = self._setup_logger()
        
        # Error statistics
        self.error_stats: Dict[str, int] = {}
        self.recovery_attempts: Dict[str, int] = {}
        
    def _setup_logger(self) -> logging.Logger:
        """Setup structured error logger"""
        logger = logging.getLogger("botphia.error_handler")
        logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # File handler for errors
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.ERROR)
        
        # Console handler for critical errors
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.CRITICAL)
        
        # JSON formatter for structured logging
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None,
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                    recovery_suggestion: str = None) -> Dict[str, Any]:
        """
        Handle and log error with full context.
        
        Args:
            error: Exception instance
            context: Additional context information
            severity: Error severity level
            recovery_suggestion: Suggested recovery action
            
        Returns:
            Dictionary with error details and handling results
        """
        try:
            # Convert to BotPhia error if needed
            if not isinstance(error, BotPhiaError):
                error = self._convert_to_botphia_error(error, context)
            
            # Add context if provided
            if context:
                error.context.update(context)
            
            # Generate error report
            error_report = self._generate_error_report(error, severity, recovery_suggestion)
            
            # Log the error
            self._log_error(error_report)
            
            # Update statistics
            self._update_error_stats(error)
            
            # Attempt recovery if suggestion provided
            if recovery_suggestion:
                self._attempt_recovery(error, recovery_suggestion)
            
            return error_report
            
        except Exception as handler_error:
            # Fallback logging if handler fails
            self.logger.critical(f"Error handler failed: {handler_error}")
            return {
                'error': 'ErrorHandler failure',
                'original_error': str(error),
                'handler_error': str(handler_error),
                'timestamp': datetime.now().isoformat()
            }
    
    def _convert_to_botphia_error(self, error: Exception, context: Dict[str, Any] = None) -> BotPhiaError:
        """Convert standard exception to BotPhia error"""
        error_mapping = {
            ValueError: DataValidationError,
            TypeError: DataValidationError,
            KeyError: MissingDataError,
            ZeroDivisionError: DivisionByZeroError,
            OverflowError: OverflowError,
            ConnectionError: NetworkError,
            TimeoutError: NetworkError,
            FileNotFoundError: ConfigurationError,
            PermissionError: AuthenticationError
        }
        
        error_class = error_mapping.get(type(error), BotPhiaError)
        return error_class(
            message=str(error),
            context=context or {},
        )
    
    def _generate_error_report(self, error: BotPhiaError, severity: ErrorSeverity,
                             recovery_suggestion: str = None) -> Dict[str, Any]:
        """Generate comprehensive error report"""
        
        # Get stack trace
        exc_type, exc_value, exc_traceback = sys.exc_info()
        stack_trace = traceback.format_exception(exc_type, exc_value, exc_traceback) if exc_traceback else []
        
        return {
            'error_id': f"{error.error_code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'error_details': error.to_dict(),
            'severity': severity.value,
            'stack_trace': stack_trace,
            'recovery_suggestion': recovery_suggestion,
            'system_info': self._get_system_info(),
            'timestamp': datetime.now().isoformat()
        }
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information for error context"""
        return {
            'python_version': sys.version,
            'platform': sys.platform,
            'error_stats': dict(self.error_stats),
            'total_errors_handled': sum(self.error_stats.values())
        }
    
    def _log_error(self, error_report: Dict[str, Any]) -> None:
        """Log error with appropriate level"""
        severity = error_report['severity']
        message = json.dumps(error_report, indent=2, default=str)
        
        if severity == ErrorSeverity.CRITICAL.value:
            self.logger.critical(message)
        elif severity == ErrorSeverity.HIGH.value:
            self.logger.error(message)
        elif severity == ErrorSeverity.MEDIUM.value:
            self.logger.warning(message)
        else:
            self.logger.info(message)
    
    def _update_error_stats(self, error: BotPhiaError) -> None:
        """Update error statistics"""
        error_type = error.__class__.__name__
        self.error_stats[error_type] = self.error_stats.get(error_type, 0) + 1
    
    def _attempt_recovery(self, error: BotPhiaError, recovery_suggestion: str) -> None:
        """Attempt error recovery based on suggestion"""
        recovery_key = f"{error.__class__.__name__}_{recovery_suggestion}"
        self.recovery_attempts[recovery_key] = self.recovery_attempts.get(recovery_key, 0) + 1
        
        # Log recovery attempt
        self.logger.info(f"Attempting recovery for {error.__class__.__name__}: {recovery_suggestion}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error handling statistics"""
        return {
            'error_counts': dict(self.error_stats),
            'recovery_attempts': dict(self.recovery_attempts),
            'total_errors': sum(self.error_stats.values()),
            'most_common_error': max(self.error_stats.items(), key=lambda x: x[1])[0] if self.error_stats else None,
            'timestamp': datetime.now().isoformat()
        }
    
    def clear_statistics(self) -> None:
        """Clear error statistics"""
        self.error_stats.clear()
        self.recovery_attempts.clear()

# Decorator for automatic error handling
# =====================================

def handle_errors(severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 recovery_suggestion: str = None,
                 error_handler: ErrorHandler = None,
                 reraise: bool = False):
    """
    Decorator for automatic error handling.
    
    Args:
        severity: Error severity level
        recovery_suggestion: Recovery suggestion
        error_handler: ErrorHandler instance (uses global if None)
        reraise: Whether to reraise the exception after handling
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Use provided handler or create default
                handler = error_handler or get_global_error_handler()
                
                # Add function context
                context = {
                    'function': func.__name__,
                    'module': func.__module__,
                    'args': str(args)[:200],  # Limit context size
                    'kwargs': str(kwargs)[:200]
                }
                
                # Handle the error
                handler.handle_error(e, context, severity, recovery_suggestion)
                
                # Reraise if requested
                if reraise:
                    raise
                
                # Return None or default value for handled errors
                return None
                
        return wrapper
    return decorator

# Global error handler instance
# =============================

_global_error_handler: Optional[ErrorHandler] = None

def get_global_error_handler() -> ErrorHandler:
    """Get or create global error handler"""
    global _global_error_handler
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler()
    return _global_error_handler

def set_global_error_handler(handler: ErrorHandler) -> None:
    """Set global error handler"""
    global _global_error_handler
    _global_error_handler = handler

# Convenience functions
# ====================

def handle_trading_error(error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Handle trading-specific error"""
    handler = get_global_error_handler()
    return handler.handle_error(error, context, ErrorSeverity.HIGH, "Check trading parameters and retry")

def handle_calculation_error(error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Handle calculation error"""
    handler = get_global_error_handler()
    return handler.handle_error(error, context, ErrorSeverity.MEDIUM, "Validate input data and retry calculation")

def handle_data_error(error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Handle data validation error"""
    handler = get_global_error_handler()
    return handler.handle_error(error, context, ErrorSeverity.MEDIUM, "Validate and clean input data")

def handle_api_error(error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Handle API communication error"""
    handler = get_global_error_handler()
    return handler.handle_error(error, context, ErrorSeverity.HIGH, "Check API connectivity and retry with backoff")

def handle_critical_error(error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """Handle critical system error"""
    handler = get_global_error_handler()
    return handler.handle_error(error, context, ErrorSeverity.CRITICAL, "Immediate attention required - system may be unstable")

# Context manager for error handling
# ==================================

class ErrorContext:
    """Context manager for automatic error handling"""
    
    def __init__(self, operation_name: str, severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                 recovery_suggestion: str = None, reraise: bool = True):
        self.operation_name = operation_name
        self.severity = severity
        self.recovery_suggestion = recovery_suggestion
        self.reraise = reraise
        self.handler = get_global_error_handler()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        if exc_value:
            context = {'operation': self.operation_name}
            self.handler.handle_error(exc_value, context, self.severity, self.recovery_suggestion)
            return not self.reraise  # Suppress exception if not reraising
        return False

# Usage example:
# with ErrorContext("calculate_pnl", ErrorSeverity.HIGH, "Validate prices"):
#     pnl = calculate_pnl(entry, current, quantity)