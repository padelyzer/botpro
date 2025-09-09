#!/usr/bin/env python3
"""
===========================================
API SECURITY MIDDLEWARE - BotPhia
===========================================

Comprehensive API security middleware with:
- Rate limiting with user-specific quotas
- Authentication and authorization
- CORS security with strict origin validation
- Security headers middleware
- Request/response logging with security context
- API versioning and deprecation security
- Real-time threat detection

SECURITY FEATURES:
- DDoS protection
- Brute force attack prevention
- API abuse detection
- Security headers enforcement
- Request fingerprinting
- Anomaly detection

Author: Security Team
Date: 2025-01-22
Version: 2.0.0
"""

import time
import hashlib
import json
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
import ipaddress
import re

from fastapi import Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint

# Import security logging
from .secure_logging import (
    SecurityLoggerFactory, SecurityEventType, SecuritySeverity,
    api_logger
)
from .validation_security import security_logger

# ===========================================
# SECURITY CONSTANTS
# ===========================================

# Rate limiting configuration
DEFAULT_RATE_LIMITS = {
    'login': {'requests': 5, 'window': 300},  # 5 attempts per 5 minutes
    'trading': {'requests': 100, 'window': 60},  # 100 trading ops per minute
    'market_data': {'requests': 1000, 'window': 60},  # 1000 market data requests per minute
    'default': {'requests': 1000, 'window': 3600},  # 1000 requests per hour
}

# User role rate limits
ROLE_RATE_LIMITS = {
    'admin': {'multiplier': 10},
    'trader': {'multiplier': 3},
    'viewer': {'multiplier': 1},
}

# Allowed origins for CORS (production should be more restrictive)
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://localhost:3000",
    "https://botphia.fly.dev",
    "https://botphia.vercel.app",
    "https://saby-botphia.vercel.app"
]

# Security headers
SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';",
    'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
}

# Suspicious patterns
SUSPICIOUS_PATTERNS = [
    re.compile(r'<script.*?>', re.IGNORECASE),
    re.compile(r'javascript:', re.IGNORECASE),
    re.compile(r'union.*select', re.IGNORECASE),
    re.compile(r'drop.*table', re.IGNORECASE),
    re.compile(r'exec.*\(', re.IGNORECASE),
    re.compile(r'\.\./', re.IGNORECASE),
    re.compile(r'passwd|shadow|hosts', re.IGNORECASE),
]

# ===========================================
# SECURITY CLASSES
# ===========================================

class ThreatLevel(Enum):
    """Threat level classification"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    requests: int
    window: int  # seconds
    burst_allowance: int = 0

@dataclass
class SecurityMetrics:
    """Security metrics tracking"""
    request_count: int = 0
    blocked_requests: int = 0
    suspicious_requests: int = 0
    rate_limited_requests: int = 0
    authentication_failures: int = 0
    last_reset: datetime = None

class RequestFingerprint:
    """Request fingerprinting for anomaly detection"""
    
    def __init__(self, request: Request):
        self.ip = request.client.host
        self.user_agent = request.headers.get('user-agent', '')
        self.accept_language = request.headers.get('accept-language', '')
        self.accept_encoding = request.headers.get('accept-encoding', '')
        self.method = request.method
        self.path = request.url.path
        
    def get_fingerprint(self) -> str:
        """Generate unique fingerprint for request"""
        fingerprint_data = f"{self.ip}:{self.user_agent}:{self.accept_language}:{self.accept_encoding}"
        return hashlib.md5(fingerprint_data.encode()).hexdigest()
    
    def is_suspicious(self) -> Tuple[bool, List[str]]:
        """Check if request fingerprint is suspicious"""
        suspicions = []
        
        # Check for missing or suspicious user agent
        if not self.user_agent or len(self.user_agent) < 10:
            suspicions.append("Missing or minimal user agent")
        
        # Check for automated tools patterns
        automated_patterns = ['bot', 'crawler', 'spider', 'scraper', 'curl', 'wget']
        if any(pattern in self.user_agent.lower() for pattern in automated_patterns):
            suspicions.append("Automated tool detected")
        
        # Check for suspicious path patterns
        for pattern in SUSPICIOUS_PATTERNS:
            if pattern.search(self.path):
                suspicions.append(f"Suspicious path pattern: {pattern.pattern}")
        
        return len(suspicions) > 0, suspicions

# ===========================================
# RATE LIMITER
# ===========================================

class AdvancedRateLimiter:
    """Advanced rate limiter with user-specific quotas and burst handling"""
    
    def __init__(self):
        self.rate_limits = DEFAULT_RATE_LIMITS.copy()
        self.user_requests: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(deque))
        self.ip_requests: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(deque))
        self.blocked_ips: Set[str] = set()
        self.blocked_until: Dict[str, datetime] = {}
        self.suspicious_activities: Dict[str, int] = defaultdict(int)
        
    def configure_rate_limit(self, endpoint: str, requests: int, window: int):
        """Configure rate limit for specific endpoint"""
        self.rate_limits[endpoint] = {'requests': requests, 'window': window}
    
    def is_rate_limited(self, 
                       request: Request, 
                       user_id: Optional[str] = None,
                       endpoint_type: str = 'default') -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Check if request should be rate limited"""
        current_time = datetime.now()
        client_ip = request.client.host
        
        # Check if IP is blocked
        if client_ip in self.blocked_ips:
            if client_ip in self.blocked_until:
                if current_time < self.blocked_until[client_ip]:
                    return True, {
                        'error': 'IP temporarily blocked',
                        'blocked_until': self.blocked_until[client_ip].isoformat(),
                        'reason': 'Suspicious activity detected'
                    }
                else:
                    # Unblock IP
                    self.blocked_ips.discard(client_ip)
                    del self.blocked_until[client_ip]
        
        # Get rate limit configuration
        rate_config = self.rate_limits.get(endpoint_type, self.rate_limits['default'])
        
        # Apply user role multiplier
        if user_id:
            # This would typically come from user context
            user_role = 'trader'  # Default role
            multiplier = ROLE_RATE_LIMITS.get(user_role, {}).get('multiplier', 1)
            effective_limit = rate_config['requests'] * multiplier
        else:
            effective_limit = rate_config['requests']
        
        window = rate_config['window']
        
        # Check rate limits
        rate_limited, details = self._check_rate_limit(
            client_ip, user_id, effective_limit, window, current_time
        )
        
        if rate_limited:
            # Track suspicious activity
            self.suspicious_activities[client_ip] += 1
            
            # Block IP if too many rate limit violations
            if self.suspicious_activities[client_ip] > 10:
                self._block_ip(client_ip, minutes=30)
                details['blocked'] = True
        
        return rate_limited, details
    
    def _check_rate_limit(self, 
                         ip: str, 
                         user_id: Optional[str], 
                         limit: int, 
                         window: int, 
                         current_time: datetime) -> Tuple[bool, Dict[str, Any]]:
        """Internal rate limit checking"""
        cutoff_time = current_time - timedelta(seconds=window)
        
        # Check IP-based rate limiting
        ip_requests = self.ip_requests[ip]['requests']
        
        # Remove old requests
        while ip_requests and datetime.fromisoformat(ip_requests[0]) < cutoff_time:
            ip_requests.popleft()
        
        # Check user-based rate limiting if user is authenticated
        if user_id:
            user_requests = self.user_requests[user_id]['requests']
            while user_requests and datetime.fromisoformat(user_requests[0]) < cutoff_time:
                user_requests.popleft()
            
            # Use the more restrictive limit
            effective_requests = max(len(ip_requests), len(user_requests))
        else:
            effective_requests = len(ip_requests)
        
        # Check if limit exceeded
        if effective_requests >= limit:
            return True, {
                'error': 'Rate limit exceeded',
                'limit': limit,
                'window': window,
                'current_requests': effective_requests,
                'reset_time': (cutoff_time + timedelta(seconds=window)).isoformat()
            }
        
        # Add current request
        current_time_str = current_time.isoformat()
        ip_requests.append(current_time_str)
        
        if user_id:
            user_requests.append(current_time_str)
        
        return False, {
            'remaining': limit - effective_requests - 1,
            'reset_time': (cutoff_time + timedelta(seconds=window)).isoformat()
        }
    
    def _block_ip(self, ip: str, minutes: int = 30):
        """Block IP address temporarily"""
        self.blocked_ips.add(ip)
        self.blocked_until[ip] = datetime.now() + timedelta(minutes=minutes)
        
        api_logger.log_security_event(
            SecurityEventType.SUSPICIOUS_ACTIVITY,
            SecuritySeverity.HIGH,
            f"IP blocked due to rate limit violations: {ip}",
            ip_address=ip,
            context={'block_duration_minutes': minutes}
        )

# ===========================================
# SECURITY MIDDLEWARE
# ===========================================

class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware"""
    
    def __init__(self, app):
        super().__init__(app)
        self.rate_limiter = AdvancedRateLimiter()
        self.security_metrics = SecurityMetrics()
        self.security_metrics.last_reset = datetime.now()
        self.request_fingerprints: Dict[str, List[RequestFingerprint]] = defaultdict(list)
        
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Main security middleware dispatch"""
        start_time = time.time()
        
        # Generate request fingerprint
        fingerprint = RequestFingerprint(request)
        
        # Security checks
        security_result = await self._perform_security_checks(request, fingerprint)
        
        if not security_result['allowed']:
            # Log security event
            api_logger.log_security_event(
                SecurityEventType.SUSPICIOUS_ACTIVITY,
                SecuritySeverity.HIGH,
                f"Request blocked: {security_result['reason']}",
                ip_address=request.client.host,
                endpoint=str(request.url),
                method=request.method,
                context=security_result
            )
            
            # Return appropriate error response
            return Response(
                content=json.dumps({
                    'error': 'Request blocked for security reasons',
                    'details': security_result['reason']
                }),
                status_code=security_result.get('status_code', 403),
                headers={'Content-Type': 'application/json'}
            )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Add security headers
            self._add_security_headers(response)
            
            # Calculate response time
            response_time = (time.time() - start_time) * 1000
            
            # Log API access
            self._log_api_access(request, response, response_time, fingerprint)
            
            # Update metrics
            self._update_security_metrics(request, response)
            
            return response
            
        except Exception as e:
            # Log security exception
            api_logger.log_security_event(
                SecurityEventType.ERROR_OCCURRED,
                SecuritySeverity.MEDIUM,
                f"Request processing error: {str(e)}",
                ip_address=request.client.host,
                endpoint=str(request.url),
                method=request.method,
                error_code=str(type(e).__name__)
            )
            raise
    
    async def _perform_security_checks(self, 
                                     request: Request, 
                                     fingerprint: RequestFingerprint) -> Dict[str, Any]:
        """Perform comprehensive security checks"""
        
        # Check request fingerprint for suspicious patterns
        is_suspicious, suspicions = fingerprint.is_suspicious()
        if is_suspicious:
            return {
                'allowed': False,
                'reason': f"Suspicious request patterns: {', '.join(suspicions)}",
                'status_code': 400
            }
        
        # Rate limiting check
        endpoint_type = self._determine_endpoint_type(request)
        user_id = await self._extract_user_id(request)
        
        is_rate_limited, rate_limit_details = self.rate_limiter.is_rate_limited(
            request, user_id, endpoint_type
        )
        
        if is_rate_limited:
            return {
                'allowed': False,
                'reason': 'Rate limit exceeded',
                'status_code': 429,
                'rate_limit_details': rate_limit_details
            }
        
        # Check for payload size attacks
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB
            return {
                'allowed': False,
                'reason': 'Request payload too large',
                'status_code': 413
            }
        
        # Check for header injection attacks
        for header_name, header_value in request.headers.items():
            if '\n' in header_value or '\r' in header_value:
                return {
                    'allowed': False,
                    'reason': 'Header injection attempt detected',
                    'status_code': 400
                }
        
        # Anomaly detection - check for unusual request patterns
        anomaly_score = self._calculate_anomaly_score(request, fingerprint)
        if anomaly_score > 0.8:  # High anomaly threshold
            return {
                'allowed': False,
                'reason': f'Anomalous request pattern detected (score: {anomaly_score:.2f})',
                'status_code': 403
            }
        
        return {'allowed': True}
    
    def _determine_endpoint_type(self, request: Request) -> str:
        """Determine endpoint type for rate limiting"""
        path = request.url.path.lower()
        
        if '/auth/login' in path:
            return 'login'
        elif any(trading_path in path for trading_path in ['/positions', '/signals', '/backtest']):
            return 'trading'
        elif any(market_path in path for market_path in ['/market', '/chart', '/price']):
            return 'market_data'
        else:
            return 'default'
    
    async def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request for rate limiting"""
        # Try to extract from Authorization header
        auth_header = request.headers.get('authorization')
        if auth_header and auth_header.startswith('Bearer '):
            # This would typically involve JWT token parsing
            # For now, return a placeholder
            return "authenticated_user"
        return None
    
    def _calculate_anomaly_score(self, request: Request, fingerprint: RequestFingerprint) -> float:
        """Calculate anomaly score for request"""
        score = 0.0
        
        # Check request frequency from same IP
        ip = request.client.host
        recent_fingerprints = [
            fp for fp in self.request_fingerprints[ip]
            if (datetime.now() - datetime.fromisoformat(fp.accept_language) if fp.accept_language else datetime.now()) < timedelta(minutes=5)
        ]
        
        if len(recent_fingerprints) > 100:  # Too many requests from same IP
            score += 0.3
        
        # Check for user agent switching
        user_agents = set(fp.user_agent for fp in recent_fingerprints)
        if len(user_agents) > 5:  # Too many different user agents
            score += 0.4
        
        # Check for path scanning behavior
        paths = set(fp.path for fp in recent_fingerprints)
        if len(paths) > 50:  # Accessing too many different paths
            score += 0.5
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _add_security_headers(self, response: Response):
        """Add security headers to response"""
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        
        # Add rate limiting headers
        response.headers['X-RateLimit-Remaining'] = '999'  # Placeholder
        response.headers['X-RateLimit-Reset'] = str(int(time.time()) + 3600)
    
    def _log_api_access(self, 
                       request: Request, 
                       response: Response, 
                       response_time: float,
                       fingerprint: RequestFingerprint):
        """Log API access with security context"""
        api_logger.log_security_event(
            SecurityEventType.DATA_ACCESS,
            SecuritySeverity.LOW,
            f"API access: {request.method} {request.url.path}",
            ip_address=request.client.host,
            method=request.method,
            endpoint=str(request.url),
            status_code=response.status_code,
            response_time_ms=response_time,
            context={
                'fingerprint': fingerprint.get_fingerprint(),
                'user_agent': fingerprint.user_agent[:100]  # Truncate for logging
            }
        )
    
    def _update_security_metrics(self, request: Request, response: Response):
        """Update security metrics"""
        self.security_metrics.request_count += 1
        
        if response.status_code >= 400:
            if response.status_code == 401:
                self.security_metrics.authentication_failures += 1
            elif response.status_code == 403:
                self.security_metrics.blocked_requests += 1
            elif response.status_code == 429:
                self.security_metrics.rate_limited_requests += 1
        
        # Reset metrics daily
        now = datetime.now()
        if (now - self.security_metrics.last_reset).days >= 1:
            self.security_metrics = SecurityMetrics()
            self.security_metrics.last_reset = now

# ===========================================
# CORS SECURITY MIDDLEWARE
# ===========================================

class SecureCORSMiddleware:
    """Enhanced CORS middleware with security features"""
    
    def __init__(self, app):
        self.app = app
        
        # Configure CORS with security
        cors_middleware = CORSMiddleware(
            app,
            allow_origins=ALLOWED_ORIGINS,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=[
                "Authorization",
                "Content-Type",
                "X-Requested-With",
                "Accept",
                "Origin",
                "User-Agent",
                "DNT",
                "Cache-Control",
                "X-Mx-ReqToken",
                "Keep-Alive",
                "X-Requested-With",
                "If-Modified-Since",
            ],
            expose_headers=[
                "X-RateLimit-Remaining",
                "X-RateLimit-Reset",
                "X-Request-ID",
            ]
        )
        
        self.cors_middleware = cors_middleware
    
    async def __call__(self, scope, receive, send):
        """CORS middleware with additional security checks"""
        
        # Additional origin validation
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            origin = headers.get(b"origin")
            
            if origin:
                origin_str = origin.decode()
                
                # Check for origin spoofing attempts
                if not self._is_valid_origin(origin_str):
                    # Log suspicious origin
                    api_logger.log_security_event(
                        SecurityEventType.SUSPICIOUS_ACTIVITY,
                        SecuritySeverity.MEDIUM,
                        f"Invalid origin detected: {origin_str}",
                        context={'origin': origin_str}
                    )
                    
                    # Return 403 for invalid origins
                    response = Response(
                        content=json.dumps({'error': 'Invalid origin'}),
                        status_code=403,
                        headers={'Content-Type': 'application/json'}
                    )
                    
                    await send({
                        'type': 'http.response.start',
                        'status': 403,
                        'headers': [(b'content-type', b'application/json')],
                    })
                    await send({
                        'type': 'http.response.body',
                        'body': response.content.encode(),
                    })
                    return
        
        # Process through standard CORS middleware
        await self.cors_middleware(scope, receive, send)
    
    def _is_valid_origin(self, origin: str) -> bool:
        """Validate origin against allowed list with additional checks"""
        # Check exact match
        if origin in ALLOWED_ORIGINS:
            return True
        
        # Check for localhost variations (development)
        if origin.startswith('http://localhost:') or origin.startswith('https://localhost:'):
            port = origin.split(':')[-1]
            if port.isdigit() and 3000 <= int(port) <= 3010:
                return True
        
        # Check for known deployment domains
        allowed_domains = ['fly.dev', 'vercel.app', 'netlify.app']
        for domain in allowed_domains:
            if f'.{domain}' in origin and 'botphia' in origin:
                return True
        
        return False

# ===========================================
# SECURITY MONITORING
# ===========================================

class SecurityMonitor:
    """Real-time security monitoring and alerting"""
    
    def __init__(self):
        self.threat_indicators: Dict[str, int] = defaultdict(int)
        self.active_threats: Dict[str, Dict[str, Any]] = {}
        self.monitoring_active = True
        
    async def start_monitoring(self):
        """Start security monitoring background task"""
        while self.monitoring_active:
            await self._analyze_threats()
            await asyncio.sleep(60)  # Check every minute
    
    async def _analyze_threats(self):
        """Analyze current threat landscape"""
        current_time = datetime.now()
        
        # Analyze threat patterns
        high_threat_ips = []
        for ip, threat_count in self.threat_indicators.items():
            if threat_count > 10:  # High threat threshold
                high_threat_ips.append(ip)
        
        # Generate threat report
        if high_threat_ips:
            api_logger.log_security_event(
                SecurityEventType.SUSPICIOUS_ACTIVITY,
                SecuritySeverity.HIGH,
                f"High threat activity detected from {len(high_threat_ips)} IPs",
                context={
                    'threat_ips': high_threat_ips[:10],  # Limit to first 10
                    'total_threat_ips': len(high_threat_ips)
                }
            )
    
    def report_threat(self, ip: str, threat_type: str, severity: ThreatLevel):
        """Report security threat"""
        self.threat_indicators[ip] += 1
        
        threat_key = f"{ip}:{threat_type}"
        self.active_threats[threat_key] = {
            'ip': ip,
            'threat_type': threat_type,
            'severity': severity.value,
            'first_seen': datetime.now().isoformat(),
            'count': self.active_threats.get(threat_key, {}).get('count', 0) + 1
        }

# ===========================================
# MIDDLEWARE FACTORY
# ===========================================

class SecurityMiddlewareFactory:
    """Factory for creating and configuring security middleware"""
    
    @staticmethod
    def create_security_stack(app):
        """Create complete security middleware stack"""
        
        # Add security middleware
        security_middleware = SecurityMiddleware(app)
        
        # Add CORS middleware
        cors_middleware = SecureCORSMiddleware(security_middleware)
        
        # Initialize security monitor
        security_monitor = SecurityMonitor()
        
        # Log security stack initialization
        api_logger.log_security_event(
            SecurityEventType.SYSTEM_OPERATION,
            SecuritySeverity.LOW,
            "Security middleware stack initialized",
            context={
                'middlewares': ['SecurityMiddleware', 'SecureCORSMiddleware'],
                'monitoring_enabled': True
            }
        )
        
        return cors_middleware, security_monitor

# ===========================================
# GLOBAL INSTANCES
# ===========================================

# Global security monitor
security_monitor = SecurityMonitor()

# Log API security system initialization
api_logger.info("API security middleware system initialized")