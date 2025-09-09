#!/usr/bin/env python3
"""
===========================================
VALIDATION & SECURITY SYSTEM - BotPhia
===========================================

Comprehensive input validation and sanitization system for trading platform.
Implements strict validation for all financial data and trading parameters.

SECURITY FEATURES:
- Pydantic models for strict type validation
- Input sanitization against XSS and SQL injection
- Trading-specific validation rules
- Permission-based access control
- Request/response filtering
- Security event logging

Author: Security Team
Date: 2025-01-22
Version: 2.0.0
"""

import re
import html
import hashlib
import secrets
import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Union, Literal
from enum import Enum
from dataclasses import dataclass

from pydantic import BaseModel, Field, validator, root_validator
from fastapi import HTTPException, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Security Logger
security_logger = logging.getLogger('security')
security_logger.setLevel(logging.INFO)

# ===========================================
# SECURITY CONSTANTS
# ===========================================

# Trading symbols whitelist (crypto pairs only)
ALLOWED_TRADING_SYMBOLS = {
    'BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT', 'LINKUSDT', 
    'SOLUSDT', 'AVAXUSDT', 'XRPUSDT', 'DOGEUSDT', 'BNBUSDT',
    'MATICUSDT', 'ATOMUSDT', 'LTCUSDT', 'BCHUSDT', 'ETCUSDT'
}

# Philosopher names whitelist
ALLOWED_PHILOSOPHERS = {
    'aristotle', 'plato', 'socrates', 'confucius', 'buddha',
    'nietzsche', 'kant', 'descartes', 'hume', 'locke'
}

# Action types for trading
TRADING_ACTIONS = {'BUY', 'SELL', 'HOLD', 'CLOSE'}

# Position types
POSITION_TYPES = {'LONG', 'SHORT'}

# Risk levels
RISK_LEVELS = {'LOW', 'MEDIUM', 'HIGH'}

# Time intervals for charts
CHART_INTERVALS = {'1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M'}

# ===========================================
# SECURITY UTILITIES
# ===========================================

class SecurityValidator:
    """Core security validation utilities"""
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 255) -> str:
        """Sanitize string input against XSS and injection attacks"""
        if not isinstance(value, str):
            raise ValueError("Input must be a string")
        
        # Limit length
        if len(value) > max_length:
            raise ValueError(f"Input exceeds maximum length of {max_length}")
        
        # HTML encode to prevent XSS
        sanitized = html.escape(value.strip())
        
        # Remove potentially dangerous patterns
        dangerous_patterns = [
            r'<script.*?>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'onload=',
            r'onerror=',
            r'onclick=',
            r'--',
            r';',
            r'union\s+select',
            r'drop\s+table',
            r'insert\s+into',
            r'delete\s+from',
            r'update\s+.*\s+set'
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, sanitized, re.IGNORECASE):
                raise ValueError(f"Input contains potentially dangerous content")
        
        return sanitized
    
    @staticmethod
    def validate_decimal_precision(value: Union[str, float, Decimal], max_decimals: int = 8) -> Decimal:
        """Validate and convert to Decimal with precision control"""
        try:
            if isinstance(value, str):
                # Remove any non-numeric characters except decimal point
                cleaned = re.sub(r'[^\d.]', '', value)
                decimal_value = Decimal(cleaned)
            else:
                decimal_value = Decimal(str(value))
            
            # Check decimal places
            if decimal_value.as_tuple().exponent < -max_decimals:
                raise ValueError(f"Too many decimal places (max {max_decimals})")
            
            return decimal_value
            
        except (InvalidOperation, ValueError) as e:
            raise ValueError(f"Invalid decimal value: {value}")
    
    @staticmethod
    def validate_percentage(value: float) -> float:
        """Validate percentage values (0-100)"""
        if not isinstance(value, (int, float)):
            raise ValueError("Percentage must be a number")
        
        if value < 0 or value > 100:
            raise ValueError("Percentage must be between 0 and 100")
        
        return float(value)
    
    @staticmethod
    def validate_trading_amount(amount: Union[str, float, Decimal], min_amount: Decimal = Decimal('0.001')) -> Decimal:
        """Validate trading amounts with minimum thresholds"""
        decimal_amount = SecurityValidator.validate_decimal_precision(amount)
        
        if decimal_amount <= 0:
            raise ValueError("Trading amount must be positive")
        
        if decimal_amount < min_amount:
            raise ValueError(f"Trading amount too small (minimum: {min_amount})")
        
        # Maximum reasonable amount for safety
        max_amount = Decimal('1000000')  # 1M USD equivalent
        if decimal_amount > max_amount:
            raise ValueError(f"Trading amount too large (maximum: {max_amount})")
        
        return decimal_amount

# ===========================================
# PYDANTIC VALIDATION MODELS
# ===========================================

class TradingSymbol(BaseModel):
    """Validated trading symbol"""
    symbol: str = Field(..., min_length=6, max_length=12)
    
    @validator('symbol')
    def validate_symbol(cls, v):
        v = v.upper().strip()
        if v not in ALLOWED_TRADING_SYMBOLS:
            raise ValueError(f"Invalid trading symbol. Allowed: {sorted(ALLOWED_TRADING_SYMBOLS)}")
        return v

class PhilosopherName(BaseModel):
    """Validated philosopher name"""
    name: str = Field(..., min_length=3, max_length=20)
    
    @validator('name')
    def validate_philosopher(cls, v):
        v = v.lower().strip()
        if v not in ALLOWED_PHILOSOPHERS:
            raise ValueError(f"Invalid philosopher. Allowed: {sorted(ALLOWED_PHILOSOPHERS)}")
        return v

class TradingAction(BaseModel):
    """Validated trading action"""
    action: str = Field(..., min_length=3, max_length=5)
    
    @validator('action')
    def validate_action(cls, v):
        v = v.upper().strip()
        if v not in TRADING_ACTIONS:
            raise ValueError(f"Invalid action. Allowed: {sorted(TRADING_ACTIONS)}")
        return v

class ChartInterval(BaseModel):
    """Validated chart interval"""
    interval: str = Field(..., min_length=2, max_length=3)
    
    @validator('interval')
    def validate_interval(cls, v):
        v = v.lower().strip()
        if v not in CHART_INTERVALS:
            raise ValueError(f"Invalid interval. Allowed: {sorted(CHART_INTERVALS)}")
        return v

class TradingPrice(BaseModel):
    """Validated trading price"""
    price: Decimal = Field(..., gt=0, max_digits=12, decimal_places=8)
    
    @validator('price', pre=True)
    def validate_price(cls, v):
        return SecurityValidator.validate_decimal_precision(v)

class TradingQuantity(BaseModel):
    """Validated trading quantity"""
    quantity: Decimal = Field(..., gt=0, max_digits=12, decimal_places=8)
    
    @validator('quantity', pre=True)
    def validate_quantity(cls, v):
        return SecurityValidator.validate_trading_amount(v)

class ConfidenceScore(BaseModel):
    """Validated confidence score (0-100)"""
    confidence: float = Field(..., ge=0, le=100)
    
    @validator('confidence')
    def validate_confidence(cls, v):
        return SecurityValidator.validate_percentage(v)

class UserPermissions(BaseModel):
    """User permission validation"""
    user_id: str = Field(..., min_length=1, max_length=50)
    role: Literal['admin', 'trader', 'viewer'] = 'trader'
    permissions: List[str] = Field(default_factory=list)
    
    @validator('user_id')
    def validate_user_id(cls, v):
        return SecurityValidator.sanitize_string(v, 50)
    
    @validator('permissions')
    def validate_permissions(cls, v):
        allowed_permissions = {
            'read_positions', 'write_positions', 'read_signals', 'write_signals',
            'read_config', 'write_config', 'admin_access', 'backtest_access'
        }
        for perm in v:
            if perm not in allowed_permissions:
                raise ValueError(f"Invalid permission: {perm}")
        return v

# ===========================================
# API REQUEST MODELS
# ===========================================

class LoginRequest(BaseModel):
    """Secure login request validation"""
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    
    @validator('username')
    def validate_username(cls, v):
        # Allow only alphanumeric and safe characters
        if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
            raise ValueError("Username contains invalid characters")
        return SecurityValidator.sanitize_string(v, 50)
    
    @validator('password')
    def validate_password(cls, v):
        # Check password complexity
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r'\d', v):
            raise ValueError("Password must contain at least one digit")
        return v

class TradingSignalRequest(BaseModel):
    """Secure trading signal request"""
    symbol: str
    action: str
    entry_price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    quantity: Optional[Decimal] = None
    confidence: Optional[float] = None
    philosopher: Optional[str] = None
    
    @validator('symbol')
    def validate_symbol(cls, v):
        return TradingSymbol(symbol=v).symbol
    
    @validator('action')
    def validate_action(cls, v):
        return TradingAction(action=v).action
    
    @validator('entry_price', 'stop_loss', 'take_profit', pre=True)
    def validate_prices(cls, v):
        if v is not None:
            return TradingPrice(price=v).price
        return v
    
    @validator('quantity', pre=True)
    def validate_quantity(cls, v):
        if v is not None:
            return TradingQuantity(quantity=v).quantity
        return v
    
    @validator('confidence')
    def validate_confidence(cls, v):
        if v is not None:
            return ConfidenceScore(confidence=v).confidence
        return v
    
    @validator('philosopher')
    def validate_philosopher(cls, v):
        if v is not None:
            return PhilosopherName(name=v).name
        return v

class PositionRequest(BaseModel):
    """Secure position management request"""
    symbol: str
    position_type: str
    entry_price: Decimal
    quantity: Decimal
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    risk_level: Optional[str] = 'MEDIUM'
    
    @validator('symbol')
    def validate_symbol(cls, v):
        return TradingSymbol(symbol=v).symbol
    
    @validator('position_type')
    def validate_position_type(cls, v):
        v = v.upper().strip()
        if v not in POSITION_TYPES:
            raise ValueError(f"Invalid position type. Allowed: {sorted(POSITION_TYPES)}")
        return v
    
    @validator('entry_price', 'stop_loss', 'take_profit', pre=True)
    def validate_prices(cls, v):
        if v is not None:
            return TradingPrice(price=v).price
        return v
    
    @validator('quantity', pre=True)
    def validate_quantity(cls, v):
        return TradingQuantity(quantity=v).quantity
    
    @validator('risk_level')
    def validate_risk_level(cls, v):
        if v is not None:
            v = v.upper().strip()
            if v not in RISK_LEVELS:
                raise ValueError(f"Invalid risk level. Allowed: {sorted(RISK_LEVELS)}")
        return v

class BacktestRequest(BaseModel):
    """Secure backtest request"""
    symbol: str
    period_days: int = Field(..., ge=1, le=365)
    initial_capital: Optional[Decimal] = Field(default=Decimal('10000'), gt=0)
    
    @validator('symbol')
    def validate_symbol(cls, v):
        return TradingSymbol(symbol=v).symbol
    
    @validator('initial_capital', pre=True)
    def validate_capital(cls, v):
        if v is not None:
            return SecurityValidator.validate_trading_amount(v, Decimal('100'))
        return v

class ChartDataRequest(BaseModel):
    """Secure chart data request"""
    symbol: str
    interval: str = '15m'
    limit: int = Field(default=100, ge=1, le=1000)
    
    @validator('symbol')
    def validate_symbol(cls, v):
        return TradingSymbol(symbol=v).symbol
    
    @validator('interval')
    def validate_interval(cls, v):
        return ChartInterval(interval=v).interval

# ===========================================
# PERMISSION VALIDATION SYSTEM
# ===========================================

class PermissionValidator:
    """Role-based access control system"""
    
    # Permission matrix
    ROLE_PERMISSIONS = {
        'admin': [
            'read_positions', 'write_positions', 'read_signals', 'write_signals',
            'read_config', 'write_config', 'admin_access', 'backtest_access',
            'user_management', 'system_maintenance'
        ],
        'trader': [
            'read_positions', 'write_positions', 'read_signals', 'write_signals',
            'read_config', 'backtest_access'
        ],
        'viewer': [
            'read_positions', 'read_signals', 'read_config'
        ]
    }
    
    @classmethod
    def validate_user_permission(cls, user: Dict[str, Any], required_permission: str) -> bool:
        """Validate if user has required permission"""
        if not user:
            return False
        
        user_role = user.get('role', 'viewer')
        user_permissions = user.get('permissions', [])
        
        # Check role-based permissions
        role_perms = cls.ROLE_PERMISSIONS.get(user_role, [])
        
        # Check if permission is granted by role or explicitly
        return required_permission in role_perms or required_permission in user_permissions
    
    @classmethod
    def require_permission(cls, required_permission: str):
        """Decorator to require specific permission"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # Extract user from kwargs (injected by dependency)
                current_user = kwargs.get('current_user')
                if not current_user:
                    raise HTTPException(status_code=401, detail="Authentication required")
                
                if not cls.validate_user_permission(current_user, required_permission):
                    security_logger.warning(f"Permission denied: {current_user.get('user_id')} tried to access {required_permission}")
                    raise HTTPException(status_code=403, detail=f"Permission denied: {required_permission} required")
                
                return await func(*args, **kwargs)
            return wrapper
        return decorator

# ===========================================
# INPUT SANITIZATION MIDDLEWARE
# ===========================================

class ValidationMiddleware:
    """Comprehensive input validation and sanitization middleware"""
    
    def __init__(self):
        self.security_events = []
        self.request_counter = 0
    
    async def __call__(self, request: Request, call_next):
        """Process request through security validation"""
        self.request_counter += 1
        request_id = f"req_{self.request_counter}_{secrets.token_hex(4)}"
        
        # Log security event
        security_event = {
            'request_id': request_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'method': request.method,
            'url': str(request.url),
            'client_ip': request.client.host,
            'user_agent': request.headers.get('user-agent', 'unknown')
        }
        
        try:
            # Validate request size
            content_length = request.headers.get('content-length')
            if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB limit
                raise HTTPException(status_code=413, detail="Request too large")
            
            # Validate content type for POST/PUT requests
            if request.method in ['POST', 'PUT', 'PATCH']:
                content_type = request.headers.get('content-type', '')
                if not content_type.startswith(('application/json', 'application/x-www-form-urlencoded')):
                    raise HTTPException(status_code=415, detail="Unsupported media type")
            
            # Process request
            response = await call_next(request)
            
            # Log successful request
            security_event['status'] = 'success'
            security_event['response_status'] = response.status_code
            
            # Add security headers to response
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['X-XSS-Protection'] = '1; mode=block'
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            response.headers['X-Request-ID'] = request_id
            
            return response
            
        except HTTPException as e:
            security_event['status'] = 'error'
            security_event['error'] = e.detail
            security_event['error_code'] = e.status_code
            security_logger.warning(f"Security validation failed: {security_event}")
            raise
        
        except Exception as e:
            security_event['status'] = 'error'
            security_event['error'] = str(e)
            security_logger.error(f"Unexpected security error: {security_event}")
            raise HTTPException(status_code=500, detail="Internal security error")
        
        finally:
            self.security_events.append(security_event)
            # Keep only last 1000 events
            if len(self.security_events) > 1000:
                self.security_events = self.security_events[-1000:]

# ===========================================
# SECURITY VALIDATION DECORATORS
# ===========================================

def validate_trading_request(model_class):
    """Decorator to validate trading requests"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Find request data in args/kwargs
            request_data = None
            for arg in args:
                if isinstance(arg, dict):
                    request_data = arg
                    break
            
            if not request_data:
                for key, value in kwargs.items():
                    if isinstance(value, dict):
                        request_data = value
                        break
            
            if request_data:
                try:
                    # Validate using Pydantic model
                    validated_data = model_class(**request_data)
                    # Replace original data with validated data
                    kwargs['validated_data'] = validated_data.dict()
                except Exception as e:
                    security_logger.warning(f"Validation failed: {e}")
                    raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def log_security_event(event_type: str):
    """Decorator to log security events"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = datetime.now(timezone.utc)
            user_id = kwargs.get('current_user', {}).get('user_id', 'anonymous')
            
            try:
                result = await func(*args, **kwargs)
                
                security_logger.info(f"Security event: {event_type} - User: {user_id} - Success")
                return result
                
            except Exception as e:
                security_logger.warning(f"Security event: {event_type} - User: {user_id} - Failed: {str(e)}")
                raise
            
        return wrapper
    return decorator

# ===========================================
# SECURITY UTILITIES
# ===========================================

def generate_secure_token(length: int = 32) -> str:
    """Generate cryptographically secure token"""
    return secrets.token_urlsafe(length)

def hash_sensitive_data(data: str) -> str:
    """Hash sensitive data for logging"""
    return hashlib.sha256(data.encode()).hexdigest()[:16]

def mask_sensitive_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """Mask sensitive fields in data"""
    sensitive_fields = {'password', 'token', 'api_key', 'secret', 'private_key'}
    masked_data = data.copy()
    
    for key, value in masked_data.items():
        if any(sensitive in key.lower() for sensitive in sensitive_fields):
            if isinstance(value, str) and len(value) > 4:
                masked_data[key] = f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"
            else:
                masked_data[key] = "***"
    
    return masked_data

# ===========================================
# SECURITY INITIALIZATION
# ===========================================

# Global validation middleware instance
validation_middleware = ValidationMiddleware()

# Global permission validator
permission_validator = PermissionValidator()

# Security event logger setup
if not security_logger.handlers:
    handler = logging.FileHandler('/Users/ja/saby/trading_api/logs/security.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    security_logger.addHandler(handler)

# Log security system initialization
security_logger.info("Security validation system initialized")