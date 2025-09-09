#!/usr/bin/env python3
"""
Market Monitor - Monitoreo continuo del mercado
"""

import asyncio
import httpx
import json
from datetime import datetime
import time

class MarketMonitor:
    def __init__(self):
        self.symbols = ["BTCUSDT", "BNBUSDT", "SOLUSDT", "ETHUSDT", "ADAUSDT"]
        self.liquidity_api = "http://localhost:8002/api/liquidity"
        self.binance_api = "https://api.binance.com/api/v3"
        
    async def get_market_snapshot(self):
        """Get quick market snapshot"""
        async with httpx.AsyncClient() as client:
            snapshot = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "btc_status": {},
                "altcoins": {}
            }
            
            # BTC analysis
            try:
                btc_ticker = await client.get(f"{self.binance_api}/ticker/price?symbol=BTCUSDT")
                btc_price = float(btc_ticker.json()["price"])
                
                # BTC status
                btc_status = "🟢 STABLE"
                if btc_price < 110000:
                    btc_status = "🔴 PULLBACK"
                elif btc_price < 111000:
                    btc_status = "🟡 CRITICAL"
                
                snapshot["btc_status"] = {
                    "price": btc_price,
                    "status": btc_status,
                    "key_level": 110000
                }
                
            except Exception as e:
                snapshot["btc_status"] = {"error": str(e)}
            
            # Altcoins analysis
            for symbol in self.symbols[1:]:  # Skip BTC
                try:
                    # Price
                    ticker = await client.get(f"{self.binance_api}/ticker/price?symbol={symbol}")
                    price = float(ticker.json()["price"])
                    
                    # Liquidity if available
                    try:
                        liquidity = await client.get(f"{self.liquidity_api}/{symbol}")
                        if liquidity.status_code == 200:
                            liq_data = liquidity.json()["order_book_analysis"]
                            imbalance = liq_data["imbalance"]
                            whale_activity = liq_data["large_orders"]["whale_activity"]
                            
                            # Status based on imbalance
                            status = "📈 BULLISH" if imbalance > 15 else "📉 BEARISH" if imbalance < -15 else "➡️ NEUTRAL"
                            
                            snapshot["altcoins"][symbol.replace("USDT", "")] = {
                                "price": price,
                                "imbalance": f"{imbalance:+.1f}%",
                                "whales": "🐋" if whale_activity else "❌",
                                "status": status
                            }
                        else:
                            snapshot["altcoins"][symbol.replace("USDT", "")] = {
                                "price": price,
                                "status": "📊 DATA N/A"
                            }
                    except:
                        snapshot["altcoins"][symbol.replace("USDT", "")] = {
                            "price": price,
                            "status": "📊 DATA N/A"
                        }
                        
                except Exception as e:
                    snapshot["altcoins"][symbol.replace("USDT", "")] = {"error": str(e)}
            
            return snapshot
    
    def display_snapshot(self, snapshot):
        """Display market snapshot"""
        print(f"\n🕐 {snapshot['timestamp']} - MARKET SNAPSHOT")
        print("="*60)
        
        # BTC
        btc = snapshot["btc_status"]
        if "error" not in btc:
            print(f"₿ BTC: ${btc['price']:,.0f} {btc['status']}")
            if btc['price'] < 111000:
                print(f"   ⚠️ Cerca de soporte clave ${btc['key_level']:,}")
        
        print()
        
        # Altcoins
        print("🪙 ALTCOINS:")
        for symbol, data in snapshot["altcoins"].items():
            if "error" not in data:
                if "imbalance" in data:
                    print(f"   {symbol}: ${data['price']:.2f} | {data['imbalance']} {data['whales']} {data['status']}")
                else:
                    print(f"   {symbol}: ${data['price']:.2f} {data['status']}")
        
        print("\n" + "-"*60)
    
    async def monitor_alerts(self, snapshot):
        """Check for trading alerts"""
        alerts = []
        
        # BTC alerts
        btc = snapshot["btc_status"]
        if "price" in btc:
            if btc["price"] < 110000:
                alerts.append("🚨 BTC BROKE 110k - ALTCOIN RISK HIGH")
            elif btc["price"] < 110500:
                alerts.append("⚠️ BTC APPROACHING 110k SUPPORT")
        
        # Altcoin alerts
        for symbol, data in snapshot["altcoins"].items():
            if "imbalance" in data:
                imbalance_val = float(data["imbalance"].replace("%", "").replace("+", ""))
                
                if imbalance_val > 25:
                    alerts.append(f"📈 {symbol} STRONG BULLISH IMBALANCE ({data['imbalance']})")
                elif imbalance_val < -25:
                    alerts.append(f"📉 {symbol} STRONG BEARISH IMBALANCE ({data['imbalance']})")
                
                # Whale activity changes
                if data['whales'] == "🐋" and imbalance_val > 15:
                    alerts.append(f"🐋 {symbol} WHALE BUYING DETECTED")
        
        # Display alerts
        if alerts:
            print("\n🚨 TRADING ALERTS:")
            for alert in alerts:
                print(f"   {alert}")
            print()
        
        return alerts
    
    async def run_monitor(self, interval=30):
        """Run continuous monitoring"""
        print("🔍 INICIANDO MARKET MONITOR...")
        print(f"📊 Símbolos: {', '.join([s.replace('USDT', '') for s in self.symbols])}")
        print(f"⏱️ Intervalo: {interval}s")
        print("🛑 Ctrl+C para detener")
        
        try:
            while True:
                snapshot = await self.get_market_snapshot()
                self.display_snapshot(snapshot)
                await self.monitor_alerts(snapshot)
                
                await asyncio.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n👋 Monitor detenido")

# Quick market check function
async def quick_check():
    """Quick market check"""
    monitor = MarketMonitor()
    snapshot = await monitor.get_market_snapshot()
    monitor.display_snapshot(snapshot)
    await monitor.monitor_alerts(snapshot)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "quick":
        asyncio.run(quick_check())
    else:
        monitor = MarketMonitor()
        asyncio.run(monitor.run_monitor(interval=20))  # 20 second intervals