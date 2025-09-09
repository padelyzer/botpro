#!/usr/bin/env python3
"""
Crypto Momentum Detector - Detección de momentum real en crypto
Reemplaza indicadores tradicionales con métricas crypto-nativas
"""

import asyncio
import httpx
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class CryptoMomentumDetector:
    """Detector de momentum específico para crypto usando volumen y aceleración de precio"""
    
    def __init__(self):
        self.binance_api = "https://api.binance.com/api/v3"
        self.volume_threshold = 2.0  # 200% spike threshold
        self.price_acceleration_threshold = 0.02  # 2% acceleration
        self.cache_duration = 60  # Cache for 60 seconds
        self.cache = {}
        
    async def get_klines(self, symbol: str, interval: str = "15m", limit: int = 100) -> List:
        """Obtener velas de Binance"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.binance_api}/klines",
                    params={
                        "symbol": symbol,
                        "interval": interval,
                        "limit": limit
                    },
                    timeout=10.0
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Error getting klines for {symbol}: {e}")
        return []
    
    async def calculate_volume_roc(self, symbol: str) -> Dict:
        """
        Volume Rate of Change - Detecta spikes de volumen
        >200% = Señal fuerte de entrada de dinero
        """
        klines = await self.get_klines(symbol, "15m", 50)
        if not klines:
            return {"vroc": 0, "signal": "NEUTRAL", "strength": 0}
        
        volumes = [float(k[5]) for k in klines]  # Volume is index 5
        
        # Calculate average volume for last 20 periods
        avg_volume_20 = np.mean(volumes[-20:-1]) if len(volumes) > 20 else np.mean(volumes[:-1])
        current_volume = volumes[-1]
        
        # Volume Rate of Change
        vroc = (current_volume / avg_volume_20) if avg_volume_20 > 0 else 0
        
        # Generate signal based on VROC
        if vroc > 3.0:
            signal = "STRONG_BUY"
            strength = 95
        elif vroc > 2.0:
            signal = "BUY"
            strength = 80
        elif vroc > 1.5:
            signal = "WEAK_BUY"
            strength = 65
        elif vroc < 0.5:
            signal = "SELL"
            strength = 70
        else:
            signal = "NEUTRAL"
            strength = 50
        
        return {
            "vroc": vroc,
            "vroc_percent": (vroc - 1) * 100,
            "signal": signal,
            "strength": strength,
            "current_volume": current_volume,
            "avg_volume": avg_volume_20,
            "volume_spike": vroc > self.volume_threshold
        }
    
    async def calculate_price_acceleration(self, symbol: str) -> Dict:
        """
        Price Acceleration - Detecta cambios en la velocidad del precio
        Más efectivo que MACD para crypto
        """
        klines = await self.get_klines(symbol, "5m", 60)
        if not klines:
            return {"acceleration": 0, "velocity": 0, "signal": "NEUTRAL"}
        
        closes = [float(k[4]) for k in klines]  # Close price is index 4
        
        # Calculate velocity (rate of change)
        velocities = []
        for i in range(1, len(closes)):
            velocity = (closes[i] - closes[i-1]) / closes[i-1]
            velocities.append(velocity)
        
        # Calculate acceleration (change in velocity)
        if len(velocities) > 10:
            recent_velocity = np.mean(velocities[-5:])
            previous_velocity = np.mean(velocities[-10:-5])
            acceleration = recent_velocity - previous_velocity
        else:
            acceleration = 0
            recent_velocity = 0
        
        # Generate signal based on acceleration
        if acceleration > 0.01 and recent_velocity > 0:
            signal = "ACCELERATING_UP"
            strength = min(95, 50 + acceleration * 1000)
        elif acceleration < -0.01 and recent_velocity < 0:
            signal = "ACCELERATING_DOWN"
            strength = min(95, 50 + abs(acceleration) * 1000)
        elif acceleration > 0.005:
            signal = "GAINING_MOMENTUM"
            strength = 65
        elif acceleration < -0.005:
            signal = "LOSING_MOMENTUM"
            strength = 60
        else:
            signal = "NEUTRAL"
            strength = 50
        
        return {
            "acceleration": acceleration,
            "velocity": recent_velocity,
            "signal": signal,
            "strength": strength,
            "trend": "UP" if recent_velocity > 0 else "DOWN" if recent_velocity < 0 else "FLAT"
        }
    
    async def get_order_book_imbalance(self, symbol: str) -> Dict:
        """
        Order Flow Imbalance - Detecta presión compradora vs vendedora
        Más preciso que RSI para crypto
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.binance_api}/depth",
                    params={"symbol": symbol, "limit": 100},
                    timeout=5.0
                )
                if response.status_code != 200:
                    return {"imbalance": 0, "signal": "NEUTRAL", "buy_pressure": 50}
                
                data = response.json()
                
                # Calculate bid/ask volumes
                bid_volume = sum(float(bid[1]) * float(bid[0]) for bid in data['bids'][:20])
                ask_volume = sum(float(ask[1]) * float(ask[0]) for ask in data['asks'][:20])
                
                # Calculate imbalance
                total_volume = bid_volume + ask_volume
                if total_volume > 0:
                    buy_pressure = (bid_volume / total_volume) * 100
                    imbalance = (bid_volume - ask_volume) / total_volume
                else:
                    buy_pressure = 50
                    imbalance = 0
                
                # Generate signal
                if buy_pressure > 65:
                    signal = "STRONG_BUY_PRESSURE"
                    strength = min(95, 50 + buy_pressure - 50)
                elif buy_pressure > 55:
                    signal = "BUY_PRESSURE"
                    strength = 70
                elif buy_pressure < 35:
                    signal = "STRONG_SELL_PRESSURE"
                    strength = min(95, 50 + (50 - buy_pressure))
                elif buy_pressure < 45:
                    signal = "SELL_PRESSURE"
                    strength = 70
                else:
                    signal = "NEUTRAL"
                    strength = 50
                
                return {
                    "imbalance": imbalance,
                    "buy_pressure": buy_pressure,
                    "sell_pressure": 100 - buy_pressure,
                    "bid_volume": bid_volume,
                    "ask_volume": ask_volume,
                    "signal": signal,
                    "strength": strength
                }
                
        except Exception as e:
            logger.error(f"Error getting order book for {symbol}: {e}")
            return {"imbalance": 0, "signal": "NEUTRAL", "buy_pressure": 50}
    
    async def get_funding_rate(self, symbol: str) -> Dict:
        """
        Funding Rate - Indicador de sentimiento en futuros
        <0.05% = Mercado sano
        >0.1% = Sobrecalentado, posible corrección
        """
        try:
            # Para futuros perpetuos, el símbolo termina en USDT pero necesitamos agregarlo
            futures_symbol = symbol
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://fapi.binance.com/fapi/v1/fundingRate",
                    params={"symbol": futures_symbol, "limit": 1},
                    timeout=5.0
                )
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        funding_rate = float(data[0]['fundingRate']) * 100  # Convert to percentage
                        
                        # Generate signal based on funding rate
                        if funding_rate < 0:
                            signal = "BEARISH_SENTIMENT"
                            strength = 65
                        elif funding_rate < 0.05:
                            signal = "HEALTHY_MARKET"
                            strength = 75
                        elif funding_rate < 0.1:
                            signal = "WARMING_UP"
                            strength = 60
                        else:
                            signal = "OVERHEATED"
                            strength = 80
                        
                        return {
                            "funding_rate": funding_rate,
                            "signal": signal,
                            "strength": strength,
                            "market_health": "HEALTHY" if funding_rate < 0.05 else "OVERHEATED" if funding_rate > 0.1 else "NORMAL"
                        }
        except Exception as e:
            logger.debug(f"Funding rate not available for {symbol}: {e}")
        
        return {
            "funding_rate": 0.05,
            "signal": "NEUTRAL",
            "strength": 50,
            "market_health": "UNKNOWN"
        }
    
    async def get_comprehensive_momentum(self, symbol: str) -> Dict:
        """
        Análisis completo de momentum crypto-nativo
        Combina todos los indicadores para una señal fuerte
        """
        # Ejecutar todos los análisis en paralelo
        results = await asyncio.gather(
            self.calculate_volume_roc(symbol),
            self.calculate_price_acceleration(symbol),
            self.get_order_book_imbalance(symbol),
            self.get_funding_rate(symbol)
        )
        
        vroc_data = results[0]
        acceleration_data = results[1]
        orderbook_data = results[2]
        funding_data = results[3]
        
        # Calculate weighted signal strength
        weights = {
            "volume": 0.35,  # Volume is king in crypto
            "acceleration": 0.25,
            "orderbook": 0.25,
            "funding": 0.15
        }
        
        weighted_strength = (
            vroc_data["strength"] * weights["volume"] +
            acceleration_data["strength"] * weights["acceleration"] +
            orderbook_data["strength"] * weights["orderbook"] +
            funding_data["strength"] * weights["funding"]
        )
        
        # Determine final signal
        buy_signals = 0
        sell_signals = 0
        
        if "BUY" in vroc_data["signal"]:
            buy_signals += 2  # Volume tiene doble peso
        if "SELL" in vroc_data["signal"]:
            sell_signals += 2
            
        if "ACCELERATING_UP" in acceleration_data["signal"] or "GAINING" in acceleration_data["signal"]:
            buy_signals += 1
        if "ACCELERATING_DOWN" in acceleration_data["signal"] or "LOSING" in acceleration_data["signal"]:
            sell_signals += 1
            
        if "BUY_PRESSURE" in orderbook_data["signal"]:
            buy_signals += 1
        if "SELL_PRESSURE" in orderbook_data["signal"]:
            sell_signals += 1
            
        if funding_data["signal"] == "HEALTHY_MARKET":
            buy_signals += 1
        elif funding_data["signal"] == "OVERHEATED":
            sell_signals += 1
        
        # Final decision
        if buy_signals >= 3 and vroc_data["volume_spike"]:
            final_signal = "STRONG_BUY"
        elif buy_signals > sell_signals:
            final_signal = "BUY"
        elif sell_signals > buy_signals:
            final_signal = "SELL"
        else:
            final_signal = "HOLD"
        
        return {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "final_signal": final_signal,
            "confidence": weighted_strength,
            "buy_signals": buy_signals,
            "sell_signals": sell_signals,
            "indicators": {
                "volume_roc": {
                    "value": vroc_data["vroc"],
                    "percent": vroc_data["vroc_percent"],
                    "spike": vroc_data["volume_spike"],
                    "signal": vroc_data["signal"]
                },
                "price_acceleration": {
                    "value": acceleration_data["acceleration"],
                    "velocity": acceleration_data["velocity"],
                    "trend": acceleration_data["trend"],
                    "signal": acceleration_data["signal"]
                },
                "order_flow": {
                    "buy_pressure": orderbook_data["buy_pressure"],
                    "imbalance": orderbook_data["imbalance"],
                    "signal": orderbook_data["signal"]
                },
                "funding_rate": {
                    "value": funding_data["funding_rate"],
                    "health": funding_data["market_health"],
                    "signal": funding_data["signal"]
                }
            },
            "entry_conditions_met": {
                "volume_spike": vroc_data["volume_spike"],
                "positive_acceleration": acceleration_data["acceleration"] > 0.005,
                "buy_pressure": orderbook_data["buy_pressure"] > 55,
                "healthy_funding": funding_data["funding_rate"] < 0.05
            }
        }
    
    async def should_enter_position(self, symbol: str) -> Dict:
        """
        Simple y claro: ¿Deberíamos entrar en posición?
        """
        momentum = await self.get_comprehensive_momentum(symbol)
        
        # Entry conditions (as specified in requirements)
        volume_spike = momentum["indicators"]["volume_roc"]["spike"]
        positive_momentum = momentum["indicators"]["price_acceleration"]["trend"] == "UP"
        healthy_funding = momentum["indicators"]["funding_rate"]["value"] < 0.05
        buy_pressure = momentum["indicators"]["order_flow"]["buy_pressure"] > 55
        
        should_enter = all([
            volume_spike,
            positive_momentum,
            healthy_funding,
            buy_pressure
        ])
        
        return {
            "action": "BUY" if should_enter else "WAIT",
            "confidence": momentum["confidence"],
            "reasons": {
                "volume_spike": "✅" if volume_spike else "❌",
                "positive_momentum": "✅" if positive_momentum else "❌",
                "healthy_funding": "✅" if healthy_funding else "❌",
                "buy_pressure": "✅" if buy_pressure else "❌"
            },
            "momentum_data": momentum
        }
    
    async def should_exit_position(self, symbol: str, entry_price: float) -> Dict:
        """
        Simple y claro: ¿Deberíamos salir de la posición?
        """
        momentum = await self.get_comprehensive_momentum(symbol)
        klines = await self.get_klines(symbol, "15m", 10)
        
        if klines:
            current_price = float(klines[-1][4])
            profit_percent = ((current_price - entry_price) / entry_price) * 100
        else:
            profit_percent = 0
        
        # Exit conditions
        volume_dying = momentum["indicators"]["volume_roc"]["value"] < 0.8
        overheated_funding = momentum["indicators"]["funding_rate"]["value"] > 0.1
        losing_momentum = "LOSING" in momentum["indicators"]["price_acceleration"]["signal"]
        
        # RSI quick calculation for 15min
        if klines and len(klines) > 14:
            closes = [float(k[4]) for k in klines[-14:]]
            gains = []
            losses = []
            for i in range(1, len(closes)):
                change = closes[i] - closes[i-1]
                if change > 0:
                    gains.append(change)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(abs(change))
            
            avg_gain = np.mean(gains) if gains else 0
            avg_loss = np.mean(losses) if losses else 0
            
            if avg_loss != 0:
                rs = avg_gain / avg_loss
                rsi_15min = 100 - (100 / (1 + rs))
            else:
                rsi_15min = 100 if avg_gain > 0 else 50
        else:
            rsi_15min = 50
        
        overbought = rsi_15min > 85
        
        should_exit = any([
            volume_dying,
            overheated_funding,
            losing_momentum and profit_percent > 0,  # Solo salir con momentum negativo si hay profit
            overbought
        ])
        
        # Force exit on big loss
        if profit_percent < -5:
            should_exit = True
        
        return {
            "action": "SELL" if should_exit else "HOLD",
            "profit_percent": profit_percent,
            "reasons": {
                "volume_dying": "⚠️" if volume_dying else "✅",
                "overheated_funding": "⚠️" if overheated_funding else "✅",
                "losing_momentum": "⚠️" if losing_momentum else "✅",
                "overbought_rsi": f"⚠️ ({rsi_15min:.0f})" if overbought else "✅"
            },
            "indicators": {
                "current_vroc": momentum["indicators"]["volume_roc"]["value"],
                "funding_rate": momentum["indicators"]["funding_rate"]["value"],
                "rsi_15min": rsi_15min,
                "momentum": momentum["indicators"]["price_acceleration"]["signal"]
            }
        }

# Testing
async def test_momentum_detector():
    """Test the momentum detector with real data"""
    detector = CryptoMomentumDetector()
    
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    
    for symbol in symbols:
        print(f"\n{'='*60}")
        print(f"Testing {symbol}")
        print('='*60)
        
        # Test comprehensive momentum
        momentum = await detector.get_comprehensive_momentum(symbol)
        print(f"\n📊 MOMENTUM ANALYSIS:")
        print(f"Signal: {momentum['final_signal']}")
        print(f"Confidence: {momentum['confidence']:.1f}%")
        print(f"\nIndicators:")
        print(f"  Volume ROC: {momentum['indicators']['volume_roc']['percent']:.1f}% - {momentum['indicators']['volume_roc']['signal']}")
        print(f"  Acceleration: {momentum['indicators']['price_acceleration']['value']:.4f} - {momentum['indicators']['price_acceleration']['signal']}")
        print(f"  Order Flow: {momentum['indicators']['order_flow']['buy_pressure']:.1f}% buy pressure")
        print(f"  Funding: {momentum['indicators']['funding_rate']['value']:.3f}% - {momentum['indicators']['funding_rate']['health']}")
        
        # Test entry signal
        entry = await detector.should_enter_position(symbol)
        print(f"\n🎯 ENTRY SIGNAL: {entry['action']}")
        for condition, status in entry['reasons'].items():
            print(f"  {condition}: {status}")
        
        # Test exit signal (simulate entry at current price)
        klines = await detector.get_klines(symbol, "15m", 1)
        if klines:
            current_price = float(klines[0][4])
            exit_signal = await detector.should_exit_position(symbol, current_price * 0.98)  # Simulate 2% profit
            print(f"\n🚪 EXIT SIGNAL: {exit_signal['action']} (P&L: {exit_signal['profit_percent']:.2f}%)")
            for condition, status in exit_signal['reasons'].items():
                print(f"  {condition}: {status}")

if __name__ == "__main__":
    asyncio.run(test_momentum_detector())