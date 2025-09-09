#!/usr/bin/env python3
"""
SOL Trade Analysis - 20x Leverage
Entry at $200 targeting $213 with higher leverage
"""

import asyncio
import httpx
from datetime import datetime
import pytz

class SOL20xAnalysis:
    def __init__(self):
        self.capital = 246.95
        self.position_size = 100.0
        self.leverage_10x = 10
        self.leverage_20x = 20
        self.entry = 200.0
        self.target_10x = 215.0
        self.target_20x = 213.0
        
    async def compare_leverages(self):
        """Compare 10x vs 20x leverage scenarios"""
        print("="*80)
        print("🎯 SOL LEVERAGE COMPARISON: 10x vs 20x")
        print("="*80)
        print(f"💰 Capital: ${self.capital:.2f}")
        print(f"📊 Position Size: ${self.position_size:.2f}")
        print(f"🎯 Entry: $200")
        print("-"*80)
        
        async with httpx.AsyncClient() as client:
            # Get current SOL data
            ticker = await client.get(
                "https://api.binance.com/api/v3/ticker/price",
                params={"symbol": "SOLUSDT"}
            )
            current_price = float(ticker.json()["price"])
            
            print(f"Current SOL Price: ${current_price:.2f}")
            print("="*80)
            
            # 10X LEVERAGE SCENARIO
            print(f"\n📊 SCENARIO 1: 10x LEVERAGE")
            print("-"*40)
            
            # Position details 10x
            position_sol_10x = (self.position_size * self.leverage_10x) / self.entry
            exposure_10x = self.position_size * self.leverage_10x
            
            print(f"Position Size: {position_sol_10x:.2f} SOL")
            print(f"Total Exposure: ${exposure_10x:.2f}")
            
            # P&L for 10x ($200 → $215)
            move_pct_10x = ((self.target_10x - self.entry) / self.entry) * 100
            profit_pct_10x = move_pct_10x * self.leverage_10x
            profit_usd_10x = self.position_size * (profit_pct_10x / 100)
            
            print(f"\nTarget: $200 → $215 (+{move_pct_10x:.1f}%)")
            print(f"Profit: +{profit_pct_10x:.0f}% = +${profit_usd_10x:.2f}")
            
            # Risk for 10x
            liquidation_10x = self.entry * (1 - (1 / self.leverage_10x) + 0.005)  # Including fees
            distance_to_liq_10x = ((self.entry - liquidation_10x) / self.entry) * 100
            
            print(f"\n⚠️ Risk Profile:")
            print(f"   Liquidation: ${liquidation_10x:.2f} (-{distance_to_liq_10x:.1f}%)")
            print(f"   Safe Stop: ${self.entry * 0.97:.2f} (-3% = -$30)")
            print(f"   Max Loss: $100 (if liquidated)")
            
            # 20X LEVERAGE SCENARIO
            print(f"\n" + "="*80)
            print(f"📊 SCENARIO 2: 20x LEVERAGE")
            print("-"*40)
            
            # Position details 20x
            position_sol_20x = (self.position_size * self.leverage_20x) / self.entry
            exposure_20x = self.position_size * self.leverage_20x
            
            print(f"Position Size: {position_sol_20x:.2f} SOL")
            print(f"Total Exposure: ${exposure_20x:.2f}")
            
            # P&L for 20x ($200 → $213)
            move_pct_20x = ((self.target_20x - self.entry) / self.entry) * 100
            profit_pct_20x = move_pct_20x * self.leverage_20x
            profit_usd_20x = self.position_size * (profit_pct_20x / 100)
            
            print(f"\nTarget: $200 → $213 (+{move_pct_20x:.1f}%)")
            print(f"Profit: +{profit_pct_20x:.0f}% = +${profit_usd_20x:.2f}")
            
            # Risk for 20x
            liquidation_20x = self.entry * (1 - (1 / self.leverage_20x) + 0.005)  # Including fees
            distance_to_liq_20x = ((self.entry - liquidation_20x) / self.entry) * 100
            
            print(f"\n⚠️ Risk Profile:")
            print(f"   Liquidation: ${liquidation_20x:.2f} (-{distance_to_liq_20x:.1f}%)")
            print(f"   Safe Stop: ${self.entry * 0.98:.2f} (-2% = -$40)")
            print(f"   Max Loss: $100 (if liquidated)")
            
            # DETAILED RISK COMPARISON
            print(f"\n" + "="*80)
            print(f"🔴 DETAILED RISK ANALYSIS")
            print("-"*80)
            
            print(f"\n📊 LIQUIDATION DISTANCES:")
            print(f"   10x: ${liquidation_10x:.2f} (Safe: -{distance_to_liq_10x:.1f}%)")
            print(f"   20x: ${liquidation_20x:.2f} (RISKY: -{distance_to_liq_20x:.1f}%)")
            
            print(f"\n💥 WHAT EACH DROP MEANS:")
            price_drops = [1, 2, 3, 4, 5]
            
            for drop in price_drops:
                price_at_drop = self.entry * (1 - drop/100)
                loss_10x = min(self.position_size * (drop * self.leverage_10x / 100), 100)
                loss_20x = min(self.position_size * (drop * self.leverage_20x / 100), 100)
                
                status_10x = "LIQUIDATED" if price_at_drop <= liquidation_10x else f"-${loss_10x:.0f}"
                status_20x = "LIQUIDATED" if price_at_drop <= liquidation_20x else f"-${loss_20x:.0f}"
                
                print(f"   -{drop}% (${price_at_drop:.2f}): 10x={status_10x} | 20x={status_20x}")
            
            # STOP LOSS STRATEGIES
            print(f"\n🛡️ STOP LOSS STRATEGIES:")
            
            print(f"\n   For 10x Leverage:")
            print(f"      Aggressive: $195 (-2.5% = -$25 loss)")
            print(f"      Standard: $194 (-3% = -$30 loss)")
            print(f"      Conservative: $192 (-4% = -$40 loss)")
            
            print(f"\n   For 20x Leverage:")
            print(f"      MANDATORY: $197 (-1.5% = -$30 loss)")
            print(f"      CRITICAL: $196 (-2% = -$40 loss)")
            print(f"      MAX: $195 (-2.5% = -$50 loss)")
            
            # PROFIT COMPARISON
            print(f"\n" + "="*80)
            print(f"💰 PROFIT COMPARISON")
            print("-"*80)
            
            print(f"\n📈 Different Price Targets:")
            targets = [205, 207, 210, 213, 215, 220]
            
            print(f"   {'Target':<10} {'Move %':<10} {'10x Profit':<12} {'20x Profit':<12}")
            print(f"   {'-'*46}")
            
            for target in targets:
                move = ((target - self.entry) / self.entry) * 100
                profit_10x = self.position_size * (move * self.leverage_10x / 100)
                profit_20x = self.position_size * (move * self.leverage_20x / 100)
                
                print(f"   ${target:<9.0f} {move:<9.1f}% ${profit_10x:<11.2f} ${profit_20x:<11.2f}")
            
            # RISK/REWARD RATIOS
            print(f"\n📊 RISK/REWARD ANALYSIS:")
            
            # For 10x
            stop_10x = 194  # -3%
            risk_10x = self.entry - stop_10x
            reward_10x = self.target_10x - self.entry
            rr_10x = reward_10x / risk_10x
            
            # For 20x
            stop_20x = 197  # -1.5%
            risk_20x = self.entry - stop_20x
            reward_20x = self.target_20x - self.entry
            rr_20x = reward_20x / risk_20x
            
            print(f"\n   10x Leverage (Target $215):")
            print(f"      Risk: $6 (-3%) = $30 loss")
            print(f"      Reward: $15 (+7.5%) = $75 profit")
            print(f"      R/R Ratio: 1:{rr_10x:.1f}")
            
            print(f"\n   20x Leverage (Target $213):")
            print(f"      Risk: $3 (-1.5%) = $30 loss")
            print(f"      Reward: $13 (+6.5%) = $130 profit")
            print(f"      R/R Ratio: 1:{rr_20x:.1f}")
            
            # FINAL VERDICT
            print(f"\n" + "="*80)
            print(f"🎯 FINAL VERDICT & RECOMMENDATION")
            print("="*80)
            
            print(f"\n✅ 10x LEVERAGE (SAFER):")
            print(f"   Pros:")
            print(f"   - More room for error (-9.5% to liquidation)")
            print(f"   - Can handle normal volatility")
            print(f"   - Stop loss at -3% reasonable")
            print(f"   - Still good profit: +$75 at $215")
            
            print(f"\n⚠️ 20x LEVERAGE (RISKY):")
            print(f"   Pros:")
            print(f"   - Double the profit: +$130 at $213")
            print(f"   - Lower target needed ($213 vs $215)")
            print(f"   - Better R/R if managed well")
            print(f"   \n   Cons:")
            print(f"   - Only -4.5% to liquidation!")
            print(f"   - MUST use tight stop (-1.5%)")
            print(f"   - One wick to $195 = LIQUIDATED")
            print(f"   - Sunday volatility = HIGH RISK")
            
            print(f"\n💡 RECOMMENDATION:")
            print(f"   Given Sunday night volatility:")
            print(f"   - USE 10x for main position ($75)")
            print(f"   - Optional: Small 20x position ($25) with TIGHT stop")
            print(f"   - Never 20x with full $100 - too risky")
            
            print(f"\n📋 SUGGESTED SPLIT:")
            print(f"   - $75 @ 10x (target $215)")
            print(f"   - $25 @ 20x (target $210, tight stop $197)")
            print(f"   - Keep $146.95 in reserve")
            
            print("="*80)

async def main():
    analyzer = SOL20xAnalysis()
    await analyzer.compare_leverages()

if __name__ == "__main__":
    asyncio.run(main())