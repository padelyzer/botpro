"""
BotPhia Secure Secret Management System
======================================

Critical security module for managing secrets, API keys, and sensitive configuration.
This module provides secure loading and validation of environment variables with encryption support.

Author: Senior Backend Developer
Phase: 1 - Days 1-2
"""

import os
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass
from cryptography.fernet import Fernet
from pathlib import Path
import base64
import hashlib
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SecretConfig:
    """Configuration class for secret management"""
    env_file: str = ".env"
    encryption_enabled: bool = False
    validate_secrets: bool = True
    log_access: bool = True

class SecretValidationError(Exception):
    """Raised when secret validation fails"""
    pass

class SecretNotFoundError(Exception):
    """Raised when a required secret is not found"""
    pass

class SecretManager:
    """
    Secure secret management system for BotPhia trading platform.
    
    Features:
    - Environment variable loading with validation
    - Optional encryption/decryption of sensitive values
    - Secret validation and format checking
    - Access logging for security audit
    - Fallback and default value support
    """
    
    def __init__(self, config: Optional[SecretConfig] = None):
        """
        Initialize SecretManager with configuration.
        
        Args:
            config: SecretConfig instance or None for defaults
        """
        self.config = config or SecretConfig()
        self._secrets_cache: Dict[str, Any] = {}
        self._access_log: Dict[str, int] = {}
        self._cipher: Optional[Fernet] = None
        
        # Load environment file
        self._load_environment()
        
        # Initialize encryption if enabled
        if self.config.encryption_enabled:
            self._initialize_encryption()
        
        logger.info("SecretManager initialized successfully")
    
    def _load_environment(self) -> None:
        """Load environment variables from .env file"""
        env_path = Path(self.config.env_file)
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"Loaded environment from {env_path}")
        else:
            logger.warning(f"Environment file {env_path} not found, using system environment")
    
    def _initialize_encryption(self) -> None:
        """Initialize Fernet encryption cipher"""
        try:
            encryption_key = os.getenv('ENCRYPTION_KEY')
            if not encryption_key:
                # Generate a new key if none exists
                encryption_key = Fernet.generate_key().decode()
                logger.warning("No ENCRYPTION_KEY found, generated new key (save this!)")
                logger.warning(f"Generated key: {encryption_key}")
            
            # Convert string key to bytes if needed
            if isinstance(encryption_key, str):
                encryption_key = encryption_key.encode()
            
            self._cipher = Fernet(encryption_key)
            logger.info("Encryption initialized successfully")
        
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise SecretValidationError(f"Encryption initialization failed: {e}")
    
    def get_secret(self, key: str, default: Any = None, required: bool = False, 
                   encrypted: bool = False, validate_func: Optional[callable] = None) -> Any:
        """
        Get a secret value with comprehensive validation and logging.
        
        Args:
            key: Environment variable name
            default: Default value if not found
            required: If True, raises exception when not found
            encrypted: If True, attempts to decrypt the value
            validate_func: Optional validation function
            
        Returns:
            Secret value (decrypted if applicable)
            
        Raises:
            SecretNotFoundError: When required secret is not found
            SecretValidationError: When validation fails
        """
        # Log access for security audit
        if self.config.log_access:
            self._access_log[key] = self._access_log.get(key, 0) + 1
        
        # Check cache first
        cache_key = f"{key}_{'enc' if encrypted else 'raw'}"
        if cache_key in self._secrets_cache:
            return self._secrets_cache[cache_key]
        
        # Get from environment
        raw_value = os.getenv(key, default)
        
        # Handle required secrets
        if required and raw_value is None:
            logger.error(f"Required secret '{key}' not found")
            raise SecretNotFoundError(f"Required secret '{key}' not found")
        
        if raw_value is None:
            return default
        
        # Handle encrypted secrets
        if encrypted and self._cipher:
            try:
                # Assume base64 encoded encrypted value
                encrypted_bytes = base64.b64decode(raw_value.encode())
                raw_value = self._cipher.decrypt(encrypted_bytes).decode()
                logger.debug(f"Successfully decrypted secret '{key}'")
            except Exception as e:
                logger.error(f"Failed to decrypt secret '{key}': {e}")
                raise SecretValidationError(f"Failed to decrypt secret '{key}': {e}")
        
        # Validate secret if validator provided
        if validate_func and self.config.validate_secrets:
            try:
                if not validate_func(raw_value):
                    raise SecretValidationError(f"Secret '{key}' failed validation")
            except Exception as e:
                logger.error(f"Secret validation failed for '{key}': {e}")
                raise SecretValidationError(f"Secret validation failed for '{key}': {e}")
        
        # Cache the result
        self._secrets_cache[cache_key] = raw_value
        logger.debug(f"Secret '{key}' loaded successfully")
        
        return raw_value
    
    def get_jwt_secret(self) -> str:
        """Get JWT secret key with validation"""
        def validate_jwt_key(key: str) -> bool:
            return len(key) >= 32 and not key.startswith("default")
        
        return self.get_secret(
            'JWT_SECRET_KEY',
            default='botphia_secure_jwt_key_2025_change_in_production',
            required=True,
            validate_func=validate_jwt_key
        )
    
    def get_database_url(self) -> str:
        """Get database connection URL"""
        # Try DATABASE_URL first (production), then fall back to sqlite
        db_url = self.get_secret('DATABASE_URL')
        if db_url:
            return db_url
        
        # Fallback to SQLite path
        db_path = self.get_secret('DATABASE_PATH', default='trading_bot.db')
        return f"sqlite:///{db_path}"
    
    def get_binance_credentials(self) -> Dict[str, str]:
        """Get Binance API credentials with validation"""
        def validate_api_key(key: str) -> bool:
            return len(key) >= 64 if key else True  # Allow empty for demo mode
        
        def validate_secret_key(key: str) -> bool:
            return len(key) >= 64 if key else True  # Allow empty for demo mode
        
        api_key = self.get_secret(
            'BINANCE_API_KEY',
            default='',
            validate_func=validate_api_key
        )
        
        secret_key = self.get_secret(
            'BINANCE_SECRET_KEY',
            default='',
            encrypted=True,  # Secret keys should be encrypted
            validate_func=validate_secret_key
        )
        
        testnet = self.get_secret('BINANCE_TESTNET', default='true').lower() == 'true'
        
        return {
            'api_key': api_key,
            'secret_key': secret_key,
            'testnet': testnet
        }
    
    def get_cors_origins(self) -> list:
        """Get CORS allowed origins as a list"""
        origins = self.get_secret(
            'ALLOWED_ORIGINS',
            default='http://localhost:3000,http://localhost:8000'
        )
        return [origin.strip() for origin in origins.split(',') if origin.strip()]
    
    def get_environment_config(self) -> Dict[str, Any]:
        """Get general environment configuration"""
        return {
            'environment': self.get_secret('ENVIRONMENT', default='development'),
            'debug': self.get_secret('DEBUG', default='false').lower() == 'true',
            'rate_limit_enabled': self.get_secret('RATE_LIMIT_ENABLED', default='true').lower() == 'true',
            'max_positions_per_user': int(self.get_secret('MAX_POSITIONS_PER_USER', default='10')),
            'max_daily_trades': int(self.get_secret('MAX_DAILY_TRADES', default='50'))
        }
    
    def encrypt_secret(self, value: str) -> str:
        """
        Encrypt a secret value for storage.
        
        Args:
            value: Plain text value to encrypt
            
        Returns:
            Base64 encoded encrypted value
            
        Raises:
            SecretValidationError: If encryption is not initialized
        """
        if not self._cipher:
            raise SecretValidationError("Encryption not initialized")
        
        try:
            encrypted_bytes = self._cipher.encrypt(value.encode())
            return base64.b64encode(encrypted_bytes).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt secret: {e}")
            raise SecretValidationError(f"Encryption failed: {e}")
    
    def validate_all_required_secrets(self) -> Dict[str, bool]:
        """
        Validate all critical secrets are present and valid.
        
        Returns:
            Dict mapping secret names to validation status
        """
        validation_results = {}
        
        # Test JWT secret
        try:
            self.get_jwt_secret()
            validation_results['JWT_SECRET_KEY'] = True
        except Exception as e:
            validation_results['JWT_SECRET_KEY'] = False
            logger.error(f"JWT secret validation failed: {e}")
        
        # Test database connection
        try:
            db_url = self.get_database_url()
            validation_results['DATABASE'] = bool(db_url)
        except Exception as e:
            validation_results['DATABASE'] = False
            logger.error(f"Database config validation failed: {e}")
        
        # Test Binance credentials (non-critical)
        try:
            creds = self.get_binance_credentials()
            validation_results['BINANCE_API'] = bool(creds['api_key']) or creds['testnet']
        except Exception as e:
            validation_results['BINANCE_API'] = False
            logger.error(f"Binance credentials validation failed: {e}")
        
        return validation_results
    
    def get_security_audit_report(self) -> Dict[str, Any]:
        """
        Generate security audit report.
        
        Returns:
            Dictionary containing security metrics and access logs
        """
        return {
            'secrets_accessed': dict(self._access_log),
            'total_secrets_cached': len(self._secrets_cache),
            'encryption_enabled': self.config.encryption_enabled,
            'validation_enabled': self.config.validate_secrets,
            'validation_results': self.validate_all_required_secrets()
        }
    
    def clear_cache(self) -> None:
        """Clear the secrets cache (useful for testing or rotation)"""
        self._secrets_cache.clear()
        logger.info("Secrets cache cleared")
    
    def __del__(self):
        """Cleanup sensitive data on destruction"""
        if hasattr(self, '_secrets_cache'):
            self._secrets_cache.clear()
        if hasattr(self, '_cipher'):
            self._cipher = None

# Global instance for application use
secret_manager = SecretManager()

# Convenience functions for common secrets
def get_jwt_secret() -> str:
    """Get JWT secret - convenience function"""
    return secret_manager.get_jwt_secret()

def get_database_url() -> str:
    """Get database URL - convenience function"""
    return secret_manager.get_database_url()

def get_binance_credentials() -> Dict[str, str]:
    """Get Binance credentials - convenience function"""
    return secret_manager.get_binance_credentials()