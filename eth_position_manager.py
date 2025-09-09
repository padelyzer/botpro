#!/usr/bin/env python3
"""
ETH Position Manager
Managing active position: $24.74 @ $4756 with 10x leverage
"""

import asyncio
import httpx
from datetime import datetime
import pytz

class ETHPositionManager:
    def __init__(self):
        self.entry_price = 4756.0
        self.position_size_usd = 24.74
        self.leverage = 10
        self.effective_exposure = self.position_size_usd * self.leverage  # $247.40
        self.position_size_eth = self.effective_exposure / self.entry_price  # 0.052 ETH
        
    async def analyze_position(self):
        """
        Analyze current position and provide management recommendations
        """
        print("="*80)
        print("📊 ETH POSITION MANAGEMENT")
        print("="*80)
        print(f"🎯 Your Position:")
        print(f"   Entry: ${self.entry_price:.2f}")
        print(f"   Size: ${self.position_size_usd:.2f} @ {self.leverage}x")
        print(f"   Exposure: ${self.effective_exposure:.2f}")
        print(f"   Amount: {self.position_size_eth:.4f} ETH")
        print("-"*80)
        
        async with httpx.AsyncClient() as client:
            # Get current price
            ticker = await client.get(
                "https://api.binance.com/api/v3/ticker/price",
                params={"symbol": "ETHUSDT"}
            )
            current_price = float(ticker.json()["price"])
            
            # Get 24h data
            ticker_24h = await client.get(
                "https://api.binance.com/api/v3/ticker/24hr",
                params={"symbol": "ETHUSDT"}
            )
            data = ticker_24h.json()
            high_24h = float(data["highPrice"])
            low_24h = float(data["lowPrice"])
            volume = float(data["volume"])
            
            # Calculate P&L
            price_change_pct = ((current_price - self.entry_price) / self.entry_price) * 100
            pnl_pct = price_change_pct * self.leverage
            pnl_usd = self.position_size_usd * (pnl_pct / 100)
            
            print(f"📈 CURRENT STATUS:")
            print(f"   Current Price: ${current_price:.2f}")
            print(f"   Price Movement: {price_change_pct:+.2f}%")
            print(f"   P&L: {pnl_pct:+.1f}% (${pnl_usd:+.2f})")
            
            if pnl_usd > 0:
                print(f"   Status: ✅ IN PROFIT")
            elif pnl_usd < 0:
                print(f"   Status: ⚠️ IN LOSS")
            else:
                print(f"   Status: ➖ BREAKEVEN")
            
            # Risk levels
            print(f"\n⚠️ RISK LEVELS:")
            
            # Liquidation price (with 10x, roughly -10% move)
            liquidation_price = self.entry_price * 0.905  # Account for fees
            distance_to_liq = ((current_price - liquidation_price) / current_price) * 100
            
            print(f"   Liquidation: ${liquidation_price:.2f} (-{distance_to_liq:.1f}% from here)")
            
            # Recommended stop loss
            stop_loss_3pct = self.entry_price * 0.97
            stop_loss_2pct = self.entry_price * 0.98
            
            print(f"   Recommended Stops:")
            print(f"      Conservative: ${stop_loss_2pct:.2f} (-2% = -20% loss)")
            print(f"      Standard: ${stop_loss_3pct:.2f} (-3% = -30% loss)")
            
            # Take profit levels
            print(f"\n🎯 TAKE PROFIT TARGETS:")
            
            # Calculate targets
            tp1 = self.entry_price * 1.01   # 1% = 10% profit
            tp2 = self.entry_price * 1.015  # 1.5% = 15% profit
            tp3 = self.entry_price * 1.025  # 2.5% = 25% profit
            tp4 = self.entry_price * 1.04   # 4% = 40% profit
            
            for i, (tp, gain_pct) in enumerate([
                (tp1, 1.0), (tp2, 1.5), (tp3, 2.5), (tp4, 4.0)
            ], 1):
                profit = self.position_size_usd * (gain_pct * self.leverage / 100)
                distance = ((tp - current_price) / current_price) * 100
                
                if current_price >= tp:
                    status = "✅ REACHED"
                else:
                    status = f"📍 +{distance:.2f}% away"
                
                print(f"   TP{i}: ${tp:.2f} (+{gain_pct}% = +${profit:.2f}) {status}")
            
            # Market context
            print(f"\n📊 MARKET CONTEXT:")
            print(f"   24h High: ${high_24h:.2f} (+{((high_24h - current_price)/current_price*100):.2f}% from here)")
            print(f"   24h Low: ${low_24h:.2f} (-{((current_price - low_24h)/current_price*100):.2f}% from here)")
            
            # Get order book data
            try:
                liquidity = await client.get(f"http://localhost:8002/api/liquidity/ETHUSDT")
                if liquidity.status_code == 200:
                    ob_data = liquidity.json().get("order_book_analysis", {})
                    imbalance = ob_data.get("imbalance", 0)
                    print(f"   Order Book Imbalance: {imbalance:.1f}%")
                    
                    if imbalance > 10:
                        print(f"   Sentiment: 🟢 BULLISH")
                    elif imbalance < -10:
                        print(f"   Sentiment: 🔴 BEARISH")
                    else:
                        print(f"   Sentiment: 🟡 NEUTRAL")
            except:
                pass
            
            # Time analysis
            mexico_tz = pytz.timezone('America/Mexico_City')
            mexico_time = datetime.now(mexico_tz)
            
            print(f"\n⏰ TIME ANALYSIS:")
            print(f"   Mexico Time: {mexico_time.strftime('%H:%M')}")
            print(f"   Day: {mexico_time.strftime('%A')}")
            
            if mexico_time.weekday() == 6:  # Sunday
                if 2 <= mexico_time.hour <= 6:
                    print(f"   🚀 SUNDAY PUMP ZONE ACTIVE!")
            elif mexico_time.weekday() == 5:  # Saturday
                print(f"   📅 Tomorrow is Sunday pump day")
            
            # RECOMMENDATIONS
            print(f"\n" + "="*80)
            print(f"💡 RECOMMENDATIONS:")
            print("-"*80)
            
            if pnl_pct >= 10:  # 10% profit (1% move)
                print(f"✅ TAKE PARTIAL PROFITS!")
                print(f"   1. Take 50% profit now (${self.position_size_usd * 0.5:.2f})")
                print(f"   2. Move stop to breakeven (${self.entry_price:.2f})")
                print(f"   3. Let 50% run to next targets")
                
            elif pnl_pct >= 5:  # 5% profit (0.5% move)
                print(f"⚠️ APPROACHING FIRST TARGET")
                print(f"   1. Set stop loss at ${stop_loss_2pct:.2f}")
                print(f"   2. Prepare to take 30% at TP1 (${tp1:.2f})")
                
            elif pnl_pct <= -15:  # 15% loss (1.5% move against)
                print(f"🔴 RISK MANAGEMENT CRITICAL")
                print(f"   1. Set HARD STOP at ${stop_loss_3pct:.2f}")
                print(f"   2. Don't add to losing position")
                print(f"   3. Max loss: ${self.position_size_usd * 0.3:.2f}")
                
            elif -5 <= pnl_pct <= 5:  # Near breakeven
                print(f"📊 POSITION MANAGEMENT")
                print(f"   1. Set stop loss at ${stop_loss_3pct:.2f} (-3%)")
                print(f"   2. Take profit orders:")
                print(f"      - 30% at ${tp1:.2f}")
                print(f"      - 30% at ${tp2:.2f}")
                print(f"      - 40% at ${tp3:.2f}")
                
                if mexico_time.weekday() >= 5:  # Weekend
                    print(f"   3. Hold for Sunday pump (2am-6am Mexico)")
            
            # Exit strategy
            print(f"\n📋 EXIT STRATEGY:")
            
            if current_price > self.entry_price:
                print(f"   ✅ You're in profit - protect it!")
                print(f"   - Trail stop by 2% below current")
                print(f"   - Take 30-50% profit on spikes")
            else:
                print(f"   ⚠️ You're in loss - manage risk!")
                print(f"   - Hard stop at -3% (${stop_loss_3pct:.2f})")
                print(f"   - Don't move stop lower")
            
            print(f"\n🎯 SUNDAY PUMP TARGETS:")
            print(f"   Quick scalp: ${self.entry_price * 1.015:.2f} (+15% profit)")
            print(f"   Medium: ${self.entry_price * 1.025:.2f} (+25% profit)")
            print(f"   Extended: ${self.entry_price * 1.04:.2f} (+40% profit)")
            
            print("="*80)

async def main():
    manager = ETHPositionManager()
    await manager.analyze_position()

if __name__ == "__main__":
    asyncio.run(main())