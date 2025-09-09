#!/usr/bin/env python3
"""
Liquidity API Server
Serves real-time liquidity data from Binance to the UI
"""

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import httpx
import json
from datetime import datetime
import uvicorn
from typing import Dict, List

app = FastAPI()

# Enable CORS for the UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

class LiquidityAnalyzer:
    def __init__(self):
        self.binance_spot = "https://api.binance.com/api/v3"
        self.binance_futures = "https://fapi.binance.com/fapi/v1"
        
    async def get_order_book(self, symbol: str, limit: int = 500):
        """Get order book depth"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.binance_spot}/depth",
                params={"symbol": symbol, "limit": limit}
            )
            return response.json() if response.status_code == 200 else {}
    
    async def get_ticker(self, symbol: str):
        """Get current price and 24h data"""
        async with httpx.AsyncClient() as client:
            # Current price
            price_resp = await client.get(
                f"{self.binance_spot}/ticker/price",
                params={"symbol": symbol}
            )
            
            # 24h data
            ticker_resp = await client.get(
                f"{self.binance_spot}/ticker/24hr",
                params={"symbol": symbol}
            )
            
            price_data = price_resp.json() if price_resp.status_code == 200 else {}
            ticker_data = ticker_resp.json() if ticker_resp.status_code == 200 else {}
            
            return {
                "price": float(price_data.get("price", 0)),
                "high_24h": float(ticker_data.get("highPrice", 0)),
                "low_24h": float(ticker_data.get("lowPrice", 0)),
                "change_24h": float(ticker_data.get("priceChangePercent", 0)),
                "volume_24h": float(ticker_data.get("volume", 0))
            }
    
    def analyze_liquidity_zones(self, order_book: Dict, current_price: float):
        """Analyze liquidity concentration zones"""
        bids = order_book.get("bids", [])
        asks = order_book.get("asks", [])
        
        # Support zones (bids)
        support_zones = []
        price_ranges = [
            (current_price * 0.99, current_price * 0.985),  # -1% to -1.5%
            (current_price * 0.98, current_price * 0.97),   # -2% to -3%
            (current_price * 0.96, current_price * 0.95),   # -4% to -5%
        ]
        
        for range_min, range_max in price_ranges:
            zone_liquidity = 0
            zone_orders = 0
            
            for bid in bids:
                price = float(bid[0])
                quantity = float(bid[1])
                
                if range_min <= price <= range_max:
                    zone_liquidity += price * quantity
                    zone_orders += 1
            
            if zone_liquidity > 0:
                support_zones.append({
                    "price": (range_min + range_max) / 2,
                    "liquidity": zone_liquidity,
                    "orders": zone_orders,
                    "distance": ((((range_min + range_max) / 2) - current_price) / current_price) * 100
                })
        
        # Resistance zones (asks)
        resistance_zones = []
        price_ranges = [
            (current_price * 1.01, current_price * 1.015),  # +1% to +1.5%
            (current_price * 1.02, current_price * 1.03),   # +2% to +3%
            (current_price * 1.04, current_price * 1.05),   # +4% to +5%
        ]
        
        for range_min, range_max in price_ranges:
            zone_liquidity = 0
            zone_orders = 0
            
            for ask in asks:
                price = float(ask[0])
                quantity = float(ask[1])
                
                if range_min <= price <= range_max:
                    zone_liquidity += price * quantity
                    zone_orders += 1
            
            if zone_liquidity > 0:
                resistance_zones.append({
                    "price": (range_min + range_max) / 2,
                    "liquidity": zone_liquidity,
                    "orders": zone_orders,
                    "distance": ((((range_min + range_max) / 2) - current_price) / current_price) * 100
                })
        
        return support_zones, resistance_zones
    
    def calculate_liquidation_zones(self, current_price: float):
        """Calculate where leveraged positions will be liquidated"""
        if current_price is None or current_price <= 0:
            return {"longs": [], "shorts": []}
            
        liquidations = {
            "longs": [],
            "shorts": []
        }
        
        # Long liquidations (price goes down)
        leverages = [100, 75, 50, 25, 20, 10]
        for leverage in leverages:
            liq_price = current_price * (1 - (1 / leverage) + 0.005)  # Including fees
            liquidations["longs"].append({
                "leverage": f"{leverage}x",
                "price": liq_price,
                "distance": ((liq_price - current_price) / current_price) * 100 if current_price != 0 else 0,
                "isMagnet": leverage >= 50  # High leverage = magnet
            })
        
        # Short liquidations (price goes up)
        for leverage in leverages:
            liq_price = current_price * (1 + (1 / leverage) - 0.005)
            liquidations["shorts"].append({
                "leverage": f"{leverage}x",
                "price": liq_price,
                "distance": ((liq_price - current_price) / current_price) * 100 if current_price != 0 else 0,
                "isMagnet": leverage >= 50
            })
        
        return liquidations
    
    def detect_signal(self, ticker_data: Dict, support_zones: List, 
                     resistance_zones: List, imbalance: float):
        """Detect trading signal based on liquidity"""
        current_price = ticker_data["price"]
        
        # Find strongest support/resistance
        strongest_support = max(support_zones, key=lambda x: x["liquidity"]) if support_zones else None
        strongest_resistance = max(resistance_zones, key=lambda x: x["liquidity"]) if resistance_zones else None
        
        signal = None
        
        # LONG signal conditions
        if strongest_support and abs(strongest_support["distance"]) < 3:  # Within 3% of support
            if imbalance > 30:  # Strong buying pressure
                signal = {
                    "type": "LONG",
                    "confidence": min(70 + abs(imbalance) / 2, 95),
                    "entry": current_price,
                    "target": current_price * 1.05,
                    "stop": strongest_support["price"] * 0.98,
                    "reason": f"Strong support at ${strongest_support['price']:.2f} with {imbalance:.1f}% buy pressure"
                }
        
        # SHORT signal conditions
        elif strongest_resistance and abs(strongest_resistance["distance"]) < 3:
            if imbalance < -30:  # Strong selling pressure
                signal = {
                    "type": "SHORT",
                    "confidence": min(70 + abs(imbalance) / 2, 95),
                    "entry": current_price,
                    "target": current_price * 0.95,
                    "stop": strongest_resistance["price"] * 1.02,
                    "reason": f"Strong resistance at ${strongest_resistance['price']:.2f} with {abs(imbalance):.1f}% sell pressure"
                }
        
        return signal
    
    async def analyze_symbol(self, symbol: str):
        """Complete analysis for a symbol"""
        # Get market data
        ticker_data = await self.get_ticker(symbol)
        order_book = await self.get_order_book(symbol)
        
        if not ticker_data or not order_book:
            return None
        
        current_price = ticker_data["price"]
        
        # Analyze liquidity zones
        support_zones, resistance_zones = self.analyze_liquidity_zones(order_book, current_price)
        
        # Calculate liquidation zones
        liquidations = self.calculate_liquidation_zones(current_price)
        
        # Calculate imbalance
        total_bid_value = sum(float(bid[0]) * float(bid[1]) for bid in order_book.get("bids", []))
        total_ask_value = sum(float(ask[0]) * float(ask[1]) for ask in order_book.get("asks", []))
        
        if total_bid_value + total_ask_value > 0:
            imbalance = ((total_bid_value - total_ask_value) / (total_bid_value + total_ask_value)) * 100
        else:
            imbalance = 0
        
        # Detect signal
        signal = self.detect_signal(ticker_data, support_zones, resistance_zones, imbalance)
        
        return {
            "symbol": symbol,
            "price": current_price,
            "change24h": ticker_data["change_24h"],
            "liquidityZones": {
                "support": support_zones,
                "resistance": resistance_zones
            },
            "liquidations": liquidations,
            "signal": signal,
            "imbalance": imbalance,
            "timestamp": datetime.now().isoformat()
        }

analyzer = LiquidityAnalyzer()

@app.get("/")
async def root():
    return {"status": "Liquidity API Server Running"}

@app.get("/api/liquidity/multi")
async def get_multi_liquidity(symbols: str = "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT"):
    """Get liquidity analysis for multiple symbols"""
    # Handle both comma-separated string and query param format
    if "," in symbols:
        symbol_list = symbols.split(",")
    else:
        symbol_list = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
    
    results = []
    
    for symbol in symbol_list:
        try:
            data = await analyzer.analyze_symbol(symbol)
            if data:
                results.append(data)
            else:
                # Add placeholder if analysis fails
                results.append({
                    "symbol": symbol, 
                    "price": 0, 
                    "change24h": 0, 
                    "liquidityZones": {"support": [], "resistance": []}, 
                    "liquidations": {"longs": [], "shorts": []}, 
                    "signal": None, 
                    "imbalance": 0,
                    "timestamp": datetime.now().isoformat()
                })
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            # Add placeholder on error
            results.append({
                "symbol": symbol, 
                "price": 0, 
                "change24h": 0, 
                "liquidityZones": {"support": [], "resistance": []}, 
                "liquidations": {"longs": [], "shorts": []}, 
                "signal": None, 
                "imbalance": 0,
                "timestamp": datetime.now().isoformat()
            })
    
    # Always return an array
    return results if results else []

@app.get("/api/liquidity/{symbol}")
async def get_liquidity(symbol: str):
    """Get liquidity analysis for a symbol"""
    data = await analyzer.analyze_symbol(symbol)
    return data if data else {"error": "Failed to fetch data"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    
    symbols = ["SOLUSDT", "ETHUSDT", "BTCUSDT", "BNBUSDT"]
    
    try:
        while True:
            # Send updates every 5 seconds
            for symbol in symbols:
                data = await analyzer.analyze_symbol(symbol)
                if data:
                    await websocket.send_json(data)
            
            await asyncio.sleep(5)
            
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    print("🚀 Starting Liquidity API Server on http://localhost:8003")
    print("📊 Endpoints:")
    print("   - GET /api/liquidity/SOLUSDT - Single symbol")
    print("   - GET /api/liquidity/multi - Multiple symbols")
    print("   - WS /ws - WebSocket stream")
    
    uvicorn.run(app, host="0.0.0.0", port=8003)