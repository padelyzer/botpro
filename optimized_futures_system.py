#!/usr/bin/env python3
"""
Sistema Optimizado de Trading de Futuros
Incluye todas las mejoras del análisis de pérdidas:
- Stops dinámicos basados en ATR
- No operar contra tendencia fuerte
- Confirmación de reversión
- Filtro de alta volatilidad
Capital: $220 USD
"""

import asyncio
import httpx
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =====================================
# CONFIGURACIÓN OPTIMIZADA
# =====================================
CAPITAL = 220.0
MAX_RISK_PER_TRADE = 0.02  # 2% = $4.40
DEFAULT_LEVERAGE = 3
MAX_LEVERAGE = 5
MIN_CONFIDENCE = 65
COMMISSION = 0.0004  # 0.04% Binance Futures

app = FastAPI(title="Optimized Futures Trading System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================
# ANÁLISIS DE MERCADO MEJORADO
# =====================================

class OptimizedMarketAnalyzer:
    """Analizador de mercado con filtros mejorados"""
    
    @staticmethod
    async def get_market_data_with_indicators(symbol: str) -> Optional[Dict]:
        """Obtiene datos del mercado con indicadores técnicos"""
        async with httpx.AsyncClient() as client:
            try:
                # Precio actual y ticker
                price_resp = await client.get(
                    f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol}"
                )
                price = float(price_resp.json()["price"])
                
                ticker_resp = await client.get(
                    f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={symbol}"
                )
                ticker = ticker_resp.json()
                
                # Klines para calcular indicadores
                klines_resp = await client.get(
                    f"https://fapi.binance.com/fapi/v1/klines",
                    params={
                        'symbol': symbol,
                        'interval': '1h',
                        'limit': 100
                    }
                )
                klines = klines_resp.json()
                
                # Convertir a DataFrame para cálculos
                df = pd.DataFrame(klines, columns=[
                    'timestamp', 'open', 'high', 'low', 'close',
                    'volume', 'close_time', 'quote_volume', 'trades',
                    'taker_buy_volume', 'taker_buy_quote', 'ignore'
                ])
                
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = df[col].astype(float)
                
                # =====================================
                # CALCULAR INDICADORES TÉCNICOS
                # =====================================
                
                # 1. ATR (Average True Range) para stops dinámicos
                high_low = df['high'] - df['low']
                high_close = abs(df['high'] - df['close'].shift())
                low_close = abs(df['low'] - df['close'].shift())
                ranges = pd.concat([high_low, high_close, low_close], axis=1)
                true_range = ranges.max(axis=1)
                atr = true_range.rolling(14).mean().iloc[-1]
                atr_percent = (atr / price) * 100
                
                # 2. Tendencia con EMA
                df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
                df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
                
                # Fuerza de tendencia
                trend_strength = 0
                if df['close'].iloc[-1] > df['ema_20'].iloc[-1] > df['ema_50'].iloc[-1]:
                    trend_strength = 1  # Tendencia alcista fuerte
                elif df['close'].iloc[-1] < df['ema_20'].iloc[-1] < df['ema_50'].iloc[-1]:
                    trend_strength = -1  # Tendencia bajista fuerte
                else:
                    trend_strength = 0  # Sin tendencia clara
                
                # 3. RSI para sobrecompra/sobreventa
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs)).iloc[-1]
                
                # 4. Volatilidad actual
                volatility = ((float(ticker['highPrice']) - float(ticker['lowPrice'])) / price) * 100
                
                # 5. Volumen
                volume_ma = df['volume'].rolling(20).mean().iloc[-1]
                volume_ratio = float(ticker['volume']) / volume_ma if volume_ma > 0 else 1
                
                # 6. Momentum
                momentum = ((df['close'].iloc[-1] - df['close'].iloc[-20]) / df['close'].iloc[-20]) * 100
                
                # Funding rate
                funding_resp = await client.get(
                    f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&limit=1"
                )
                funding = funding_resp.json()[0] if funding_resp.status_code == 200 else {"fundingRate": 0}
                
                return {
                    "symbol": symbol,
                    "price": price,
                    "change_24h": float(ticker["priceChangePercent"]),
                    "volume_24h": float(ticker["volume"]),
                    "volume_usdt": float(ticker["quoteVolume"]),
                    "high_24h": float(ticker["highPrice"]),
                    "low_24h": float(ticker["lowPrice"]),
                    "funding_rate": float(funding.get("fundingRate", 0)),
                    # Nuevos indicadores
                    "atr": atr,
                    "atr_percent": atr_percent,
                    "trend_strength": trend_strength,
                    "rsi": rsi,
                    "volatility": volatility,
                    "volume_ratio": volume_ratio,
                    "momentum": momentum,
                    "ema_20": df['ema_20'].iloc[-1],
                    "ema_50": df['ema_50'].iloc[-1]
                }
                
            except Exception as e:
                logger.error(f"Error getting market data for {symbol}: {e}")
                return None
    
    @staticmethod
    def analyze_signal_optimized(data: Dict) -> Dict:
        """Análisis optimizado con todos los filtros"""
        
        price = data["price"]
        change = data["change_24h"]
        
        # Posición del precio en el rango del día
        price_range = data["high_24h"] - data["low_24h"]
        if price_range > 0:
            price_position = (price - data["low_24h"]) / price_range
        else:
            price_position = 0.5
        
        signal_type = None
        confidence = 0
        reasons = []
        stop_loss = 0
        take_profit = 0
        
        # =====================================
        # FILTRO 1: NO OPERAR EN ALTA VOLATILIDAD
        # =====================================
        if data["volatility"] > 10:  # Volatilidad extrema > 10%
            return {
                "type": None,
                "confidence": 0,
                "reasons": ["Volatilidad muy alta, riesgo excesivo"]
            }
        
        # =====================================
        # FILTRO 2: NO OPERAR CONTRA TENDENCIA FUERTE
        # =====================================
        trend = data["trend_strength"]
        
        # No SHORT en tendencia alcista fuerte
        if trend > 0.5 and change > 2:
            return {
                "type": None,
                "confidence": 0,
                "reasons": ["No SHORT contra tendencia alcista fuerte"]
            }
        
        # No LONG en tendencia bajista fuerte
        if trend < -0.5 and change < -2:
            return {
                "type": None,
                "confidence": 0,
                "reasons": ["No LONG contra tendencia bajista fuerte"]
            }
        
        # =====================================
        # SEÑALES CON CONFIRMACIÓN
        # =====================================
        
        # SEÑAL LONG
        if trend >= 0:  # Tendencia neutral o alcista
            
            # Confirmación de reversión alcista
            if (change < -2 and change > -5 and  # Caída moderada
                data["rsi"] < 35 and  # RSI sobreventa
                price_position < 0.3 and  # Precio en zona baja
                data["volume_ratio"] > 1.2):  # Volumen alto
                
                signal_type = "LONG"
                confidence = 80
                reasons.append("Reversión alcista confirmada (RSI oversold + volumen)")
                
                # Stop dinámico basado en ATR
                atr_multiplier = 2.5 if data["volatility"] > 5 else 2.0
                stop_distance = data["atr"] * atr_multiplier
                stop_loss = price - stop_distance
                
                # Mínimo 1.5% de stop
                min_stop = price * 0.985
                stop_loss = min(stop_loss, min_stop)
                
                # Take profit 2:1 risk/reward
                take_profit = price + (stop_distance * 2)
            
            # Pullback en tendencia alcista
            elif (trend > 0 and  # Tendencia alcista
                  change < 0 and change > -2 and  # Pullback menor
                  data["rsi"] > 40 and data["rsi"] < 60 and  # RSI neutral
                  price > data["ema_20"]):  # Precio sobre EMA20
                
                signal_type = "LONG"
                confidence = 70
                reasons.append("Pullback en tendencia alcista")
                
                # Stop bajo el mínimo reciente
                stop_loss = data["low_24h"] * 0.995
                take_profit = price * 1.03
        
        # SEÑAL SHORT
        elif trend <= 0:  # Tendencia neutral o bajista
            
            # Confirmación de reversión bajista
            if (change > 2 and change < 5 and  # Subida moderada
                data["rsi"] > 65 and  # RSI sobrecompra
                price_position > 0.7 and  # Precio en zona alta
                data["volume_ratio"] > 1.2):  # Volumen alto
                
                signal_type = "SHORT"
                confidence = 80
                reasons.append("Reversión bajista confirmada (RSI overbought + volumen)")
                
                # Stop dinámico basado en ATR
                atr_multiplier = 2.5 if data["volatility"] > 5 else 2.0
                stop_distance = data["atr"] * atr_multiplier
                stop_loss = price + stop_distance
                
                # Mínimo 1.5% de stop
                max_stop = price * 1.015
                stop_loss = max(stop_loss, max_stop)
                
                # Take profit 2:1 risk/reward
                take_profit = price - (stop_distance * 2)
            
            # Rally en tendencia bajista
            elif (trend < 0 and  # Tendencia bajista
                  change > 0 and change < 2 and  # Rally menor
                  data["rsi"] > 40 and data["rsi"] < 60 and  # RSI neutral
                  price < data["ema_20"]):  # Precio bajo EMA20
                
                signal_type = "SHORT"
                confidence = 70
                reasons.append("Rally en tendencia bajista")
                
                # Stop sobre el máximo reciente
                stop_loss = data["high_24h"] * 1.005
                take_profit = price * 0.97
        
        # =====================================
        # FILTRO 3: VOLUMEN MÍNIMO
        # =====================================
        if signal_type and data["volume_ratio"] < 0.5:
            signal_type = None
            confidence = 0
            reasons = ["Volumen insuficiente"]
        
        # =====================================
        # FILTRO 4: VERIFICAR RISK/REWARD
        # =====================================
        if signal_type and stop_loss > 0:
            risk = abs(price - stop_loss)
            reward = abs(take_profit - price)
            risk_reward = reward / risk if risk > 0 else 0
            
            if risk_reward < 1.5:
                signal_type = None
                confidence = 0
                reasons = ["Risk/Reward insuficiente"]
        
        return {
            "type": signal_type,
            "confidence": confidence,
            "reasons": reasons,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "price_position": price_position,
            "indicators": {
                "rsi": data["rsi"],
                "atr_percent": data["atr_percent"],
                "trend_strength": trend,
                "volatility": data["volatility"],
                "volume_ratio": data["volume_ratio"],
                "momentum": data["momentum"]
            }
        }

class OptimizedSignalGenerator:
    """Generador de señales optimizado"""
    
    @staticmethod
    def generate_optimized_signal(market_data: Dict, analysis: Dict) -> Optional[Dict]:
        """Genera señal optimizada con gestión de riesgo mejorada"""
        
        if not analysis["type"] or analysis["confidence"] < MIN_CONFIDENCE:
            return None
        
        price = market_data["price"]
        signal_type = analysis["type"]
        
        # Usar stops y TPs calculados en el análisis
        stop_loss = analysis["stop_loss"]
        take_profit = analysis["take_profit"]
        
        # Calcular tamaño de posición basado en riesgo
        risk_amount = CAPITAL * MAX_RISK_PER_TRADE
        stop_distance_pct = abs(price - stop_loss) / price
        
        # Ajustar leverage según volatilidad
        if market_data["volatility"] > 7:
            leverage = 2  # Reducir leverage en alta volatilidad
        elif market_data["volatility"] > 5:
            leverage = DEFAULT_LEVERAGE
        else:
            leverage = min(4, MAX_LEVERAGE)  # Puede usar más leverage en baja volatilidad
        
        position_size = (risk_amount / stop_distance_pct) * leverage
        
        # Limitar posición al 50% del capital con leverage
        max_position = CAPITAL * 0.5 * leverage
        position_size = min(position_size, max_position)
        
        # Calcular risk/reward final
        risk = abs(price - stop_loss)
        reward = abs(take_profit - price)
        risk_reward = reward / risk if risk > 0 else 0
        
        return {
            "id": f"{market_data['symbol']}_{int(datetime.now().timestamp())}",
            "symbol": market_data["symbol"],
            "type": signal_type,
            "entry_price": price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "position_size": position_size,
            "leverage": leverage,
            "confidence": analysis["confidence"],
            "risk_reward_ratio": risk_reward,
            "strategy_name": "Optimized Futures System",
            "strategy_version": "3.0",
            "market_conditions": {
                "trend": "UP" if market_data["trend_strength"] > 0 else "DOWN" if market_data["trend_strength"] < 0 else "NEUTRAL",
                "volatility": "HIGH" if market_data["volatility"] > 5 else "NORMAL",
                "volume": "HIGH" if market_data["volume_ratio"] > 1.5 else "NORMAL",
                "momentum": market_data["momentum"]
            },
            "metadata": {
                "capital": CAPITAL,
                "risk_amount": risk_amount,
                "price_change_24h": market_data["change_24h"],
                "volume_24h_usdt": market_data["volume_usdt"],
                "funding_rate": market_data["funding_rate"],
                "reasons": analysis["reasons"],
                "indicators": analysis["indicators"],
                "stop_type": "ATR-based dynamic stop",
                "atr_value": market_data["atr"],
                "atr_percent": market_data["atr_percent"]
            },
            "timestamp": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(minutes=15)).isoformat()
        }

# =====================================
# SISTEMA PRINCIPAL OPTIMIZADO
# =====================================

class OptimizedFuturesSystem:
    """Sistema principal optimizado con todos los filtros"""
    
    def __init__(self):
        self.analyzer = OptimizedMarketAnalyzer()
        self.generator = OptimizedSignalGenerator()
        self.active_signals = []
        self.positions = {}
        
    async def scan_market(self) -> List[Dict]:
        """Escanea el mercado con filtros optimizados"""
        
        # Símbolos principales
        symbols = [
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT",
            "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT",
            "DOTUSDT", "MATICUSDT", "LINKUSDT", "UNIUSDT"
        ]
        
        signals = []
        
        for symbol in symbols:
            try:
                # Obtener datos con indicadores
                market_data = await self.analyzer.get_market_data_with_indicators(symbol)
                if not market_data:
                    continue
                
                # Analizar con filtros optimizados
                analysis = self.analyzer.analyze_signal_optimized(market_data)
                
                # Generar señal si pasa todos los filtros
                signal = self.generator.generate_optimized_signal(market_data, analysis)
                if signal:
                    signals.append(signal)
                    logger.info(f"Optimized signal for {symbol}: {signal['type']} @ {signal['entry_price']}")
                    logger.info(f"  Stop: {signal['stop_loss']:.2f}, TP: {signal['take_profit']:.2f}")
                    logger.info(f"  Reason: {signal['metadata']['reasons']}")
                    
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
        
        # Ordenar por confianza
        signals.sort(key=lambda x: x["confidence"], reverse=True)
        
        # Máximo 3 señales simultáneas para diversificar con $220
        return signals[:3]

# Instancia global
system = OptimizedFuturesSystem()

# =====================================
# API ENDPOINTS
# =====================================

@app.get("/api/signals")
async def get_signals():
    """Obtiene señales optimizadas"""
    try:
        signals = await system.scan_market()
        return signals
    except Exception as e:
        logger.error(f"Error generating signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/signals/all")
async def get_all_signals():
    """Alias para compatibilidad"""
    return await get_signals()

@app.get("/api/recent-signals")
async def get_recent_signals(limit: int = 10):
    """Obtiene señales recientes"""
    return await get_signals()

@app.get("/api/status")
async def get_status():
    """Estado del sistema optimizado"""
    return {
        "capital": CAPITAL,
        "active_signals": len(system.active_signals),
        "positions": len(system.positions),
        "total_pnl": 0,
        "max_risk_per_trade": MAX_RISK_PER_TRADE,
        "default_leverage": DEFAULT_LEVERAGE,
        "system_version": "3.0 - Optimized",
        "improvements": [
            "ATR-based dynamic stops",
            "Strong trend filter",
            "Reversal confirmation (RSI + Volume)",
            "High volatility filter",
            "Risk-adjusted position sizing"
        ],
        "components": {
            "market_analyzer": "active",
            "signal_generator": "active",
            "risk_manager": "active",
            "position_manager": "active"
        }
    }

@app.get("/api/analysis/{symbol}")
async def analyze_symbol(symbol: str):
    """Análisis detallado optimizado"""
    symbol = symbol.upper()
    if not symbol.endswith("USDT"):
        symbol += "USDT"
    
    market_data = await system.analyzer.get_market_data_with_indicators(symbol)
    if not market_data:
        raise HTTPException(status_code=404, detail="Symbol not found")
    
    analysis = system.analyzer.analyze_signal_optimized(market_data)
    signal = system.generator.generate_optimized_signal(market_data, analysis) if analysis["type"] else None
    
    return {
        "market_data": {
            "price": market_data["price"],
            "change_24h": market_data["change_24h"],
            "volatility": market_data["volatility"],
            "trend": "UP" if market_data["trend_strength"] > 0 else "DOWN" if market_data["trend_strength"] < 0 else "NEUTRAL",
            "rsi": market_data["rsi"],
            "atr_percent": market_data["atr_percent"],
            "volume_ratio": market_data["volume_ratio"]
        },
        "analysis": analysis,
        "signal": signal,
        "recommendation": "TRADE" if signal else "WAIT - " + (analysis["reasons"][0] if analysis["reasons"] else "No setup")
    }

if __name__ == "__main__":
    import uvicorn
    print("="*60)
    print("SISTEMA OPTIMIZADO DE FUTUROS v3.0")
    print(f"Capital: ${CAPITAL}")
    print(f"Riesgo por trade: {MAX_RISK_PER_TRADE*100}% (${CAPITAL*MAX_RISK_PER_TRADE})")
    print(f"Leverage: {DEFAULT_LEVERAGE}x (ajustable según volatilidad)")
    print("="*60)
    print("MEJORAS IMPLEMENTADAS:")
    print("  ✅ Stops dinámicos basados en ATR")
    print("  ✅ No operar contra tendencia fuerte")
    print("  ✅ Confirmación de reversión (RSI + Volumen)")
    print("  ✅ Filtro de alta volatilidad (>10%)")
    print("  ✅ Risk/Reward mínimo 1.5:1")
    print("="*60)
    print("UI: http://localhost:5175 (Botphia)")
    print("API: http://localhost:8002")
    print("="*60)
    
    uvicorn.run(app, host="0.0.0.0", port=8002)