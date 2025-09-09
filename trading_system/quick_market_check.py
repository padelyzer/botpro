#!/usr/bin/env python3
"""Quick market direction check"""

import requests
import json
from datetime import datetime

def check_market():
    symbols = ["BTCUSDT", "SOLUSDT", "ETHUSDT", "AVAXUSDT", "NEARUSDT"]
    url = "https://api.binance.com/api/v3/ticker/24hr"
    
    print('📊 MARKET ANALYSIS - Current Direction')
    print(f'⏰ {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
    print('Symbol    Price        24h Change   Volume(M)    Direction')
    print('=' * 65)
    
    total_change = 0
    bearish_count = 0
    bullish_count = 0
    
    for symbol in symbols:
        try:
            response = requests.get(url, params={"symbol": symbol})
            data = response.json()
            
            price = float(data['lastPrice'])
            change = float(data['priceChangePercent'])
            volume = float(data['volume']) * price / 1_000_000
            
            total_change += change
            if change > 0:
                bullish_count += 1
                direction = '📈 UP'
                color = '\033[92m'  # green
            else:
                bearish_count += 1
                direction = '📉 DOWN'
                color = '\033[91m'  # red
            
            reset = '\033[0m'
            symbol_name = symbol.replace('USDT', '')
            
            print(f'{symbol_name:8} ${price:10.2f} {color}{change:+7.2f}%{reset}  ${volume:7.1f}M  {direction}')
            
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
    
    avg_change = total_change / len(symbols)
    print('=' * 65)
    
    # Special SOL analysis for your position
    try:
        sol_response = requests.get(url, params={"symbol": "SOLUSDT"})
        sol_data = sol_response.json()
        sol_price = float(sol_data['lastPrice'])
        entry_price = 198.20
        pnl = (sol_price - entry_price) / entry_price * 100
        pnl_usd = (sol_price - entry_price) * 29.82  # position size
        
        print(f'\n💼 YOUR SOL POSITION:')
        print(f'   Entry: $198.20 | Current: ${sol_price:.2f}')
        pnl_color = '\033[92m' if pnl > 0 else '\033[91m'
        print(f'   P&L: {pnl_color}{pnl:+.2f}% (${pnl_usd:+.2f})\033[0m')
    except:
        pass
    
    print(f'\n🎯 MARKET SENTIMENT:')
    print(f'   Average Change: {avg_change:+.2f}%')
    print(f'   Bulls: {bullish_count} | Bears: {bearish_count}')
    
    if avg_change > 3:
        print('   ✅ STRONG BULLISH - Market rallying')
    elif avg_change > 0:
        print('   🟢 BULLISH - Market recovering')
    elif avg_change < -3:
        print('   🔴 STRONG BEARISH - Market dumping')
    elif avg_change < 0:
        print('   🟠 BEARISH - Market correcting')
    else:
        print('   ⚪ NEUTRAL - Sideways movement')
    
    # Trading recommendations
    print('\n💡 SWING TRADING OPPORTUNITIES:')
    
    for symbol in symbols:
        try:
            # Get RSI approximation (simplified)
            klines_url = "https://api.binance.com/api/v3/klines"
            klines = requests.get(klines_url, params={"symbol": symbol, "interval": "1h", "limit": 14})
            closes = [float(k[4]) for k in klines.json()]
            
            # Simple oversold/overbought check
            current = closes[-1]
            avg = sum(closes) / len(closes)
            
            response = requests.get(url, params={"symbol": symbol})
            data = response.json()
            change = float(data['priceChangePercent'])
            
            symbol_name = symbol.replace('USDT', '')
            
            if change < -7 and current < avg * 0.95:
                print(f'   🟢 {symbol_name}: Oversold - Consider buying')
            elif change > 7 and current > avg * 1.05:
                print(f'   🔴 {symbol_name}: Overbought - Consider selling')
            
        except:
            pass

if __name__ == "__main__":
    check_market()