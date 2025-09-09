# Security Integration Guide - BotPhia Phase 2

This guide explains how to integrate the Phase 2 security components into the existing BotPhia trading platform.

## 1. Security Components Overview

The Phase 2 security implementation consists of 5 core modules:

1. **`validation_security.py`** - Input validation and sanitization
2. **`secure_operations.py`** - Secure system operations (no subprocess)
3. **`secure_logging.py`** - Advanced security logging
4. **`api_security_middleware.py`** - API security middleware
5. **`secure_run_system.py`** - Secure system runner

## 2. FastAPI Integration

### 2.1 Add Security Imports

Add these imports to `fastapi_server.py`:

```python
# Phase 2 Security Imports
from .validation_security import (
    ValidationMiddleware, PermissionValidator, 
    TradingSignalRequest, PositionRequest, ChartDataRequest,
    validate_trading_request, log_security_event
)
from .secure_logging import SecurityLoggerFactory, SecurityEventType, SecuritySeverity
from .api_security_middleware import SecurityMiddlewareFactory, security_monitor
from .secure_operations import system_manager, secure_ops
```

### 2.2 Initialize Security Components

Add to app initialization:

```python
# Initialize security loggers
api_logger = SecurityLoggerFactory.get_api_logger()
trading_logger = SecurityLoggerFactory.get_trading_logger()

# Create security middleware stack
security_middleware, security_monitor = SecurityMiddlewareFactory.create_security_stack(app)

# Initialize validation middleware
validation_middleware = ValidationMiddleware()
app.middleware("http")(validation_middleware)

# Add security middleware
app.add_middleware(SecurityMiddleware)
```

### 2.3 Update Authentication Dependencies

Replace existing auth functions:

```python
from .validation_security import PermissionValidator

async def get_current_user_with_permissions(
    authorization: str = Header(None),
    required_permission: str = None
):
    """Enhanced authentication with permission checking"""
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Authentication required")
    
    token = authorization.split(' ')[1]
    user_data = auth_manager.verify_token(token)
    
    if not user_data:
        # Log failed authentication
        api_logger.log_authentication(
            user_id="unknown",
            success=False,
            ip_address="unknown"
        )
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    
    # Check permissions if required
    if required_permission:
        if not PermissionValidator.validate_user_permission(user_data, required_permission):
            api_logger.log_authorization(
                user_id=user_data.get('user_id'),
                resource=required_permission,
                action="access",
                success=False
            )
            raise HTTPException(status_code=403, detail=f"Permission denied: {required_permission}")
    
    # Log successful authentication
    api_logger.log_authentication(
        user_id=user_data.get('user_id'),
        success=True,
        ip_address="unknown"
    )
    
    return user_data
```

### 2.4 Secure Endpoint Examples

#### Trading Endpoints

```python
@app.post("/api/positions/open")
@validate_trading_request(PositionRequest)
@log_security_event(SecurityEventType.SYSTEM_OPERATION)
async def open_position_securely(
    request: Request,
    position_data: PositionRequest,
    current_user: dict = Depends(lambda: get_current_user_with_permissions(required_permission="write_positions"))
):
    """Securely open trading position"""
    try:
        # Log trading operation
        trading_logger.log_trading_operation(
            user_id=current_user['user_id'],
            operation="open_position",
            symbol=position_data.symbol,
            data=position_data.dict()
        )
        
        # Process position opening
        result = await trading_manager.open_position(position_data.dict())
        
        return {"success": True, "data": result}
        
    except Exception as e:
        api_logger.log_security_event(
            SecurityEventType.ERROR_OCCURRED,
            SecuritySeverity.MEDIUM,
            f"Position opening failed: {str(e)}",
            user_id=current_user['user_id'],
            context={"error": str(e), "symbol": position_data.symbol}
        )
        raise HTTPException(status_code=500, detail="Position opening failed")
```

#### Chart Data Endpoints

```python
@app.get("/api/market/{symbol}/chart")
@validate_trading_request(ChartDataRequest)
async def get_chart_data_securely(
    symbol: str,
    interval: str = "15m",
    limit: int = 100,
    current_user: dict = Depends(lambda: get_current_user_with_permissions(required_permission="read_signals"))
):
    """Securely get chart data"""
    try:
        # Validate inputs using security models
        chart_request = ChartDataRequest(
            symbol=symbol,
            interval=interval,
            limit=limit
        )
        
        # Log data access
        api_logger.log_data_access(
            user_id=current_user['user_id'],
            resource=f"chart_data_{symbol}",
            action="read"
        )
        
        # Get chart data
        chart_data = await get_binance_chart_data(
            chart_request.symbol,
            chart_request.interval,
            chart_request.limit
        )
        
        return {"success": True, "data": chart_data}
        
    except Exception as e:
        api_logger.error(f"Chart data error: {str(e)}", extra={
            "user_id": current_user['user_id'],
            "symbol": symbol,
            "error": str(e)
        })
        raise HTTPException(status_code=500, detail="Chart data retrieval failed")
```

## 3. System Operations Integration

### 3.1 Replace Subprocess Calls

Replace all subprocess usage with secure operations:

```python
# BEFORE (Insecure):
import subprocess
result = subprocess.run(['python', 'maintenance.py'], capture_output=True)

# AFTER (Secure):
from .secure_operations import system_manager
result = await system_manager.run_maintenance()
```

### 3.2 System Health Monitoring

```python
@app.get("/api/system/health")
async def get_system_health(
    current_user: dict = Depends(lambda: get_current_user_with_permissions(required_permission="admin_access"))
):
    """Get secure system health status"""
    try:
        # Use secure operations
        health_result = system_manager.health_check()
        
        if health_result.success:
            return {"success": True, "data": health_result.data}
        else:
            return {"success": False, "error": health_result.error}
            
    except Exception as e:
        api_logger.error(f"Health check error: {str(e)}")
        raise HTTPException(status_code=500, detail="Health check failed")
```

## 4. Database Security Integration

### 4.1 Secure Database Operations

Update database operations to use secure patterns:

```python
from .secure_operations import SecureDatabaseManager

# Initialize secure database manager
secure_db = SecureDatabaseManager("/Users/ja/saby/trading_api/trading_bot.db")

@app.post("/api/database/maintenance")
async def run_database_maintenance(
    current_user: dict = Depends(lambda: get_current_user_with_permissions(required_permission="admin_access"))
):
    """Run secure database maintenance"""
    try:
        # Vacuum database
        vacuum_result = secure_db.vacuum_database()
        
        # Cleanup old records
        cleanup_result = secure_db.cleanup_old_records(days_to_keep=30)
        
        # Log maintenance activity
        api_logger.log_security_event(
            SecurityEventType.SYSTEM_OPERATION,
            SecuritySeverity.LOW,
            "Database maintenance completed",
            user_id=current_user['user_id'],
            context={
                "vacuum_success": vacuum_result.success,
                "cleanup_success": cleanup_result.success
            }
        )
        
        return {
            "success": True,
            "vacuum_result": vacuum_result.to_dict(),
            "cleanup_result": cleanup_result.to_dict()
        }
        
    except Exception as e:
        api_logger.error(f"Database maintenance error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database maintenance failed")
```

## 5. Logging Integration

### 5.1 Replace Standard Logging

```python
# BEFORE:
import logging
logger = logging.getLogger(__name__)
logger.info("User logged in")

# AFTER:
from .secure_logging import SecurityLoggerFactory
api_logger = SecurityLoggerFactory.get_api_logger()

api_logger.log_authentication(
    user_id=user_id,
    success=True,
    ip_address=request.client.host
)
```

### 5.2 Trading Operation Logging

```python
async def execute_trade(user_id: str, trade_data: dict):
    """Execute trade with secure logging"""
    try:
        # Log trade initiation
        trading_logger.log_trading_operation(
            user_id=user_id,
            operation="execute_trade",
            symbol=trade_data['symbol'],
            data=trade_data  # Will be automatically sanitized
        )
        
        # Execute trade logic
        result = await perform_trade_execution(trade_data)
        
        # Log successful completion
        trading_logger.info(f"Trade executed successfully", extra={
            "user_id": user_id,
            "symbol": trade_data['symbol'],
            "result": result
        })
        
        return result
        
    except Exception as e:
        trading_logger.log_security_event(
            SecurityEventType.ERROR_OCCURRED,
            SecuritySeverity.HIGH,
            f"Trade execution failed: {str(e)}",
            user_id=user_id,
            context={"error": str(e), "trade_data": trade_data}
        )
        raise
```

## 6. Rate Limiting Integration

### 6.1 Endpoint-Specific Rate Limiting

```python
from .api_security_middleware import AdvancedRateLimiter

# Initialize rate limiter
rate_limiter = AdvancedRateLimiter()

# Configure specific endpoints
rate_limiter.configure_rate_limit("login", requests=5, window=300)
rate_limiter.configure_rate_limit("trading", requests=100, window=60)

async def check_rate_limit(request: Request, endpoint_type: str = "default"):
    """Check rate limiting for endpoint"""
    user_id = await extract_user_id_from_request(request)
    
    is_limited, details = rate_limiter.is_rate_limited(
        request, user_id, endpoint_type
    )
    
    if is_limited:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(details.get('reset_time', 3600))}
        )
```

## 7. Deployment Integration

### 7.1 Update Startup Script

Create a new secure startup script:

```python
# secure_startup.py
import asyncio
from .secure_run_system import SecureTradingSystemManager

async def main():
    """Secure system startup"""
    system_manager = SecureTradingSystemManager()
    
    # Start secure trading system
    result = await system_manager.start_system()
    
    if result.success:
        print("🔒 Secure trading system started successfully")
        
        # Keep running
        try:
            while system_manager.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await system_manager.stop_system()
    else:
        print(f"❌ Failed to start system: {result.error}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 7.2 Environment Configuration

Update environment variables for security:

```bash
# Security configuration
export SECURITY_LOGGING_ENABLED=true
export RATE_LIMITING_ENABLED=true
export VALIDATION_STRICT_MODE=true
export SUBPROCESS_DISABLED=true

# Logging configuration
export LOG_LEVEL=INFO
export SECURITY_LOG_LEVEL=INFO
export LOG_SANITIZATION=true
```

## 8. Testing Security Integration

### 8.1 Security Test Suite

```python
# test_security_integration.py
import pytest
from fastapi.testclient import TestClient
from .fastapi_server import app

client = TestClient(app)

def test_input_validation():
    """Test input validation security"""
    # Test XSS prevention
    response = client.post("/api/positions/open", json={
        "symbol": "<script>alert('xss')</script>",
        "type": "LONG"
    })
    assert response.status_code == 422  # Validation error

def test_rate_limiting():
    """Test rate limiting"""
    # Make multiple rapid requests
    for i in range(10):
        response = client.post("/api/auth/login", json={
            "username": "test",
            "password": "test"
        })
    
    # Should get rate limited
    assert response.status_code == 429

def test_authentication_required():
    """Test authentication requirement"""
    response = client.get("/api/positions")
    assert response.status_code == 401

def test_permission_enforcement():
    """Test permission enforcement"""
    # Test with insufficient permissions
    response = client.post("/api/config", json={"key": "value"})
    assert response.status_code in [401, 403]
```

### 8.2 Security Validation Checklist

- [ ] All endpoints use secure validation
- [ ] Rate limiting is enforced
- [ ] Authentication is required where needed
- [ ] Permissions are properly checked
- [ ] Sensitive data is sanitized in logs
- [ ] No subprocess calls remain
- [ ] Security headers are present
- [ ] CORS is properly configured

## 9. Monitoring and Alerting

### 9.1 Security Dashboard Setup

```python
@app.get("/api/security/dashboard")
async def get_security_dashboard(
    current_user: dict = Depends(lambda: get_current_user_with_permissions(required_permission="admin_access"))
):
    """Get security monitoring dashboard"""
    try:
        # Get security metrics
        security_metrics = {
            "rate_limit_violations": get_rate_limit_violations(),
            "authentication_failures": get_auth_failures(),
            "suspicious_activities": get_suspicious_activities(),
            "system_health": system_manager.health_check().to_dict()
        }
        
        return {"success": True, "data": security_metrics}
        
    except Exception as e:
        api_logger.error(f"Security dashboard error: {str(e)}")
        raise HTTPException(status_code=500, detail="Dashboard unavailable")
```

### 9.2 Alert Configuration

```python
# Configure security alerts
SECURITY_ALERTS = {
    "failed_logins_threshold": 5,
    "rate_limit_violations_threshold": 10,
    "suspicious_requests_threshold": 3,
    "error_rate_threshold": 0.05
}

async def check_security_alerts():
    """Check for security alert conditions"""
    # Implementation for alert checking
    pass
```

## 10. Migration Plan

### 10.1 Phased Migration

1. **Phase 1:** Deploy validation and logging components
2. **Phase 2:** Enable API security middleware
3. **Phase 3:** Replace subprocess calls with secure operations
4. **Phase 4:** Full security monitoring activation

### 10.2 Rollback Plan

If issues arise, rollback steps:

1. Disable security middleware
2. Revert to original endpoints
3. Restore original logging
4. Document issues and plan fixes

## Conclusion

This integration guide provides a comprehensive approach to implementing Phase 2 security enhancements. Follow the steps carefully and test thoroughly before deploying to production.

For questions or support, refer to the `SECURITY_AUDIT_REPORT.md` for detailed technical specifications.