#!/usr/bin/env python3
"""
TRADING CONFIG - Configuración global del sistema de trading
"""

# ========================================
# CONFIGURACIÓN DE INDICADORES TÉCNICOS
# ========================================

# RSI Configuration
RSI_CONFIG = {
    'period': 14,                  # Periodo estándar RSI
    'overbought': 73,              # Nivel de sobrecompra (antes 70)
    'oversold': 28,                # Nivel de sobreventa (antes 30)
    'neutral_high': 60,            # Zona neutral alta
    'neutral_low': 40,             # Zona neutral baja
    'extreme_overbought': 80,      # Sobrecompra extrema
    'extreme_oversold': 20         # Sobreventa extrema
}

# Moving Averages Configuration
MA_CONFIG = {
    'sma_fast': 20,
    'sma_slow': 50,
    'ema_fast': 9,
    'ema_medium': 21,
    'ema_slow': 50,
    'sma_long': 200
}

# Bollinger Bands Configuration
BB_CONFIG = {
    'period': 20,
    'std_dev': 2.0,
    'extreme_upper': 0.95,  # Precio en 95% del rango BB
    'extreme_lower': 0.05   # Precio en 5% del rango BB
}

# ATR Configuration
ATR_CONFIG = {
    'period': 14,
    'stop_loss_multiplier': 2.0,
    'take_profit_multiplier': 3.0
}

# MACD Configuration
MACD_CONFIG = {
    'fast_period': 12,
    'slow_period': 26,
    'signal_period': 9
}

# ========================================
# CONFIGURACIÓN DE GESTIÓN DE RIESGO
# ========================================

RISK_CONFIG = {
    'max_risk_per_trade': 2.0,     # % máximo del capital por operación
    'max_open_trades': 3,           # Máximo de operaciones abiertas
    'min_risk_reward': 1.5,         # R:R mínimo aceptable
    'default_leverage': 1,          # Apalancamiento por defecto
    'max_leverage': 20              # Apalancamiento máximo permitido
}

# ========================================
# CONFIGURACIÓN DE SEÑALES
# ========================================

SIGNAL_CONFIG = {
    'min_confidence': 60,           # Confianza mínima para señal válida
    'high_confidence': 80,          # Umbral de alta confianza
    'volume_confirmation': 1.2,     # Volumen mínimo vs promedio
    'trend_alignment_required': False,  # Requerir alineación con tendencia
    'multi_timeframe_confirmation': True  # Requerir confirmación multi-TF
}

# ========================================
# CONFIGURACIÓN POR TIMEFRAME
# ========================================

TIMEFRAME_CONFIG = {
    '5m': {
        'bars_required': 100,
        'max_leverage': 5,
        'min_confidence': 65,
        'rsi_overbought': 75,  # Más estricto en TF cortos
        'rsi_oversold': 25
    },
    '15m': {
        'bars_required': 100,
        'max_leverage': 8,
        'min_confidence': 60,
        'rsi_overbought': 73,
        'rsi_oversold': 28
    },
    '1h': {
        'bars_required': 100,
        'max_leverage': 10,
        'min_confidence': 60,
        'rsi_overbought': 73,
        'rsi_oversold': 28
    },
    '4h': {
        'bars_required': 100,
        'max_leverage': 15,
        'min_confidence': 55,
        'rsi_overbought': 73,
        'rsi_oversold': 28
    }
}

# ========================================
# CONFIGURACIÓN DE PARES
# ========================================

TRADING_PAIRS_CONFIG = {
    'BTCUSDT': {
        'min_volume': 1000000,
        'max_volatility': 10,
        'preferred_timeframes': ['1h', '4h']
    },
    'ETHUSDT': {
        'min_volume': 500000,
        'max_volatility': 15,
        'preferred_timeframes': ['1h', '4h']
    },
    'default': {
        'min_volume': 100000,
        'max_volatility': 20,
        'preferred_timeframes': ['15m', '1h', '4h']
    }
}

# ========================================
# FUNCIONES HELPER
# ========================================

def get_rsi_levels(timeframe: str = '1h') -> dict:
    """Obtiene los niveles RSI para un timeframe específico"""
    if timeframe in TIMEFRAME_CONFIG:
        return {
            'overbought': TIMEFRAME_CONFIG[timeframe].get('rsi_overbought', RSI_CONFIG['overbought']),
            'oversold': TIMEFRAME_CONFIG[timeframe].get('rsi_oversold', RSI_CONFIG['oversold'])
        }
    return {
        'overbought': RSI_CONFIG['overbought'],
        'oversold': RSI_CONFIG['oversold']
    }

def get_leverage_limits(timeframe: str = '1h') -> int:
    """Obtiene el apalancamiento máximo para un timeframe"""
    if timeframe in TIMEFRAME_CONFIG:
        return TIMEFRAME_CONFIG[timeframe]['max_leverage']
    return RISK_CONFIG['default_leverage']

def is_rsi_overbought(rsi_value: float, timeframe: str = '1h') -> bool:
    """Verifica si el RSI está en sobrecompra"""
    levels = get_rsi_levels(timeframe)
    return rsi_value > levels['overbought']

def is_rsi_oversold(rsi_value: float, timeframe: str = '1h') -> bool:
    """Verifica si el RSI está en sobreventa"""
    levels = get_rsi_levels(timeframe)
    return rsi_value < levels['oversold']

# ========================================
# EXPORT
# ========================================

__all__ = [
    'RSI_CONFIG',
    'MA_CONFIG',
    'BB_CONFIG',
    'ATR_CONFIG',
    'MACD_CONFIG',
    'RISK_CONFIG',
    'SIGNAL_CONFIG',
    'TIMEFRAME_CONFIG',
    'TRADING_PAIRS_CONFIG',
    'get_rsi_levels',
    'get_leverage_limits',
    'is_rsi_overbought',
    'is_rsi_oversold'
]