#!/usr/bin/env python3
"""
ETH Analysis with $250 capital
Previous resistance at $4667 now potential support
Current price: $4756
"""

import asyncio
from swing_trading_system import SwingTradingSystem
from datetime import datetime
import httpx

async def analyze_eth_entry():
    """
    Analyze ETH for potential entry with new capital
    """
    # Updated capital from successful SOL trade
    system = SwingTradingSystem(capital=250.0)
    
    print("="*80)
    print("📊 ETH SWING ANALYSIS")
    print("="*80)
    print(f"💰 Updated Capital: ${system.capital:.2f}")
    print(f"📈 ETH Current Price: $4756")
    print(f"🎯 Previous Resistance (now support?): $4667")
    print("-"*80)
    
    # Get current ETH price
    async with httpx.AsyncClient() as client:
        ticker = await client.get(
            "https://api.binance.com/api/v3/ticker/24hr",
            params={"symbol": "ETHUSDT"}
        )
        data = ticker.json()
        current_price = float(data["lastPrice"])
        change_24h = float(data["priceChangePercent"])
        high_24h = float(data["highPrice"])
        low_24h = float(data["lowPrice"])
        volume = float(data["volume"])
    
    print(f"\n📊 CURRENT MARKET DATA:")
    print(f"   Price: ${current_price:.2f}")
    print(f"   24h Change: {change_24h:+.2f}%")
    print(f"   24h High: ${high_24h:.2f}")
    print(f"   24h Low: ${low_24h:.2f}")
    print(f"   Distance from $4667 support: +${current_price - 4667:.2f} (+{((current_price - 4667) / 4667 * 100):.2f}%)")
    
    # Generate swing signal
    signal = await system.generate_swing_signal("ETHUSDT")
    
    if signal:
        print(f"\n✅ SWING SIGNAL DETECTED:")
        print(f"   Setup: {signal['setup_type']}")
        print(f"   Direction: {signal['direction']}")
        print(f"   Confidence: {signal['confidence']}")
        
        print(f"\n💹 TRADE LEVELS:")
        print(f"   Entry: ${signal['entry_price']:.2f}")
        print(f"   Stop Loss: ${signal['stop_loss']:.2f} (-{signal['risk_pct']:.2f}%)")
        print(f"   Target 1 (40%): ${signal['take_profit_1']:.2f} (+{signal['reward_pct_1']:.2f}%)")
        print(f"   Target 2 (40%): ${signal['take_profit_2']:.2f} (+{signal['reward_pct_2']:.2f}%)")
        print(f"   Target 3 (20%): ${signal['take_profit_3']:.2f} (+{signal['reward_pct_3']:.2f}%)")
        
        print(f"\n📊 RISK MANAGEMENT:")
        print(f"   Position Size: {signal['position_size']:.5f} ETH")
        print(f"   Position Value: ${signal['position_value']:.2f}")
        print(f"   Risk Amount: ${system.capital * system.risk_per_trade:.2f} (2% of capital)")
        print(f"   Risk/Reward: 1:{signal['rr_ratio']:.2f}")
        
        # Market structure
        structure = signal.get('market_structure', {})
        daily = structure.get('macro', {})
        h4 = structure.get('swing', {})
        h1 = structure.get('entry', {})
        
        print(f"\n📈 MARKET STRUCTURE:")
        print(f"   Daily Trend: {daily.get('trend', 'N/A')}")
        print(f"   4H RSI: {h4.get('rsi', 0):.1f}")
        print(f"   4H Momentum: {h4.get('momentum', 'N/A')}")
        print(f"   1H Volume Ratio: {h1.get('volume', 0):.2f}x average")
        
        # Liquidity analysis
        liquidity = signal.get('liquidity_data', {})
        print(f"\n💧 LIQUIDITY ANALYSIS:")
        print(f"   Order Book Imbalance: {liquidity.get('imbalance', 0):.1f}%")
        print(f"   Whale Activity: {'✅ Detected' if liquidity.get('whale_activity') else '❌ None'}")
        
        # Support/Resistance levels from liquidity
        support_levels = liquidity.get('support_levels', [])
        resistance_levels = liquidity.get('resistance_levels', [])
        
        if support_levels:
            print(f"\n📉 KEY SUPPORT LEVELS:")
            for s in support_levels[:3]:
                print(f"   ${s.get('price', 0):.2f} ({s.get('strength', 'N/A')} strength)")
        
        if resistance_levels:
            print(f"\n📈 KEY RESISTANCE LEVELS:")
            for r in resistance_levels[:3]:
                print(f"   ${r.get('price', 0):.2f} ({r.get('strength', 'N/A')} strength)")
    else:
        print(f"\n⚠️ NO CLEAR SIGNAL AT CURRENT LEVELS")
        print(f"\nPOSSIBLE REASONS:")
        print(f"   - Price in consolidation zone")
        print(f"   - Waiting for better risk/reward setup")
        print(f"   - Insufficient momentum confirmation")
    
    # My recommendation based on $4667 support
    print("\n" + "="*80)
    print("🎯 RECOMMENDATION:")
    
    if current_price > 4700:
        support_held = current_price > 4667
        distance_from_support = (current_price - 4667) / 4667 * 100
        
        if support_held and distance_from_support < 2:
            print(f"✅ ETH holding above $4667 support (currently +{distance_from_support:.1f}%)")
            print(f"   - Previous resistance turned support is BULLISH")
            print(f"   - Good risk/reward with stop below $4667")
            print(f"   - Entry zone: $4700-4760")
            print(f"   - Stop loss: $4650 (-1.5%)")
            print(f"   - Target 1: $4850 (+2%)")
            print(f"   - Target 2: $4940 (+4%)")
            print(f"   - Target 3: $5000 (+5.2%)")
        elif distance_from_support > 3:
            print(f"⚠️ ETH extended from support (+{distance_from_support:.1f}%)")
            print(f"   - Consider waiting for pullback to $4700-4720")
            print(f"   - Or wait for break and retest of $4800")
        else:
            print(f"✅ ETH in good entry zone above support")
            print(f"   - Monitor for volume confirmation")
            print(f"   - Watch BTC correlation")
    else:
        print(f"⚠️ ETH below $4700 - wait for reclaim of support")
        print(f"   - Watch for bounce from $4667")
        print(f"   - Need volume confirmation for entry")
    
    print("="*80)

if __name__ == "__main__":
    asyncio.run(analyze_eth_entry())