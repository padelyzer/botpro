"""
Configuración centralizada y segura para botphIA
IMPORTANTE: Usar variables de entorno en producción
"""

import os
from typing import List, Dict
from pathlib import Path

# Intentar cargar dotenv si está disponible
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️ python-dotenv no instalado. Usando variables de entorno del sistema.")

class Settings:
    """Configuración central del sistema"""
    
    # === SEGURIDAD ===
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_DAYS: int = int(os.getenv("JWT_EXPIRATION_DAYS", "7"))
    
    # === BASE DE DATOS ===
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "trading_bot.db")
    DATABASE_BACKUP_PATH: str = os.getenv("DATABASE_BACKUP_PATH", "backups/")
    
    # === CORS ===
    ALLOWED_ORIGINS: List[str] = os.getenv(
        "ALLOWED_ORIGINS", 
        "http://localhost:5173,http://localhost:5174,http://localhost:3000"
    ).split(",")
    
    # === BINANCE API ===
    BINANCE_API_KEY: str = os.getenv("BINANCE_API_KEY", "")
    BINANCE_SECRET_KEY: str = os.getenv("BINANCE_SECRET_KEY", "")
    BINANCE_TESTNET: bool = os.getenv("BINANCE_TESTNET", "false").lower() == "true"
    
    # === AMBIENTE ===
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    IS_PRODUCTION: bool = ENVIRONMENT == "production"
    IS_DEVELOPMENT: bool = ENVIRONMENT == "development"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # === LOGGING ===
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO" if IS_PRODUCTION else "DEBUG")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/botphia.log")
    
    # === LÍMITES ===
    MAX_POSITIONS_PER_USER: int = int(os.getenv("MAX_POSITIONS_PER_USER", "10"))
    MAX_DAILY_TRADES: int = int(os.getenv("MAX_DAILY_TRADES", "50"))
    MIN_TRADE_AMOUNT: float = float(os.getenv("MIN_TRADE_AMOUNT", "10"))
    
    # === RATE LIMITING ===
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # segundos
    
    # === USUARIOS DEMO (Solo desarrollo) ===
    DEMO_USERS: Dict = {}
    if IS_DEVELOPMENT:
        # En desarrollo, usar usuarios demo
        # En producción, esto debe venir de una BD real
        DEMO_USERS = {
            "aurbaez@botphia.com": {
                "id": "user_1",
                "password": os.getenv("DEMO_PASSWORD", "Profitz2025!"),
                "name": "Aurora Báez",
                "role": "admin"
            },
            "jalcazar@botphia.com": {
                "id": "user_2", 
                "password": os.getenv("DEMO_PASSWORD", "Profitz2025!"),
                "name": "Jorge Alcázar",
                "role": "trader"
            },
            "antonio@botphia.com": {
                "id": "user_3",
                "password": "Binance2025!",
                "name": "Antonio",
                "role": "trader"
            },
            "jaime@botphia.com": {
                "id": "user_4",
                "password": "Binance2025!",
                "name": "Jaime",
                "role": "trader"
            }
        }
    
    @classmethod
    def validate(cls) -> bool:
        """Valida que la configuración crítica esté presente"""
        errors = []
        
        # Validaciones críticas para producción
        if cls.IS_PRODUCTION:
            if not cls.JWT_SECRET_KEY:
                errors.append("JWT_SECRET_KEY no configurado")
            
            if cls.JWT_SECRET_KEY == "botphia_secret_key_2025":
                errors.append("JWT_SECRET_KEY usa valor por defecto inseguro")
            
            if not cls.BINANCE_API_KEY:
                errors.append("BINANCE_API_KEY no configurado")
            
            if "localhost" in str(cls.ALLOWED_ORIGINS):
                errors.append("ALLOWED_ORIGINS contiene localhost en producción")
            
            if cls.DEMO_USERS:
                errors.append("DEMO_USERS activos en producción")
        
        # Validaciones generales
        if not Path(cls.DATABASE_PATH).parent.exists():
            errors.append(f"Directorio de BD no existe: {Path(cls.DATABASE_PATH).parent}")
        
        if errors:
            print("❌ ERRORES DE CONFIGURACIÓN:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        return True
    
    @classmethod
    def get_safe_config(cls) -> dict:
        """Retorna configuración segura para el frontend (sin secrets)"""
        return {
            "environment": cls.ENVIRONMENT,
            "is_production": cls.IS_PRODUCTION,
            "allowed_origins": cls.ALLOWED_ORIGINS,
            "max_positions": cls.MAX_POSITIONS_PER_USER,
            "max_daily_trades": cls.MAX_DAILY_TRADES,
            "min_trade_amount": cls.MIN_TRADE_AMOUNT,
            "rate_limit_enabled": cls.RATE_LIMIT_ENABLED,
            "binance_testnet": cls.BINANCE_TESTNET
        }

# Instancia global
settings = Settings()

# Validar configuración al importar
if settings.IS_PRODUCTION:
    if not settings.validate():
        raise ValueError("❌ Configuración inválida para producción")
else:
    # En desarrollo, solo advertir
    if not settings.validate():
        print("⚠️ Configuración con advertencias (modo desarrollo)")

# Exportar configuración
__all__ = ['settings', 'Settings']