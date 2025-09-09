#!/usr/bin/env python3
"""
ETH Liquidation Map
Shows where leveraged positions will be liquidated
"""

import asyncio
import httpx
from datetime import datetime
import json

class ETHLiquidationMap:
    def __init__(self):
        self.symbol = "ETHUSDT"
        
    async def analyze_liquidation_zones(self):
        """
        Analyze liquidation zones for ETH
        """
        print("="*80)
        print("🎯 ETH LIQUIDATION MAP")
        print("="*80)
        
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
            
            print(f"📊 CURRENT MARKET:")
            print(f"   Price: ${current_price:.2f}")
            print(f"   24h Range: ${low_24h:.2f} - ${high_24h:.2f}")
            print(f"   24h Volume: {volume_24h:,.0f} ETH")
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
                            print(f"      ${price:.2f} ({distance:+.2f}%): {size:.2f} ETH")
                        print(f"      Total: {total_buy_liquidity:.2f} ETH")
                    
                    if resistance_levels:
                        print(f"\n   📈 SELL LIQUIDITY (Resistance):")
                        total_sell_liquidity = 0
                        for level in resistance_levels[:5]:
                            price = level.get('price', 0)
                            size = level.get('total_size', 0)
                            total_sell_liquidity += size
                            distance = ((price - current_price) / current_price) * 100
                            print(f"      ${price:.2f} (+{distance:.2f}%): {size:.2f} ETH")
                        print(f"      Total: {total_sell_liquidity:.2f} ETH")
            except:
                pass
            
            # Calculate liquidation zones based on leverage
            print(f"\n🔴 LIQUIDATION ZONES (LONGS):")
            print(f"   From current price ${current_price:.2f}:\n")
            
            # Common leverage levels and their liquidation points
            long_liquidations = [
                (100, 0.99),   # 100x leverage = 1% down
                (75, 0.987),   # 75x leverage = 1.3% down
                (50, 0.98),    # 50x leverage = 2% down
                (25, 0.96),    # 25x leverage = 4% down
                (20, 0.95),    # 20x leverage = 5% down
                (10, 0.905),   # 10x leverage = 9.5% down
                (5, 0.81),     # 5x leverage = 19% down
                (3, 0.68),     # 3x leverage = 32% down
            ]
            
            liquidation_clusters_down = []
            for leverage, multiplier in long_liquidations:
                liq_price = current_price * multiplier
                distance = ((liq_price - current_price) / current_price) * 100
                
                # Mark major zones
                if liq_price > low_24h:
                    marker = "⚠️ "
                    liquidation_clusters_down.append((liq_price, leverage))
                else:
                    marker = "  "
                    
                print(f"   {marker}{leverage}x longs: ${liq_price:.2f} ({distance:.1f}%)")
            
            # Key liquidation clusters
            print(f"\n   💥 MAJOR LIQUIDATION CLUSTERS (DOWNSIDE):")
            cluster_1 = current_price * 0.98  # 50x longs
            cluster_2 = current_price * 0.96  # 25x longs
            cluster_3 = current_price * 0.95  # 20x longs
            
            print(f"      Cluster 1: ${cluster_1:.2f} (50x-75x longs)")
            print(f"      Cluster 2: ${cluster_2:.2f} (25x longs)")
            print(f"      Cluster 3: ${cluster_3:.2f} (20x longs)")
            
            # Upside liquidations (shorts)
            print(f"\n🟢 LIQUIDATION ZONES (SHORTS):")
            print(f"   From current price ${current_price:.2f}:\n")
            
            short_liquidations = [
                (100, 1.01),   # 100x leverage = 1% up
                (75, 1.013),   # 75x leverage = 1.3% up
                (50, 1.02),    # 50x leverage = 2% up
                (25, 1.04),    # 25x leverage = 4% up
                (20, 1.05),    # 20x leverage = 5% up
                (10, 1.095),   # 10x leverage = 9.5% up
                (5, 1.19),     # 5x leverage = 19% up
                (3, 1.32),     # 3x leverage = 32% up
            ]
            
            liquidation_clusters_up = []
            for leverage, multiplier in short_liquidations:
                liq_price = current_price * multiplier
                distance = ((liq_price - current_price) / current_price) * 100
                
                # Mark major zones
                if liq_price < high_24h:
                    marker = "⚠️ "
                    liquidation_clusters_up.append((liq_price, leverage))
                else:
                    marker = "  "
                    
                print(f"   {marker}{leverage}x shorts: ${liq_price:.2f} (+{distance:.1f}%)")
            
            print(f"\n   💥 MAJOR LIQUIDATION CLUSTERS (UPSIDE):")
            cluster_1_up = current_price * 1.02  # 50x shorts
            cluster_2_up = current_price * 1.04  # 25x shorts
            cluster_3_up = current_price * 1.05  # 20x shorts
            
            print(f"      Cluster 1: ${cluster_1_up:.2f} (50x-75x shorts)")
            print(f"      Cluster 2: ${cluster_2_up:.2f} (25x shorts)")
            print(f"      Cluster 3: ${cluster_3_up:.2f} (20x shorts)")
            
            # Magnetic zones
            print(f"\n🧲 MAGNETIC LIQUIDATION ZONES:")
            print(f"   (Price tends to move toward these zones)\n")
            
            # Downside magnets
            print(f"   📉 DOWNSIDE MAGNETS:")
            magnet_1_down = 4700  # Round number + liquidations
            magnet_2_down = 4650  # Major support + liquidations
            magnet_3_down = 4600  # Psychological + liquidations
            
            for magnet in [magnet_1_down, magnet_2_down, magnet_3_down]:
                if magnet < current_price:
                    distance = ((magnet - current_price) / current_price) * 100
                    print(f"      ${magnet:.0f} ({distance:.1f}%): High liquidation density")
            
            # Upside magnets
            print(f"\n   📈 UPSIDE MAGNETS:")
            magnet_1_up = 4800  # Round number
            magnet_2_up = 4850  # Resistance
            magnet_3_up = 4900  # Psychological
            magnet_4_up = 5000  # Major psychological
            
            for magnet in [magnet_1_up, magnet_2_up, magnet_3_up, magnet_4_up]:
                if magnet > current_price:
                    distance = ((magnet - current_price) / current_price) * 100
                    print(f"      ${magnet:.0f} (+{distance:.1f}%): Short liquidations")
            
            # Trading strategy based on liquidations
            print(f"\n" + "="*80)
            print(f"💡 LIQUIDATION HUNTING STRATEGY:")
            print("-"*80)
            
            # Check which side has more liquidations
            nearest_long_liq = current_price * 0.98  # 2% down
            nearest_short_liq = current_price * 1.02  # 2% up
            
            print(f"\n🎯 IMMEDIATE TARGETS:")
            print(f"   Downside: ${nearest_long_liq:.2f} (50x-100x long liquidations)")
            print(f"   Upside: ${nearest_short_liq:.2f} (50x-100x short liquidations)")
            
            # Sunday specific analysis
            print(f"\n🌙 SUNDAY NIGHT PATTERN:")
            print(f"   1. Hunt down to ${magnet_2_down} (liquidate longs)")
            print(f"   2. Reverse pump to ${magnet_2_up} (liquidate shorts)")
            print(f"   3. Common sequence: Down 2-3% → Up 4-5%")
            
            print(f"\n📊 RECOMMENDED TRADES:")
            print(f"   1. Wait for wick to ${magnet_2_down}-${magnet_1_down}")
            print(f"   2. Enter LONG at liquidation cluster")
            print(f"   3. Target: ${magnet_1_up}-${magnet_2_up}")
            print(f"   4. Risk/Reward: 1:2+")
            
            print(f"\n⚠️ WARNING:")
            print(f"   - Price WILL hunt ${nearest_long_liq:.2f} (long liquidations)")
            print(f"   - Then likely pump to ${nearest_short_liq:.2f}+ (short liquidations)")
            print(f"   - This is how exchanges make money on Sunday")
            
            print("="*80)

async def main():
    mapper = ETHLiquidationMap()
    await mapper.analyze_liquidation_zones()

if __name__ == "__main__":
    asyncio.run(main())