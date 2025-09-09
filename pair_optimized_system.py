#!/usr/bin/env python3
"""
Sistema Optimizado por Par - Estrategias específicas para cada criptomoneda
Cada par tiene su propia configuración basada en su comportamiento único
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

# Configuración ESPECÍFICA por PAR y TIMEFRAME
PAIR_CONFIG = {
    'BTCUSDT': {
        # BTC: Menos volátil, movimientos más predecibles
        # Mejor en tendencias largas
        '15m': {
            'min_change_pct': 1.5,      # BTC se mueve menos
            'rsi_oversold': 38,         
            'rsi_overbought': 62,        
            'min_volume_ratio': 1.2,    # BTC necesita más volumen para confirmar
            'max_volatility': 8,         # BTC menos volátil
            'atr_multiplier': 1.8,       # Stops más ajustados
            'min_confidence': 60,        
            'trend_filter_strength': 0.8,
            'use_trend_following': True  # BTC respeta más las tendencias
        },
        '1h': {
            'min_change_pct': 2.0,
            'rsi_oversold': 35,
            'rsi_overbought': 65,
            'min_volume_ratio': 1.15,
            'max_volatility': 9,
            'atr_multiplier': 2.0,
            'min_confidence': 58,
            'trend_filter_strength': 1.0,
            'use_trend_following': True
        },
        '4h': {
            'min_change_pct': 2.5,      # BTC 4h muy confiable
            'rsi_oversold': 32,
            'rsi_overbought': 68,
            'min_volume_ratio': 1.1,
            'max_volatility': 10,
            'atr_multiplier': 2.2,
            'min_confidence': 55,
            'trend_filter_strength': 1.2,
            'use_trend_following': True
        }
    },
    
    'ETHUSDT': {
        # ETH: Volatilidad media, sigue a BTC pero con más fuerza
        # Bueno para reversiones
        '15m': {
            'min_change_pct': 2.0,
            'rsi_oversold': 35,
            'rsi_overbought': 65,
            'min_volume_ratio': 1.1,
            'max_volatility': 11,        # ETH más volátil que BTC
            'atr_multiplier': 2.0,
            'min_confidence': 55,
            'trend_filter_strength': 0.6,
            'use_mean_reversion': True   # ETH bueno para reversión
        },
        '1h': {
            'min_change_pct': 2.5,
            'rsi_oversold': 33,
            'rsi_overbought': 67,
            'min_volume_ratio': 1.15,
            'max_volatility': 12,
            'atr_multiplier': 2.2,
            'min_confidence': 57,
            'trend_filter_strength': 0.8,
            'use_mean_reversion': True
        },
        '4h': {
            'min_change_pct': 3.0,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'min_volume_ratio': 1.2,
            'max_volatility': 13,
            'atr_multiplier': 2.5,
            'min_confidence': 60,
            'trend_filter_strength': 1.0,
            'use_mean_reversion': True
        }
    },
    
    'SOLUSDT': {
        # SOL: Alta volatilidad, movimientos explosivos
        # Excelente para momentum
        '15m': {
            'min_change_pct': 2.5,       # SOL se mueve mucho
            'rsi_oversold': 32,         # Más extremos para SOL
            'rsi_overbought': 68,
            'min_volume_ratio': 1.0,     # SOL siempre tiene volumen
            'max_volatility': 15,        # SOL muy volátil
            'atr_multiplier': 2.3,       # Stops más amplios
            'min_confidence': 52,        # Más oportunidades
            'trend_filter_strength': 0.4,
            'use_momentum': True         # SOL excelente para momentum
        },
        '1h': {
            'min_change_pct': 3.0,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'min_volume_ratio': 1.05,
            'max_volatility': 16,
            'atr_multiplier': 2.5,
            'min_confidence': 55,
            'trend_filter_strength': 0.5,
            'use_momentum': True
        },
        '4h': {
            'min_change_pct': 3.5,
            'rsi_oversold': 28,
            'rsi_overbought': 72,
            'min_volume_ratio': 1.1,
            'max_volatility': 17,
            'atr_multiplier': 2.8,
            'min_confidence': 58,
            'trend_filter_strength': 0.7,
            'use_momentum': True
        }
    },
    
    'BNBUSDT': {
        # BNB: Estable, movimientos por eventos Binance
        # Bueno para rangos
        '15m': {
            'min_change_pct': 1.8,
            'rsi_oversold': 36,
            'rsi_overbought': 64,
            'min_volume_ratio': 1.15,
            'max_volatility': 9,
            'atr_multiplier': 1.9,
            'min_confidence': 58,
            'trend_filter_strength': 0.7,
            'use_range_trading': True    # BNB tiende a rangos
        },
        '1h': {
            'min_change_pct': 2.2,
            'rsi_oversold': 34,
            'rsi_overbought': 66,
            'min_volume_ratio': 1.2,
            'max_volatility': 10,
            'atr_multiplier': 2.1,
            'min_confidence': 60,
            'trend_filter_strength': 0.9,
            'use_range_trading': True
        },
        '4h': {
            'min_change_pct': 2.8,
            'rsi_oversold': 31,
            'rsi_overbought': 69,
            'min_volume_ratio': 1.25,
            'max_volatility': 11,
            'atr_multiplier': 2.3,
            'min_confidence': 62,
            'trend_filter_strength': 1.1,
            'use_range_trading': True
        }
    },
    
    'ADAUSDT': {
        # ADA: Volatilidad media-alta, buenos swings
        '15m': {
            'min_change_pct': 2.2,
            'rsi_oversold': 34,
            'rsi_overbought': 66,
            'min_volume_ratio': 1.1,
            'max_volatility': 13,
            'atr_multiplier': 2.1,
            'min_confidence': 54,
            'trend_filter_strength': 0.5,
            'use_mean_reversion': True
        },
        '1h': {
            'min_change_pct': 2.8,
            'rsi_oversold': 32,
            'rsi_overbought': 68,
            'min_volume_ratio': 1.15,
            'max_volatility': 14,
            'atr_multiplier': 2.3,
            'min_confidence': 56,
            'trend_filter_strength': 0.7,
            'use_mean_reversion': True
        },
        '4h': {
            'min_change_pct': 3.2,
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'min_volume_ratio': 1.2,
            'max_volatility': 15,
            'atr_multiplier': 2.6,
            'min_confidence': 59,
            'trend_filter_strength': 0.9,
            'use_mean_reversion': True
        }
    },
    
    'DOGEUSDT': {
        # DOGE: Extremadamente volátil, movimientos por memes/tweets
        '15m': {
            'min_change_pct': 3.0,       # DOGE movimientos extremos
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'min_volume_ratio': 0.9,     # DOGE volumen errático
            'max_volatility': 20,        # DOGE súper volátil
            'atr_multiplier': 3.0,       # Stops muy amplios
            'min_confidence': 50,        # Más especulativo
            'trend_filter_strength': 0.3,
            'use_momentum': True,        # DOGE es puro momentum
            'extra_caution': True        # Cuidado extra con DOGE
        },
        '1h': {
            'min_change_pct': 3.5,
            'rsi_oversold': 28,
            'rsi_overbought': 72,
            'min_volume_ratio': 0.95,
            'max_volatility': 22,
            'atr_multiplier': 3.2,
            'min_confidence': 52,
            'trend_filter_strength': 0.4,
            'use_momentum': True,
            'extra_caution': True
        },
        '4h': {
            'min_change_pct': 4.0,
            'rsi_oversold': 25,
            'rsi_overbought': 75,
            'min_volume_ratio': 1.0,
            'max_volatility': 25,
            'atr_multiplier': 3.5,
            'min_confidence': 55,
            'trend_filter_strength': 0.5,
            'use_momentum': True,
            'extra_caution': True
        }
    }
}

# Configuración general
INITIAL_CAPITAL = 220.0
MAX_RISK_PER_TRADE = 0.02
DEFAULT_LEVERAGE = 3
MAX_LEVERAGE = 5

class PairOptimizedSignalGenerator:
    """Generador de señales optimizado por par"""
    
    @staticmethod
    async def fetch_market_data(symbol: str, interval: str) -> Optional[pd.DataFrame]:
        """Obtiene datos de mercado"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    'https://fapi.binance.com/fapi/v1/klines',
                    params={
                        'symbol': symbol,
                        'interval': interval,
                        'limit': 100
                    }
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
        """Calcula indicadores técnicos"""
        
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
        
        # MACD para momentum
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands para rangos
        df['bb_middle'] = df['close'].rolling(20).mean()
        df['bb_std'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * 2)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * 2)
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Volatilidad
        df['volatility'] = ((df['high'] - df['low']) / df['close']) * 100
        
        # Volumen
        df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        df['volume_trend'] = df['volume'].rolling(5).mean() / df['volume'].rolling(20).mean()
        
        # Tendencia
        df['trend_strength'] = abs(df['ema_20'] - df['ema_50']) / df['close'] * 100
        df['is_uptrend'] = df['ema_20'] > df['ema_50']
        
        return df
    
    @staticmethod
    async def generate_signal(symbol: str, interval: str) -> Optional[Dict]:
        """Genera señales específicas por par"""
        
        # Obtener configuración específica del par
        if symbol not in PAIR_CONFIG:
            logger.warning(f"No config for {symbol}, using BTCUSDT defaults")
            config = PAIR_CONFIG['BTCUSDT'].get(interval, PAIR_CONFIG['BTCUSDT']['1h'])
        else:
            config = PAIR_CONFIG[symbol].get(interval, PAIR_CONFIG[symbol]['1h'])
        
        # Obtener datos
        df = await PairOptimizedSignalGenerator.fetch_market_data(symbol, interval)
        if df is None or len(df) < 50:
            return None
        
        # Calcular indicadores
        df = PairOptimizedSignalGenerator.calculate_indicators(df)
        
        # Última vela
        last = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Verificar datos válidos
        if pd.isna(last['atr']) or pd.isna(last['rsi']):
            return None
        
        # Filtro de volatilidad
        if last['volatility'] > config['max_volatility']:
            return None
        
        signal = None
        confidence = 0
        
        # ESTRATEGIA ESPECÍFICA POR PAR
        
        # 1. TREND FOLLOWING (BTC)
        if config.get('use_trend_following'):
            if last['is_uptrend'] and last['macd_histogram'] > 0:
                if last['change_pct'] > config['min_change_pct'] * 0.5:  # Menos exigente en tendencia
                    if last['rsi'] < 70:  # No sobrecomprado
                        confidence = config['min_confidence'] + 10
                        signal = {
                            'type': 'LONG',
                            'strategy': 'TREND_FOLLOWING',
                            'confidence': confidence
                        }
            
            elif not last['is_uptrend'] and last['macd_histogram'] < 0:
                if last['change_pct'] < -config['min_change_pct'] * 0.5:
                    if last['rsi'] > 30:  # No sobrevendido
                        confidence = config['min_confidence'] + 10
                        signal = {
                            'type': 'SHORT',
                            'strategy': 'TREND_FOLLOWING',
                            'confidence': confidence
                        }
        
        # 2. MEAN REVERSION (ETH, ADA)
        elif config.get('use_mean_reversion'):
            # Long en sobreventa
            if (last['change_pct'] < -config['min_change_pct'] and 
                last['rsi'] < config['rsi_oversold'] and
                last['bb_position'] < 0.2):
                
                if last['volume_ratio'] > config['min_volume_ratio']:
                    confidence = config['min_confidence']
                    if last['rsi'] < config['rsi_oversold'] - 5:
                        confidence += 15
                    
                    signal = {
                        'type': 'LONG',
                        'strategy': 'MEAN_REVERSION',
                        'confidence': confidence
                    }
            
            # Short en sobrecompra
            elif (last['change_pct'] > config['min_change_pct'] and
                  last['rsi'] > config['rsi_overbought'] and
                  last['bb_position'] > 0.8):
                
                if last['volume_ratio'] > config['min_volume_ratio']:
                    confidence = config['min_confidence']
                    if last['rsi'] > config['rsi_overbought'] + 5:
                        confidence += 15
                    
                    signal = {
                        'type': 'SHORT',
                        'strategy': 'MEAN_REVERSION',
                        'confidence': confidence
                    }
        
        # 3. MOMENTUM (SOL, DOGE)
        elif config.get('use_momentum'):
            # Long momentum
            if (last['change_pct'] > config['min_change_pct'] and
                last['volume_ratio'] > config['min_volume_ratio'] and
                last['macd_histogram'] > prev['macd_histogram'] and
                last['rsi'] > 50 and last['rsi'] < config['rsi_overbought']):
                
                confidence = config['min_confidence']
                if last['volume_trend'] > 1.5:  # Volumen creciente
                    confidence += 10
                
                signal = {
                    'type': 'LONG',
                    'strategy': 'MOMENTUM',
                    'confidence': confidence
                }
            
            # Short momentum
            elif (last['change_pct'] < -config['min_change_pct'] and
                  last['volume_ratio'] > config['min_volume_ratio'] and
                  last['macd_histogram'] < prev['macd_histogram'] and
                  last['rsi'] < 50 and last['rsi'] > config['rsi_oversold']):
                
                confidence = config['min_confidence']
                if last['volume_trend'] > 1.5:
                    confidence += 10
                
                signal = {
                    'type': 'SHORT',
                    'strategy': 'MOMENTUM',
                    'confidence': confidence
                }
        
        # 4. RANGE TRADING (BNB)
        elif config.get('use_range_trading'):
            # Long en soporte
            if (last['bb_position'] < 0.2 and
                last['rsi'] < config['rsi_oversold'] + 5 and
                last['change_pct'] < -config['min_change_pct'] * 0.7):
                
                confidence = config['min_confidence']
                if last['bb_position'] < 0.1:
                    confidence += 10
                
                signal = {
                    'type': 'LONG',
                    'strategy': 'RANGE_TRADING',
                    'confidence': confidence
                }
            
            # Short en resistencia
            elif (last['bb_position'] > 0.8 and
                  last['rsi'] > config['rsi_overbought'] - 5 and
                  last['change_pct'] > config['min_change_pct'] * 0.7):
                
                confidence = config['min_confidence']
                if last['bb_position'] > 0.9:
                    confidence += 10
                
                signal = {
                    'type': 'SHORT',
                    'strategy': 'RANGE_TRADING',
                    'confidence': confidence
                }
        
        # ESTRATEGIA GENERAL (FALLBACK)
        else:
            # Señales estándar de reversión
            if (last['change_pct'] < -config['min_change_pct'] and 
                last['range_position'] < 0.3 and
                last['rsi'] < config['rsi_oversold']):
                
                if last['volume_ratio'] > config['min_volume_ratio']:
                    confidence = config['min_confidence']
                    signal = {
                        'type': 'LONG',
                        'strategy': 'STANDARD',
                        'confidence': confidence
                    }
            
            elif (last['change_pct'] > config['min_change_pct'] and
                  last['range_position'] > 0.7 and
                  last['rsi'] > config['rsi_overbought']):
                
                if last['volume_ratio'] > config['min_volume_ratio']:
                    confidence = config['min_confidence']
                    signal = {
                        'type': 'SHORT',
                        'strategy': 'STANDARD',
                        'confidence': confidence
                    }
        
        # Aplicar stops y detalles si hay señal
        if signal and signal['confidence'] >= config['min_confidence']:
            # Extra precaución para pares volátiles
            if config.get('extra_caution'):
                signal['confidence'] = min(signal['confidence'], 70)
            
            # ATR multiplier específico
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
                    'bb_position': last['bb_position']
                },
                'atr': last['atr'],
                'timestamp': datetime.now().isoformat()
            })
            
            # Calcular stops
            if signal['type'] == 'LONG':
                signal['stop_loss'] = signal['price'] - stop_distance
                signal['take_profit'] = signal['price'] + (stop_distance * 1.5)
            else:
                signal['stop_loss'] = signal['price'] + stop_distance
                signal['take_profit'] = signal['price'] - (stop_distance * 1.5)
            
            # Tamaño de posición
            risk_amount = INITIAL_CAPITAL * MAX_RISK_PER_TRADE
            signal['position_size'] = (risk_amount * DEFAULT_LEVERAGE) / signal['price']
            signal['leverage'] = DEFAULT_LEVERAGE
            
            return signal
        
        return None

# API
app = FastAPI(title="Pair Optimized Futures System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cache de señales activas
active_signals = {}

@app.get("/api/signals")
async def get_signals():
    """Obtiene señales optimizadas por par"""
    
    symbols = list(PAIR_CONFIG.keys())
    intervals = ['15m', '1h', '4h']
    
    all_signals = []
    
    for symbol in symbols:
        for interval in intervals:
            signal = await PairOptimizedSignalGenerator.generate_signal(symbol, interval)
            if signal:
                # Agregar info del par
                signal['pair_strategy'] = PAIR_CONFIG[symbol][interval]
                all_signals.append(signal)
                
                # Guardar en cache
                key = f"{symbol}_{interval}"
                active_signals[key] = signal
    
    # Ordenar por confianza y estrategia
    all_signals.sort(key=lambda x: (x['confidence'], x['strategy']), reverse=True)
    
    return all_signals

@app.get("/api/config/{symbol}/{timeframe}")
async def get_pair_config(symbol: str, timeframe: str):
    """Obtiene configuración específica del par y timeframe"""
    if symbol in PAIR_CONFIG:
        return PAIR_CONFIG[symbol].get(timeframe, {})
    return {}

@app.get("/api/pairs")
async def get_configured_pairs():
    """Lista de pares configurados con sus características"""
    pairs_info = {}
    
    for symbol, config in PAIR_CONFIG.items():
        pairs_info[symbol] = {
            'strategies': [],
            'characteristics': []
        }
        
        # Identificar estrategias principales
        for tf_config in config.values():
            if tf_config.get('use_trend_following'):
                if 'TREND_FOLLOWING' not in pairs_info[symbol]['strategies']:
                    pairs_info[symbol]['strategies'].append('TREND_FOLLOWING')
                    pairs_info[symbol]['characteristics'].append('Respeta tendencias')
            
            if tf_config.get('use_mean_reversion'):
                if 'MEAN_REVERSION' not in pairs_info[symbol]['strategies']:
                    pairs_info[symbol]['strategies'].append('MEAN_REVERSION')
                    pairs_info[symbol]['characteristics'].append('Buenos rebotes')
            
            if tf_config.get('use_momentum'):
                if 'MOMENTUM' not in pairs_info[symbol]['strategies']:
                    pairs_info[symbol]['strategies'].append('MOMENTUM')
                    pairs_info[symbol]['characteristics'].append('Movimientos explosivos')
            
            if tf_config.get('use_range_trading'):
                if 'RANGE_TRADING' not in pairs_info[symbol]['strategies']:
                    pairs_info[symbol]['strategies'].append('RANGE_TRADING')
                    pairs_info[symbol]['characteristics'].append('Opera en rangos')
            
            if tf_config.get('extra_caution'):
                if 'Alta volatilidad' not in pairs_info[symbol]['characteristics']:
                    pairs_info[symbol]['characteristics'].append('Alta volatilidad')
    
    return pairs_info

@app.get("/api/stats")
async def get_stats():
    """Estadísticas del sistema"""
    return {
        "capital": INITIAL_CAPITAL,
        "risk_per_trade": MAX_RISK_PER_TRADE,
        "default_leverage": DEFAULT_LEVERAGE,
        "configured_pairs": len(PAIR_CONFIG),
        "active_signals": len(active_signals),
        "strategies": ["TREND_FOLLOWING", "MEAN_REVERSION", "MOMENTUM", "RANGE_TRADING"],
        "active": True
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket para actualizaciones en tiempo real"""
    await websocket.accept()
    
    try:
        while True:
            # Enviar señales cada 30 segundos
            await asyncio.sleep(30)
            
            # Obtener nuevas señales
            signals = await get_signals()
            
            await websocket.send_json({
                "type": "signals_update",
                "data": signals[:5],  # Top 5 señales
                "timestamp": datetime.now().isoformat()
            })
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    print("="*60)
    print("SISTEMA OPTIMIZADO POR PAR")
    print("="*60)
    print(f"Capital: ${INITIAL_CAPITAL}")
    print(f"Riesgo por trade: {MAX_RISK_PER_TRADE*100}%")
    print(f"Apalancamiento: {DEFAULT_LEVERAGE}x")
    print(f"\nPares configurados: {len(PAIR_CONFIG)}")
    
    for symbol in PAIR_CONFIG.keys():
        print(f"  • {symbol}")
    
    print("\nEstrategias por par:")
    for symbol, config in PAIR_CONFIG.items():
        strategies = set()
        for tf_config in config.values():
            if tf_config.get('use_trend_following'):
                strategies.add('TREND')
            if tf_config.get('use_mean_reversion'):
                strategies.add('REVERSION')
            if tf_config.get('use_momentum'):
                strategies.add('MOMENTUM')
            if tf_config.get('use_range_trading'):
                strategies.add('RANGE')
        
        print(f"  {symbol}: {', '.join(strategies)}")
    
    print("\n" + "="*60)
    print("Iniciando servidor en http://localhost:8002")
    print("="*60)
    
    uvicorn.run(app, host="0.0.0.0", port=8002)