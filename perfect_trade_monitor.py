#!/usr/bin/env python3
"""
Perfect Trade Monitor for SOL & ETH
Real-time monitoring of all variables for optimal entry
Designed for high leverage trades (10x-100x)
"""

import asyncio
import httpx
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import time

@dataclass
class TradingSignal:
    symbol: str
    action: str  # LONG/SHORT/WAIT
    confidence: float  # 0-100
    entry_price: float
    stop_loss: float
    take_profit: List[float]
    leverage: int
    reason: str
    risk_reward: float
    
class PerfectTradeMonitor:
    """
    Advanced monitoring system for perfect trade entries
    """
    
    def __init__(self):
        self.symbols = ["ETHUSDT", "SOLUSDT"]
        self.refresh_interval = 5  # seconds
        self.liquidity_api = "http://localhost:8002/api/liquidity"
        
        # Trading parameters
        self.min_confidence = 70  # Minimum confidence for signal
        self.max_leverage = 100
        self.risk_per_trade = 0.02  # 2% risk
        
        # Liquidation levels cache
        self.liquidation_zones = {}
        self.last_signals = {}
        
        # Colors for terminal
        self.GREEN = '\033[92m'
        self.RED = '\033[91m'
        self.YELLOW = '\033[93m'
        self.BLUE = '\033[94m'
        self.BOLD = '\033[1m'
        self.END = '\033[0m'
        
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    async def get_market_data(self, symbol: str) -> Dict:
        """Get comprehensive market data"""
        async with httpx.AsyncClient() as client:
            try:
                # Current price
                ticker = await client.get(
                    "https://api.binance.com/api/v3/ticker/price",
                    params={"symbol": symbol}
                )
                current_price = float(ticker.json()["price"])
                
                # 24h data
                ticker_24h = await client.get(
                    "https://api.binance.com/api/v3/ticker/24hr",
                    params={"symbol": symbol}
                )
                data_24h = ticker_24h.json()
                
                # Recent klines for momentum
                klines_15m = await client.get(
                    "https://fapi.binance.com/fapi/v1/klines",
                    params={"symbol": symbol, "interval": "15m", "limit": 20}
                )
                
                klines_1h = await client.get(
                    "https://fapi.binance.com/fapi/v1/klines",
                    params={"symbol": symbol, "interval": "1h", "limit": 24}
                )
                
                # Parse klines
                df_15m = pd.DataFrame(klines_15m.json(), columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                    'taker_buy_quote', 'ignore'
                ])
                df_15m[['open', 'high', 'low', 'close', 'volume']] = df_15m[['open', 'high', 'low', 'close', 'volume']].astype(float)
                
                df_1h = pd.DataFrame(klines_1h.json(), columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                    'taker_buy_quote', 'ignore'
                ])
                df_1h[['open', 'high', 'low', 'close', 'volume']] = df_1h[['open', 'high', 'low', 'close', 'volume']].astype(float)
                
                # Calculate indicators
                rsi_15m = self.calculate_rsi(df_15m['close'])
                rsi_1h = self.calculate_rsi(df_1h['close'])
                
                # Volume analysis
                avg_volume_15m = df_15m['volume'].mean()
                current_volume_15m = df_15m['volume'].iloc[-1]
                volume_ratio = current_volume_15m / avg_volume_15m
                
                # Support/Resistance
                recent_high = df_1h['high'].max()
                recent_low = df_1h['low'].min()
                
                return {
                    "price": current_price,
                    "high_24h": float(data_24h["highPrice"]),
                    "low_24h": float(data_24h["lowPrice"]),
                    "change_24h": float(data_24h["priceChangePercent"]),
                    "volume_24h": float(data_24h["volume"]),
                    "rsi_15m": rsi_15m,
                    "rsi_1h": rsi_1h,
                    "volume_ratio": volume_ratio,
                    "recent_high": recent_high,
                    "recent_low": recent_low,
                    "range_position": (current_price - recent_low) / (recent_high - recent_low) if recent_high > recent_low else 0.5
                }
            except Exception as e:
                print(f"Error fetching market data: {e}")
                return {}
    
    async def get_liquidity_data(self, symbol: str) -> Dict:
        """Get liquidity and order book data"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.liquidity_api}/{symbol}")
                if response.status_code == 200:
                    data = response.json()
                    ob = data.get("order_book_analysis", {})
                    
                    return {
                        "imbalance": ob.get("imbalance", 0),
                        "whale_activity": ob.get("large_orders", {}).get("whale_activity", False),
                        "bid_liquidity": ob.get("liquidity_score", {}).get("0.5%", {}).get("bid_liquidity", 0),
                        "ask_liquidity": ob.get("liquidity_score", {}).get("0.5%", {}).get("ask_liquidity", 0),
                        "support_levels": ob.get("support_levels", []),
                        "resistance_levels": ob.get("resistance_levels", [])
                    }
            except:
                return {}
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if not rsi.empty else 50
    
    def calculate_liquidation_zones(self, price: float) -> Dict:
        """Calculate liquidation zones for different leverages"""
        zones = {
            "longs": {
                100: price * 0.99,
                75: price * 0.987,
                50: price * 0.98,
                25: price * 0.96,
                20: price * 0.95,
                10: price * 0.905,
            },
            "shorts": {
                100: price * 1.01,
                75: price * 1.013,
                50: price * 1.02,
                25: price * 1.04,
                20: price * 1.05,
                10: price * 1.095,
            }
        }
        return zones
    
    def analyze_trade_setup(self, symbol: str, market_data: Dict, liquidity_data: Dict) -> Optional[TradingSignal]:
        """Analyze and generate trading signal"""
        if not market_data:
            return None
        
        price = market_data["price"]
        confidence = 0
        reasons = []
        
        # Calculate liquidation zones
        liq_zones = self.calculate_liquidation_zones(price)
        
        # 1. RSI Analysis (20 points)
        rsi_15m = market_data.get("rsi_15m", 50)
        rsi_1h = market_data.get("rsi_1h", 50)
        
        if rsi_15m < 30:
            confidence += 20
            reasons.append(f"RSI 15m oversold ({rsi_15m:.1f})")
        elif rsi_15m > 70:
            confidence += 20
            reasons.append(f"RSI 15m overbought ({rsi_15m:.1f})")
        
        # 2. Support/Resistance (20 points)
        range_pos = market_data.get("range_position", 0.5)
        if range_pos < 0.2:
            confidence += 20
            reasons.append("Near strong support")
        elif range_pos > 0.8:
            confidence += 20
            reasons.append("Near strong resistance")
        
        # 3. Volume Analysis (15 points)
        volume_ratio = market_data.get("volume_ratio", 1)
        if volume_ratio > 2:
            confidence += 15
            reasons.append(f"High volume ({volume_ratio:.1f}x)")
        
        # 4. Liquidity Imbalance (20 points)
        imbalance = liquidity_data.get("imbalance", 0)
        if abs(imbalance) > 30:
            confidence += 20
            if imbalance > 0:
                reasons.append(f"Strong buy pressure ({imbalance:.1f}%)")
            else:
                reasons.append(f"Strong sell pressure ({imbalance:.1f}%)")
        
        # 5. Whale Activity (15 points)
        if liquidity_data.get("whale_activity"):
            confidence += 15
            reasons.append("Whale activity detected")
        
        # 6. Liquidation Magnet (10 points)
        # Check if price is near liquidation zones
        for leverage, liq_price in liq_zones["longs"].items():
            if abs(price - liq_price) / price < 0.005:  # Within 0.5%
                confidence += 10
                reasons.append(f"Near {leverage}x long liquidations")
                break
        
        for leverage, liq_price in liq_zones["shorts"].items():
            if abs(price - liq_price) / price < 0.005:  # Within 0.5%
                confidence += 10
                reasons.append(f"Near {leverage}x short liquidations")
                break
        
        # Determine trade direction
        action = "WAIT"
        entry_price = price
        stop_loss = price
        take_profit = []
        leverage = 10
        
        if confidence >= self.min_confidence:
            # LONG setup
            if rsi_15m < 35 and range_pos < 0.3 and imbalance > 20:
                action = "LONG"
                stop_loss = price * 0.97
                take_profit = [
                    price * 1.015,  # TP1: 1.5%
                    price * 1.025,  # TP2: 2.5%
                    price * 1.04,   # TP3: 4%
                ]
                leverage = min(50, self.max_leverage) if confidence > 80 else 25
                
            # SHORT setup
            elif rsi_15m > 65 and range_pos > 0.7 and imbalance < -20:
                action = "SHORT"
                stop_loss = price * 1.03
                take_profit = [
                    price * 0.985,  # TP1: 1.5%
                    price * 0.975,  # TP2: 2.5%
                    price * 0.96,   # TP3: 4%
                ]
                leverage = min(50, self.max_leverage) if confidence > 80 else 25
        
        # Calculate risk/reward
        if action != "WAIT":
            risk = abs(entry_price - stop_loss) / entry_price
            reward = abs(take_profit[1] - entry_price) / entry_price if take_profit else 0
            risk_reward = reward / risk if risk > 0 else 0
            
            return TradingSignal(
                symbol=symbol,
                action=action,
                confidence=confidence,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                leverage=leverage,
                reason=" | ".join(reasons),
                risk_reward=risk_reward
            )
        
        return None
    
    def print_header(self):
        """Print monitor header"""
        self.clear_screen()
        print(f"{self.BOLD}{'='*100}{self.END}")
        print(f"{self.BOLD}🎯 PERFECT TRADE MONITOR - SOL & ETH{self.END}")
        print(f"{self.BOLD}{'='*100}{self.END}")
        
        # Time info
        mexico_tz = pytz.timezone('America/Mexico_City')
        mexico_time = datetime.now(mexico_tz)
        print(f"📅 {mexico_time.strftime('%Y-%m-%d %H:%M:%S')} Mexico City")
        
        # Sunday pump timer
        if mexico_time.weekday() == 6:  # Sunday
            hours_to_2am = (26 - mexico_time.hour) % 24
            if hours_to_2am > 0:
                print(f"⏰ {self.YELLOW}Sunday pump in {hours_to_2am}h (2am){self.END}")
        
        print(f"{'-'*100}")
    
    def print_market_data(self, symbol: str, market_data: Dict, liquidity_data: Dict):
        """Print market analysis"""
        coin = symbol.replace("USDT", "")
        price = market_data.get("price", 0)
        change_24h = market_data.get("change_24h", 0)
        
        # Header with color based on 24h change
        color = self.GREEN if change_24h > 0 else self.RED
        print(f"\n{self.BOLD}📊 {coin}{self.END}")
        print(f"Price: ${price:.2f} {color}({change_24h:+.2f}%){self.END}")
        
        # Market metrics
        print(f"├─ 24h Range: ${market_data.get('low_24h', 0):.2f} - ${market_data.get('high_24h', 0):.2f}")
        print(f"├─ RSI: 15m={market_data.get('rsi_15m', 0):.1f} | 1h={market_data.get('rsi_1h', 0):.1f}")
        print(f"├─ Volume: {market_data.get('volume_ratio', 0):.1f}x average")
        print(f"├─ Range Position: {market_data.get('range_position', 0)*100:.1f}%")
        
        # Liquidity metrics
        imbalance = liquidity_data.get("imbalance", 0)
        imb_color = self.GREEN if imbalance > 0 else self.RED
        print(f"├─ Order Book: {imb_color}{imbalance:+.1f}%{self.END}")
        
        if liquidity_data.get("whale_activity"):
            print(f"└─ {self.YELLOW}🐋 Whale Activity Detected{self.END}")
        else:
            print(f"└─ No whale activity")
        
        # Liquidation zones
        liq_zones = self.calculate_liquidation_zones(price)
        print(f"\n   Liquidations:")
        print(f"   ├─ Longs: ${liq_zones['longs'][100]:.2f} (100x) | ${liq_zones['longs'][50]:.2f} (50x)")
        print(f"   └─ Shorts: ${liq_zones['shorts'][100]:.2f} (100x) | ${liq_zones['shorts'][50]:.2f} (50x)")
    
    def print_signal(self, signal: TradingSignal):
        """Print trading signal"""
        if signal.action == "LONG":
            color = self.GREEN
            emoji = "🟢"
        elif signal.action == "SHORT":
            color = self.RED
            emoji = "🔴"
        else:
            return
        
        print(f"\n{self.BOLD}{color}{'='*50}{self.END}")
        print(f"{emoji} {self.BOLD}{signal.action} SIGNAL - {signal.symbol}{self.END}")
        print(f"Confidence: {self.get_confidence_bar(signal.confidence)} {signal.confidence:.0f}%")
        print(f"Entry: ${signal.entry_price:.2f}")
        print(f"Stop: ${signal.stop_loss:.2f}")
        print(f"Targets: {' | '.join([f'${tp:.2f}' for tp in signal.take_profit])}")
        print(f"Leverage: {signal.leverage}x")
        print(f"R/R: 1:{signal.risk_reward:.1f}")
        print(f"Reason: {signal.reason}")
        print(f"{color}{'='*50}{self.END}")
    
    def get_confidence_bar(self, confidence: float) -> str:
        """Create visual confidence bar"""
        filled = int(confidence / 10)
        empty = 10 - filled
        return f"[{'█' * filled}{'░' * empty}]"
    
    async def monitor_loop(self):
        """Main monitoring loop"""
        print("🚀 Starting Perfect Trade Monitor...")
        await asyncio.sleep(2)
        
        while True:
            try:
                self.print_header()
                
                # Monitor each symbol
                for symbol in self.symbols:
                    # Get data
                    market_data = await self.get_market_data(symbol)
                    liquidity_data = await self.get_liquidity_data(symbol)
                    
                    # Print market analysis
                    self.print_market_data(symbol, market_data, liquidity_data)
                    
                    # Check for trading signal
                    signal = self.analyze_trade_setup(symbol, market_data, liquidity_data)
                    
                    if signal and signal.confidence >= self.min_confidence:
                        self.print_signal(signal)
                        
                        # Alert sound
                        if signal.confidence >= 80:
                            os.system('echo -e "\\a"')  # Terminal bell
                
                # Status line
                print(f"\n{self.BLUE}Refreshing every {self.refresh_interval}s | Press Ctrl+C to stop{self.END}")
                
                # Wait for next refresh
                await asyncio.sleep(self.refresh_interval)
                
            except KeyboardInterrupt:
                print(f"\n{self.YELLOW}Monitor stopped by user{self.END}")
                break
            except Exception as e:
                print(f"\n{self.RED}Error: {e}{self.END}")
                await asyncio.sleep(10)

async def main():
    monitor = PerfectTradeMonitor()
    await monitor.monitor_loop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✅ Monitor stopped")