#!/usr/bin/env python3
"""
Live Monitor - Terminal visual simple para trading
"""

import asyncio
import httpx
import json
import os
import time
from datetime import datetime

class LiveMonitor:
    def __init__(self):
        self.symbols = ["BTCUSDT", "SOLUSDT", "BNBUSDT", "ETHUSDT"]
        self.api = "http://localhost:8002/api/liquidity"
        self.binance = "https://api.binance.com/api/v3"
        self.previous_prices = {}
        
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
                    if imbalance > 20:
                        status = "🟢 STRONG BUY"
                        color = "\033[92m"  # Green
                    elif imbalance > 5:
                        status = "🟡 BULLISH"
                        color = "\033[93m"  # Yellow
                    elif imbalance < -20:
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
        print("="*80)
        print(f"🚀 LIVE TRADING MONITOR - {now}")
        print("="*80)
        
        # BTC Status
        if "BTCUSDT" in data and "error" not in data["BTCUSDT"]:
            btc = data["BTCUSDT"]
            btc_price = btc["price"]
            
            btc_status = "🟢 SAFE" if btc_price > 111000 else "🟡 CRITICAL" if btc_price > 110000 else "🔴 DANGER"
            print(f"₿ BTC: ${btc_price:,.0f} {btc['arrow']} {btc_status}")
            print()
        
        # Altcoins
        print("🪙 ALTCOINS LIVE:")
        print("-" * 80)
        
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
                
                # Special formatting for price based on symbol
                if symbol == "SOLUSDT":
                    price_str = f"${price:.2f}"
                elif symbol == "BNBUSDT":
                    price_str = f"${price:.2f}"
                elif symbol == "ETHUSDT":
                    price_str = f"${price:.2f}"
                
                print(f"{color}{coin_name:4} {price_str:>10} {arrow} {whale} {imbalance:+6.1f}% {status}\033[0m")
        
        print("-" * 80)
        
        # Trading alerts
        alerts = []
        for symbol, coin_data in data.items():
            if "error" not in coin_data:
                coin_name = symbol.replace("USDT", "")
                imbalance = coin_data["imbalance"]
                
                if imbalance > 30:
                    alerts.append(f"🚨 {coin_name} EXTREME BULLISH ({imbalance:+.1f}%)")
                elif imbalance < -30:
                    alerts.append(f"🚨 {coin_name} EXTREME BEARISH ({imbalance:+.1f}%)")
                elif coin_data["whale"] and imbalance > 15:
                    alerts.append(f"🐋 {coin_name} WHALE BUYING ({imbalance:+.1f}%)")
        
        if alerts:
            print("🚨 ALERTS:")
            for alert in alerts:
                print(f"   {alert}")
            print()
        
        # Instructions
        print("📋 CONTROLS:")
        print("   Ctrl+C = Exit")
        print("   Updates every 3 seconds")
        
        # Special SOL tracking if in trade
        if "SOLUSDT" in data and "error" not in data["SOLUSDT"]:
            sol_price = data["SOLUSDT"]["price"]
            if hasattr(self, 'sol_entry'):
                profit = sol_price - self.sol_entry
                profit_pct = (profit / self.sol_entry) * 100
                print(f"\n💰 SOL TRADE: Entry ${self.sol_entry:.2f} → Current ${sol_price:.2f} → P/L: ${profit:.2f} ({profit_pct:+.2f}%)")
    
    async def run(self, update_interval=3):
        """Run live monitor"""
        # Check if user has SOL position
        sol_entry = input("¿Tienes posición en SOL? Enter price (o Enter para skip): ")
        if sol_entry.strip():
            try:
                self.sol_entry = float(sol_entry)
                print(f"Tracking SOL desde ${self.sol_entry:.2f}")
                time.sleep(1)
            except:
                pass
        
        try:
            while True:
                data = await self.get_live_data()
                self.display_dashboard(data)
                await asyncio.sleep(update_interval)
                
        except KeyboardInterrupt:
            self.clear_screen()
            print("👋 Monitor stopped. Happy trading!")

if __name__ == "__main__":
    monitor = LiveMonitor()
    asyncio.run(monitor.run())