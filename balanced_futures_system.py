#!/usr/bin/env python3
"""
Sistema Balanceado de Futuros - Optimizado por Timeframe
Balancea calidad de señales con cantidad suficiente
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

# Configuración adaptativa por timeframe
TIMEFRAME_CONFIG = {
    '15m': {
        'min_change_pct': 2.0,      # Reducido de 3%
        'rsi_oversold': 35,         # Relajado de 30
        'rsi_overbought': 65,        # Relajado de 70
        'min_volume_ratio': 1.1,    # Reducido de 1.2
        'max_volatility': 12,        # Aumentado de 10
        'atr_multiplier': 2.0,       # Reducido de 2.5
        'min_confidence': 55,        # Reducido de 60
        'trend_filter_strength': 0.5 # Más permisivo
    },
    '1h': {
        'min_change_pct': 2.5,
        'rsi_oversold': 32,
        'rsi_overbought': 68,
        'min_volume_ratio': 1.15,
        'max_volatility': 11,
        'atr_multiplier': 2.2,
        'min_confidence': 58,
        'trend_filter_strength': 0.7
    },
    '4h': {
        'min_change_pct': 3.0,
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'min_volume_ratio': 1.2,
        'max_volatility': 10,
        'atr_multiplier': 2.5,
        'min_confidence': 60,
        'trend_filter_strength': 1.0
    }
}

# Configuración general
INITIAL_CAPITAL = 220.0
MAX_RISK_PER_TRADE = 0.02
DEFAULT_LEVERAGE = 3
MAX_LEVERAGE = 5

class BalancedSignalGenerator:
    """Generador de señales balanceado por timeframe"""
    
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
            logger.error(f"Error fetching data: {e}")
        
        return None
    
    @staticmethod
    def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores técnicos"""
        
        # Cambio porcentual
        df['change_pct'] = df['close'].pct_change() * 100
        
        # Posición en rango
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
        
        # Volatilidad
        df['volatility'] = ((df['high'] - df['low']) / df['close']) * 100
        
        # Volumen relativo
        df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        
        # Fuerza de tendencia
        df['trend_strength'] = abs(df['ema_20'] - df['ema_50']) / df['close'] * 100
        df['is_uptrend'] = df['ema_20'] > df['ema_50']
        
        return df
    
    @staticmethod
    async def generate_signal(symbol: str, interval: str) -> Optional[Dict]:
        """Genera señales adaptadas por timeframe"""
        
        # Obtener configuración específica del timeframe
        config = TIMEFRAME_CONFIG.get(interval, TIMEFRAME_CONFIG['1h'])
        
        # Obtener datos
        df = await BalancedSignalGenerator.fetch_market_data(symbol, interval)
        if df is None or len(df) < 50:
            return None
        
        # Calcular indicadores
        df = BalancedSignalGenerator.calculate_indicators(df)
        
        # Última vela
        last = df.iloc[-1]
        
        # Verificar datos válidos
        if pd.isna(last['atr']) or pd.isna(last['rsi']):
            return None
        
        # FILTRO 1: Volatilidad máxima (adaptativo)
        if last['volatility'] > config['max_volatility']:
            return None
        
        signal = None
        confidence = 0
        
        # SEÑAL LONG
        if (last['change_pct'] < -config['min_change_pct'] and 
            last['range_position'] < 0.3):
            
            # Confirmación RSI (adaptativa)
            if last['rsi'] < config['rsi_oversold']:
                
                # Filtro de tendencia (adaptativo)
                trend_ok = True
                if last['is_uptrend'] == False and last['trend_strength'] > (1.5 * config['trend_filter_strength']):
                    trend_ok = False
                
                if trend_ok:
                    # Confirmación de volumen (adaptativa)
                    if last['volume_ratio'] > config['min_volume_ratio']:
                        
                        # Calcular confianza
                        confidence = config['min_confidence']
                        
                        # Bonus por RSI extremo
                        if last['rsi'] < (config['rsi_oversold'] - 5):
                            confidence += 10
                        
                        # Bonus por volumen alto
                        if last['volume_ratio'] > (config['min_volume_ratio'] + 0.3):
                            confidence += 5
                        
                        # Bonus por rebote desde soporte
                        if last['range_position'] < 0.2:
                            confidence += 5
                        
                        signal = {
                            'symbol': symbol,
                            'type': 'LONG',
                            'price': last['close'],
                            'confidence': min(confidence, 90),
                            'timeframe': interval,
                            'indicators': {
                                'rsi': last['rsi'],
                                'change_pct': last['change_pct'],
                                'volume_ratio': last['volume_ratio'],
                                'volatility': last['volatility']
                            },
                            'atr': last['atr'],
                            'timestamp': datetime.now().isoformat()
                        }
        
        # SEÑAL SHORT
        elif (last['change_pct'] > config['min_change_pct'] and 
              last['range_position'] > 0.7):
            
            # Confirmación RSI (adaptativa)
            if last['rsi'] > config['rsi_overbought']:
                
                # Filtro de tendencia (adaptativo)
                trend_ok = True
                if last['is_uptrend'] == True and last['trend_strength'] > (1.5 * config['trend_filter_strength']):
                    trend_ok = False
                
                if trend_ok:
                    # Confirmación de volumen (adaptativa)
                    if last['volume_ratio'] > config['min_volume_ratio']:
                        
                        # Calcular confianza
                        confidence = config['min_confidence']
                        
                        # Bonus por RSI extremo
                        if last['rsi'] > (config['rsi_overbought'] + 5):
                            confidence += 10
                        
                        # Bonus por volumen alto
                        if last['volume_ratio'] > (config['min_volume_ratio'] + 0.3):
                            confidence += 5
                        
                        # Bonus por rechazo desde resistencia
                        if last['range_position'] > 0.8:
                            confidence += 5
                        
                        signal = {
                            'symbol': symbol,
                            'type': 'SHORT',
                            'price': last['close'],
                            'confidence': min(confidence, 90),
                            'timeframe': interval,
                            'indicators': {
                                'rsi': last['rsi'],
                                'change_pct': last['change_pct'],
                                'volume_ratio': last['volume_ratio'],
                                'volatility': last['volatility']
                            },
                            'atr': last['atr'],
                            'timestamp': datetime.now().isoformat()
                        }
        
        # Aplicar stops dinámicos si hay señal
        if signal and signal['confidence'] >= config['min_confidence']:
            atr_mult = config['atr_multiplier']
            
            # Ajustar multiplicador según volatilidad
            if last['volatility'] > 8:
                atr_mult += 0.3
            
            stop_distance = last['atr'] * atr_mult
            
            if signal['type'] == 'LONG':
                signal['stop_loss'] = signal['price'] - stop_distance
                signal['take_profit'] = signal['price'] + (stop_distance * 1.5)
            else:
                signal['stop_loss'] = signal['price'] + stop_distance
                signal['take_profit'] = signal['price'] - (stop_distance * 1.5)
            
            # Calcular tamaño de posición
            risk_amount = INITIAL_CAPITAL * MAX_RISK_PER_TRADE
            signal['position_size'] = (risk_amount * DEFAULT_LEVERAGE) / signal['price']
            signal['leverage'] = DEFAULT_LEVERAGE
            
            return signal
        
        return None

# API
app = FastAPI(title="Balanced Futures System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/signals")
async def get_signals():
    """Obtiene señales para todos los símbolos y timeframes"""
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT']
    intervals = ['15m', '1h', '4h']
    
    all_signals = []
    
    for symbol in symbols:
        for interval in intervals:
            signal = await BalancedSignalGenerator.generate_signal(symbol, interval)
            if signal:
                all_signals.append(signal)
    
    # Ordenar por confianza
    all_signals.sort(key=lambda x: x['confidence'], reverse=True)
    
    return all_signals

@app.get("/api/config/{timeframe}")
async def get_timeframe_config(timeframe: str):
    """Obtiene configuración específica del timeframe"""
    return TIMEFRAME_CONFIG.get(timeframe, TIMEFRAME_CONFIG['1h'])

@app.get("/api/stats")
async def get_stats():
    """Estadísticas del sistema"""
    return {
        "capital": INITIAL_CAPITAL,
        "risk_per_trade": MAX_RISK_PER_TRADE,
        "default_leverage": DEFAULT_LEVERAGE,
        "timeframes": list(TIMEFRAME_CONFIG.keys()),
        "active": True
    }

if __name__ == "__main__":
    print("="*60)
    print("SISTEMA BALANCEADO DE FUTUROS")
    print("="*60)
    print(f"Capital: ${INITIAL_CAPITAL}")
    print(f"Riesgo por trade: {MAX_RISK_PER_TRADE*100}%")
    print(f"Apalancamiento: {DEFAULT_LEVERAGE}x")
    print("\nConfiguraciones por timeframe:")
    for tf, config in TIMEFRAME_CONFIG.items():
        print(f"\n{tf}:")
        print(f"  - RSI: {config['rsi_oversold']}/{config['rsi_overbought']}")
        print(f"  - Cambio mín: {config['min_change_pct']}%")
        print(f"  - Confianza mín: {config['min_confidence']}%")
    print("\n" + "="*60)
    print("Iniciando servidor en http://localhost:8002")
    print("="*60)
    
    uvicorn.run(app, host="0.0.0.0", port=8002)