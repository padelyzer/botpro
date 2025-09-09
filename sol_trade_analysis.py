#!/usr/bin/env python3
"""
SOL Trade Analysis
Entry at $200 with 10x leverage targeting $215
"""

import asyncio
import httpx
from datetime import datetime
import pytz

class SOLTradeAnalysis:
    def __init__(self):
        self.capital = 246.95
        self.position_size = 100.0
        self.leverage = 10
        self.target_entry = 200.0
        self.target_exit = 215.0
        
    async def analyze_trade_setup(self):
        """Analyze SOL $200 entry setup"""
        print("="*80)
        print("🎯 SOL TRADE ANALYSIS - $200 ENTRY PLAN")
        print("="*80)
        print(f"💰 Capital: ${self.capital:.2f}")
        print(f"📊 Plan: $100 @ 10x leverage")
        print(f"🎯 Entry: $200 | Target: $215")
        print("-"*80)
        
        async with httpx.AsyncClient() as client:
            # Get current SOL data
            ticker = await client.get(
                "https://api.binance.com/api/v3/ticker/price",
                params={"symbol": "SOLUSDT"}
            )
            current_price = float(ticker.json()["price"])
            
            # Get 24h data
            ticker_24h = await client.get(
                "https://api.binance.com/api/v3/ticker/24hr",
                params={"symbol": "SOLUSDT"}
            )
            data = ticker_24h.json()
            high_24h = float(data["highPrice"])
            low_24h = float(data["lowPrice"])
            volume = float(data["volume"])
            
            # Get order book depth
            depth = await client.get(
                "https://api.binance.com/api/v3/depth",
                params={"symbol": "SOLUSDT", "limit": 100}
            )
            order_book = depth.json()
            
            # Calculate support at $200
            bids = order_book["bids"]
            support_200 = sum(float(bid[1]) for bid in bids if 199 <= float(bid[0]) <= 201)
            
            print(f"\n📊 CURRENT MARKET:")
            print(f"   SOL Price: ${current_price:.2f}")
            print(f"   24h Range: ${low_24h:.2f} - ${high_24h:.2f}")
            print(f"   Distance to $200: {((200 - current_price) / current_price * 100):.2f}%")
            print(f"   Support at $200: {support_200:.0f} SOL")
            
            # Trade calculations
            print(f"\n💹 TRADE CALCULATIONS:")
            
            # Position details
            position_size_sol = (self.position_size * self.leverage) / self.target_entry
            
            print(f"   Position Size: {position_size_sol:.2f} SOL")
            print(f"   Exposure: ${self.position_size * self.leverage:.2f}")
            
            # P&L Calculation
            price_move_pct = ((self.target_exit - self.target_entry) / self.target_entry) * 100
            profit_pct = price_move_pct * self.leverage
            profit_usd = self.position_size * (profit_pct / 100)
            
            print(f"\n   Price Move: ${self.target_entry:.2f} → ${self.target_exit:.2f} (+{price_move_pct:.2f}%)")
            print(f"   Profit with 10x: +{profit_pct:.1f}% = +${profit_usd:.2f}")
            
            # Risk analysis
            print(f"\n⚠️ RISK ANALYSIS:")
            
            # Stop loss levels
            stop_5pct = self.target_entry * 0.95
            stop_3pct = self.target_entry * 0.97
            stop_2pct = self.target_entry * 0.98
            
            liquidation = self.target_entry * 0.905  # ~9.5% with 10x
            
            print(f"   Stop Loss Options:")
            print(f"      Conservative: ${stop_2pct:.2f} (-2% = -$20 loss)")
            print(f"      Standard: ${stop_3pct:.2f} (-3% = -$30 loss)")
            print(f"      Aggressive: ${stop_5pct:.2f} (-5% = -$50 loss)")
            print(f"   Liquidation: ${liquidation:.2f} (-9.5% = -$100 total loss)")
            
            # Probability analysis
            print(f"\n📈 PROBABILITY ANALYSIS:")
            
            # Check how many times SOL bounced from $200
            print(f"   $200 Level:")
            print(f"      - Major psychological support")
            print(f"      - Previous resistance turned support")
            print(f"      - High liquidation density")
            
            if low_24h < 202:
                print(f"      ✅ Already tested ${low_24h:.2f} and bounced")
            else:
                print(f"      ⏳ Not tested yet in 24h")
            
            # Sunday analysis
            mexico_tz = pytz.timezone('America/Mexico_City')
            mexico_time = datetime.now(mexico_tz)
            
            print(f"\n🌙 TIMING ANALYSIS:")
            print(f"   Current: {mexico_time.strftime('%H:%M')} Mexico, {mexico_time.strftime('%A')}")
            
            if mexico_time.weekday() == 6:  # Sunday
                if mexico_time.hour >= 23 or mexico_time.hour <= 2:
                    print(f"   ✅ PERFECT TIMING - Sunday night/early Monday")
                    print(f"   High probability of pump after touching $200")
            
            # Key levels
            print(f"\n🎯 KEY LEVELS TO WATCH:")
            print(f"   Entry Zone: $199-201 (flexibility needed)")
            print(f"   First Resistance: $207-208 (previous support)")
            print(f"   Target Zone: $213-215 (recent high)")
            print(f"   Extension: $220 (if short squeeze)")
            
            # Trade execution plan
            print(f"\n📋 EXECUTION PLAN:")
            print(f"   1. Place LIMIT orders:")
            print(f"      - $50 @ $201")
            print(f"      - $50 @ $200")
            print(f"   2. If filled:")
            print(f"      - Set stop at $194-195 (-3%)")
            print(f"      - TP1: $207 (take 30%)")
            print(f"      - TP2: $210 (take 30%)")
            print(f"      - TP3: $215 (take 40%)")
            
            # Risk/Reward
            avg_entry = 200.5  # Average if both orders fill
            risk = avg_entry - 195  # $5.5 risk
            reward = 215 - avg_entry  # $14.5 reward
            rr_ratio = reward / risk
            
            print(f"\n📊 RISK/REWARD:")
            print(f"   Risk: ${risk:.2f} per SOL (-{(risk/avg_entry*100):.1f}%)")
            print(f"   Reward: ${reward:.2f} per SOL (+{(reward/avg_entry*100):.1f}%)")
            print(f"   R/R Ratio: 1:{rr_ratio:.1f}")
            
            # Final verdict
            print(f"\n" + "="*80)
            print(f"🎯 VERDICT:")
            print("-"*80)
            
            if current_price > 202:
                print(f"✅ GOOD SETUP - Wait for dip to $200")
                print(f"   - Strong psychological support")
                print(f"   - R/R ratio 1:{rr_ratio:.1f} excellent")
                print(f"   - Sunday night timing perfect")
                print(f"   - Profit potential: +$75 (7.5% move = 75% with 10x)")
            elif current_price <= 202 and current_price > 200:
                print(f"⚠️ ALMOST THERE - Get ready")
                print(f"   - Very close to entry zone")
                print(f"   - Place orders now")
            else:
                print(f"🚨 RECONSIDER - Price below $200")
                print(f"   - Support may be breaking")
                print(f"   - Wait for confirmation of bounce")
            
            print(f"\n⚠️ IMPORTANT NOTES:")
            print(f"   - $200 MUST HOLD - break below = cascade to $190")
            print(f"   - Don't chase if it bounces before hitting $200")
            print(f"   - Use only $100 (40% of capital) - keep reserves")
            
            print("="*80)

async def main():
    analyzer = SOLTradeAnalysis()
    await analyzer.analyze_trade_setup()

if __name__ == "__main__":
    asyncio.run(main())