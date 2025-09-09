#!/usr/bin/env python3
"""
Validate Current Positions
Check if market is moving as expected
"""

import asyncio
import httpx
from datetime import datetime
import pytz

class PositionValidator:
    def __init__(self):
        # Current positions
        self.eth_position = {
            "entry": 4756.0,
            "size_usd": 24.74,
            "leverage": 10,
            "direction": "LONG"
        }
        
        # DCA orders placed
        self.eth_dca_orders = [
            {"price": 4680, "size": 25},
            {"price": 4650, "size": 25},
            {"price": 4600, "size": 25}
        ]
        
        # Expected scenario
        self.expected_scenario = {
            "phase1": "Drop to $4600-4650 to hunt long liquidations",
            "phase2": "Pump to $4850+ after liquidation hunt",
            "timing": "Sunday 11pm-2am Mexico for drop, 2am-6am for pump"
        }
        
    async def validate_market_movement(self):
        """Check if market is following expected pattern"""
        print("="*80)
        print("📊 POSITION VALIDATION & MARKET ANALYSIS")
        print("="*80)
        
        async with httpx.AsyncClient() as client:
            # Get current ETH price
            eth_ticker = await client.get(
                "https://api.binance.com/api/v3/ticker/price",
                params={"symbol": "ETHUSDT"}
            )
            eth_price = float(eth_ticker.json()["price"])
            
            # Get SOL price
            sol_ticker = await client.get(
                "https://api.binance.com/api/v3/ticker/price",
                params={"symbol": "SOLUSDT"}
            )
            sol_price = float(sol_ticker.json()["price"])
            
            # Get 24h data
            eth_24h = await client.get(
                "https://api.binance.com/api/v3/ticker/24hr",
                params={"symbol": "ETHUSDT"}
            )
            eth_data = eth_24h.json()
            eth_low = float(eth_data["lowPrice"])
            eth_high = float(eth_data["highPrice"])
            
            sol_24h = await client.get(
                "https://api.binance.com/api/v3/ticker/24hr",
                params={"symbol": "SOLUSDT"}
            )
            sol_data = sol_24h.json()
            sol_low = float(sol_data["lowPrice"])
            sol_high = float(sol_data["highPrice"])
            
            # Time analysis
            mexico_tz = pytz.timezone('America/Mexico_City')
            mexico_time = datetime.now(mexico_tz)
            
            print(f"⏰ Current Time: {mexico_time.strftime('%H:%M')} Mexico")
            print(f"📅 Day: {mexico_time.strftime('%A')}")
            print("-"*80)
            
            # ETH Position Analysis
            print(f"\n💼 ETH POSITION STATUS:")
            print(f"   Entry: ${self.eth_position['entry']:.2f}")
            print(f"   Current: ${eth_price:.2f}")
            
            pnl_pct = ((eth_price - self.eth_position['entry']) / self.eth_position['entry']) * 100
            pnl_usd = self.eth_position['size_usd'] * (pnl_pct * self.eth_position['leverage'] / 100)
            
            if pnl_usd >= 0:
                print(f"   P&L: ✅ +${pnl_usd:.2f} (+{pnl_pct*self.eth_position['leverage']:.1f}%)")
            else:
                print(f"   P&L: ⚠️ ${pnl_usd:.2f} ({pnl_pct*self.eth_position['leverage']:.1f}%)")
            
            print(f"\n   24h Range: ${eth_low:.2f} - ${eth_high:.2f}")
            print(f"   Distance from 24h low: +{((eth_price - eth_low)/eth_low*100):.2f}%")
            
            # DCA Orders Status
            print(f"\n📋 DCA ORDERS STATUS:")
            for order in self.eth_dca_orders:
                if eth_price > order["price"]:
                    status = f"⏳ Waiting (${order['price']:.2f})"
                else:
                    status = f"✅ FILLED at ${order['price']:.2f}"
                print(f"   ${order['size']} @ ${order['price']}: {status}")
            
            # Market Movement Validation
            print(f"\n🎯 EXPECTED SCENARIO:")
            print(f"   Phase 1: {self.expected_scenario['phase1']}")
            print(f"   Phase 2: {self.expected_scenario['phase2']}")
            print(f"   Timing: {self.expected_scenario['timing']}")
            
            print(f"\n📊 ACTUAL MARKET MOVEMENT:")
            
            # Check ETH movement
            if eth_low < 4650:
                print(f"   ✅ ETH touched liquidation zone (${eth_low:.2f})")
                print(f"      Phase 1 COMPLETED - Longs liquidated")
                
                if eth_price > 4700:
                    print(f"   ✅ ETH bouncing back (${eth_price:.2f})")
                    print(f"      Phase 2 IN PROGRESS - Moving toward targets")
            elif eth_price < 4700:
                print(f"   ⏳ ETH dropping toward liquidation zones")
                print(f"      Phase 1 IN PROGRESS - Hunting ${4650}")
            else:
                print(f"   ⏳ ETH consolidating above ${4700}")
                print(f"      Waiting for Sunday night action")
            
            # SOL Analysis
            print(f"\n📊 SOL STATUS:")
            print(f"   Current: ${sol_price:.2f}")
            print(f"   24h Range: ${sol_low:.2f} - ${sol_high:.2f}")
            
            if sol_low < 202:
                print(f"   ✅ SOL hit liquidation target (${sol_low:.2f})")
                if sol_price > 205:
                    print(f"      Bouncing from liquidation hunt")
            else:
                print(f"   ⏳ SOL waiting to test $200-202 support")
            
            # Sunday Pump Analysis
            print(f"\n🌙 SUNDAY PUMP ANALYSIS:")
            
            if mexico_time.weekday() == 6:  # Sunday
                hours_since_midnight = mexico_time.hour
                
                if hours_since_midnight < 2:
                    print(f"   ⏳ {2 - hours_since_midnight} hours until pump window (2am)")
                    print(f"      Expect more downside first")
                elif 2 <= hours_since_midnight <= 6:
                    print(f"   🚀 IN PUMP WINDOW NOW!")
                    print(f"      Markets should be moving UP")
                else:
                    print(f"   ✅ Pump window passed")
            
            # Market Direction Validation
            print(f"\n" + "="*80)
            print(f"🎯 MARKET DIRECTION VALIDATION:")
            print("-"*80)
            
            # Compare to our thesis
            thesis_correct = 0
            thesis_total = 4
            
            # Check 1: ETH holding above $4600
            if eth_price > 4600:
                print(f"✅ ETH holding above $4600 support")
                thesis_correct += 1
            else:
                print(f"❌ ETH broke $4600 support")
            
            # Check 2: SOL holding above $200
            if sol_price > 200:
                print(f"✅ SOL holding above $200 support")
                thesis_correct += 1
            else:
                print(f"❌ SOL broke $200 support")
            
            # Check 3: Liquidation hunt pattern
            if eth_low < 4700 or sol_low < 205:
                print(f"✅ Liquidation hunt occurred as expected")
                thesis_correct += 1
            else:
                print(f"⏳ Liquidation hunt pending")
            
            # Check 4: Time alignment
            if mexico_time.weekday() == 6 and 22 <= mexico_time.hour <= 23:
                print(f"✅ Perfect timing for Sunday setup")
                thesis_correct += 1
            elif mexico_time.weekday() == 6:
                print(f"✅ Sunday - pump day active")
                thesis_correct += 1
            else:
                print(f"⏳ Not Sunday yet")
            
            accuracy = (thesis_correct / thesis_total) * 100
            print(f"\n📊 THESIS ACCURACY: {thesis_correct}/{thesis_total} ({accuracy:.0f}%)")
            
            if accuracy >= 75:
                print(f"✅ Market moving as expected - STAY THE COURSE")
            elif accuracy >= 50:
                print(f"⚠️ Partially aligned - MONITOR CLOSELY")
            else:
                print(f"❌ Market diverging - CONSIDER ADJUSTING")
            
            # Final Recommendation
            print(f"\n💡 RECOMMENDATION:")
            
            if eth_price < 4700 and eth_price > 4600:
                print(f"   ✅ ETH in perfect DCA zone")
                print(f"   Action: Let DCA orders fill, prepare for pump")
            elif eth_price > 4750:
                print(f"   ⏳ ETH consolidating")
                print(f"   Action: Wait for dip to DCA levels or breakout >$4800")
            
            if pnl_usd > 5:
                print(f"   💰 Consider taking partial profits (30-50%)")
            elif pnl_usd < -10:
                print(f"   ⚠️ Approaching max loss - stick to plan, don't panic")
            
            print("="*80)

async def main():
    validator = PositionValidator()
    await validator.validate_market_movement()

if __name__ == "__main__":
    asyncio.run(main())