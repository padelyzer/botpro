"""
BotPhia Safe Math System
=======================

Critical mathematical operations module with division-by-zero protection,
overflow handling, and precision management for financial calculations.

Author: Senior Backend Developer
Phase: 1 - Days 3-4
"""

import math
import logging
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Union, Optional, Tuple, Dict
import numpy as np
import pandas as pd

# Configure logging
logger = logging.getLogger(__name__)

# Type aliases for numeric types
NumericType = Union[int, float, Decimal]

class SafeMathError(Exception):
    """Base exception for safe math operations"""
    pass

class DivisionByZeroError(SafeMathError):
    """Raised when attempting division by zero"""
    pass

class OverflowError(SafeMathError):
    """Raised when calculation results in overflow"""
    pass

class PrecisionError(SafeMathError):
    """Raised when precision requirements cannot be met"""
    pass

class SafeMath:
    """
    Thread-safe mathematical operations with comprehensive error handling.
    
    Features:
    - Division by zero protection
    - Overflow detection and handling
    - Precision control for financial calculations
    - Logging of mathematical errors
    - Support for various numeric types
    """
    
    # Constants for financial calculations
    EPSILON = Decimal('1e-10')  # Minimum non-zero value
    MAX_VALUE = Decimal('1e15')  # Maximum safe value
    DEFAULT_PRECISION = 8  # Default decimal places
    
    @classmethod
    def safe_divide(cls, dividend: NumericType, divisor: NumericType, 
                   default: NumericType = 0, precision: int = DEFAULT_PRECISION,
                   raise_on_zero: bool = False) -> Decimal:
        """
        Perform safe division with zero protection.
        
        Args:
            dividend: The number to be divided
            divisor: The number to divide by
            default: Default value when division by zero occurs
            precision: Number of decimal places for result
            raise_on_zero: If True, raises exception on division by zero
            
        Returns:
            Division result as Decimal
            
        Raises:
            DivisionByZeroError: If divisor is zero and raise_on_zero is True
            OverflowError: If result exceeds maximum safe value
        """
        try:
            # Convert to Decimal for precision
            dividend_dec = Decimal(str(dividend))
            divisor_dec = Decimal(str(divisor))
            default_dec = Decimal(str(default))
            
            # Check for zero divisor
            if abs(divisor_dec) < cls.EPSILON:
                if raise_on_zero:
                    logger.error(f"Division by zero: {dividend} ÷ {divisor}")
                    raise DivisionByZeroError(f"Cannot divide {dividend} by {divisor}")
                
                logger.warning(f"Division by zero detected, returning default: {default}")
                return default_dec.quantize(Decimal('0.1') ** precision)
            
            # Perform division
            result = dividend_dec / divisor_dec
            
            # Check for overflow
            if abs(result) > cls.MAX_VALUE:
                logger.error(f"Division overflow: {dividend} ÷ {divisor} = {result}")
                raise OverflowError(f"Division result exceeds maximum value: {result}")
            
            # Apply precision
            quantized_result = result.quantize(Decimal('0.1') ** precision, rounding=ROUND_HALF_UP)
            
            logger.debug(f"Safe division: {dividend} ÷ {divisor} = {quantized_result}")
            return quantized_result
            
        except (InvalidOperation, ValueError) as e:
            logger.error(f"Invalid operation in safe_divide: {e}")
            return Decimal(str(default)).quantize(Decimal('0.1') ** precision)
        except Exception as e:
            logger.error(f"Unexpected error in safe_divide: {e}")
            if raise_on_zero:
                raise SafeMathError(f"Safe division failed: {e}")
            return Decimal(str(default)).quantize(Decimal('0.1') ** precision)
    
    @classmethod
    def safe_percentage(cls, part: NumericType, total: NumericType, 
                       default: NumericType = 0, precision: int = 4) -> Decimal:
        """
        Calculate percentage safely with zero protection.
        
        Args:
            part: Part value
            total: Total value
            default: Default percentage when total is zero
            precision: Number of decimal places
            
        Returns:
            Percentage as Decimal (0-100 scale)
        """
        try:
            if abs(Decimal(str(total))) < cls.EPSILON:
                logger.warning(f"Percentage calculation with zero total, returning default: {default}%")
                return Decimal(str(default)).quantize(Decimal('0.1') ** precision)
            
            percentage = cls.safe_divide(part, total, 0, precision + 2) * 100
            result = percentage.quantize(Decimal('0.1') ** precision, rounding=ROUND_HALF_UP)
            
            logger.debug(f"Safe percentage: {part}/{total} = {result}%")
            return result
            
        except Exception as e:
            logger.error(f"Error in safe_percentage: {e}")
            return Decimal(str(default)).quantize(Decimal('0.1') ** precision)
    
    @classmethod
    def safe_pnl_calculation(cls, entry_price: NumericType, current_price: NumericType,
                           quantity: NumericType, position_type: str = 'long',
                           precision: int = DEFAULT_PRECISION) -> Dict[str, Decimal]:
        """
        Calculate PnL safely with comprehensive error handling.
        
        Args:
            entry_price: Position entry price
            current_price: Current market price
            quantity: Position quantity
            position_type: 'long' or 'short'
            precision: Decimal precision for results
            
        Returns:
            Dictionary containing PnL calculations
        """
        try:
            # Convert to Decimal
            entry = Decimal(str(entry_price))
            current = Decimal(str(current_price))
            qty = Decimal(str(quantity))
            
            # Validate inputs
            if entry <= 0 or current <= 0 or qty <= 0:
                logger.error(f"Invalid PnL inputs: entry={entry}, current={current}, qty={qty}")
                return cls._empty_pnl_result(precision)
            
            # Calculate price difference
            if position_type.lower() == 'long':
                price_diff = current - entry
            elif position_type.lower() == 'short':
                price_diff = entry - current
            else:
                logger.error(f"Invalid position type: {position_type}")
                return cls._empty_pnl_result(precision)
            
            # Calculate absolute PnL
            absolute_pnl = price_diff * qty
            
            # Calculate percentage PnL
            percentage_pnl = cls.safe_percentage(price_diff, entry, 0, precision)
            
            # Calculate return on investment
            investment = entry * qty
            roi = cls.safe_percentage(absolute_pnl, investment, 0, precision)
            
            result = {
                'absolute_pnl': absolute_pnl.quantize(Decimal('0.1') ** precision),
                'percentage_pnl': percentage_pnl,
                'roi': roi,
                'investment': investment.quantize(Decimal('0.1') ** precision),
                'current_value': (current * qty).quantize(Decimal('0.1') ** precision),
                'price_diff': price_diff.quantize(Decimal('0.1') ** precision)
            }
            
            logger.debug(f"PnL calculated: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error in safe_pnl_calculation: {e}")
            return cls._empty_pnl_result(precision)
    
    @classmethod
    def _empty_pnl_result(cls, precision: int) -> Dict[str, Decimal]:
        """Return empty PnL result with proper precision"""
        zero = Decimal('0').quantize(Decimal('0.1') ** precision)
        return {
            'absolute_pnl': zero,
            'percentage_pnl': zero,
            'roi': zero,
            'investment': zero,
            'current_value': zero,
            'price_diff': zero
        }
    
    @classmethod
    def safe_multiply(cls, a: NumericType, b: NumericType, 
                     precision: int = DEFAULT_PRECISION) -> Decimal:
        """
        Safe multiplication with overflow protection.
        
        Args:
            a: First number
            b: Second number
            precision: Decimal precision
            
        Returns:
            Multiplication result
            
        Raises:
            OverflowError: If result exceeds maximum value
        """
        try:
            a_dec = Decimal(str(a))
            b_dec = Decimal(str(b))
            
            result = a_dec * b_dec
            
            if abs(result) > cls.MAX_VALUE:
                logger.error(f"Multiplication overflow: {a} × {b} = {result}")
                raise OverflowError(f"Multiplication result exceeds maximum value: {result}")
            
            return result.quantize(Decimal('0.1') ** precision)
            
        except Exception as e:
            logger.error(f"Error in safe_multiply: {e}")
            raise SafeMathError(f"Safe multiplication failed: {e}")
    
    @classmethod
    def safe_add(cls, a: NumericType, b: NumericType, 
                precision: int = DEFAULT_PRECISION) -> Decimal:
        """Safe addition with overflow protection"""
        try:
            a_dec = Decimal(str(a))
            b_dec = Decimal(str(b))
            
            result = a_dec + b_dec
            
            if abs(result) > cls.MAX_VALUE:
                logger.error(f"Addition overflow: {a} + {b} = {result}")
                raise OverflowError(f"Addition result exceeds maximum value: {result}")
            
            return result.quantize(Decimal('0.1') ** precision)
            
        except Exception as e:
            logger.error(f"Error in safe_add: {e}")
            raise SafeMathError(f"Safe addition failed: {e}")
    
    @classmethod
    def safe_subtract(cls, a: NumericType, b: NumericType, 
                     precision: int = DEFAULT_PRECISION) -> Decimal:
        """Safe subtraction with overflow protection"""
        try:
            a_dec = Decimal(str(a))
            b_dec = Decimal(str(b))
            
            result = a_dec - b_dec
            
            if abs(result) > cls.MAX_VALUE:
                logger.error(f"Subtraction overflow: {a} - {b} = {result}")
                raise OverflowError(f"Subtraction result exceeds maximum value: {result}")
            
            return result.quantize(Decimal('0.1') ** precision)
            
        except Exception as e:
            logger.error(f"Error in safe_subtract: {e}")
            raise SafeMathError(f"Safe subtraction failed: {e}")
    
    @classmethod
    def safe_sqrt(cls, value: NumericType, precision: int = DEFAULT_PRECISION) -> Decimal:
        """
        Safe square root calculation.
        
        Args:
            value: Value to calculate square root
            precision: Decimal precision
            
        Returns:
            Square root result
            
        Raises:
            SafeMathError: If value is negative
        """
        try:
            value_dec = Decimal(str(value))
            
            if value_dec < 0:
                logger.error(f"Square root of negative number: {value}")
                raise SafeMathError(f"Cannot calculate square root of negative number: {value}")
            
            if value_dec == 0:
                return Decimal('0').quantize(Decimal('0.1') ** precision)
            
            # Use Newton's method for square root
            result = value_dec.sqrt()
            return result.quantize(Decimal('0.1') ** precision)
            
        except Exception as e:
            logger.error(f"Error in safe_sqrt: {e}")
            raise SafeMathError(f"Safe square root failed: {e}")
    
    @classmethod
    def safe_power(cls, base: NumericType, exponent: NumericType, 
                  precision: int = DEFAULT_PRECISION) -> Decimal:
        """
        Safe power calculation with overflow protection.
        
        Args:
            base: Base number
            exponent: Exponent
            precision: Decimal precision
            
        Returns:
            Power result
        """
        try:
            base_dec = Decimal(str(base))
            exp_dec = Decimal(str(exponent))
            
            # Handle special cases
            if base_dec == 0 and exp_dec <= 0:
                if exp_dec == 0:
                    return Decimal('1').quantize(Decimal('0.1') ** precision)
                else:
                    logger.error(f"Zero to negative power: {base}^{exponent}")
                    raise SafeMathError(f"Cannot raise zero to negative power: {base}^{exponent}")
            
            result = base_dec ** exp_dec
            
            if abs(result) > cls.MAX_VALUE:
                logger.error(f"Power overflow: {base}^{exponent} = {result}")
                raise OverflowError(f"Power result exceeds maximum value: {result}")
            
            return result.quantize(Decimal('0.1') ** precision)
            
        except Exception as e:
            logger.error(f"Error in safe_power: {e}")
            raise SafeMathError(f"Safe power calculation failed: {e}")
    
    @classmethod
    def safe_log(cls, value: NumericType, base: Optional[NumericType] = None,
                precision: int = DEFAULT_PRECISION) -> Decimal:
        """
        Safe logarithm calculation.
        
        Args:
            value: Value to calculate logarithm
            base: Logarithm base (natural log if None)
            precision: Decimal precision
            
        Returns:
            Logarithm result
        """
        try:
            value_dec = Decimal(str(value))
            
            if value_dec <= 0:
                logger.error(f"Logarithm of non-positive number: {value}")
                raise SafeMathError(f"Cannot calculate logarithm of non-positive number: {value}")
            
            if base is None:
                result = value_dec.ln()
            else:
                base_dec = Decimal(str(base))
                if base_dec <= 0 or base_dec == 1:
                    logger.error(f"Invalid logarithm base: {base}")
                    raise SafeMathError(f"Invalid logarithm base: {base}")
                
                result = value_dec.ln() / base_dec.ln()
            
            return result.quantize(Decimal('0.1') ** precision)
            
        except Exception as e:
            logger.error(f"Error in safe_log: {e}")
            raise SafeMathError(f"Safe logarithm failed: {e}")

# Pandas/NumPy integration functions
class SafeArrayMath:
    """Safe mathematical operations for arrays and DataFrames"""
    
    @staticmethod
    def safe_divide_series(series1: pd.Series, series2: pd.Series, 
                          default: float = 0.0) -> pd.Series:
        """Safe division for pandas Series"""
        try:
            # Replace zero values with NaN to avoid division by zero
            divisor = series2.replace(0, np.nan)
            result = series1 / divisor
            
            # Fill NaN values with default
            result = result.fillna(default)
            
            logger.debug(f"Safe series division completed with {result.isna().sum()} NaN values filled")
            return result
            
        except Exception as e:
            logger.error(f"Error in safe_divide_series: {e}")
            return pd.Series([default] * len(series1), index=series1.index)
    
    @staticmethod
    def safe_percentage_series(part_series: pd.Series, total_series: pd.Series,
                              default: float = 0.0) -> pd.Series:
        """Safe percentage calculation for pandas Series"""
        try:
            result = SafeArrayMath.safe_divide_series(part_series, total_series, 0.0) * 100
            return result.fillna(default)
            
        except Exception as e:
            logger.error(f"Error in safe_percentage_series: {e}")
            return pd.Series([default] * len(part_series), index=part_series.index)

# Global convenience functions
def safe_divide(dividend: NumericType, divisor: NumericType, 
               default: NumericType = 0, precision: int = 8) -> Decimal:
    """Global convenience function for safe division"""
    return SafeMath.safe_divide(dividend, divisor, default, precision)

def safe_percentage(part: NumericType, total: NumericType, 
                   default: NumericType = 0, precision: int = 4) -> Decimal:
    """Global convenience function for safe percentage"""
    return SafeMath.safe_percentage(part, total, default, precision)

def safe_pnl(entry_price: NumericType, current_price: NumericType,
            quantity: NumericType, position_type: str = 'long') -> Dict[str, Decimal]:
    """Global convenience function for safe PnL calculation"""
    return SafeMath.safe_pnl_calculation(entry_price, current_price, quantity, position_type)