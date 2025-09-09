#!/usr/bin/env python3
"""
Configuración mejorada del sistema de trading con más símbolos y opciones
"""

from typing import List, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class TradingSymbolConfig:
    """Configuración específica por símbolo"""
    symbol: str
    min_confidence: int = 60
    max_positions: int = 1
    risk_multiplier: float = 1.0
    timeframes: List[str] = None
    priority: int = 1  # 1=alta, 2=media, 3=baja
    
    def __post_init__(self):
        if self.timeframes is None:
            self.timeframes = ['15m', '1h', '4h']

class EnhancedTradingConfig:
    """Configuración mejorada del sistema de trading"""
    
    def __init__(self):
        self.setup_symbol_configs()
        self.setup_timeframe_configs()
        self.setup_alert_configs()
    
    def setup_symbol_configs(self):
        """Configuración expandida de símbolos"""
        
        # Símbolos de alta prioridad (mercado principal)
        high_priority = [
            TradingSymbolConfig("BTCUSDT", min_confidence=70, priority=1, risk_multiplier=0.8),
            TradingSymbolConfig("ETHUSDT", min_confidence=65, priority=1, risk_multiplier=0.9),
            TradingSymbolConfig("BNBUSDT", min_confidence=65, priority=1, risk_multiplier=0.9),
        ]
        
        # Símbolos de media prioridad (altcoins establecidos)
        medium_priority = [
            TradingSymbolConfig("ADAUSDT", min_confidence=60, priority=2),
            TradingSymbolConfig("SOLUSDT", min_confidence=60, priority=2),
            TradingSymbolConfig("XRPUSDT", min_confidence=60, priority=2),
            TradingSymbolConfig("DOTUSDT", min_confidence=60, priority=2),
            TradingSymbolConfig("LINKUSDT", min_confidence=60, priority=2),
            TradingSymbolConfig("AVAXUSDT", min_confidence=60, priority=2),
            TradingSymbolConfig("MATICUSDT", min_confidence=60, priority=2),
            TradingSymbolConfig("UNIUSDT", min_confidence=60, priority=2),
        ]
        
        # Símbolos de baja prioridad (más volátiles)
        low_priority = [
            TradingSymbolConfig("DOGEUSDT", min_confidence=55, priority=3, risk_multiplier=1.2),
            TradingSymbolConfig("SHIBUSDT", min_confidence=55, priority=3, risk_multiplier=1.2),
            TradingSymbolConfig("PEPEUSDT", min_confidence=55, priority=3, risk_multiplier=1.3),
            TradingSymbolConfig("FLOKIUSDT", min_confidence=55, priority=3, risk_multiplier=1.3),
            TradingSymbolConfig("WIFUSDT", min_confidence=55, priority=3, risk_multiplier=1.3),
        ]
        
        # Símbolos DeFi (oportunidades emergentes)
        defi_symbols = [
            TradingSymbolConfig("AAVEUSDT", min_confidence=62, priority=2),
            TradingSymbolConfig("COMPUSDT", min_confidence=62, priority=2),
            TradingSymbolConfig("MKRUSDT", min_confidence=62, priority=2),
            TradingSymbolConfig("CRVUSDT", min_confidence=60, priority=2),
        ]
        
        # Símbolos Gaming/Metaverse
        gaming_symbols = [
            TradingSymbolConfig("SANDUSDT", min_confidence=58, priority=3),
            TradingSymbolConfig("MANAUSDT", min_confidence=58, priority=3),
            TradingSymbolConfig("AXSUSDT", min_confidence=58, priority=3),
        ]
        
        # Combinar todas las configuraciones
        self.symbol_configs = {}
        all_symbols = high_priority + medium_priority + low_priority + defi_symbols + gaming_symbols
        
        for config in all_symbols:
            self.symbol_configs[config.symbol] = config
        
        # Lista de símbolos por prioridad
        self.high_priority_symbols = [s.symbol for s in high_priority]
        self.medium_priority_symbols = [s.symbol for s in medium_priority]
        self.low_priority_symbols = [s.symbol for s in low_priority]
        self.defi_symbols = [s.symbol for s in defi_symbols]
        self.gaming_symbols = [s.symbol for s in gaming_symbols]
        
        # Lista completa
        self.all_symbols = list(self.symbol_configs.keys())
        
        logger.info(f"✅ Configurados {len(self.all_symbols)} símbolos de trading")
    
    def setup_timeframe_configs(self):
        """Configuración de timeframes para análisis granular"""
        self.timeframe_configs = {
            # Timeframes para scalping (análisis rápido)
            'scalping': ['1m', '5m', '15m'],
            
            # Timeframes para swing trading (análisis medio)
            'swing': ['15m', '1h', '4h'],
            
            # Timeframes para position trading (análisis largo)
            'position': ['4h', '1d', '1w'],
            
            # Timeframes para análisis completo
            'complete': ['5m', '15m', '1h', '4h', '1d'],
        }
        
        # Configuración por defecto
        self.default_timeframes = self.timeframe_configs['swing']
        
        logger.info(f"✅ Configurados {len(self.timeframe_configs)} sets de timeframes")
    
    def setup_alert_configs(self):
        """Configuración de alertas para señales de alta calidad"""
        self.alert_configs = {
            'high_quality_threshold': 80,  # Señales con score >= 80
            'excellent_threshold': 90,     # Señales con score >= 90
            'multi_philosopher_agreement': 3,  # Cuando 3+ filósofos coinciden
            'priority_symbol_threshold': 75,  # Threshold menor para símbolos de alta prioridad
        }
        
        # Configuración de notificaciones
        self.notification_configs = {
            'console_alerts': True,
            'log_alerts': True,
            'webhook_alerts': False,  # Para futuras integraciones
            'email_alerts': False,    # Para futuras integraciones
        }
        
        logger.info("✅ Configuradas alertas de alta calidad")
    
    def get_symbols_by_priority(self, priority: int = None) -> List[str]:
        """Obtiene símbolos por nivel de prioridad"""
        if priority is None:
            return self.all_symbols
        
        return [symbol for symbol, config in self.symbol_configs.items() 
                if config.priority == priority]
    
    def get_symbol_config(self, symbol: str) -> TradingSymbolConfig:
        """Obtiene configuración específica de un símbolo"""
        return self.symbol_configs.get(symbol, TradingSymbolConfig(symbol))
    
    def get_active_symbols(self, max_symbols: int = None) -> List[str]:
        """Obtiene lista activa de símbolos para trading"""
        # Priorizar símbolos de alta prioridad
        active = self.high_priority_symbols + self.medium_priority_symbols
        
        if max_symbols:
            return active[:max_symbols]
        
        return active
    
    def get_timeframes_for_strategy(self, strategy: str = 'swing') -> List[str]:
        """Obtiene timeframes para una estrategia específica"""
        return self.timeframe_configs.get(strategy, self.default_timeframes)

# Instancia global de configuración
enhanced_config = EnhancedTradingConfig()

def get_enhanced_config() -> EnhancedTradingConfig:
    """Obtiene la configuración mejorada"""
    return enhanced_config

if __name__ == "__main__":
    # Test de la configuración
    config = get_enhanced_config()
    
    print("🎯 CONFIGURACIÓN MEJORADA DE TRADING")
    print("=" * 50)
    print(f"📊 Total símbolos: {len(config.all_symbols)}")
    print(f"🔥 Alta prioridad: {len(config.high_priority_symbols)}")
    print(f"⚡ Media prioridad: {len(config.medium_priority_symbols)}")
    print(f"🎮 Gaming/DeFi: {len(config.gaming_symbols + config.defi_symbols)}")
    print("\n🎯 Símbolos activos principales:")
    for symbol in config.get_active_symbols(10):
        cfg = config.get_symbol_config(symbol)
        print(f"  • {symbol}: min_conf={cfg.min_confidence}%, risk_mult={cfg.risk_multiplier}")
    
    print(f"\n📈 Timeframes por estrategia:")
    for strategy, timeframes in config.timeframe_configs.items():
        print(f"  • {strategy}: {', '.join(timeframes)}")
    
    print(f"\n🚨 Configuración de alertas:")
    for key, value in config.alert_configs.items():
        print(f"  • {key}: {value}")