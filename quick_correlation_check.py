#!/usr/bin/env python3
"""
Quick BTC/SOL correlation check with entry score
"""

import httpx
import asyncio
import numpy as np

async def quick_check():
    async with httpx.AsyncClient() as client:
        print('='*70)
        print('🔬 BTC/SOL CORRELATION - QUICK CHECK')
        print('='*70)
        
        # Get current data
        btc = await client.get('https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT')
        sol = await client.get('https://api.binance.com/api/v3/ticker/24hr?symbol=SOLUSDT')
        
        btc_data = btc.json()
        sol_data = sol.json()
        
        btc_price = float(btc_data['lastPrice'])
        btc_change = float(btc_data['priceChangePercent'])
        btc_volume = float(btc_data['quoteVolume'])
        
        sol_price = float(sol_data['lastPrice'])
        sol_change = float(sol_data['priceChangePercent'])
        sol_volume = float(sol_data['quoteVolume'])
        sol_low = float(sol_data['lowPrice'])
        
        print(f'\n📊 CURRENT PRICES:')
        print(f'BTC: ${btc_price:,.2f} ({btc_change:+.2f}%)')
        print(f'SOL: ${sol_price:.2f} ({sol_change:+.2f}%)')
        
        print(f'\n📈 24H STATS:')
        print(f'SOL 24h Low: ${sol_low:.2f}')
        print(f'BTC Volume: ${btc_volume/1e6:.1f}M')
        print(f'SOL Volume: ${sol_volume/1e6:.1f}M')
        
        # Simple correlation based on 24h changes
        if btc_change < 0 and sol_change < 0:
            if abs(sol_change) > abs(btc_change) * 1.5:
                correlation_status = "SOL falling faster (normal in bear)"
            else:
                correlation_status = "Moving together bearish"
        elif btc_change > 0 and sol_change > 0:
            correlation_status = "Both bullish (good correlation)"
        else:
            correlation_status = "Divergence detected"
        
        print(f'\n🔗 CORRELATION STATUS: {correlation_status}')
        
        # Entry score calculation
        score = 0
        factors = []
        
        # Price levels (30 points)
        if sol_price <= 180:
            score += 20
            factors.append("✅ SOL at target $180 zone")
        elif sol_price <= 185:
            score += 10
            factors.append("🟡 SOL approaching target")
        else:
            factors.append("❌ SOL above $185 (wait)")
        
        if btc_price >= 110000:
            score += 10
            factors.append("✅ BTC showing strength >$110k")
        elif btc_price >= 109000:
            score += 5
            factors.append("🟡 BTC neutral zone")
        else:
            factors.append("❌ BTC weak <$109k")
        
        # Volume (20 points)
        if sol_volume > 2000000000:
            score += 20
            factors.append("✅ High volume (capitulation)")
        elif sol_volume > 1500000000:
            score += 10
            factors.append("🟡 Normal volume")
        else:
            factors.append("❌ Low volume")
        
        # Oversold conditions (20 points)
        if sol_change < -8:
            score += 20
            factors.append(f"✅ SOL oversold ({sol_change:.1f}%)")
        elif sol_change < -5:
            score += 10
            factors.append(f"🟡 SOL weak ({sol_change:.1f}%)")
        
        # Near 24h low (15 points)
        if abs(sol_price - sol_low) < 2:
            score += 15
            factors.append("✅ Near 24h low (bounce zone)")
        elif abs(sol_price - sol_low) < 5:
            score += 8
            factors.append("🟡 Close to 24h low")
        
        # Market sentiment (15 points)
        if btc_change > -1 and sol_change < -5:
            score += 15
            factors.append("✅ SOL oversold vs BTC")
        elif btc_change < -3 and sol_change < -7:
            score += 5
            factors.append("🟡 Both bearish but SOL extreme")
        
        print(f'\n🎯 ENTRY SCORE: {score}/100')
        
        print('\n📋 ANALYSIS FACTORS:')
        for factor in factors:
            print(f'   {factor}')
        
        print(f'\n💡 RECOMMENDATION:')
        if score >= 70:
            print('🟢 STRONG BUY SIGNAL!')
            print(f'   → Entry: ${sol_price:.2f}')
            print(f'   → Size: $60-80')
            print(f'   → Stop: ${sol_price * 0.97:.2f}')
            print(f'   → Target: ${sol_price * 1.05:.2f}-${sol_price * 1.08:.2f}')
        elif score >= 50:
            print('🟡 MODERATE SIGNAL')
            print(f'   → Consider small entry: $30-40')
            print(f'   → Wait for confirmation')
        elif score >= 35:
            print('⚠️ WEAK SIGNAL')
            print('   → Continue waiting')
            print('   → Monitor for better setup')
        else:
            print('🔴 NO ENTRY')
            print('   → Conditions not met')
            print('   → Wait for SOL <$180 or BTC recovery')
        
        print(f'\n📍 KEY LEVELS TO WATCH:')
        print(f'SOL: $180 (target) | $183 (support) | $175 (panic)')
        print(f'BTC: $108k (critical) | $110k (recovery) | $112k (bullish)')
        
        print(f'\n💼 YOUR POSITION STATUS:')
        your_breakeven = 204
        your_liq = 152.05
        pnl = (sol_price - your_breakeven) * 0.156
        liq_distance = ((sol_price - your_liq) / sol_price) * 100
        
        print(f'P&L: ${pnl:.2f}')
        print(f'Distance to liquidation: {liq_distance:.1f}%')
        print(f'Risk: {"✅ Safe" if liq_distance > 15 else "⚠️ Monitor closely"}')
        
        print('='*70)

asyncio.run(quick_check())