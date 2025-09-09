#!/usr/bin/env python3
"""
Current Liquidity Map for SOL and ETH
Real-time analysis of where liquidity is accumulating
"""

import asyncio
import httpx
from datetime import datetime
import pytz
import pandas as pd

class CurrentLiquidityMap:
    def __init__(self):
        self.symbols = ["SOLUSDT", "ETHUSDT"]
        self.liquidity_api = "http://localhost:8002/api/liquidity"
        
    async def analyze_current_liquidity(self):
        """Analyze where liquidity is accumulating right now"""
        print("="*80)
        print("🎯 REAL-TIME LIQUIDITY MAP")
        print("="*80)
        
        mexico_tz = pytz.timezone('America/Mexico_City')
        mexico_time = datetime.now(mexico_tz)
        print(f"⏰ {mexico_time.strftime('%H:%M:%S')} Mexico - Sunday Night")
        print("-"*80)
        
        async with httpx.AsyncClient() as client:
            for symbol in self.symbols:
                coin = symbol.replace("USDT", "")
                
                # Get current price
                ticker = await client.get(
                    "https://api.binance.com/api/v3/ticker/price",
                    params={"symbol": symbol}
                )
                current_price = float(ticker.json()["price"])
                
                # Get 24h data
                ticker_24h = await client.get(
                    "https://api.binance.com/api/v3/ticker/24hr",
                    params={"symbol": symbol}
                )
                data_24h = ticker_24h.json()
                high_24h = float(data_24h["highPrice"])
                low_24h = float(data_24h["lowPrice"])
                
                # Get order book
                depth = await client.get(
                    "https://api.binance.com/api/v3/depth",
                    params={"symbol": symbol, "limit": 500}
                )
                order_book = depth.json()
                
                print(f"\n{'='*60}")
                print(f"📊 {coin} LIQUIDITY ANALYSIS")
                print(f"{'='*60}")
                print(f"Current Price: ${current_price:.2f}")
                print(f"24h Range: ${low_24h:.2f} - ${high_24h:.2f}")
                
                # Analyze bid liquidity (support)
                bids = order_book["bids"]
                bid_df = pd.DataFrame(bids, columns=['price', 'quantity'])
                bid_df['price'] = bid_df['price'].astype(float)
                bid_df['quantity'] = bid_df['quantity'].astype(float)
                bid_df['usd_value'] = bid_df['price'] * bid_df['quantity']
                
                # Find liquidity clusters below current price
                print(f"\n💰 BUY LIQUIDITY (Support Zones):")
                print(f"   {'Price':<12} {'Size':<15} {'USD Value':<15} {'Distance':<10}")
                print(f"   {'-'*52}")
                
                # Define price zones
                if coin == "SOL":
                    support_zones = [203, 202, 201, 200, 198, 195, 190]
                else:  # ETH
                    support_zones = [4700, 4680, 4650, 4600, 4550, 4500]
                
                total_bid_liquidity = 0
                for zone in support_zones:
                    # Calculate liquidity in ±0.5% range of zone
                    zone_min = zone * 0.995
                    zone_max = zone * 1.005
                    
                    zone_liquidity = bid_df[
                        (bid_df['price'] >= zone_min) & 
                        (bid_df['price'] <= zone_max)
                    ]['quantity'].sum()
                    
                    zone_usd = zone * zone_liquidity
                    distance = ((zone - current_price) / current_price) * 100
                    
                    if zone_liquidity > 0:
                        total_bid_liquidity += zone_liquidity
                        
                        # Mark important zones
                        if zone_usd > 100000:
                            marker = "🔥 HOT"
                        elif zone_usd > 50000:
                            marker = "⚠️"
                        else:
                            marker = ""
                            
                        print(f"   ${zone:<11.2f} {zone_liquidity:<14.2f} ${zone_usd:<14,.0f} {distance:<9.2f}% {marker}")
                
                # Analyze ask liquidity (resistance)
                asks = order_book["asks"]
                ask_df = pd.DataFrame(asks, columns=['price', 'quantity'])
                ask_df['price'] = ask_df['price'].astype(float)
                ask_df['quantity'] = ask_df['quantity'].astype(float)
                ask_df['usd_value'] = ask_df['price'] * ask_df['quantity']
                
                print(f"\n💸 SELL LIQUIDITY (Resistance Zones):")
                print(f"   {'Price':<12} {'Size':<15} {'USD Value':<15} {'Distance':<10}")
                print(f"   {'-'*52}")
                
                # Define resistance zones
                if coin == "SOL":
                    resistance_zones = [206, 207, 208, 210, 213, 215, 220]
                else:  # ETH
                    resistance_zones = [4750, 4800, 4850, 4900, 4950, 5000]
                
                total_ask_liquidity = 0
                for zone in resistance_zones:
                    zone_min = zone * 0.995
                    zone_max = zone * 1.005
                    
                    zone_liquidity = ask_df[
                        (ask_df['price'] >= zone_min) & 
                        (ask_df['price'] <= zone_max)
                    ]['quantity'].sum()
                    
                    zone_usd = zone * zone_liquidity
                    distance = ((zone - current_price) / current_price) * 100
                    
                    if zone_liquidity > 0:
                        total_ask_liquidity += zone_liquidity
                        
                        if zone_usd > 100000:
                            marker = "🔥 HOT"
                        elif zone_usd > 50000:
                            marker = "⚠️"
                        else:
                            marker = ""
                            
                        print(f"   ${zone:<11.2f} {zone_liquidity:<14.2f} ${zone_usd:<14,.0f} {distance:<9.2f}% {marker}")
                
                # Calculate liquidation zones
                print(f"\n🔴 LIQUIDATION CLUSTERS:")
                
                # Long liquidations (below)
                long_liquidations = {
                    "100x": current_price * 0.99,
                    "50x": current_price * 0.98,
                    "25x": current_price * 0.96,
                    "20x": current_price * 0.95,
                    "10x": current_price * 0.905
                }
                
                print(f"   Long Liquidations (Stop Hunts):")
                for leverage, price in long_liquidations.items():
                    distance = ((price - current_price) / current_price) * 100
                    
                    # Check if near key support
                    if coin == "SOL":
                        if 199 <= price <= 201:
                            print(f"      {leverage}: ${price:.2f} ({distance:.1f}%) 🎯 MAGNET ZONE")
                        else:
                            print(f"      {leverage}: ${price:.2f} ({distance:.1f}%)")
                    else:
                        if 4600 <= price <= 4650:
                            print(f"      {leverage}: ${price:.2f} ({distance:.1f}%) 🎯 MAGNET ZONE")
                        else:
                            print(f"      {leverage}: ${price:.2f} ({distance:.1f}%)")
                
                # Short liquidations (above)
                short_liquidations = {
                    "100x": current_price * 1.01,
                    "50x": current_price * 1.02,
                    "25x": current_price * 1.04,
                    "20x": current_price * 1.05,
                    "10x": current_price * 1.095
                }
                
                print(f"\n   Short Liquidations (Squeeze Targets):")
                for leverage, price in short_liquidations.items():
                    distance = ((price - current_price) / current_price) * 100
                    
                    if coin == "SOL":
                        if 212 <= price <= 215:
                            print(f"      {leverage}: ${price:.2f} (+{distance:.1f}%) 🎯 TARGET ZONE")
                        else:
                            print(f"      {leverage}: ${price:.2f} (+{distance:.1f}%)")
                    else:
                        if 4850 <= price <= 4900:
                            print(f"      {leverage}: ${price:.2f} (+{distance:.1f}%) 🎯 TARGET ZONE")
                        else:
                            print(f"      {leverage}: ${price:.2f} (+{distance:.1f}%)")
                
                # Liquidity imbalance
                total_bid_usd = bid_df['usd_value'].sum()
                total_ask_usd = ask_df['usd_value'].sum()
                imbalance = ((total_bid_usd - total_ask_usd) / (total_bid_usd + total_ask_usd)) * 100
                
                print(f"\n📊 MARKET IMBALANCE:")
                print(f"   Total Buy Orders: ${total_bid_usd:,.0f}")
                print(f"   Total Sell Orders: ${total_ask_usd:,.0f}")
                print(f"   Imbalance: {imbalance:+.1f}%")
                
                if imbalance > 20:
                    print(f"   🟢 BULLISH - More buyers waiting")
                elif imbalance < -20:
                    print(f"   🔴 BEARISH - More sellers waiting")
                else:
                    print(f"   🟡 NEUTRAL - Balanced order book")
        
        # Final analysis
        print(f"\n{'='*80}")
        print(f"🎯 WHERE LIQUIDITY IS ACCUMULATING:")
        print(f"{'='*80}")
        
        print(f"\n📍 SOL LIQUIDITY MAGNETS:")
        print(f"   Below: $200-202 (psychological + long liquidations)")
        print(f"   Above: $210-213 (previous high + short liquidations)")
        
        print(f"\n📍 ETH LIQUIDITY MAGNETS:")
        print(f"   Below: $4650-4700 (support + long liquidations)")
        print(f"   Above: $4850-4900 (resistance + short liquidations)")
        
        print(f"\n💡 TRADING IMPLICATIONS:")
        print(f"   1. Price gravitates toward liquidity")
        print(f"   2. Large liquidity = strong support/resistance")
        print(f"   3. Liquidation zones = magnetic targets")
        print(f"   4. Sunday night = liquidity hunts common")
        
        print("="*80)

async def main():
    mapper = CurrentLiquidityMap()
    await mapper.analyze_current_liquidity()

if __name__ == "__main__":
    asyncio.run(main())