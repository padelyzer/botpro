#!/usr/bin/env python3
"""
SOL Liquidation Map
Shows where leveraged positions will be liquidated
SOL dropped from 213 to 207 - analyzing liquidation hunt
"""

import asyncio
import httpx
from datetime import datetime
import json

class SOLLiquidationMap:
    def __init__(self):
        self.symbol = "SOLUSDT"
        
    async def analyze_liquidation_zones(self):
        """
        Analyze liquidation zones for SOL after drop from 213 to 207
        """
        print("="*80)
        print("🎯 SOLANA LIQUIDATION MAP")
        print("="*80)
        print("📉 Context: SOL dropped from $213 → $207")
        print("-"*80)
        
        async with httpx.AsyncClient() as client:
            # Get current price
            ticker = await client.get(
                "https://api.binance.com/api/v3/ticker/price",
                params={"symbol": self.symbol}
            )
            current_price = float(ticker.json()["price"])
            
            # Get 24h data for context
            ticker_24h = await client.get(
                "https://api.binance.com/api/v3/ticker/24hr",
                params={"symbol": self.symbol}
            )
            data = ticker_24h.json()
            high_24h = float(data["highPrice"])
            low_24h = float(data["lowPrice"])
            volume_24h = float(data["volume"])
            change_24h = float(data["priceChangePercent"])
            
            print(f"📊 CURRENT MARKET:")
            print(f"   Price: ${current_price:.2f}")
            print(f"   24h Range: ${low_24h:.2f} - ${high_24h:.2f}")
            print(f"   24h Change: {change_24h:+.2f}%")
            print(f"   24h Volume: {volume_24h:,.0f} SOL")
            print(f"   Drop from $213: {((current_price - 213) / 213 * 100):.2f}%")
            print("-"*80)
            
            # Get liquidation data from API
            try:
                liquidity_response = await client.get(f"http://localhost:8002/api/liquidity/{self.symbol}")
                if liquidity_response.status_code == 200:
                    liquidity_data = liquidity_response.json()
                    order_book = liquidity_data.get("order_book_analysis", {})
                    
                    # Get support/resistance from order book
                    support_levels = order_book.get("support_levels", [])
                    resistance_levels = order_book.get("resistance_levels", [])
                    
                    print(f"\n💧 ORDER BOOK LIQUIDITY:")
                    
                    if support_levels:
                        print(f"\n   📉 BUY LIQUIDITY (Support):")
                        total_buy_liquidity = 0
                        for level in support_levels[:5]:
                            price = level.get('price', 0)
                            size = level.get('total_size', 0)
                            total_buy_liquidity += size
                            distance = ((current_price - price) / current_price) * 100
                            print(f"      ${price:.2f} ({distance:+.2f}%): {size:.2f} SOL")
                        print(f"      Total: {total_buy_liquidity:.2f} SOL")
                    
                    if resistance_levels:
                        print(f"\n   📈 SELL LIQUIDITY (Resistance):")
                        total_sell_liquidity = 0
                        for level in resistance_levels[:5]:
                            price = level.get('price', 0)
                            size = level.get('total_size', 0)
                            total_sell_liquidity += size
                            distance = ((price - current_price) / current_price) * 100
                            print(f"      ${price:.2f} (+{distance:.2f}%): {size:.2f} SOL")
                        print(f"      Total: {total_sell_liquidity:.2f} SOL")
                    
                    # Whale activity
                    large_orders = order_book.get("large_orders", {})
                    if large_orders.get("whale_activity"):
                        print(f"\n   🐋 WHALE ACTIVITY DETECTED")
                        whale_bids = large_orders.get("total_large_bid_volume", 0)
                        whale_asks = large_orders.get("total_large_ask_volume", 0)
                        if whale_bids > whale_asks:
                            print(f"      Whales ACCUMULATING at these levels ✅")
                        else:
                            print(f"      Whales DISTRIBUTING ⚠️")
            except:
                pass
            
            # SOL specific liquidation analysis
            print(f"\n🔴 LIQUIDATION ZONES - LONGS (from ${current_price:.2f}):")
            print(f"   {'Level':<12} {'Price':<10} {'Distance':<12} {'Status':<20}")
            print(f"   {'-'*54}")
            
            # Long liquidations (downside)
            long_liquidations = [
                ("100x longs", current_price * 0.99, "Extreme risk"),
                ("75x longs", current_price * 0.987, "Very high risk"),
                ("50x longs", current_price * 0.98, "High risk"),
                ("25x longs", current_price * 0.96, "Moderate risk"),
                ("20x longs", current_price * 0.95, "Moderate risk"),
                ("10x longs", current_price * 0.905, "Low risk"),
                ("5x longs", current_price * 0.81, "Very low risk"),
            ]
            
            critical_long_zones = []
            for name, price, risk in long_liquidations:
                distance = ((price - current_price) / current_price) * 100
                
                # Mark critical zones
                if price > 200:  # Above $200 support
                    marker = "⚠️ CRITICAL"
                    critical_long_zones.append(price)
                else:
                    marker = ""
                    
                print(f"   {name:<12} ${price:<9.2f} {distance:<11.1f}% {marker:<20}")
            
            # Key downside targets
            print(f"\n   💥 MAJOR LIQUIDATION MAGNETS (DOWNSIDE):")
            key_levels_down = [
                (205, "Recent support + 50x longs"),
                (202, "Psychological $200 + 25x longs"),
                (200, "MEGA psychological + liquidation cascade"),
                (195, "Panic zone - 20x longs wipeout"),
                (190, "Capitulation - 10x longs gone"),
            ]
            
            for price, description in key_levels_down:
                distance = ((price - current_price) / current_price) * 100
                if price < current_price:
                    print(f"      ${price}: {description} ({distance:.1f}%)")
            
            # Short liquidations (upside)
            print(f"\n🟢 LIQUIDATION ZONES - SHORTS (from ${current_price:.2f}):")
            print(f"   {'Level':<12} {'Price':<10} {'Distance':<12} {'Status':<20}")
            print(f"   {'-'*54}")
            
            short_liquidations = [
                ("100x shorts", current_price * 1.01, "Extreme risk"),
                ("75x shorts", current_price * 1.013, "Very high risk"),
                ("50x shorts", current_price * 1.02, "High risk"),
                ("25x shorts", current_price * 1.04, "Moderate risk"),
                ("20x shorts", current_price * 1.05, "Moderate risk"),
                ("10x shorts", current_price * 1.095, "Low risk"),
                ("5x shorts", current_price * 1.19, "Very low risk"),
            ]
            
            critical_short_zones = []
            for name, price, risk in short_liquidations:
                distance = ((price - current_price) / current_price) * 100
                
                # Mark critical zones
                if price < 220:  # Below recent high
                    marker = "⚠️ LIKELY"
                    critical_short_zones.append(price)
                else:
                    marker = ""
                    
                print(f"   {name:<12} ${price:<9.2f} {distance:<11.1f}% {marker:<20}")
            
            # Key upside targets
            print(f"\n   💥 MAJOR LIQUIDATION MAGNETS (UPSIDE):")
            key_levels_up = [
                (210, "First resistance + 50x shorts"),
                (212, "Previous support now resistance"),
                (213, "Recent high - major shorts trapped"),
                (215, "Breakout level + 25x shorts liquidation"),
                (220, "Extension target - short squeeze zone"),
            ]
            
            for price, description in key_levels_up:
                distance = ((price - current_price) / current_price) * 100
                if price > current_price:
                    print(f"      ${price}: {description} (+{distance:.1f}%)")
            
            # SOL specific patterns
            print(f"\n" + "="*80)
            print(f"💡 SOL LIQUIDATION HUNT ANALYSIS:")
            print("-"*80)
            
            print(f"\n📊 WHAT HAPPENED:")
            print(f"   - SOL dropped from $213 → $207 (-2.8%)")
            print(f"   - This liquidated 50x-100x longs")
            print(f"   - Now shorts are piling in")
            
            print(f"\n🎯 NEXT LIQUIDATION TARGETS:")
            
            # Determine next move
            if current_price > 205:
                print(f"\n   📉 DOWNSIDE HUNT (More likely first):")
                print(f"      Target 1: $205 (100x long liquidations)")
                print(f"      Target 2: $202 (50x long liquidations)")
                print(f"      Target 3: $200 (MEGA liquidation cascade)")
                
                print(f"\n   📈 UPSIDE REVERSAL (After downside hunt):")
                print(f"      Target 1: $210 (trap shorts from drop)")
                print(f"      Target 2: $213 (reclaim previous high)")
                print(f"      Target 3: $215-220 (short squeeze)")
            else:
                print(f"\n   📈 BOUNCE TARGETS (Oversold):")
                print(f"      Immediate: $210 (50x shorts)")
                print(f"      Strong: $213 (recover drop)")
                print(f"      Extension: $215+ (short squeeze)")
            
            print(f"\n🌙 SUNDAY NIGHT SPECIAL:")
            print(f"   Classic pattern for SOL:")
            print(f"   1. Hunt $200-202 (psychological + liquidations)")
            print(f"   2. Rapid reversal to $210-213")
            print(f"   3. Time: Usually 11pm-2am Mexico time")
            
            print(f"\n📋 TRADING STRATEGY:")
            print(f"   🔴 For SHORT: Wait for bounce to $209-210")
            print(f"   🟢 For LONG: Wait for wick to $200-202")
            print(f"   ⚡ For 100x: Only enter at $200 or $213 break")
            
            print(f"\n⚠️ CRITICAL LEVELS:")
            print(f"   MUST HOLD: $200 (lose this = cascade to $190)")
            print(f"   MUST BREAK: $213 (break this = squeeze to $220)")
            
            # Risk warning
            print(f"\n🚨 CURRENT RISK:")
            if current_price < 210 and current_price > 205:
                print(f"   - In NO MAN'S LAND ($205-210)")
                print(f"   - Can go either way violently")
                print(f"   - Wait for clear direction")
            elif current_price <= 205:
                print(f"   - APPROACHING $200 CRITICAL SUPPORT")
                print(f"   - High bounce probability")
                print(f"   - But if breaks, cascade to $190")
            
            print("="*80)

async def main():
    mapper = SOLLiquidationMap()
    await mapper.analyze_liquidation_zones()

if __name__ == "__main__":
    asyncio.run(main())