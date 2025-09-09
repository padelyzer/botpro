#!/usr/bin/env python3
"""
Unified Signals API - Combines liquidity, trend, and bot signals
"""

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import httpx
import json
from datetime import datetime
import uvicorn
from typing import Dict, List
import numpy as np

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

class UnifiedAnalyzer:
    def __init__(self):
        self.binance_spot = "https://api.binance.com/api/v3"
        self.bot_signals = {}  # Store latest bot signals
        
    async def get_klines(self, symbol: str, interval: str = "15m", limit: int = 100):
        """Get candlestick data"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
                await asyncio.sleep(0.2)  # Increased rate limiting delay
                response = await client.get(
                    f"{self.binance_spot}/klines",
                    params={"symbol": symbol, "interval": interval, "limit": limit}
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"API error {response.status_code} for {symbol}")
                    return []
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            return []
    
    async def calculate_trend(self, symbol: str):
        """Calculate trend direction using multiple timeframes"""
        try:
            # Get data for different timeframes
            klines_15m = await self.get_klines(symbol, "15m", 50)
            klines_1h = await self.get_klines(symbol, "1h", 24)
            klines_4h = await self.get_klines(symbol, "4h", 12)
            
            trends = {}
            
            for timeframe, klines in [("15m", klines_15m), ("1h", klines_1h), ("4h", klines_4h)]:
                if not klines:
                    continue
                    
                # Extract closing prices
                closes = [float(k[4]) for k in klines]
                
                if len(closes) < 20:
                    continue
                
                # Calculate EMAs
                ema_9 = self.calculate_ema(closes, 9)
                ema_21 = self.calculate_ema(closes, 21)
                
                # Calculate trend strength
                current_price = closes[-1]
                ema_9_current = ema_9[-1]
                ema_21_current = ema_21[-1]
                
                # Determine trend with better sensitivity
                if ema_21_current == 0 or ema_21_current is None:
                    ema_diff_pct = 0
                else:
                    ema_diff_pct = ((ema_9_current - ema_21_current) / ema_21_current) * 100
                
                # Calculate RSI for trend determination
                rsi = await self.get_rsi(closes)
                
                # Improved trend detection using RSI and EMAs
                if abs(ema_diff_pct) < 0.1:  # Less than 0.1% difference
                    trend = "NEUTRAL"
                    strength = 0
                elif ema_9_current > ema_21_current:
                    # Check RSI for overbought conditions
                    if rsi > 70:
                        trend = "NEUTRAL"  # Overbought, expect reversal
                        strength = 20
                    else:
                        trend = "UPTREND"
                        strength = min(abs(ema_diff_pct) * 25, 100)  # More sensitive scale
                else:
                    # Check RSI for oversold conditions
                    if rsi < 30:
                        trend = "NEUTRAL"  # Oversold, expect reversal
                        strength = 20
                    else:
                        trend = "DOWNTREND"
                        strength = min(abs(ema_diff_pct) * 25, 100)
                
                # Check momentum
                if closes[-10] == 0:
                    price_change = 0
                else:
                    price_change = ((closes[-1] - closes[-10]) / closes[-10]) * 100
                
                trends[timeframe] = {
                    "direction": trend,
                    "strength": strength,
                    "momentum": price_change,
                    "ema9": ema_9_current,
                    "ema21": ema_21_current,
                    "rsi": rsi
                }
            
            # Overall trend analysis with NEUTRAL included
            trend_votes = {"UPTREND": 0, "DOWNTREND": 0, "NEUTRAL": 0}
            total_strength = 0
            
            for tf, data in trends.items():
                trend_votes[data["direction"]] += 1
                total_strength += data["strength"]
            
            # Determine overall direction based on votes
            if trend_votes["NEUTRAL"] > len(trends) / 2:
                overall_direction = "NEUTRAL"
            elif trend_votes["UPTREND"] > trend_votes["DOWNTREND"]:
                overall_direction = "UPTREND"
            elif trend_votes["DOWNTREND"] > trend_votes["UPTREND"]:
                overall_direction = "DOWNTREND"
            else:
                overall_direction = "NEUTRAL"
            
            overall_strength = total_strength / len(trends) if trends else 0
            
            # Calculate confidence based on consensus
            max_votes = max(trend_votes.values()) if trend_votes else 0
            total_votes = sum(trend_votes.values())
            confidence = (max_votes / total_votes) * 100 if total_votes > 0 else 0
            
            return {
                "overall": {
                    "direction": overall_direction,
                    "strength": overall_strength,
                    "confidence": confidence
                },
                "timeframes": trends
            }
            
        except Exception as e:
            print(f"Error calculating trend for {symbol}: {e}")
            return {
                "overall": {"direction": "NEUTRAL", "strength": 0, "confidence": 0},
                "timeframes": {}
            }
    
    def calculate_ema(self, prices: List[float], period: int):
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return prices
            
        ema = []
        multiplier = 2 / (period + 1)
        
        # Start with SMA
        sma = sum(prices[:period]) / period
        ema.append(sma)
        
        # Calculate EMA for rest
        for price in prices[period:]:
            new_ema = (price - ema[-1]) * multiplier + ema[-1]
            ema.append(new_ema)
        
        # Pad beginning with first value
        return [ema[0]] * (period - 1) + ema
    
    async def get_rsi(self, closes: List[float], period: int = 14):
        """Calculate RSI"""
        if len(closes) < period + 1:
            return 50
            
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        if avg_loss == 0:
            return 100
            
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    async def get_liquidity_data(self, symbol: str):
        """Get liquidity data from our liquidity API"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://localhost:8003/api/liquidity/{symbol}")
                if response.status_code == 200:
                    return response.json()
        except:
            pass
        return None
    
    async def calculate_entry_points(self, symbol: str, current_price: float, 
                                     trend_data: Dict, liquidity_data: Dict):
        """Calculate optimal entry, target, and stop loss points"""
        entry_points = {
            "entry": current_price,
            "target": 0,
            "stopLoss": 0
        }
        
        if not trend_data or not trend_data.get("overall"):
            return entry_points
            
        direction = trend_data["overall"]["direction"]
        
        # Get support/resistance from liquidity data
        support_zones = []
        resistance_zones = []
        if liquidity_data and "liquidityZones" in liquidity_data:
            support_zones = liquidity_data["liquidityZones"].get("support", [])
            resistance_zones = liquidity_data["liquidityZones"].get("resistance", [])
        
        if direction == "UPTREND":
            # For LONG positions
            # Entry: Current price or nearest support
            if support_zones:
                nearest_support = min(support_zones, key=lambda x: abs(x["price"] - current_price))
                if nearest_support["price"] < current_price:
                    entry_points["entry"] = nearest_support["price"]
            
            # Target: Next resistance or +3-5%
            if resistance_zones:
                next_resistance = min([r for r in resistance_zones if r["price"] > current_price], 
                                     key=lambda x: x["price"], default=None)
                if next_resistance:
                    entry_points["target"] = next_resistance["price"]
                else:
                    entry_points["target"] = current_price * 1.03
            else:
                entry_points["target"] = current_price * 1.03
            
            # Stop loss: Below support or -2%
            if support_zones:
                entry_points["stopLoss"] = support_zones[0]["price"] * 0.995
            else:
                entry_points["stopLoss"] = current_price * 0.98
                
        elif direction == "DOWNTREND":
            # For SHORT positions
            # Entry: Current price or nearest resistance
            if resistance_zones:
                nearest_resistance = min(resistance_zones, key=lambda x: abs(x["price"] - current_price))
                if nearest_resistance["price"] > current_price:
                    entry_points["entry"] = nearest_resistance["price"]
            
            # Target: Next support or -3-5%
            if support_zones:
                next_support = max([s for s in support_zones if s["price"] < current_price], 
                                  key=lambda x: x["price"], default=None)
                if next_support:
                    entry_points["target"] = next_support["price"]
                else:
                    entry_points["target"] = current_price * 0.97
            else:
                entry_points["target"] = current_price * 0.97
            
            # Stop loss: Above resistance or +2%
            if resistance_zones:
                entry_points["stopLoss"] = resistance_zones[0]["price"] * 1.005
            else:
                entry_points["stopLoss"] = current_price * 1.02
        
        return entry_points
    
    def get_bot_signal(self, symbol: str):
        """Get latest bot signal for symbol"""
        # This would connect to the actual bot signals
        # For now, return mock data based on trend
        return self.bot_signals.get(symbol, {
            "type": None,
            "confidence": 0,
            "source": "none"
        })
    
    async def analyze_complete(self, symbol: str):
        """Complete analysis including trend, liquidity, and bot signals"""
        # Get current price first from Binance
        current_price = 0
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
                response = await client.get(
                    f"{self.binance_spot}/ticker/price",
                    params={"symbol": symbol}
                )
                if response.status_code == 200:
                    data = response.json()
                    current_price = float(data["price"])
        except Exception as e:
            print(f"Error fetching price for {symbol}: {e}")
        
        # Get all data in parallel
        trend_task = self.calculate_trend(symbol)
        liquidity_task = self.get_liquidity_data(symbol)
        
        trend_data = await trend_task
        liquidity_data = await liquidity_task
        
        # Update current price from liquidity if available and price is still 0
        if current_price == 0 and liquidity_data and "price" in liquidity_data:
            current_price = liquidity_data["price"]
        
        # Determine trading bias based on trend and additional factors
        trading_bias = "NEUTRAL"
        bias_strength = 0
        
        if trend_data["overall"]["direction"] == "UPTREND":
            trading_bias = "BULLISH"
            bias_strength = trend_data["overall"]["strength"]
        elif trend_data["overall"]["direction"] == "DOWNTREND":
            trading_bias = "BEARISH"
            bias_strength = trend_data["overall"]["strength"]
        else:
            # NEUTRAL trend
            trading_bias = "NEUTRAL"
            bias_strength = trend_data["overall"]["strength"]
        
        # Calculate entry points based on trend and liquidity
        entry_points = await self.calculate_entry_points(
            symbol, current_price, trend_data, liquidity_data
        )
        
        # Adjust confidence based on multiple factors
        base_confidence = trend_data["overall"]["confidence"]
        
        # Boost confidence if trend aligns across timeframes
        if trend_data.get("timeframes"):
            aligned = all(tf_data["direction"] == trend_data["overall"]["direction"] 
                         for tf_data in trend_data["timeframes"].values())
            if aligned:
                base_confidence = min(base_confidence * 1.5, 95)
        
        # Generate bot signals with improved confidence calculation
        signal_type = None
        if trading_bias == "BULLISH" and bias_strength > 20:
            signal_type = "LONG"
        elif trading_bias == "BEARISH" and bias_strength > 20:
            signal_type = "SHORT"
        elif trading_bias == "NEUTRAL":
            signal_type = "NEUTRAL"
        
        bot_signal = {
            "active": base_confidence > 30 and trading_bias != "NEUTRAL",
            "type": signal_type,
            "confidence": base_confidence if trading_bias != "NEUTRAL" else 0,
            "sources": ["perfect_trade_monitor", "swing_monitor"] if base_confidence > 30 else [],
            "entry": entry_points.get("entry", current_price),
            "target": entry_points.get("target", 0),
            "stopLoss": entry_points.get("stopLoss", 0)
        }
        
        return {
            "symbol": symbol,
            "price": current_price,
            "trend": trend_data,
            "tradingBias": {
                "direction": trading_bias,
                "strength": bias_strength,
                "description": self.get_bias_description(trading_bias, bias_strength)
            },
            "botSignals": bot_signal,
            "liquidity": liquidity_data if liquidity_data else {},
            "timestamp": datetime.now().isoformat()
        }
    
    def get_bias_description(self, bias: str, strength: float):
        """Get human-readable description of trading bias"""
        if bias == "BULLISH":
            if strength > 70:
                return "Strong uptrend - Good for LONG entries"
            elif strength > 40:
                return "Moderate uptrend - Watch for pullbacks"
            else:
                return "Weak uptrend - Use caution"
        elif bias == "BEARISH":
            if strength > 70:
                return "Strong downtrend - Good for SHORT entries"
            elif strength > 40:
                return "Moderate downtrend - Watch for bounces"
            else:
                return "Weak downtrend - Use caution"
        else:
            return "No clear trend - Wait for direction"

analyzer = UnifiedAnalyzer()

@app.get("/")
async def root():
    return {"status": "Unified Signals API Running"}

@app.get("/api/unified/{symbol}")
async def get_unified_analysis(symbol: str):
    """Get complete analysis for a symbol"""
    data = await analyzer.analyze_complete(symbol)
    return data

@app.get("/api/unified/multi")
async def get_multi_analysis(symbols: str = "BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT"):
    """Get analysis for multiple symbols"""
    symbol_list = symbols.split(",") if "," in symbols else ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
    
    results = []
    for symbol in symbol_list:
        try:
            data = await analyzer.analyze_complete(symbol)
            results.append(data)
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            results.append({
                "symbol": symbol,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
    
    return results

@app.get("/api/market/status")
async def get_market_status():
    """Get global market status and sentiment"""
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
    
    # Analyze all symbols
    analyses = []
    for symbol in symbols:
        try:
            data = await analyzer.analyze_complete(symbol)
            analyses.append(data)
        except:
            continue
    
    if not analyses:
        return {"status": "UNKNOWN", "message": "Unable to analyze market"}
    
    # Calculate global metrics
    bullish_count = 0
    bearish_count = 0
    neutral_count = 0
    total_strength = 0
    avg_momentum = 0
    
    for analysis in analyses:
        bias = analysis.get("tradingBias", {}).get("direction", "NEUTRAL")
        strength = analysis.get("tradingBias", {}).get("strength", 0)
        
        if bias == "BULLISH":
            bullish_count += 1
        elif bias == "BEARISH":
            bearish_count += 1
        else:
            neutral_count += 1
        
        total_strength += strength
        
        # Get average momentum from timeframes
        if "trend" in analysis and "timeframes" in analysis["trend"]:
            momentums = [tf.get("momentum", 0) for tf in analysis["trend"]["timeframes"].values()]
            if momentums:
                avg_momentum += sum(momentums) / len(momentums)
    
    avg_strength = total_strength / len(analyses) if analyses else 0
    avg_momentum = avg_momentum / len(analyses) if analyses else 0
    
    # Determine market status
    if bearish_count > bullish_count * 2:
        market_status = "STRONG_BEARISH"
        status_emoji = "🔴🔴"
        recommendation = "Avoid LONG positions. Look for SHORT opportunities on bounces."
    elif bearish_count > bullish_count:
        market_status = "BEARISH"
        status_emoji = "🔴"
        recommendation = "Market is weak. Use caution with LONG positions."
    elif bullish_count > bearish_count * 2:
        market_status = "STRONG_BULLISH"
        status_emoji = "🟢🟢"
        recommendation = "Good for LONG positions. Look for entries on pullbacks."
    elif bullish_count > bearish_count:
        market_status = "BULLISH"
        status_emoji = "🟢"
        recommendation = "Market is positive. Consider LONG positions."
    else:
        market_status = "NEUTRAL"
        status_emoji = "🟡"
        recommendation = "Market is undecided. Wait for clear direction."
    
    # Calculate fear/greed index (0-100)
    fear_greed = 50  # Start neutral
    fear_greed += (bullish_count - bearish_count) * 10
    fear_greed += avg_momentum * 2
    fear_greed = max(0, min(100, fear_greed))
    
    fear_greed_label = "Extreme Fear"
    if fear_greed > 80:
        fear_greed_label = "Extreme Greed"
    elif fear_greed > 60:
        fear_greed_label = "Greed"
    elif fear_greed > 40:
        fear_greed_label = "Neutral"
    elif fear_greed > 20:
        fear_greed_label = "Fear"
    
    return {
        "marketStatus": market_status,
        "statusEmoji": status_emoji,
        "recommendation": recommendation,
        "metrics": {
            "bullishCount": bullish_count,
            "bearishCount": bearish_count,
            "neutralCount": neutral_count,
            "averageStrength": round(avg_strength, 1),
            "averageMomentum": round(avg_momentum, 2)
        },
        "fearGreedIndex": {
            "value": round(fear_greed),
            "label": fear_greed_label
        },
        "symbols": {
            symbol: {
                "bias": analysis.get("tradingBias", {}).get("direction"),
                "strength": analysis.get("tradingBias", {}).get("strength", 0),
                "signal": analysis.get("botSignals", {}).get("type")
            }
            for symbol, analysis in zip(symbols, analyses)
        },
        "timestamp": datetime.now().isoformat()
    }

@app.websocket("/ws/unified")
async def websocket_unified(websocket: WebSocket):
    """WebSocket for real-time unified updates"""
    await websocket.accept()
    
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
    
    try:
        while True:
            for symbol in symbols:
                data = await analyzer.analyze_complete(symbol)
                await websocket.send_json(data)
            
            await asyncio.sleep(10)  # Update every 10 seconds
            
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    print("🚀 Starting Unified Signals API on http://localhost:8004")
    print("📊 Endpoints:")
    print("   - GET /api/unified/BTCUSDT - Single symbol analysis")
    print("   - GET /api/unified/multi - Multiple symbols")
    print("   - WS /ws/unified - WebSocket stream")
    
    uvicorn.run(app, host="0.0.0.0", port=8004)