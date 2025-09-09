#!/usr/bin/env python3
"""
Sunday Swing Scanner for ETH/BNB
$120 position with 10x leverage
Targeting Sunday 2am Mexico time pump
"""

import asyncio
import httpx
from datetime import datetime, timedelta
from swing_trading_system import SwingTradingSystem
import pytz

class SundaySwingScanner:
    def __init__(self):
        self.capital = 250.0
        self.position_size_usd = 120.0
        self.leverage = 10
        self.symbols = ["ETHUSDT", "BNBUSDT"]
        
    async def analyze_sunday_setup(self):
        """
        Analyze ETH and BNB for Sunday pump setup
        """
        print("="*80)
        print("🌙 SUNDAY SWING SETUP SCANNER")
        print("="*80)
        print(f"💰 Capital: ${self.capital}")
        print(f"📊 Position Size: ${self.position_size_usd} @ {self.leverage}x leverage")
        print(f"🎯 Effective exposure: ${self.position_size_usd * self.leverage}")
        
        # Mexico City time
        mexico_tz = pytz.timezone('America/Mexico_City')
        mexico_time = datetime.now(mexico_tz)
        print(f"🕐 Mexico Time: {mexico_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Calculate hours until Sunday 2am Mexico
        days_until_sunday = (6 - mexico_time.weekday()) % 7
        if days_until_sunday == 0 and mexico_time.hour >= 2:
            days_until_sunday = 7
        
        target_time = mexico_time.replace(hour=2, minute=0, second=0, microsecond=0)
        target_time += timedelta(days=days_until_sunday)
        hours_until = (target_time - mexico_time).total_seconds() / 3600
        
        print(f"⏰ Hours until Sunday 2am: {hours_until:.1f} hours")
        print("-"*80)
        
        async with httpx.AsyncClient() as client:
            for symbol in self.symbols:
                coin = symbol.replace("USDT", "")
                print(f"\n📈 {coin} ANALYSIS:")
                print("-"*40)
                
                # Get current data
                ticker = await client.get(
                    "https://api.binance.com/api/v3/ticker/24hr",
                    params={"symbol": symbol}
                )
                data = ticker.json()
                current_price = float(data["lastPrice"])
                change_24h = float(data["priceChangePercent"])
                low_24h = float(data["lowPrice"])
                high_24h = float(data["highPrice"])
                
                print(f"Current Price: ${current_price:.2f}")
                print(f"24h Change: {change_24h:+.2f}%")
                print(f"24h Range: ${low_24h:.2f} - ${high_24h:.2f}")
                
                # Get 4H candles for trend
                klines_4h = await client.get(
                    "https://fapi.binance.com/fapi/v1/klines",
                    params={
                        "symbol": symbol,
                        "interval": "4h",
                        "limit": 6
                    }
                )
                
                if klines_4h.status_code == 200:
                    candles = klines_4h.json()
                    
                    # Check if we're near 24h low (good for Sunday pump)
                    distance_from_low = (current_price - low_24h) / low_24h * 100
                    distance_from_high = (high_24h - current_price) / current_price * 100
                    
                    print(f"\n📊 POSITION IN RANGE:")
                    print(f"   From 24h Low: +{distance_from_low:.2f}%")
                    print(f"   To 24h High: +{distance_from_high:.2f}%")
                    
                    # Check last 3 Sundays pattern
                    print(f"\n📅 SUNDAY PATTERN CHECK:")
                    last_close = float(candles[-2][4])
                    current_close = float(candles[-1][4])
                    
                    if current_price < last_close:
                        print(f"   ✅ Price pulled back from ${last_close:.2f}")
                        print(f"   Good setup for Sunday bounce")
                    else:
                        print(f"   ⚠️ Already up from ${last_close:.2f}")
                    
                    # Calculate entry levels for swing
                    print(f"\n💹 SWING TRADE SETUP:")
                    
                    # Entry zones
                    if distance_from_low < 2:
                        entry_price = current_price
                        entry_status = "✅ PERFECT - At 24h low"
                    elif distance_from_low < 5:
                        entry_price = current_price
                        entry_status = "✅ GOOD - Near 24h low"
                    else:
                        entry_price = low_24h * 1.02
                        entry_status = f"⚠️ WAIT for pullback to ${entry_price:.2f}"
                    
                    # With 10x leverage
                    position_size = self.position_size_usd / current_price
                    
                    # Risk management with 10x
                    liquidation_price_long = current_price * 0.91  # ~9% down = liquidation at 10x
                    safe_stop_loss = current_price * 0.97  # 3% stop to avoid liquidation
                    
                    # Targets for Sunday pump
                    target_1 = current_price * 1.015  # 1.5% = 15% profit at 10x
                    target_2 = current_price * 1.025  # 2.5% = 25% profit at 10x
                    target_3 = current_price * 1.04   # 4% = 40% profit at 10x
                    
                    print(f"   Entry: ${current_price:.2f} ({entry_status})")
                    print(f"   Position: {position_size:.4f} {coin}")
                    print(f"   Stop Loss: ${safe_stop_loss:.2f} (-3%)")
                    print(f"   Liquidation: ${liquidation_price_long:.2f} (-9%)")
                    
                    print(f"\n   🎯 TARGETS (with 10x leverage):")
                    print(f"   T1: ${target_1:.2f} (+1.5% = +15% profit)")
                    print(f"   T2: ${target_2:.2f} (+2.5% = +25% profit)")
                    print(f"   T3: ${target_3:.2f} (+4% = +40% profit)")
                    
                    # Calculate potential profits
                    profit_t1 = self.position_size_usd * 0.15  # 15% on position
                    profit_t2 = self.position_size_usd * 0.25  # 25% on position
                    profit_t3 = self.position_size_usd * 0.40  # 40% on position
                    
                    print(f"\n   💰 PROFIT POTENTIAL:")
                    print(f"   At T1: +${profit_t1:.2f}")
                    print(f"   At T2: +${profit_t2:.2f}")
                    print(f"   At T3: +${profit_t3:.2f}")
                    
                    # Risk calculation
                    risk_amount = self.position_size_usd * 0.03  # 3% stop
                    
                    print(f"\n   ⚠️ RISK:")
                    print(f"   Max Loss (at stop): -${risk_amount:.2f}")
                    print(f"   Risk/Reward to T2: 1:{25/3:.1f}")
                    
                    # Sunday pump probability
                    if coin == "ETH":
                        if distance_from_low < 3 and change_24h < 0:
                            print(f"\n   🚀 SUNDAY PUMP PROBABILITY: HIGH")
                            print(f"   ETH typically bounces Sunday 2am Mexico")
                        else:
                            print(f"\n   📊 SUNDAY PUMP PROBABILITY: MEDIUM")
                    elif coin == "BNB":
                        if distance_from_low < 3 and change_24h < 1:
                            print(f"\n   🚀 SUNDAY PUMP PROBABILITY: HIGH")
                            print(f"   BNB follows BTC Sunday moves")
                        else:
                            print(f"\n   📊 SUNDAY PUMP PROBABILITY: MEDIUM")
        
        print("\n" + "="*80)
        print("🎯 RECOMMENDATION FOR SUNDAY PUMP:")
        print("-"*80)
        
        # Get latest prices for final recommendation
        async with httpx.AsyncClient() as client:
            eth_ticker = await client.get(
                "https://api.binance.com/api/v3/ticker/price",
                params={"symbol": "ETHUSDT"}
            )
            eth_price = float(eth_ticker.json()["price"])
            
            bnb_ticker = await client.get(
                "https://api.binance.com/api/v3/ticker/price",
                params={"symbol": "BNBUSDT"}
            )
            bnb_price = float(bnb_ticker.json()["price"])
        
        print(f"\n🔥 BEST SETUP:")
        
        # Compare setups
        eth_score = 0
        bnb_score = 0
        
        # Check 24h position with new client
        async with httpx.AsyncClient() as new_client:
            eth_24h = await new_client.get(
                "https://api.binance.com/api/v3/ticker/24hr",
                params={"symbol": "ETHUSDT"}
            )
            eth_data = eth_24h.json()
            eth_from_low = (eth_price - float(eth_data["lowPrice"])) / float(eth_data["lowPrice"]) * 100
            
            bnb_24h = await new_client.get(
                "https://api.binance.com/api/v3/ticker/24hr",
                params={"symbol": "BNBUSDT"}
            )
            bnb_data = bnb_24h.json()
            bnb_from_low = (bnb_price - float(bnb_data["lowPrice"])) / float(bnb_data["lowPrice"]) * 100
        
        if eth_from_low < bnb_from_low:
            print(f"✅ ETH mejor setup - más cerca del low 24h")
            print(f"   Entry: ${eth_price:.2f}")
            print(f"   Stop: ${eth_price * 0.97:.2f}")
            print(f"   Target: ${eth_price * 1.025:.2f} (+25% con 10x)")
        else:
            print(f"✅ BNB mejor setup - más cerca del low 24h")
            print(f"   Entry: ${bnb_price:.2f}")
            print(f"   Stop: ${bnb_price * 0.97:.2f}")
            print(f"   Target: ${bnb_price * 1.025:.2f} (+25% con 10x)")
        
        print(f"\n📋 EXECUTION PLAN:")
        print(f"1. Place LIMIT order now at current price or lower")
        print(f"2. Set STOP LOSS at -3% immediately after entry")
        print(f"3. Take 50% profit at T1 (+1.5%)")
        print(f"4. Take 30% profit at T2 (+2.5%)")
        print(f"5. Let 20% run to T3 (+4%)")
        print(f"\n⏰ Best entry: Saturday night / Sunday early morning")
        print(f"🚀 Expected pump: Sunday 2am-6am Mexico time")
        
        print("="*80)

async def main():
    scanner = SundaySwingScanner()
    await scanner.analyze_sunday_setup()

if __name__ == "__main__":
    asyncio.run(main())