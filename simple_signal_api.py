#!/usr/bin/env python3
"""
API Simplificada para generar señales reales de futuros
Compatible con botphia UI
"""

import asyncio
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
from datetime import datetime, timedelta
import random

app = FastAPI(title="Simple Futures Signals API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def get_market_data(symbol: str) -> Dict:
    """Obtiene datos reales del mercado"""
    async with httpx.AsyncClient() as client:
        try:
            # Precio actual
            price_resp = await client.get(f"https://fapi.binance.com/fapi/v1/ticker/price?symbol={symbol}")
            price = float(price_resp.json()["price"])
            
            # Ticker 24h
            ticker_resp = await client.get(f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={symbol}")
            ticker = ticker_resp.json()
            
            return {
                "price": price,
                "change_24h": float(ticker["priceChangePercent"]),
                "volume": float(ticker["volume"]),
                "high_24h": float(ticker["highPrice"]),
                "low_24h": float(ticker["lowPrice"])
            }
        except:
            return None

async def analyze_signal(symbol: str) -> Dict:
    """Analiza si generar señal para un símbolo"""
    data = await get_market_data(symbol)
    if not data:
        return None
    
    # Análisis simple basado en cambio 24h y posición del precio
    price = data["price"]
    change = data["change_24h"]
    price_position = (price - data["low_24h"]) / (data["high_24h"] - data["low_24h"]) if data["high_24h"] != data["low_24h"] else 0.5
    
    # Lógica de señales
    signal = None
    confidence = 0
    
    # Señal LONG: caída > 3% y precio cerca del mínimo
    if change < -3 and price_position < 0.3:
        signal = "LONG"
        confidence = min(85, 60 + abs(change) * 2)
        stop_loss = price * 0.98
        take_profit = price * 1.04
        
    # Señal SHORT: subida > 3% y precio cerca del máximo
    elif change > 3 and price_position > 0.7:
        signal = "SHORT"
        confidence = min(85, 60 + change * 2)
        stop_loss = price * 1.02
        take_profit = price * 0.96
        
    # Señal LONG: recuperación después de caída
    elif change < -1 and price_position < 0.4:
        signal = "LONG"
        confidence = 65
        stop_loss = price * 0.985
        take_profit = price * 1.03
        
    # Señal SHORT: sobrecomprado
    elif change > 2 and price_position > 0.8:
        signal = "SHORT"
        confidence = 65
        stop_loss = price * 1.015
        take_profit = price * 0.97
    
    if signal and confidence >= 60:
        return {
            "id": f"{symbol}_{int(datetime.now().timestamp())}",
            "symbol": symbol,
            "type": signal,
            "entry_price": price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "confidence": confidence,
            "risk_reward_ratio": abs((take_profit - price) / (price - stop_loss)),
            "strategy_name": "Market Extremes",
            "strategy_version": "1.0",
            "market_regime": "VOLATILE" if abs(change) > 3 else "TRENDING",
            "metadata": {
                "leverage": 3,
                "price_change_24h": change,
                "price_position": f"{price_position:.2%}",
                "volume_24h": data["volume"],
                "reasons": [
                    f"Cambio 24h: {change:.2f}%",
                    f"Posición del precio: {price_position:.2%}",
                    f"Volumen: ${data['volume']/1e6:.1f}M"
                ]
            },
            "timestamp": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(minutes=15)).isoformat()
        }
    
    return None

@app.get("/api/signals")
async def get_signals():
    """Genera señales de trading reales"""
    symbols = [
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", 
        "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT",
        "DOTUSDT", "MATICUSDT", "LINKUSDT", "UNIUSDT"
    ]
    
    signals = []
    for symbol in symbols:
        signal = await analyze_signal(symbol)
        if signal:
            signals.append(signal)
    
    # Ordenar por confianza
    signals.sort(key=lambda x: x["confidence"], reverse=True)
    
    return signals[:5]  # Máximo 5 señales

@app.get("/api/signals/all")
async def get_all_signals():
    """Alias para botphia"""
    return await get_signals()

@app.get("/api/recent-signals")
async def get_recent_signals(limit: int = 10):
    """Alias para botphia"""
    return await get_signals()

@app.get("/api/status")
async def get_status():
    """Estado del sistema"""
    return {
        "capital": 220,
        "active_signals": 0,
        "positions": 0,
        "total_pnl": 0,
        "components": {
            "market_analyzer": "active",
            "signal_generator": "active",
            "risk_manager": "active"
        }
    }

@app.get("/api/liquidity/{symbol}")
async def get_liquidity(symbol: str):
    """Análisis de liquidez simplificado"""
    data = await get_market_data(symbol.upper() + "USDT" if not symbol.endswith("USDT") else symbol)
    
    if not data:
        raise HTTPException(status_code=404, detail="Symbol not found")
    
    return {
        "symbol": symbol,
        "current_situation": f"{data['change_24h']:.1f}% change",
        "liquidation_pressure": "BALANCED",
        "short_term_outlook": "CONSOLIDATION" if abs(data['change_24h']) < 2 else "VOLATILE",
        "key_levels": {
            "support": data["low_24h"],
            "resistance": data["high_24h"]
        },
        "recommended_action": "MONITOR",
        "confidence": 60
    }

if __name__ == "__main__":
    import uvicorn
    print("="*60)
    print("SIMPLE FUTURES SIGNALS API")
    print("Capital: $220")
    print("="*60)
    print("Endpoints:")
    print("  - http://localhost:8002/api/signals")
    print("  - http://localhost:8002/api/status")
    print("  - http://localhost:8002/api/liquidity/{symbol}")
    print("="*60)
    
    uvicorn.run(app, host="0.0.0.0", port=8002)