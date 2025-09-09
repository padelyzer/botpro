#!/usr/bin/env python3
"""
ETH Optimal Entry Analysis
Using liquidity system for $120 @ 10x leverage
"""

import asyncio
import httpx
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from swing_trading_system import SwingTradingSystem
import json

class ETHOptimalEntry:
    def __init__(self):
        self.symbol = "ETHUSDT"
        self.position_size_usd = 120.0
        self.leverage = 10
        self.capital = 250.0
        self.liquidity_api = "http://localhost:8002/api/liquidity"
        
    async def get_comprehensive_analysis(self):
        """
        Full analysis using our liquidity system
        """
        print("="*80)
        print("🎯 ETH OPTIMAL ENTRY ANALYSIS")
        print("="*80)
        print(f"💰 Position: ${self.position_size_usd} @ {self.leverage}x")
        print(f"📊 Effective Exposure: ${self.position_size_usd * self.leverage}")
        print("-"*80)
        
        async with httpx.AsyncClient() as client:
            # 1. Get current price and 24h data
            ticker = await client.get(
                "https://api.binance.com/api/v3/ticker/24hr",
                params={"symbol": self.symbol}
            )
            ticker_data = ticker.json()
            current_price = float(ticker_data["lastPrice"])
            high_24h = float(ticker_data["highPrice"])
            low_24h = float(ticker_data["lowPrice"])
            volume_24h = float(ticker_data["volume"])
            change_24h = float(ticker_data["priceChangePercent"])
            
            print(f"📈 CURRENT MARKET:")
            print(f"   Price: ${current_price:.2f}")
            print(f"   24h Range: ${low_24h:.2f} - ${high_24h:.2f}")
            print(f"   24h Change: {change_24h:+.2f}%")
            print(f"   Position from 24h Low: +{((current_price - low_24h) / low_24h * 100):.2f}%")
            
            # 2. Get liquidity data
            try:
                liquidity_response = await client.get(f"{self.liquidity_api}/{self.symbol}")
                if liquidity_response.status_code == 200:
                    liquidity_data = liquidity_response.json()
                    order_book = liquidity_data.get("order_book_analysis", {})
                    
                    print(f"\n💧 LIQUIDITY ANALYSIS:")
                    imbalance = order_book.get("imbalance", 0)
                    print(f"   Order Book Imbalance: {imbalance:.1f}%")
                    
                    # Support levels from liquidity
                    support_levels = order_book.get("support_levels", [])
                    if support_levels:
                        print(f"\n   📉 Key Support Levels:")
                        for i, level in enumerate(support_levels[:3], 1):
                            price = level.get('price', 0)
                            volume = level.get('total_size', 0)
                            print(f"      S{i}: ${price:.2f} (Volume: {volume:.2f} ETH)")
                    
                    # Resistance levels
                    resistance_levels = order_book.get("resistance_levels", [])
                    if resistance_levels:
                        print(f"\n   📈 Key Resistance Levels:")
                        for i, level in enumerate(resistance_levels[:3], 1):
                            price = level.get('price', 0)
                            volume = level.get('total_size', 0)
                            print(f"      R{i}: ${price:.2f} (Volume: {volume:.2f} ETH)")
                    
                    # Whale activity
                    large_orders = order_book.get("large_orders", {})
                    whale_activity = large_orders.get("whale_activity", False)
                    if whale_activity:
                        print(f"\n   🐋 Whale Activity: DETECTED")
                        whale_bids = large_orders.get("total_large_bid_volume", 0)
                        whale_asks = large_orders.get("total_large_ask_volume", 0)
                        print(f"      Large Bid Volume: {whale_bids:.2f} ETH")
                        print(f"      Large Ask Volume: {whale_asks:.2f} ETH")
                        if whale_bids > whale_asks:
                            print(f"      Direction: ACCUMULATION ✅")
                        else:
                            print(f"      Direction: DISTRIBUTION ⚠️")
            except:
                liquidity_data = {}
                support_levels = []
                resistance_levels = []
            
            # 3. Get multiple timeframe analysis
            print(f"\n📊 MULTI-TIMEFRAME ANALYSIS:")
            
            # 4H candles
            klines_4h = await client.get(
                "https://fapi.binance.com/fapi/v1/klines",
                params={"symbol": self.symbol, "interval": "4h", "limit": 50}
            )
            if klines_4h.status_code == 200:
                df_4h = pd.DataFrame(klines_4h.json(), columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                    'taker_buy_quote', 'ignore'
                ])
                df_4h['close'] = df_4h['close'].astype(float)
                df_4h['high'] = df_4h['high'].astype(float)
                df_4h['low'] = df_4h['low'].astype(float)
                df_4h['volume'] = df_4h['volume'].astype(float)
                
                # Calculate indicators
                df_4h['sma_20'] = df_4h['close'].rolling(20).mean()
                df_4h['ema_9'] = df_4h['close'].ewm(span=9).mean()
                
                # RSI
                delta = df_4h['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                df_4h['rsi'] = 100 - (100 / (1 + rs))
                
                latest_4h = df_4h.iloc[-1]
                prev_4h = df_4h.iloc[-2]
                
                print(f"   4H Timeframe:")
                print(f"      RSI: {latest_4h['rsi']:.1f}")
                print(f"      Trend: {'BULLISH' if latest_4h['close'] > latest_4h['sma_20'] else 'BEARISH'}")
                print(f"      Volume: {latest_4h['volume'] / df_4h['volume'].mean():.2f}x average")
            
            # 1H candles
            klines_1h = await client.get(
                "https://fapi.binance.com/fapi/v1/klines",
                params={"symbol": self.symbol, "interval": "1h", "limit": 24}
            )
            if klines_1h.status_code == 200:
                df_1h = pd.DataFrame(klines_1h.json(), columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                    'taker_buy_quote', 'ignore'
                ])
                df_1h['close'] = df_1h['close'].astype(float)
                df_1h['volume'] = df_1h['volume'].astype(float)
                
                # Find recent support/resistance
                recent_high = df_1h['close'].max()
                recent_low = df_1h['close'].min()
                
                print(f"   1H Timeframe:")
                print(f"      24h High: ${recent_high:.2f}")
                print(f"      24h Low: ${recent_low:.2f}")
                print(f"      Current Position: {((current_price - recent_low) / (recent_high - recent_low) * 100):.1f}% of range")
            
            # 4. Calculate optimal entry points
            print(f"\n🎯 OPTIMAL ENTRY ZONES:")
            
            # Entry Zone 1: Current Market Order
            entry_1 = current_price
            print(f"\n   1️⃣ MARKET ORDER (Immediate):")
            print(f"      Entry: ${entry_1:.2f}")
            print(f"      Pros: Immediate execution, catch momentum")
            print(f"      Cons: No discount, higher risk")
            
            # Entry Zone 2: First support level
            if support_levels and len(support_levels) > 0:
                entry_2 = support_levels[0].get('price', current_price * 0.995)
            else:
                entry_2 = current_price * 0.995  # 0.5% below
            
            print(f"\n   2️⃣ FIRST SUPPORT (Conservative):")
            print(f"      Entry: ${entry_2:.2f} (-{((current_price - entry_2) / current_price * 100):.2f}%)")
            print(f"      Pros: Better R/R, liquidity support")
            print(f"      Cons: May not fill")
            
            # Entry Zone 3: Aggressive support
            entry_3 = low_24h * 1.005  # Just above 24h low
            print(f"\n   3️⃣ NEAR 24H LOW (Aggressive):")
            print(f"      Entry: ${entry_3:.2f} (-{((current_price - entry_3) / current_price * 100):.2f}%)")
            print(f"      Pros: Best R/R, strong bounce zone")
            print(f"      Cons: Low probability of fill")
            
            # Entry Zone 4: VWAP/Fair Value
            if df_4h is not None:
                vwap = (df_4h['close'] * df_4h['volume']).sum() / df_4h['volume'].sum()
                entry_4 = vwap
                print(f"\n   4️⃣ VWAP ZONE (Fair Value):")
                print(f"      Entry: ${entry_4:.2f} ({'+' if entry_4 > current_price else ''}{((entry_4 - current_price) / current_price * 100):.2f}%)")
                print(f"      Pros: High probability zone")
                print(f"      Cons: May need to wait")
            
            # 5. Risk Management for each entry
            print(f"\n⚠️ RISK MANAGEMENT @ 10x:")
            
            position_size_eth = self.position_size_usd / current_price
            
            for i, entry in enumerate([entry_1, entry_2, entry_3], 1):
                print(f"\n   Entry Zone {i} (${entry:.2f}):")
                
                # Calculate stops and targets
                stop_loss = entry * 0.97  # 3% stop
                target_1 = entry * 1.015   # 1.5%
                target_2 = entry * 1.025   # 2.5%
                target_3 = entry * 1.04    # 4%
                
                # Profits at 10x
                profit_t1 = self.position_size_usd * 0.15
                profit_t2 = self.position_size_usd * 0.25
                profit_t3 = self.position_size_usd * 0.40
                
                print(f"      Stop: ${stop_loss:.2f} (-3%)")
                print(f"      T1: ${target_1:.2f} (+{profit_t1:.2f} USD)")
                print(f"      T2: ${target_2:.2f} (+{profit_t2:.2f} USD)")
                print(f"      T3: ${target_3:.2f} (+{profit_t3:.2f} USD)")
                print(f"      R/R to T2: 1:{(2.5/3):.1f}")
            
            # 6. Final recommendation
            print(f"\n" + "="*80)
            print(f"💡 RECOMMENDED STRATEGY:")
            print("-"*80)
            
            # Check RSI for entry timing
            if df_4h is not None and latest_4h['rsi'] < 45:
                print(f"✅ RSI OVERSOLD ({latest_4h['rsi']:.1f}) - GOOD ENTRY")
                recommended_entry = entry_1  # Market buy on oversold
            elif (current_price - low_24h) / low_24h * 100 < 1.5:
                print(f"✅ NEAR 24H LOW - GOOD ENTRY")
                recommended_entry = entry_1  # Market buy near support
            else:
                print(f"⏳ WAIT FOR BETTER ENTRY")
                recommended_entry = entry_2  # Limit order at support
            
            print(f"\n📋 EXECUTION PLAN:")
            print(f"1. Place LIMIT orders at:")
            print(f"   - ${entry_2:.2f} (50% of position)")
            print(f"   - ${entry_3:.2f} (50% of position)")
            print(f"2. If filled, set STOP at -3%")
            print(f"3. Take profits:")
            print(f"   - 40% at T1 (+1.5%)")
            print(f"   - 40% at T2 (+2.5%)")
            print(f"   - 20% at T3 (+4%)")
            
            # Check if Sunday pump applies
            from datetime import datetime
            import pytz
            mexico_tz = pytz.timezone('America/Mexico_City')
            now = datetime.now(mexico_tz)
            
            if now.weekday() >= 5:  # Friday night or weekend
                print(f"\n🚀 WEEKEND BONUS:")
                print(f"   Sunday 2am pump likely!")
                print(f"   Consider entering before Sunday")
            
            print("="*80)

async def main():
    analyzer = ETHOptimalEntry()
    await analyzer.get_comprehensive_analysis()

if __name__ == "__main__":
    asyncio.run(main())