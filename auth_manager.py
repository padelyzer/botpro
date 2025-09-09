"""
Sistema de Gestión de Autenticación y Sesiones por Usuario
Actualizado para usar SecretManager para seguridad mejorada
"""

import jwt
from datetime import datetime, timedelta
from typing import Dict, Optional
import uuid
import logging
import os

# Import the secure secret manager
from secret_manager import secret_manager

# Configure logging
logger = logging.getLogger(__name__)

class AuthManager:
    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize AuthManager with secure secret management.
        
        Args:
            secret_key: Optional override for JWT secret (uses SecretManager by default)
        """
        # Use SecretManager for secure key retrieval
        self.secret_key = secret_key or secret_manager.get_jwt_secret()
        self.active_sessions = {}  # user_id -> session_data
        
        logger.info("AuthManager initialized with secure secret management")
        
    def create_token(self, user_data: Dict) -> str:
        """
        Crea un token JWT para el usuario con validación de seguridad.
        
        Args:
            user_data: Dictionary containing user information
            
        Returns:
            JWT token string
            
        Raises:
            ValueError: If user_data is invalid
            Exception: If token creation fails
        """
        try:
            # Validate required user data
            required_fields = ['id', 'email', 'name', 'role']
            for field in required_fields:
                if field not in user_data:
                    raise ValueError(f"Missing required field: {field}")
            
            payload = {
                'user_id': user_data['id'],
                'email': user_data['email'],
                'name': user_data['name'],
                'role': user_data['role'],
                'exp': datetime.utcnow() + timedelta(days=7),  # Expira en 7 días
                'iat': datetime.utcnow()
            }
            
            token = jwt.encode(payload, self.secret_key, algorithm='HS256')
            
            # Crear sesión activa
            session_id = str(uuid.uuid4())
            self.active_sessions[user_data['id']] = {
                'user_id': user_data['id'],
                'email': user_data['email'],
                'name': user_data['name'],
                'role': user_data['role'],
                'login_time': datetime.now().isoformat(),
                'last_activity': datetime.now().isoformat(),
                'session_id': session_id
            }
            
            logger.info(f"Token created for user {user_data['email']} (session: {session_id})")
            return token
            
        except Exception as e:
            logger.error(f"Token creation failed for user {user_data.get('email', 'unknown')}: {e}")
            raise
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """
        Verifica y decodifica un token JWT con manejo robusto de errores.
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded payload if valid, None otherwise
        """
        if not token:
            logger.warning("Empty token provided for verification")
            return None
            
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            user_id = payload['user_id']
            
            # Verificar que la sesión siga activa
            if user_id in self.active_sessions:
                # Actualizar última actividad
                self.active_sessions[user_id]['last_activity'] = datetime.now().isoformat()
                logger.debug(f"Token verified for user {user_id}")
                return payload
            else:
                logger.warning(f"No active session found for user {user_id}")
                return None
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token verification failed: expired signature")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token verification failed: invalid token - {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during token verification: {e}")
            return None
    
    def get_user_session(self, user_id: str) -> Optional[Dict]:
        """Obtiene la sesión activa de un usuario"""
        return self.active_sessions.get(user_id)
    
    def logout_user(self, user_id: str) -> bool:
        """
        Cierra la sesión de un usuario con logging de seguridad.
        
        Args:
            user_id: User ID to logout
            
        Returns:
            True if session was found and removed, False otherwise
        """
        if user_id in self.active_sessions:
            session_info = self.active_sessions[user_id]
            del self.active_sessions[user_id]
            logger.info(f"User {session_info.get('email', user_id)} logged out (session: {session_info.get('session_id')})")
            return True
        else:
            logger.warning(f"Logout attempted for non-existent session: {user_id}")
            return False
    
    def get_active_users(self) -> list:
        """Obtiene lista de usuarios activos"""
        return list(self.active_sessions.keys())
    
    def cleanup_expired_sessions(self, max_idle_hours: int = 24):
        """
        Limpia sesiones expiradas con logging y configuración.
        
        Args:
            max_idle_hours: Maximum idle time before session expires
            
        Returns:
            List of expired user IDs
        """
        current_time = datetime.now()
        expired_users = []
        
        for user_id, session in self.active_sessions.items():
            try:
                last_activity = datetime.fromisoformat(session['last_activity'])
                idle_seconds = (current_time - last_activity).total_seconds()
                
                # Check if session has exceeded idle time
                if idle_seconds > max_idle_hours * 3600:
                    expired_users.append(user_id)
                    logger.info(f"Session expired for user {session.get('email', user_id)} "
                              f"(idle for {idle_seconds/3600:.1f} hours)")
                              
            except Exception as e:
                logger.error(f"Error checking session expiry for user {user_id}: {e}")
                expired_users.append(user_id)  # Remove problematic sessions
        
        # Remove expired sessions
        for user_id in expired_users:
            try:
                del self.active_sessions[user_id]
            except KeyError:
                pass  # Already removed
        
        if expired_users:
            logger.info(f"Cleaned up {len(expired_users)} expired sessions")
        
        return expired_users

# Instancia global del gestor de autenticación con manejo de errores
try:
    auth_manager = AuthManager()
    logger.info("Global AuthManager instance created successfully")
except Exception as e:
    logger.critical(f"Failed to create AuthManager instance: {e}")
    # Create fallback instance with environment variable or generated secret
    import secrets
    fallback_secret = os.getenv("JWT_FALLBACK_SECRET", secrets.token_urlsafe(32))
    auth_manager = AuthManager(secret_key=fallback_secret)
    logger.warning("Using fallback AuthManager with generated secret")