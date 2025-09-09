#!/usr/bin/env python3
"""
Live Monitor Auto - Terminal visual para trading sin input
"""

import asyncio
import httpx
import json
import os
import time
from datetime import datetime

class LiveMonitorAuto:
    def __init__(self):
        self.symbols = ["BTCUSDT", "SOLUSDT", "BNBUSDT", "ETHUSDT"]
        self.api = "http://localhost:8002/api/liquidity"
        self.binance = "https://api.binance.com/api/v3"
        self.previous_prices = {}
        # Auto-track SOL position
        self.sol_entry = 202.00  # Your SOL entry price
        
    def clear_screen(self):
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def get_price_arrow(self, symbol, current_price):
        """Get price direction arrow"""
        if symbol in self.previous_prices:
            if current_price > self.previous_prices[symbol]:
                return "📈"
            elif current_price < self.previous_prices[symbol]:
                return "📉"
        return "➡️"
    
    async def get_live_data(self):
        """Get live market data"""
        async with httpx.AsyncClient() as client:
            data = {}
            
            for symbol in self.symbols:
                try:
                    # Get price
                    ticker = await client.get(f"{self.binance}/ticker/price?symbol={symbol}")
                    price = float(ticker.json()["price"])
                    
                    # Get liquidity if available
                    try:
                        liq_resp = await client.get(f"{self.api}/{symbol}")
                        if liq_resp.status_code == 200:
                            liq_data = liq_resp.json()["order_book_analysis"]
                            imbalance = liq_data["imbalance"]
                            whale_activity = liq_data["large_orders"]["whale_activity"]
                        else:
                            imbalance = 0
                            whale_activity = False
                    except:
                        imbalance = 0
                        whale_activity = False
                    
                    # Price direction
                    arrow = self.get_price_arrow(symbol, price)
                    self.previous_prices[symbol] = price
                    
                    # Status
                    if imbalance > 30:
                        status = "🔥 EXTREME BUY"
                        color = "\033[91m"  # Red (hot)
                    elif imbalance > 15:
                        status = "🟢 STRONG BUY"
                        color = "\033[92m"  # Green
                    elif imbalance > 5:
                        status = "🟡 BULLISH"
                        color = "\033[93m"  # Yellow
                    elif imbalance < -30:
                        status = "💀 EXTREME SELL"
                        color = "\033[91m"  # Red
                    elif imbalance < -15:
                        status = "🔴 STRONG SELL"
                        color = "\033[91m"  # Red
                    elif imbalance < -5:
                        status = "🟠 BEARISH"
                        color = "\033[95m"  # Magenta
                    else:
                        status = "⚪ NEUTRAL"
                        color = "\033[0m"   # White
                    
                    data[symbol] = {
                        "price": price,
                        "imbalance": imbalance,
                        "whale": whale_activity,
                        "arrow": arrow,
                        "status": status,
                        "color": color
                    }
                    
                except Exception as e:
                    data[symbol] = {"error": str(e)}
            
            return data
    
    def display_dashboard(self, data):
        """Display trading dashboard"""
        self.clear_screen()
        
        # Header
        now = datetime.now().strftime("%H:%M:%S")
        print("="*90)
        print(f"🚀 LIVE TRADING MONITOR - {now}")
        print("="*90)
        
        # BTC Status
        if "BTCUSDT" in data and "error" not in data["BTCUSDT"]:
            btc = data["BTCUSDT"]
            btc_price = btc["price"]
            
            if btc_price > 111000:
                btc_status = "🟢 SAFE"
                btc_color = "\033[92m"
            elif btc_price > 110000:
                btc_status = "🟡 CRITICAL"
                btc_color = "\033[93m"
            else:
                btc_status = "🔴 DANGER"
                btc_color = "\033[91m"
                
            print(f"{btc_color}₿ BTC: ${btc_price:,.0f} {btc['arrow']} {btc_status}\033[0m")
            print()
        
        # SOL Trade Tracking
        if "SOLUSDT" in data and "error" not in data["SOLUSDT"]:
            sol_data = data["SOLUSDT"]
            sol_price = sol_data["price"]
            profit = sol_price - self.sol_entry
            profit_pct = (profit / self.sol_entry) * 100
            
            if profit_pct > 0:
                profit_color = "\033[92m"  # Green
                profit_emoji = "💰"
            else:
                profit_color = "\033[91m"  # Red
                profit_emoji = "📉"
                
            print(f"{profit_color}🎯 SOL TRADE: Entry ${self.sol_entry:.2f} → Current ${sol_price:.2f} → P/L: ${profit:.2f} ({profit_pct:+.2f}%) {profit_emoji}\033[0m")
            print()
        
        # Altcoins
        print("🪙 ALTCOINS LIVE:")
        print("-" * 90)
        print(f"{'COIN':<6} {'PRICE':<12} {'DIR':<4} {'WHALE':<6} {'IMBALANCE':<12} {'STATUS'}")
        print("-" * 90)
        
        for symbol in ["SOLUSDT", "BNBUSDT", "ETHUSDT"]:
            if symbol in data and "error" not in data[symbol]:
                coin_data = data[symbol]
                coin_name = symbol.replace("USDT", "")
                
                price = coin_data["price"]
                imbalance = coin_data["imbalance"]
                whale = "🐋" if coin_data["whale"] else "  "
                arrow = coin_data["arrow"]
                status = coin_data["status"]
                color = coin_data["color"]
                
                # Price formatting
                if symbol == "SOLUSDT":
                    price_str = f"${price:.2f}"
                elif symbol == "BNBUSDT":
                    price_str = f"${price:.2f}"
                elif symbol == "ETHUSDT":
                    price_str = f"${price:.2f}"
                
                print(f"{color}{coin_name:<6} {price_str:<12} {arrow:<4} {whale:<6} {imbalance:+6.1f}%{' ':<5} {status}\033[0m")
        
        print("-" * 90)
        
        # Trading alerts
        alerts = []
        for symbol, coin_data in data.items():
            if "error" not in coin_data:
                coin_name = symbol.replace("USDT", "")
                imbalance = coin_data["imbalance"]
                
                if imbalance > 40:
                    alerts.append(f"🚨 {coin_name} EXTREME BULLISH SIGNAL ({imbalance:+.1f}%)")
                elif imbalance < -40:
                    alerts.append(f"🚨 {coin_name} EXTREME BEARISH SIGNAL ({imbalance:+.1f}%)")
                elif coin_data["whale"] and imbalance > 20:
                    alerts.append(f"🐋 {coin_name} WHALE ACCUMULATION ({imbalance:+.1f}%)")
                elif coin_data["whale"] and imbalance < -20:
                    alerts.append(f"🐋 {coin_name} WHALE DISTRIBUTION ({imbalance:+.1f}%)")
        
        if alerts:
            print("\n🚨 TRADING ALERTS:")
            for alert in alerts:
                print(f"   {alert}")
        else:
            print("\n✅ NO CRITICAL ALERTS")
        
        print(f"\n📋 CONTROLS: Ctrl+C = Exit | Updates every 3 seconds")
        
        # TP Suggestions for SOL
        if "SOLUSDT" in data and "error" not in data["SOLUSDT"]:
            sol_price = data["SOLUSDT"]["price"]
            if sol_price > self.sol_entry:
                tp1 = sol_price * 1.01   # +1% from current
                tp2 = sol_price * 1.025  # +2.5% from current
                print(f"\n🎯 SOL TP SUGGESTIONS: TP1 ${tp1:.2f} (+1%) | TP2 ${tp2:.2f} (+2.5%)")
    
    async def run(self, update_interval=3):
        """Run live monitor"""
        print("🚀 Starting Live Monitor...")
        print("📊 Tracking SOL position from $202.00")
        time.sleep(2)
        
        try:
            while True:
                data = await self.get_live_data()
                self.display_dashboard(data)
                await asyncio.sleep(update_interval)
                
        except KeyboardInterrupt:
            self.clear_screen()
            print("👋 Monitor stopped. Happy trading!")

if __name__ == "__main__":
    monitor = LiveMonitorAuto()
    asyncio.run(monitor.run())