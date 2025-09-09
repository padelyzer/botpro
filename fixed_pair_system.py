#!/usr/bin/env python3
"""
Sistema con Configuraciones Corregidas
Aplica todas las soluciones identificadas para cada par problemático
"""

import asyncio
import httpx
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuraciones CORREGIDAS basadas en el análisis
FIXED_PAIR_CONFIG = {
    'BTCUSDT': {
        # PROBLEMA: BTC 15m/1h con demasiado ruido
        # SOLUCIÓN: Filtros más estrictos, solo tendencias muy fuertes
        '15m': {
            'min_change_pct': 1.2,           # Reducido para más oportunidades
            'rsi_oversold': 40, 'rsi_overbought': 60,  # Menos extremo
            'min_volume_ratio': 1.5,         # AUMENTADO: Solo volumen excepcional
            'max_volatility': 7,             # Reducido para menos ruido
            'atr_multiplier': 2.2,           # Aumentado para mejores stops
            'min_confidence': 65,            # Aumentado para mejor calidad
            'trend_filter_strength': 1.2,   # AUMENTADO: Tendencia más fuerte
            'use_trend_following': True,
            'macd_threshold': 0.1,           # NUEVO: MACD más estricto
            'trend_strength_min': 2.0        # NUEVO: EMA20-EMA50 > 2%
        },
        '1h': {
            'min_change_pct': 1.8,
            'rsi_oversold': 38, 'rsi_overbought': 62,
            'min_volume_ratio': 1.3,         # AUMENTADO
            'max_volatility': 8,
            'atr_multiplier': 2.5,           # AUMENTADO para mejores stops
            'min_confidence': 62,
            'trend_filter_strength': 1.5,   # AUMENTADO
            'use_trend_following': True,
            'macd_threshold': 0.08,
            'trend_strength_min': 1.5
        },
        '4h': {
            # Ya funcionaba bien, solo ajuste menor
            'min_change_pct': 2.5, 'rsi_oversold': 32, 'rsi_overbought': 68,
            'min_volume_ratio': 1.1, 'max_volatility': 10, 'atr_multiplier': 2.2,
            'min_confidence': 55, 'trend_filter_strength': 1.2, 'use_trend_following': True
        }
    },
    
    'ETHUSDT': {
        # PROBLEMA: ETH Mean Reversion con stops muy ajustados
        # SOLUCIÓN: ATR más amplio, RSI más extremo, BB más estricto
        '15m': {
            'min_change_pct': 2.0,
            'rsi_oversold': 25, 'rsi_overbought': 75,  # MÁS EXTREMO
            'min_volume_ratio': 1.2,         # Aumentado para confirmación
            'max_volatility': 11,
            'atr_multiplier': 3.0,           # AUMENTADO de 2.0 a 3.0
            'min_confidence': 60,            # Aumentado
            'trend_filter_strength': 0.4,   # Reducido para más oportunidades
            'use_mean_reversion': True,
            'bb_extreme_threshold': 0.15,   # NUEVO: BB más estricto <0.15 y >0.85
            'rsi_confirmation': True         # NUEVO: Confirmar con RSI extremo
        },
        '1h': {
            'min_change_pct': 2.5,
            'rsi_oversold': 27, 'rsi_overbought': 73,  # MÁS EXTREMO
            'min_volume_ratio': 1.25,
            'max_volatility': 12,
            'atr_multiplier': 3.2,           # AUMENTADO de 2.2 a 3.2
            'min_confidence': 62,
            'trend_filter_strength': 0.6,
            'use_mean_reversion': True,
            'bb_extreme_threshold': 0.15,
            'rsi_confirmation': True
        },
        '4h': {
            'min_change_pct': 3.0,
            'rsi_oversold': 25, 'rsi_overbought': 75,  # MÁS EXTREMO
            'min_volume_ratio': 1.3,
            'max_volatility': 13,
            'atr_multiplier': 3.5,           # AUMENTADO de 2.5 a 3.5
            'min_confidence': 65,
            'trend_filter_strength': 0.8,
            'use_mean_reversion': True,
            'bb_extreme_threshold': 0.15,
            'rsi_confirmation': True
        }
    },
    
    'SOLUSDT': {
        # PROBLEMA: SOL 15m no genera trades
        # SOLUCIÓN: Filtros más relajados
        '15m': {
            'min_change_pct': 2.0,           # REDUCIDO de 2.5 a 2.0
            'rsi_oversold': 35, 'rsi_overbought': 65,  # MENOS EXTREMO
            'min_volume_ratio': 0.9,         # REDUCIDO de 1.0 a 0.9
            'max_volatility': 18,            # AUMENTADO para más oportunidades
            'atr_multiplier': 2.1,           # Reducido ligeramente
            'min_confidence': 50,            # REDUCIDO de 52 a 50
            'trend_filter_strength': 0.3,   # MÁS RELAJADO
            'use_momentum': True
        },
        '1h': {
            # Ya funcionaba bien (66.7% WR)
            'min_change_pct': 3.0, 'rsi_oversold': 30, 'rsi_overbought': 70,
            'min_volume_ratio': 1.05, 'max_volatility': 16, 'atr_multiplier': 2.5,
            'min_confidence': 55, 'trend_filter_strength': 0.5, 'use_momentum': True
        },
        '4h': {
            # Mejorar el 50% WR
            'min_change_pct': 3.2,           # Ligeramente reducido
            'rsi_oversold': 30, 'rsi_overbought': 70,
            'min_volume_ratio': 1.0,         # REDUCIDO para más trades
            'max_volatility': 17,
            'atr_multiplier': 2.6,           # Reducido ligeramente
            'min_confidence': 56,            # Reducido
            'trend_filter_strength': 0.6,   # Reducido
            'use_momentum': True
        }
    },
    
    'BNBUSDT': {
        # Ya funciona bien, solo ajuste menor en 15m
        '15m': {
            'min_change_pct': 1.6,           # REDUCIDO para más oportunidades
            'rsi_oversold': 38, 'rsi_overbought': 62,  # Menos extremo
            'min_volume_ratio': 1.1,         # Reducido
            'max_volatility': 10,            # Aumentado
            'atr_multiplier': 2.1,           # Aumentado
            'min_confidence': 55,            # Reducido
            'trend_filter_strength': 0.6,   # Reducido
            'use_range_trading': True
        },
        '1h': {
            # Excelente (61.5% WR, +58.31%), mantener
            'min_change_pct': 2.2, 'rsi_oversold': 34, 'rsi_overbought': 66,
            'min_volume_ratio': 1.2, 'max_volatility': 10, 'atr_multiplier': 2.1,
            'min_confidence': 60, 'trend_filter_strength': 0.9, 'use_range_trading': True
        },
        '4h': {
            # Bueno (66.7% WR), mantener
            'min_change_pct': 2.8, 'rsi_oversold': 31, 'rsi_overbought': 69,
            'min_volume_ratio': 1.25, 'max_volatility': 11, 'atr_multiplier': 2.3,
            'min_confidence': 62, 'trend_filter_strength': 1.1, 'use_range_trading': True
        }
    },
    
    'ADAUSDT': {
        # PROBLEMA: ADA 15m/1h win rate bajo
        # SOLUCIÓN: Similar a ETH, ATR más amplio
        '15m': {
            'min_change_pct': 2.0,           # Reducido ligeramente
            'rsi_oversold': 28, 'rsi_overbought': 72,  # MÁS EXTREMO
            'min_volume_ratio': 1.2,         # Aumentado para confirmación
            'max_volatility': 14,            # Aumentado
            'atr_multiplier': 2.8,           # AUMENTADO de 2.1 a 2.8
            'min_confidence': 58,            # Aumentado
            'trend_filter_strength': 0.4,   # Reducido
            'use_mean_reversion': True,
            'bb_extreme_threshold': 0.15,   # Nuevo
            'rsi_confirmation': True         # Nuevo
        },
        '1h': {
            'min_change_pct': 2.5,           # Reducido
            'rsi_oversold': 30, 'rsi_overbought': 70,  # MÁS EXTREMO
            'min_volume_ratio': 1.25,        # Aumentado
            'max_volatility': 15,            # Aumentado
            'atr_multiplier': 3.0,           # AUMENTADO de 2.3 a 3.0
            'min_confidence': 60,            # Aumentado
            'trend_filter_strength': 0.6,   # Reducido
            'use_mean_reversion': True,
            'bb_extreme_threshold': 0.15,
            'rsi_confirmation': True
        },
        '4h': {
            # Ya funciona bien (55.6% WR, +38.34%), solo ajuste menor
            'min_change_pct': 3.0,           # Reducido ligeramente
            'rsi_oversold': 28, 'rsi_overbought': 72,
            'min_volume_ratio': 1.15,        # Reducido para más trades
            'max_volatility': 15,
            'atr_multiplier': 2.6,
            'min_confidence': 57,            # Reducido
            'trend_filter_strength': 0.8,   # Reducido
            'use_mean_reversion': True
        }
    },
    
    'DOGEUSDT': {
        # Ya funciona excelente, mantener configuraciones
        '15m': {
            'min_change_pct': 3.0, 'rsi_oversold': 30, 'rsi_overbought': 70,
            'min_volume_ratio': 0.9, 'max_volatility': 20, 'atr_multiplier': 3.0,
            'min_confidence': 50, 'trend_filter_strength': 0.3, 'use_momentum': True, 'extra_caution': True
        },
        '1h': {
            'min_change_pct': 3.5, 'rsi_oversold': 28, 'rsi_overbought': 72,
            'min_volume_ratio': 0.95, 'max_volatility': 22, 'atr_multiplier': 3.2,
            'min_confidence': 52, 'trend_filter_strength': 0.4, 'use_momentum': True, 'extra_caution': True
        },
        '4h': {
            'min_change_pct': 4.0, 'rsi_oversold': 25, 'rsi_overbought': 75,
            'min_volume_ratio': 1.0, 'max_volatility': 25, 'atr_multiplier': 3.5,
            'min_confidence': 55, 'trend_filter_strength': 0.5, 'use_momentum': True, 'extra_caution': True
        }
    }
}

INITIAL_CAPITAL = 220.0
MAX_RISK_PER_TRADE = 0.02
DEFAULT_LEVERAGE = 3

class FixedPairSignalGenerator:
    """Generador con configuraciones corregidas"""
    
    @staticmethod
    async def fetch_market_data(symbol: str, interval: str) -> Optional[pd.DataFrame]:
        """Obtiene datos de mercado"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    'https://fapi.binance.com/fapi/v1/klines',
                    params={'symbol': symbol, 'interval': interval, 'limit': 100}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    df = pd.DataFrame(data, columns=[
                        'timestamp', 'open', 'high', 'low', 'close',
                        'volume', 'close_time', 'quote_volume', 'trades',
                        'taker_buy_volume', 'taker_buy_quote', 'ignore'
                    ])
                    
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        df[col] = df[col].astype(float)
                    
                    return df
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
        
        return None
    
    @staticmethod
    def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores mejorados"""
        
        # Básicos
        df['change_pct'] = df['close'].pct_change() * 100
        df['range_position'] = (df['close'] - df['low']) / (df['high'] - df['low'] + 0.00001)
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        df['atr'] = ranges.max(axis=1).rolling(14).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 0.00001)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # EMAs
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        # MACD mejorado
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands mejorados
        df['bb_middle'] = df['close'].rolling(20).mean()
        df['bb_std'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * 2)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * 2)
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'] + 0.00001)
        
        # Volatilidad y volumen
        df['volatility'] = ((df['high'] - df['low']) / df['close']) * 100
        df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        df['volume_trend'] = df['volume'].rolling(5).mean() / df['volume'].rolling(20).mean()
        
        # Tendencia mejorada
        df['trend_strength'] = abs(df['ema_20'] - df['ema_50']) / df['close'] * 100
        df['is_uptrend'] = df['ema_20'] > df['ema_50']
        
        return df
    
    @staticmethod
    async def generate_signal(symbol: str, interval: str) -> Optional[Dict]:
        """Genera señales con configuraciones corregidas"""
        
        config = FIXED_PAIR_CONFIG[symbol][interval]
        
        df = await FixedPairSignalGenerator.fetch_market_data(symbol, interval)
        if df is None or len(df) < 50:
            return None
        
        df = FixedPairSignalGenerator.calculate_indicators(df)
        
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        if pd.isna(last['atr']) or pd.isna(last['rsi']):
            return None
        
        # Filtro de volatilidad
        if last['volatility'] > config['max_volatility']:
            return None
        
        signal = None
        confidence = 0
        
        # TREND FOLLOWING MEJORADO (BTC)
        if config.get('use_trend_following'):
            # Verificar tendencia más fuerte
            trend_strength_ok = True
            if 'trend_strength_min' in config:
                trend_strength_ok = last['trend_strength'] > config['trend_strength_min']
            
            # Verificar MACD más estricto
            macd_ok = True
            if 'macd_threshold' in config:
                if last['is_uptrend']:
                    macd_ok = last['macd_histogram'] > config['macd_threshold']
                else:
                    macd_ok = last['macd_histogram'] < -config['macd_threshold']
            
            if (last['is_uptrend'] and trend_strength_ok and macd_ok and
                last['change_pct'] > config['min_change_pct'] * 0.5 and
                last['rsi'] < config['rsi_overbought'] and last['rsi'] > 45 and
                last['volume_ratio'] > config['min_volume_ratio']):
                
                confidence = config['min_confidence'] + 10
                if last['macd_histogram'] > prev['macd_histogram']:
                    confidence += 5
                if last['volume_ratio'] > config['min_volume_ratio'] * 1.2:
                    confidence += 5
                
                signal = {'type': 'LONG', 'strategy': 'TREND_FOLLOWING_IMPROVED', 'confidence': min(confidence, 85)}
            
            elif (not last['is_uptrend'] and trend_strength_ok and macd_ok and
                  last['change_pct'] < -config['min_change_pct'] * 0.5 and
                  last['rsi'] > config['rsi_oversold'] and last['rsi'] < 55 and
                  last['volume_ratio'] > config['min_volume_ratio']):
                
                confidence = config['min_confidence'] + 10
                if last['macd_histogram'] < prev['macd_histogram']:
                    confidence += 5
                if last['volume_ratio'] > config['min_volume_ratio'] * 1.2:
                    confidence += 5
                
                signal = {'type': 'SHORT', 'strategy': 'TREND_FOLLOWING_IMPROVED', 'confidence': min(confidence, 85)}
        
        # MEAN REVERSION MEJORADO (ETH, ADA)
        elif config.get('use_mean_reversion'):
            # BB más estricto si está configurado
            bb_threshold = config.get('bb_extreme_threshold', 0.2)
            
            # RSI confirmation si está configurado
            rsi_confirm = True
            if config.get('rsi_confirmation'):
                # Verificar que RSI está realmente en extremo
                rsi_confirm = (last['rsi'] < config['rsi_oversold'] - 2) if last['change_pct'] < 0 else \
                             (last['rsi'] > config['rsi_overbought'] + 2)
            
            # Long mejorado
            if (last['change_pct'] < -config['min_change_pct'] and
                last['rsi'] < config['rsi_oversold'] and
                last['bb_position'] < bb_threshold and
                last['volume_ratio'] > config['min_volume_ratio'] and
                rsi_confirm):
                
                confidence = config['min_confidence']
                if last['rsi'] < config['rsi_oversold'] - 5:
                    confidence += 15
                if last['bb_position'] < bb_threshold * 0.7:
                    confidence += 10
                if last['volume_ratio'] > config['min_volume_ratio'] * 1.3:
                    confidence += 5
                
                signal = {'type': 'LONG', 'strategy': 'MEAN_REVERSION_IMPROVED', 'confidence': min(confidence, 80)}
            
            # Short mejorado
            elif (last['change_pct'] > config['min_change_pct'] and
                  last['rsi'] > config['rsi_overbought'] and
                  last['bb_position'] > (1 - bb_threshold) and
                  last['volume_ratio'] > config['min_volume_ratio'] and
                  rsi_confirm):
                
                confidence = config['min_confidence']
                if last['rsi'] > config['rsi_overbought'] + 5:
                    confidence += 15
                if last['bb_position'] > (1 - bb_threshold * 0.7):
                    confidence += 10
                if last['volume_ratio'] > config['min_volume_ratio'] * 1.3:
                    confidence += 5
                
                signal = {'type': 'SHORT', 'strategy': 'MEAN_REVERSION_IMPROVED', 'confidence': min(confidence, 80)}
        
        # MOMENTUM (SOL, DOGE) - Filtros relajados
        elif config.get('use_momentum'):
            if (last['change_pct'] > config['min_change_pct'] and
                last['volume_ratio'] > config['min_volume_ratio'] and
                last['macd_histogram'] > prev['macd_histogram'] and
                last['rsi'] > 50 and last['rsi'] < config['rsi_overbought'] and
                last['volume_trend'] > 1.1):  # Reducido de 1.2 a 1.1
                
                confidence = config['min_confidence']
                if last['volume_trend'] > 1.4:  # Reducido de 1.5
                    confidence += 10
                if last['change_pct'] > config['min_change_pct'] * 1.3:  # Reducido de 1.5
                    confidence += 8
                
                if config.get('extra_caution'):
                    confidence = min(confidence, 70)
                
                signal = {'type': 'LONG', 'strategy': 'MOMENTUM_RELAXED', 'confidence': confidence}
            
            elif (last['change_pct'] < -config['min_change_pct'] and
                  last['volume_ratio'] > config['min_volume_ratio'] and
                  last['macd_histogram'] < prev['macd_histogram'] and
                  last['rsi'] < 50 and last['rsi'] > config['rsi_oversold'] and
                  last['volume_trend'] > 1.1):
                
                confidence = config['min_confidence']
                if last['volume_trend'] > 1.4:
                    confidence += 10
                if abs(last['change_pct']) > config['min_change_pct'] * 1.3:
                    confidence += 8
                
                if config.get('extra_caution'):
                    confidence = min(confidence, 70)
                
                signal = {'type': 'SHORT', 'strategy': 'MOMENTUM_RELAXED', 'confidence': confidence}
        
        # RANGE TRADING (BNB) - Sin cambios, ya funciona
        elif config.get('use_range_trading'):
            if (last['bb_position'] < 0.2 and
                last['rsi'] < config['rsi_oversold'] + 5 and
                last['change_pct'] < -config['min_change_pct'] * 0.7):
                
                confidence = config['min_confidence']
                if last['bb_position'] < 0.1:
                    confidence += 10
                if last['rsi'] < config['rsi_oversold']:
                    confidence += 8
                
                signal = {'type': 'LONG', 'strategy': 'RANGE_TRADING', 'confidence': confidence}
            
            elif (last['bb_position'] > 0.8 and
                  last['rsi'] > config['rsi_overbought'] - 5 and
                  last['change_pct'] > config['min_change_pct'] * 0.7):
                
                confidence = config['min_confidence']
                if last['bb_position'] > 0.9:
                    confidence += 10
                if last['rsi'] > config['rsi_overbought']:
                    confidence += 8
                
                signal = {'type': 'SHORT', 'strategy': 'RANGE_TRADING', 'confidence': confidence}
        
        # Aplicar stops y detalles si hay señal
        if signal and signal['confidence'] >= config['min_confidence']:
            atr_mult = config['atr_multiplier']
            
            if last['volatility'] > config['max_volatility'] * 0.8:
                atr_mult += 0.3
            
            stop_distance = last['atr'] * atr_mult
            
            signal.update({
                'symbol': symbol,
                'price': last['close'],
                'timeframe': interval,
                'indicators': {
                    'rsi': last['rsi'],
                    'change_pct': last['change_pct'],
                    'volume_ratio': last['volume_ratio'],
                    'volatility': last['volatility'],
                    'macd_histogram': last['macd_histogram'],
                    'bb_position': last['bb_position'],
                    'trend_strength': last['trend_strength']
                },
                'atr': last['atr'],
                'timestamp': datetime.now().isoformat()
            })
            
            if signal['type'] == 'LONG':
                signal['stop_loss'] = signal['price'] - stop_distance
                signal['take_profit'] = signal['price'] + (stop_distance * 1.5)
            else:
                signal['stop_loss'] = signal['price'] + stop_distance
                signal['take_profit'] = signal['price'] - (stop_distance * 1.5)
            
            risk_amount = INITIAL_CAPITAL * MAX_RISK_PER_TRADE
            signal['position_size'] = (risk_amount * DEFAULT_LEVERAGE) / signal['price']
            signal['leverage'] = DEFAULT_LEVERAGE
            
            return signal
        
        return None

# API
app = FastAPI(title="Fixed Pair Optimized System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/signals")
async def get_signals():
    """Obtiene señales con configuraciones corregidas"""
    
    symbols = list(FIXED_PAIR_CONFIG.keys())
    intervals = ['15m', '1h', '4h']
    
    all_signals = []
    
    for symbol in symbols:
        for interval in intervals:
            signal = await FixedPairSignalGenerator.generate_signal(symbol, interval)
            if signal:
                all_signals.append(signal)
    
    all_signals.sort(key=lambda x: x['confidence'], reverse=True)
    return all_signals

@app.get("/api/fixes")
async def get_applied_fixes():
    """Muestra qué correcciones se aplicaron"""
    
    fixes = {
        "BTCUSDT": [
            "Filtros MACD más estrictos (>0.1 para 15m)",
            "Volumen excepcional requerido (>1.5x para 15m)", 
            "Tendencia más fuerte (EMA20-EMA50 > 2%)",
            "ATR aumentado para mejores stops"
        ],
        "ETHUSDT": [
            "ATR aumentado 3.0-3.5x (era 2.0-2.5x)",
            "RSI más extremo (25/75 en lugar de 30/70)",
            "Bollinger Bands más estricto (<0.15 y >0.85)",
            "Confirmación RSI obligatoria"
        ],
        "SOLUSDT": [
            "min_change_pct reducido de 2.5% a 2.0% (15m)",
            "RSI menos extremo (35/65 en lugar de 32/68)",
            "Volumen mínimo reducido a 0.9x",
            "Filtros de momentum relajados"
        ],
        "ADAUSDT": [
            "Similar a ETH: ATR más amplio (2.8-3.0x)",
            "RSI más extremo y confirmación obligatoria",
            "Bollinger Bands más estricto"
        ],
        "BNBUSDT": [
            "Ajuste menor en 15m para más oportunidades",
            "Mantener 1h y 4h (ya funcionaban bien)"
        ],
        "DOGEUSDT": [
            "Sin cambios (ya funcionaba excelente)",
            "Mantener extra precaución"
        ]
    }
    
    return fixes

@app.get("/api/stats")
async def get_stats():
    """Estadísticas del sistema corregido"""
    return {
        "capital": INITIAL_CAPITAL,
        "risk_per_trade": MAX_RISK_PER_TRADE,
        "default_leverage": DEFAULT_LEVERAGE,
        "version": "FIXED_CONFIGURATIONS",
        "fixes_applied": 6,
        "active": True
    }

if __name__ == "__main__":
    print("="*60)
    print("SISTEMA CON CONFIGURACIONES CORREGIDAS")
    print("="*60)
    print(f"Capital: ${INITIAL_CAPITAL}")
    print(f"Versión: Configuraciones corregidas basadas en análisis")
    
    fixes_summary = [
        "✓ BTC: Filtros más estrictos para reducir ruido",
        "✓ ETH: ATR 3.0-3.5x, RSI extremo 25/75",
        "✓ SOL: Filtros relajados para generar trades",
        "✓ ADA: ATR amplio + confirmaciones",
        "✓ BNB: Ajuste menor (ya funcionaba)",
        "✓ DOGE: Sin cambios (perfecto)"
    ]
    
    for fix in fixes_summary:
        print(f"  {fix}")
    
    print("\n" + "="*60)
    print("Iniciando servidor corregido en http://localhost:8002")
    print("="*60)
    
    uvicorn.run(app, host="0.0.0.0", port=8002)