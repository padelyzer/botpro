#!/usr/bin/env python3
import requests
import json

response = requests.get("http://localhost:8003/api/liquidity/multi?symbols=SOLUSDT,ETHUSDT,BTCUSDT,BNBUSDT")
data = response.json()

print("\n🎯 DATOS EN VIVO DEL DASHBOARD:\n")
print("-" * 60)

for item in data:
    if item.get('price'):
        symbol = item['symbol'].replace('USDT', '')
        price = item['price']
        change = item['change24h']
        imbalance = item['imbalance']
        
        # Check for signals
        signal = item.get('signal')
        signal_text = f" | 🔥 {signal['type']} SIGNAL!" if signal else ""
        
        print(f"{symbol:<6} ${price:<10.2f} {change:+6.2f}% | Imbalance: {imbalance:+6.1f}%{signal_text}")

print("-" * 60)
print("\n✅ Dashboard en: http://localhost:8080/liquidity_dashboard_live.html")
print("📊 Actualizándose cada 5 segundos")