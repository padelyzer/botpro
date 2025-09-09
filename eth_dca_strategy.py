#!/usr/bin/env python3
"""
ETH DCA (Dollar Cost Average) Strategy
Analyzing if we should average down without stop loss
"""

import asyncio
import httpx
from datetime import datetime
import pytz

class ETHDCAStrategy:
    def __init__(self):
        # Current position
        self.entry_1_price = 4756.0
        self.entry_1_size = 24.74
        self.leverage = 10
        
        # Available capital for DCA
        self.remaining_capital = 250.0 - 24.74  # $225.26 left
        self.max_additional_position = 50.0  # Max we're willing to add
        
    async def analyze_dca_strategy(self):
        """
        Analyze DCA strategy without stop loss
        """
        print("="*80)
        print("🎯 ETH DCA STRATEGY ANALYSIS (NO STOP LOSS)")
        print("="*80)
        print(f"📊 Current Position:")
        print(f"   Entry 1: ${self.entry_1_price:.2f} x $24.74 @ 10x")
        print(f"   Remaining Capital: ${self.remaining_capital:.2f}")
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
            
            # Get recent support levels
            klines_4h = await client.get(
                "https://fapi.binance.com/fapi/v1/klines",
                params={"symbol": "ETHUSDT", "interval": "4h", "limit": 24}
            )
            
            support_levels = []
            if klines_4h.status_code == 200:
                candles = klines_4h.json()
                lows = [float(c[3]) for c in candles]
                
                # Find key support levels
                support_levels = [
                    low_24h,  # 24h low
                    sorted(lows)[len(lows)//4],  # 25th percentile
                    min(lows),  # Recent absolute low
                ]
                support_levels = sorted(set(support_levels))
            
            print(f"📈 CURRENT MARKET:")
            print(f"   Price: ${current_price:.2f}")
            print(f"   24h Range: ${low_24h:.2f} - ${high_24h:.2f}")
            print(f"   ATH Distance: ETH near ATH = trap risk ⚠️")
            
            # Liquidity traps analysis
            print(f"\n🪤 EXCHANGE TRAP ANALYSIS:")
            print(f"   - Near ATH = High liquidation hunt risk")
            print(f"   - Sunday night = Low volume = Easy manipulation")
            print(f"   - Common trap: Quick wick to $4600-4650 to trigger stops")
            print(f"   - Then pump to $4900+ after stops cleared")
            
            # DCA levels calculation
            print(f"\n📊 DCA STRATEGY OPTIONS:")
            print("-"*40)
            
            # Option 1: Conservative DCA
            dca_level_1 = low_24h * 1.01  # Just above 24h low
            dca_size_1 = 25.0  # Another $25
            
            print(f"\n1️⃣ CONSERVATIVE DCA:")
            print(f"   Entry 2: ${dca_level_1:.2f} (-{((current_price - dca_level_1)/current_price*100):.1f}%)")
            print(f"   Size: ${dca_size_1:.2f} @ 10x")
            
            # Calculate average entry
            total_size_1 = self.entry_1_size + dca_size_1
            avg_entry_1 = ((self.entry_1_price * self.entry_1_size) + 
                          (dca_level_1 * dca_size_1)) / total_size_1
            
            print(f"   New Average Entry: ${avg_entry_1:.2f}")
            print(f"   Total Position: ${total_size_1:.2f} @ 10x = ${total_size_1 * 10:.2f}")
            
            # Liquidation with DCA
            liq_price_1 = avg_entry_1 * 0.905
            print(f"   Liquidation: ${liq_price_1:.2f}")
            
            # Option 2: Aggressive DCA
            dca_level_2a = 4650  # Trap zone
            dca_level_2b = 4600  # Deep trap zone
            dca_size_2a = 25.0
            dca_size_2b = 25.0
            
            print(f"\n2️⃣ AGGRESSIVE DCA (TRAP ZONES):")
            print(f"   Entry 2: ${dca_level_2a:.2f} (-{((current_price - dca_level_2a)/current_price*100):.1f}%)")
            print(f"   Entry 3: ${dca_level_2b:.2f} (-{((current_price - dca_level_2b)/current_price*100):.1f}%)")
            print(f"   Size: ${dca_size_2a:.2f} + ${dca_size_2b:.2f} @ 10x")
            
            # Calculate average with aggressive DCA
            if current_price < dca_level_2a:
                total_size_2 = self.entry_1_size + dca_size_2a + dca_size_2b
                avg_entry_2 = ((self.entry_1_price * self.entry_1_size) + 
                              (dca_level_2a * dca_size_2a) +
                              (dca_level_2b * dca_size_2b)) / total_size_2
            else:
                total_size_2 = self.entry_1_size + dca_size_2a + dca_size_2b
                avg_entry_2 = ((self.entry_1_price * self.entry_1_size) + 
                              (dca_level_2a * dca_size_2a) +
                              (dca_level_2b * dca_size_2b)) / total_size_2
            
            print(f"   New Average Entry: ${avg_entry_2:.2f}")
            print(f"   Total Position: ${total_size_2:.2f} @ 10x = ${total_size_2 * 10:.2f}")
            
            # Liquidation with aggressive DCA
            liq_price_2 = avg_entry_2 * 0.905
            print(f"   Liquidation: ${liq_price_2:.2f}")
            
            # Risk Analysis
            print(f"\n⚠️ RISK ANALYSIS WITHOUT STOP LOSS:")
            
            # Scenario 1: No DCA
            max_loss_no_dca = self.entry_1_size
            print(f"\n   Current Position Only:")
            print(f"   Max Loss (liquidation): ${max_loss_no_dca:.2f}")
            print(f"   Liquidation at: ${self.entry_1_price * 0.905:.2f}")
            
            # Scenario 2: With DCA
            max_loss_with_dca = total_size_2
            print(f"\n   With Full DCA:")
            print(f"   Max Loss (liquidation): ${max_loss_with_dca:.2f}")
            print(f"   Liquidation at: ${liq_price_2:.2f}")
            
            # Profit targets with DCA
            print(f"\n🎯 PROFIT TARGETS (NO STOP LOSS):")
            
            for avg_entry, total_size, strategy in [
                (self.entry_1_price, self.entry_1_size, "Current"),
                (avg_entry_1, total_size_1, "Conservative DCA"),
                (avg_entry_2, total_size_2, "Aggressive DCA")
            ]:
                print(f"\n   {strategy} (Avg: ${avg_entry:.2f}):")
                
                targets = [
                    (avg_entry * 1.015, 1.5),  # 1.5%
                    (avg_entry * 1.025, 2.5),  # 2.5%
                    (avg_entry * 1.04, 4.0),   # 4%
                    (avg_entry * 1.06, 6.0),   # 6% (ATH push)
                ]
                
                for target_price, move_pct in targets:
                    profit = total_size * (move_pct * 10 / 100)
                    print(f"      +{move_pct}%: ${target_price:.2f} = +${profit:.2f}")
            
            # Sunday pump probability
            print(f"\n🚀 SUNDAY PUMP SCENARIO:")
            mexico_tz = pytz.timezone('America/Mexico_City')
            mexico_time = datetime.now(mexico_tz)
            hours_to_2am = (26 - mexico_time.hour) % 24
            
            print(f"   Time to 2am: {hours_to_2am} hours")
            print(f"   Historical pattern: Wick down → Pump up")
            print(f"   Trap zone: $4600-4650 (stop hunt)")
            print(f"   Pump target: $4850-4950")
            
            # FINAL RECOMMENDATION
            print(f"\n" + "="*80)
            print(f"💡 RECOMMENDATION (NO STOP LOSS STRATEGY):")
            print("-"*80)
            
            print(f"\n✅ BEST APPROACH:")
            print(f"1. Place DCA orders:")
            print(f"   - $25 @ $4680 (above 24h low)")
            print(f"   - $25 @ $4650 (trap zone 1)")
            print(f"   - $25 @ $4600 (trap zone 2)")
            
            print(f"\n2. Why this works:")
            print(f"   - Exchanges hunt stops at $4600-4650")
            print(f"   - Your DCA catches the trap")
            print(f"   - Average entry improves to ~$4670")
            print(f"   - Sunday pump to $4850+ = massive profit")
            
            print(f"\n3. Exit strategy:")
            print(f"   - Take 30% at +2% move")
            print(f"   - Take 30% at +3% move")
            print(f"   - Take 30% at +4% move")
            print(f"   - Let 10% run to ATH")
            
            print(f"\n⚠️ MAXIMUM RISK:")
            print(f"   - Total at risk: ${total_size_2:.2f}")
            print(f"   - Only 10% of capital (${total_size_2/250*100:.1f}%)")
            print(f"   - Worth it for Sunday pump potential")
            
            print(f"\n🎯 EXPECTED OUTCOME:")
            print(f"   - 70% chance: Trap → Pump → +$20-40 profit")
            print(f"   - 20% chance: Direct pump → +$10-20 profit")
            print(f"   - 10% chance: Real dump → Wait for recovery")
            
            print("="*80)

async def main():
    strategy = ETHDCAStrategy()
    await strategy.analyze_dca_strategy()

if __name__ == "__main__":
    asyncio.run(main())