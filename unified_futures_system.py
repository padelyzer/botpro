#!/usr/bin/env python3
"""
Sistema Unificado de Trading de Futuros
Capital: $220 USD
UI: Botphia en http://localhost:5175
"""

import asyncio
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =====================================
# CONFIGURACIÓN
# =====================================
CAPITAL = 220.0
MAX_RISK_PER_TRADE = 0.02  # 2% = $4.40
DEFAULT_LEVERAGE = 3  # Conservador para $220
MAX_LEVERAGE = 5

app = FastAPI(title="Unified Futures Trading System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================
# ANÁLISIS DE MERCADO
# =====================================

class MarketAnalyzer:
    """Analiza condiciones del mercado para generar señales"""
    
    @staticmethod
    async def get_market_data(symbol: str) -> Optional[Dict]:
        """Obtiene datos reales del mercado desde Binance"""
        async with httpx.AsyncClient() as client:
            try:
                # Precio actual
                price_resp = await client.get(
                    f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol}"
                )
                price = float(price_resp.json()["price"])
                
                # Ticker 24h
                ticker_resp = await client.get(
                    f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={symbol}"
                )
                ticker = ticker_resp.json()
                
                # Funding rate
                funding_resp = await client.get(
                    f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&limit=1"
                )
                funding = funding_resp.json()[0] if funding_resp.status_code == 200 else {"fundingRate": 0}
                
                # Open Interest
                oi_resp = await client.get(
                    f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}"
                )
                oi = oi_resp.json() if oi_resp.status_code == 200 else {"openInterest": 0}
                
                return {
                    "symbol": symbol,
                    "price": price,
                    "change_24h": float(ticker["priceChangePercent"]),
                    "volume_24h": float(ticker["volume"]),
                    "volume_usdt": float(ticker["quoteVolume"]),
                    "high_24h": float(ticker["highPrice"]),
                    "low_24h": float(ticker["lowPrice"]),
                    "funding_rate": float(funding.get("fundingRate", 0)),
                    "open_interest": float(oi.get("openInterest", 0))
                }
            except Exception as e:
                logger.error(f"Error getting market data for {symbol}: {e}")
                return None
    
    @staticmethod
    def calculate_signal_strength(data: Dict) -> Dict:
        """Calcula la fuerza y dirección de la señal"""
        price = data["price"]
        change = data["change_24h"]
        
        # Posición del precio en el rango del día
        price_range = data["high_24h"] - data["low_24h"]
        if price_range > 0:
            price_position = (price - data["low_24h"]) / price_range
        else:
            price_position = 0.5
        
        # Análisis de presión por funding
        funding_pressure = "NEUTRAL"
        if data["funding_rate"] > 0.001:  # > 0.1%
            funding_pressure = "LONG_HEAVY"  # Muchos longs, posible corrección
        elif data["funding_rate"] < -0.0005:  # < -0.05%
            funding_pressure = "SHORT_HEAVY"  # Muchos shorts, posible squeeze
        
        # Lógica de señales
        signal_type = None
        confidence = 0
        reasons = []
        
        # SEÑAL 1: Reversión en extremos (más confiable)
        if change < -3 and price_position < 0.3:
            signal_type = "LONG"
            confidence = min(85, 60 + abs(change) * 3)
            reasons.append(f"Caída fuerte ({change:.1f}%) con precio en zona baja")
            if funding_pressure == "LONG_HEAVY":
                confidence -= 10  # Reducir confianza si hay muchos longs
                
        elif change > 3 and price_position > 0.7:
            signal_type = "SHORT"
            confidence = min(85, 60 + change * 3)
            reasons.append(f"Subida fuerte ({change:.1f}%) con precio en zona alta")
            if funding_pressure == "SHORT_HEAVY":
                confidence -= 10  # Reducir confianza si hay muchos shorts
        
        # SEÑAL 2: Momentum con volumen
        elif data["volume_usdt"] > 100_000_000:  # > $100M volumen
            if change < -2 and price_position < 0.4:
                signal_type = "LONG"
                confidence = 70
                reasons.append("Alto volumen en caída, posible rebote")
            elif change > 2 and price_position > 0.6:
                signal_type = "SHORT"
                confidence = 70
                reasons.append("Alto volumen en subida, posible corrección")
        
        # SEÑAL 3: Squeeze de posiciones
        if funding_pressure == "SHORT_HEAVY" and change > 0:
            signal_type = "LONG"
            confidence = max(confidence, 65)
            reasons.append("Posible short squeeze")
        elif funding_pressure == "LONG_HEAVY" and change < 0:
            signal_type = "SHORT"
            confidence = max(confidence, 65)
            reasons.append("Posible long squeeze")
        
        return {
            "type": signal_type,
            "confidence": confidence,
            "reasons": reasons,
            "price_position": price_position,
            "funding_pressure": funding_pressure
        }

class SignalGenerator:
    """Genera señales de trading con gestión de riesgo"""
    
    @staticmethod
    def calculate_position_size(capital: float, leverage: int, risk_percent: float = 0.02) -> float:
        """Calcula el tamaño de posición basado en el riesgo"""
        risk_amount = capital * risk_percent
        position_size = risk_amount * leverage
        return position_size
    
    @staticmethod
    def generate_signal(market_data: Dict, analysis: Dict) -> Optional[Dict]:
        """Genera una señal completa de trading"""
        if not analysis["type"] or analysis["confidence"] < 60:
            return None
        
        price = market_data["price"]
        signal_type = analysis["type"]
        
        # Calcular niveles de entrada y salida
        if signal_type == "LONG":
            stop_loss = price * 0.98  # 2% stop loss
            take_profit_1 = price * 1.02  # 2% TP1
            take_profit_2 = price * 1.04  # 4% TP2
            take_profit_3 = price * 1.06  # 6% TP3
        else:  # SHORT
            stop_loss = price * 1.02
            take_profit_1 = price * 0.98
            take_profit_2 = price * 0.96
            take_profit_3 = price * 0.94
        
        # Calcular risk/reward
        risk = abs(price - stop_loss)
        reward = abs(take_profit_2 - price)
        risk_reward = reward / risk if risk > 0 else 0
        
        # Solo generar señal si R:R > 1.5
        if risk_reward < 1.5:
            return None
        
        # Calcular tamaño de posición
        position_size = SignalGenerator.calculate_position_size(
            CAPITAL, 
            DEFAULT_LEVERAGE, 
            MAX_RISK_PER_TRADE
        )
        
        return {
            "id": f"{market_data['symbol']}_{int(datetime.now().timestamp())}",
            "symbol": market_data["symbol"],
            "type": signal_type,
            "entry_price": price,
            "stop_loss": stop_loss,
            "take_profit": take_profit_2,  # TP principal
            "take_profit_levels": {
                "tp1": take_profit_1,
                "tp2": take_profit_2,
                "tp3": take_profit_3
            },
            "position_size": position_size,
            "leverage": DEFAULT_LEVERAGE,
            "confidence": analysis["confidence"],
            "risk_reward_ratio": risk_reward,
            "strategy_name": "Unified Futures System",
            "strategy_version": "2.0",
            "market_regime": SignalGenerator.get_market_regime(market_data),
            "metadata": {
                "capital": CAPITAL,
                "risk_amount": CAPITAL * MAX_RISK_PER_TRADE,
                "price_change_24h": market_data["change_24h"],
                "volume_24h_usdt": market_data["volume_usdt"],
                "funding_rate": market_data["funding_rate"],
                "open_interest": market_data["open_interest"],
                "price_position": f"{analysis['price_position']:.1%}",
                "funding_pressure": analysis["funding_pressure"],
                "reasons": analysis["reasons"]
            },
            "timestamp": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(minutes=15)).isoformat()
        }
    
    @staticmethod
    def get_market_regime(data: Dict) -> str:
        """Determina el régimen del mercado"""
        change = abs(data["change_24h"])
        if change > 5:
            return "HIGHLY_VOLATILE"
        elif change > 3:
            return "VOLATILE"
        elif change > 1:
            return "TRENDING"
        else:
            return "RANGING"

# =====================================
# SISTEMA PRINCIPAL
# =====================================

class UnifiedFuturesSystem:
    """Sistema principal unificado"""
    
    def __init__(self):
        self.analyzer = MarketAnalyzer()
        self.generator = SignalGenerator()
        self.active_signals = []
        self.positions = {}
        
    async def scan_market(self) -> List[Dict]:
        """Escanea el mercado en busca de oportunidades"""
        # Símbolos principales a analizar
        symbols = [
            "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", 
            "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT",
            "DOTUSDT", "MATICUSDT", "LINKUSDT", "UNIUSDT",
            "LTCUSDT", "ATOMUSDT", "NEARUSDT", "ARBUSDT"
        ]
        
        signals = []
        
        for symbol in symbols:
            try:
                # Obtener datos del mercado
                market_data = await self.analyzer.get_market_data(symbol)
                if not market_data:
                    continue
                
                # Analizar señal
                analysis = self.analyzer.calculate_signal_strength(market_data)
                
                # Generar señal si hay oportunidad
                signal = self.generator.generate_signal(market_data, analysis)
                if signal:
                    signals.append(signal)
                    logger.info(f"Signal generated for {symbol}: {signal['type']} @ {signal['entry_price']}")
                    
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
        
        # Ordenar por confianza y retornar las mejores
        signals.sort(key=lambda x: x["confidence"], reverse=True)
        return signals[:5]  # Máximo 5 señales activas

# Instancia global
system = UnifiedFuturesSystem()

# =====================================
# API ENDPOINTS
# =====================================

@app.get("/api/signals")
async def get_signals():
    """Obtiene señales de trading activas"""
    try:
        signals = await system.scan_market()
        return signals
    except Exception as e:
        logger.error(f"Error generating signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/signals/all")
async def get_all_signals():
    """Alias para compatibilidad con botphia"""
    return await get_signals()

@app.get("/api/recent-signals")
async def get_recent_signals(limit: int = 10):
    """Obtiene señales recientes"""
    return await get_signals()

@app.get("/api/status")
async def get_status():
    """Estado del sistema"""
    return {
        "capital": CAPITAL,
        "active_signals": len(system.active_signals),
        "positions": len(system.positions),
        "total_pnl": 0,
        "max_risk_per_trade": MAX_RISK_PER_TRADE,
        "default_leverage": DEFAULT_LEVERAGE,
        "components": {
            "market_analyzer": "active",
            "signal_generator": "active",
            "risk_manager": "active",
            "position_manager": "active"
        }
    }

@app.get("/api/liquidity/{symbol}")
async def analyze_liquidity(symbol: str):
    """Análisis de liquidez para un símbolo"""
    symbol = symbol.upper()
    if not symbol.endswith("USDT"):
        symbol += "USDT"
    
    data = await system.analyzer.get_market_data(symbol)
    if not data:
        raise HTTPException(status_code=404, detail="Symbol not found")
    
    # Análisis simple de liquidez
    price = data["price"]
    change = data["change_24h"]
    
    # Zonas de liquidación estimadas
    liquidation_zones = {
        "long_liquidations": [
            {"leverage": "5x", "price": price * 0.84, "distance": f"{16:.1f}%"},
            {"leverage": "10x", "price": price * 0.92, "distance": f"{8:.1f}%"},
            {"leverage": "20x", "price": price * 0.96, "distance": f"{4:.1f}%"}
        ],
        "short_liquidations": [
            {"leverage": "5x", "price": price * 1.16, "distance": f"{16:.1f}%"},
            {"leverage": "10x", "price": price * 1.08, "distance": f"{8:.1f}%"},
            {"leverage": "20x", "price": price * 1.04, "distance": f"{4:.1f}%"}
        ]
    }
    
    # Determinar presión
    if data["funding_rate"] > 0.001:
        pressure = "LONG_HEAVY"
        outlook = "POTENTIAL_CORRECTION"
    elif data["funding_rate"] < -0.0005:
        pressure = "SHORT_HEAVY"
        outlook = "POTENTIAL_SQUEEZE"
    else:
        pressure = "BALANCED"
        outlook = "NEUTRAL"
    
    return {
        "symbol": symbol,
        "current_price": price,
        "change_24h": f"{change:.2f}%",
        "funding_rate": f"{data['funding_rate']*100:.4f}%",
        "open_interest": f"${data['open_interest']:,.0f}",
        "liquidation_pressure": pressure,
        "short_term_outlook": outlook,
        "liquidation_zones": liquidation_zones,
        "key_levels": {
            "support": data["low_24h"],
            "resistance": data["high_24h"],
            "current": price
        }
    }

@app.get("/api/analysis/{symbol}")
async def analyze_symbol(symbol: str):
    """Análisis completo de un símbolo"""
    symbol = symbol.upper()
    if not symbol.endswith("USDT"):
        symbol += "USDT"
    
    market_data = await system.analyzer.get_market_data(symbol)
    if not market_data:
        raise HTTPException(status_code=404, detail="Symbol not found")
    
    analysis = system.analyzer.calculate_signal_strength(market_data)
    signal = system.generator.generate_signal(market_data, analysis)
    
    return {
        "market_data": market_data,
        "analysis": analysis,
        "signal": signal,
        "recommendation": "TRADE" if signal else "WAIT"
    }

if __name__ == "__main__":
    import uvicorn
    print("="*60)
    print("SISTEMA UNIFICADO DE FUTUROS")
    print(f"Capital: ${CAPITAL}")
    print(f"Riesgo por trade: {MAX_RISK_PER_TRADE*100}% (${CAPITAL*MAX_RISK_PER_TRADE})")
    print(f"Leverage: {DEFAULT_LEVERAGE}x (max {MAX_LEVERAGE}x)")
    print("="*60)
    print("UI: http://localhost:5175 (Botphia)")
    print("API: http://localhost:8002")
    print("="*60)
    print("Endpoints principales:")
    print("  - /api/signals - Señales de trading")
    print("  - /api/status - Estado del sistema")
    print("  - /api/liquidity/{symbol} - Análisis de liquidez")
    print("  - /api/analysis/{symbol} - Análisis completo")
    print("="*60)
    
    uvicorn.run(app, host="0.0.0.0", port=8002)