#!/usr/bin/env python3
"""
Quick Profit Scanner - Detecta oportunidades inmediatas de trading
"""

import requests
import json
from datetime import datetime

def scan_opportunities():
    """Escanea el mercado para oportunidades de profit inmediatas"""
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'LINKUSDT', 'DOTUSDT']
    url = 'https://api.binance.com/api/v3/ticker/24hr'
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        opportunities = []
        high_volume = []
        momentum_plays = []
        
        print('🚀 SCANNER DE PROFITS - ANÁLISIS EN VIVO')
        print('=' * 70)
        print(f'⏰ {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        print()
        
        for ticker in data:
            if ticker['symbol'] in symbols:
                symbol = ticker['symbol'].replace('USDT', '')
                price = float(ticker['lastPrice'])
                change = float(ticker['priceChangePercent'])
                volume = float(ticker['quoteVolume'])
                high = float(ticker['highPrice'])
                low = float(ticker['lowPrice'])
                
                # Calcular métricas
                range_size = high - low
                if range_size > 0:
                    position = (price - low) / range_size
                else:
                    position = 0.5
                
                # RSI aproximado basado en cambio
                rsi_approx = 50 + (change * 2)
                
                # DETECTAR OPORTUNIDADES
                signal = None
                strength = 0
                
                # 1. OVERSOLD con volumen alto
                if change < -4 and position < 0.35 and volume > 50000000:
                    signal = 'BUY_OVERSOLD'
                    strength = min(100, abs(change) * 10 + (1-position) * 50)
                    opportunities.append({
                        'symbol': symbol,
                        'action': '🟢 LONG',
                        'price': price,
                        'reason': 'Oversold + Soporte',
                        'strength': strength,
                        'target': price * 1.03,
                        'stop': price * 0.98
                    })
                
                # 2. BREAKOUT con volumen
                elif change > 5 and position > 0.8 and volume > 100000000:
                    signal = 'BUY_BREAKOUT'
                    strength = min(100, change * 8 + position * 30)
                    momentum_plays.append({
                        'symbol': symbol,
                        'action': '🚀 MOMENTUM',
                        'price': price,
                        'reason': 'Breakout + Volumen',
                        'strength': strength,
                        'target': price * 1.05,
                        'stop': price * 0.97
                    })
                
                # 3. SHORT en resistencia
                elif change > 7 and position > 0.9 and volume > 75000000:
                    signal = 'SHORT_RESISTANCE'
                    strength = min(100, change * 5 + position * 40)
                    opportunities.append({
                        'symbol': symbol,
                        'action': '🔴 SHORT',
                        'price': price,
                        'reason': 'Overbought + Resistencia',
                        'strength': strength,
                        'target': price * 0.97,
                        'stop': price * 1.02
                    })
                
                # 4. Volumen anormal
                if volume > 200000000:
                    high_volume.append({
                        'symbol': symbol,
                        'volume': volume/1e6,
                        'change': change,
                        'price': price
                    })
                
                # Mostrar datos relevantes
                if abs(change) > 3 or volume > 100000000:
                    print(f'{symbol}:')
                    print(f'  💰 ${price:,.4f} ({change:+.2f}%)')
                    print(f'  📊 Posición: {position:.1%} | Vol: ${volume/1e6:.1f}M')
                    
                    if signal:
                        if signal.startswith('BUY'):
                            print(f'  🟢 SEÑAL COMPRA - Fuerza: {strength:.0f}%')
                        elif signal.startswith('SHORT'):
                            print(f'  🔴 SEÑAL SHORT - Fuerza: {strength:.0f}%')
                    print()
        
        # RESUMEN DE OPORTUNIDADES
        print('\n' + '='*70)
        print('📋 RESUMEN DE OPORTUNIDADES DE PROFIT:')
        print('='*70)
        
        if opportunities:
            print('\n🎯 TRADES INMEDIATOS (Mayor probabilidad):')
            for opp in sorted(opportunities, key=lambda x: x['strength'], reverse=True)[:3]:
                print(f"\n  {opp['action']} {opp['symbol']}")
                print(f"  Entrada: ${opp['price']:,.4f}")
                print(f"  Target: ${opp['target']:,.4f} (+{((opp['target']/opp['price'])-1)*100:.1f}%)")
                print(f"  Stop: ${opp['stop']:,.4f} ({((opp['stop']/opp['price'])-1)*100:.1f}%)")
                print(f"  Razón: {opp['reason']}")
                print(f"  Fuerza: {opp['strength']:.0f}%")
        
        if momentum_plays:
            print('\n🚀 MOMENTUM PLAYS (Seguir tendencia):')
            for play in momentum_plays[:2]:
                print(f"\n  {play['action']} {play['symbol']}")
                print(f"  Entrada: ${play['price']:,.4f}")
                print(f"  Target: ${play['target']:,.4f}")
                print(f"  Stop: ${play['stop']:,.4f}")
        
        if high_volume:
            print('\n💎 ALTO VOLUMEN (Observar):')
            for hv in sorted(high_volume, key=lambda x: x['volume'], reverse=True)[:3]:
                print(f"  • {hv['symbol']}: ${hv['volume']:.0f}M ({hv['change']:+.1f}%)")
        
        if not opportunities and not momentum_plays:
            print('\n⏳ Sin señales claras en este momento')
            print('   Recomendación: Esperar mejores setups')
        
        # Guardar oportunidades en archivo
        if opportunities or momentum_plays:
            with open('profit_opportunities.json', 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'opportunities': opportunities,
                    'momentum': momentum_plays,
                    'high_volume': high_volume
                }, f, indent=2)
            print('\n💾 Oportunidades guardadas en profit_opportunities.json')
        
        return opportunities, momentum_plays
        
    except Exception as e:
        print(f'❌ Error: {e}')
        return [], []

if __name__ == "__main__":
    scan_opportunities()