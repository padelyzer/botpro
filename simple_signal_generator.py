#!/usr/bin/env python3
"""
SIMPLE SIGNAL GENERATOR - BotphIA
Generador de señales reales usando indicadores técnicos
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime
import requests
import json
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class SimpleSignalGenerator:
    def __init__(self):
        self.symbols = [
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", 
            "ADAUSDT", "DOGEUSDT", "XRPUSDT", "DOTUSDT",
            "AVAXUSDT", "LINKUSDT"
        ]
        self.base_url = "https://api.binance.com/api/v3"
        
    def get_klines(self, symbol: str, interval: str = "1h", limit: int = 100):
        """Obtener datos históricos de Binance"""
        try:
            url = f"{self.base_url}/klines"
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            klines = response.json()
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            # Convertir a float
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
                
            return df
        except Exception as e:
            logger.error(f"Error getting klines for {symbol}: {e}")
            return None
            
    def calculate_rsi(self, prices, period=14):
        """Calcular RSI"""
        deltas = np.diff(prices)
        seed = deltas[:period+1]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        rs = up / down if down != 0 else 100
        rsi = np.zeros_like(prices)
        rsi[:period] = 100. - 100. / (1. + rs)
        
        for i in range(period, len(prices)):
            delta = deltas[i-1]
            if delta > 0:
                upval = delta
                downval = 0.
            else:
                upval = 0.
                downval = -delta
                
            up = (up * (period - 1) + upval) / period
            down = (down * (period - 1) + downval) / period
            rs = up / down if down != 0 else 100
            rsi[i] = 100. - 100. / (1. + rs)
            
        return rsi[-1]
        
    def calculate_macd(self, prices):
        """Calcular MACD"""
        exp1 = pd.Series(prices).ewm(span=12, adjust=False).mean()
        exp2 = pd.Series(prices).ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        histogram = macd - signal
        return {
            'macd': macd.iloc[-1],
            'signal': signal.iloc[-1],
            'histogram': histogram.iloc[-1]
        }
        
    def calculate_bollinger_bands(self, prices, period=20):
        """Calcular Bandas de Bollinger"""
        sma = pd.Series(prices).rolling(window=period).mean()
        std = pd.Series(prices).rolling(window=period).std()
        upper = sma + (std * 2)
        lower = sma - (std * 2)
        return {
            'upper': upper.iloc[-1],
            'middle': sma.iloc[-1],
            'lower': lower.iloc[-1],
            'price': prices[-1]
        }
        
    async def generate_signals(self) -> List[Dict]:
        """Generar señales reales basadas en indicadores técnicos"""
        signals = []
        
        for symbol in self.symbols:
            try:
                # Obtener datos
                df = self.get_klines(symbol, "1h", 100)
                if df is None:
                    continue
                    
                prices = df['close'].values
                current_price = prices[-1]
                
                # Calcular indicadores
                rsi = self.calculate_rsi(prices)
                macd_data = self.calculate_macd(prices)
                bb_data = self.calculate_bollinger_bands(prices)
                
                # Calcular volumen promedio
                avg_volume = df['volume'].mean()
                current_volume = df['volume'].iloc[-1]
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
                
                # Generar señal basada en múltiples indicadores
                signal_strength = 0
                signal_type = None
                reasons = []
                
                # RSI
                if rsi < 28:
                    signal_strength += 30
                    signal_type = "BUY"
                    reasons.append(f"RSI oversold ({rsi:.1f})")
                elif rsi > 73:
                    signal_strength += 30
                    signal_type = "SELL"
                    reasons.append(f"RSI overbought ({rsi:.1f})")
                    
                # MACD
                if macd_data['histogram'] > 0 and macd_data['macd'] > macd_data['signal']:
                    if signal_type == "BUY" or signal_type is None:
                        signal_strength += 25
                        signal_type = "BUY"
                        reasons.append("MACD bullish crossover")
                elif macd_data['histogram'] < 0 and macd_data['macd'] < macd_data['signal']:
                    if signal_type == "SELL" or signal_type is None:
                        signal_strength += 25
                        signal_type = "SELL"
                        reasons.append("MACD bearish crossover")
                        
                # Bollinger Bands
                if current_price < bb_data['lower']:
                    if signal_type == "BUY" or signal_type is None:
                        signal_strength += 20
                        signal_type = "BUY"
                        reasons.append("Price below lower BB")
                elif current_price > bb_data['upper']:
                    if signal_type == "SELL" or signal_type is None:
                        signal_strength += 20
                        signal_type = "SELL"
                        reasons.append("Price above upper BB")
                        
                # Volumen
                if volume_ratio > 1.5:
                    signal_strength += 15
                    reasons.append(f"High volume ({volume_ratio:.1f}x avg)")
                    
                # Generar señal si hay suficiente confianza
                if signal_strength >= 60 and signal_type:
                    # Calcular SL y TP
                    if signal_type == "BUY":
                        stop_loss = current_price * 0.97  # 3% SL
                        take_profit_1 = current_price * 1.03  # 3% TP1
                        take_profit_2 = current_price * 1.06  # 6% TP2
                    else:
                        stop_loss = current_price * 1.03
                        take_profit_1 = current_price * 0.97
                        take_profit_2 = current_price * 0.94
                        
                    signal = {
                        "symbol": symbol,
                        "signal_type": signal_type,
                        "confidence": min(signal_strength, 95),
                        "entry_price": f"{current_price:.8f}",
                        "stop_loss": f"{stop_loss:.8f}",
                        "take_profit_1": f"{take_profit_1:.8f}",
                        "take_profit_2": f"{take_profit_2:.8f}",
                        "rsi": rsi,
                        "volume_ratio": f"{volume_ratio:.2f}",
                        "reasons": reasons,
                        "timestamp": datetime.now().isoformat(),
                        "timeframe": "1h",
                        "recommended_leverage": "3x" if signal_strength < 80 else "5x"
                    }
                    
                    signals.append(signal)
                    logger.info(f"📊 Señal generada: {symbol} - {signal_type} ({signal_strength}%)")
                    
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                continue
                
        return signals