#!/usr/bin/env python3
"""
Strategy Monitor: Wait for SOL $180 + BTC Recovery
NO ACTION until BTC shows strength
"""

import httpx
import asyncio
import time
from datetime import datetime

async def monitor_wait_strategy():
    print('='*60)
    print('⏳ STRATEGY: WAIT FOR $180 SOL + BTC RECOVERY')
    print('='*60)
    print('\n🎯 PLAN DEFINIDO:')
    print('1. ESPERAR SOL a $180 (500k liquidaciones)')
    print('2. NO MOVER hasta que BTC muestre recuperación')
    print('3. HOLD posición actual - liquidación segura en $152')
    print('='*60)
    
    while True:
        try:
            async with httpx.AsyncClient() as client:
                # Get market data
                btc = await client.get('https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT')
                sol = await client.get('https://api.binance.com/api/v3/ticker/24hr?symbol=SOLUSDT')
                
                btc_data = btc.json()
                sol_data = sol.json()
                
                btc_price = float(btc_data['lastPrice'])
                btc_change = float(btc_data['priceChangePercent'])
                
                sol_price = float(sol_data['lastPrice'])
                sol_change = float(sol_data['priceChangePercent'])
                sol_low = float(sol_data['lowPrice'])
                
                # Clear screen for clean display
                print('\033[2J\033[H')  # Clear screen
                
                timestamp = datetime.now().strftime('%H:%M:%S')
                print(f'⏰ {timestamp} - MONITORING WAIT STRATEGY')
                print('='*60)
                
                # BTC Status
                btc_status = "🟢 RECOVERY" if btc_price > 112000 else "🟡 NEUTRAL" if btc_price > 108000 else "🔴 BEARISH"
                print(f'\n₿ BTC: ${btc_price:,.2f} ({btc_change:+.2f}%)')
                print(f'Status: {btc_status}')
                print(f'Key levels: $108k | $110k | $112k')
                
                # BTC recovery signals
                recovery_signals = 0
                print(f'\n📊 BTC RECOVERY SIGNALS:')
                
                if btc_price > 110000:
                    print('✅ Above $110k')
                    recovery_signals += 1
                else:
                    print('❌ Below $110k')
                
                if btc_change > 0:
                    print('✅ Positive 24h')
                    recovery_signals += 1
                else:
                    print('❌ Negative 24h')
                
                if btc_price > 112000:
                    print('✅ Strong momentum >$112k')
                    recovery_signals += 1
                else:
                    print('❌ No strong momentum')
                
                btc_ready = recovery_signals >= 2
                
                # SOL Status
                print(f'\n📉 SOL: ${sol_price:.2f} ({sol_change:+.2f}%)')
                print(f'24h Low: ${sol_low:.2f}')
                print(f'Distance to $180: {((sol_price - 180) / sol_price * 100):+.1f}%')
                
                # Check if conditions are met
                sol_at_target = sol_price <= 180.50
                
                print(f'\n🎯 CONDITIONS CHECK:')
                print(f'SOL ≤ $180: {"✅ READY" if sol_at_target else f"❌ Wait (${sol_price:.2f})"}')
                print(f'BTC Recovery: {"✅ CONFIRMED" if btc_ready else f"❌ Wait ({recovery_signals}/2 signals)"}')
                
                # Action status
                if sol_at_target and btc_ready:
                    print(f'\n🚨 ACTION TRIGGER! 🚨')
                    print(f'✅ SOL at target zone!')
                    print(f'✅ BTC showing recovery!')
                    print(f'→ CONSIDERAR RECOMPRA AHORA')
                    
                    print(f'\n💰 SUGGESTED BUY:')
                    print(f'• Amount: $40-60 USD')
                    print(f'• Entry: ${sol_price:.2f}')
                    print(f'• Stop loss: $175')
                    print(f'• Target: $190-195')
                    
                elif sol_at_target and not btc_ready:
                    print(f'\n⚠️ SOL AT TARGET BUT BTC WEAK')
                    print(f'→ WAIT for BTC recovery')
                    print(f'→ Risk of more downside')
                    
                elif not sol_at_target and btc_ready:
                    print(f'\n📈 BTC RECOVERING BUT SOL NOT AT TARGET')
                    print(f'→ May not reach $180')
                    print(f'→ Consider $183-185 entry')
                    
                else:
                    print(f'\n⏳ WAITING...')
                    print(f'→ No action yet')
                    print(f'→ Continue monitoring')
                
                # Position status
                print(f'\n💼 YOUR POSITION:')
                your_liquidation = 152.05
                distance_to_liq = ((sol_price - your_liquidation) / sol_price * 100)
                
                print(f'Current P&L: ~${(sol_price - 204) * 0.156:.2f}')
                print(f'Liquidation: ${your_liquidation}')
                print(f'Safety buffer: {distance_to_liq:.1f}%')
                
                if distance_to_liq < 15:
                    print(f'⚠️ WARNING: Getting close to liquidation!')
                else:
                    print(f'✅ Safe distance from liquidation')
                
                # Market overview
                print(f'\n🌍 MARKET MOOD:')
                if btc_change < -2 and sol_change < -5:
                    print('🔴 BEARISH - Continued selling')
                elif btc_change > 2 and sol_change > 2:
                    print('🟢 BULLISH - Recovery in progress')
                else:
                    print('🟡 MIXED - Consolidation phase')
                
                # Key levels reminder
                print(f'\n📍 KEY LEVELS:')
                print(f'SOL targets: $180 → $183 → $185')
                print(f'BTC signals: $108k → $110k → $112k')
                
                print(f'\n{"="*60}')
                print(f'Refreshing in 30 seconds... (Ctrl+C to stop)')
                
                await asyncio.sleep(30)
                
        except KeyboardInterrupt:
            print('\n\n⏹️ Monitor stopped by user')
            break
        except Exception as e:
            print(f'\n❌ Error: {e}')
            print('Retrying in 10 seconds...')
            await asyncio.sleep(10)

if __name__ == "__main__":
    print('🚀 Starting Wait Strategy Monitor...')
    print('Monitoring SOL for $180 + BTC recovery signals')
    print('Press Ctrl+C to stop\n')
    
    try:
        asyncio.run(monitor_wait_strategy())
    except KeyboardInterrupt:
        print('\n👋 Monitor stopped. Good luck with your trades!')