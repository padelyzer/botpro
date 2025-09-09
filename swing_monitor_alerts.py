#!/usr/bin/env python3
"""
Swing Trading Monitor with Alerts
Continuous monitoring for swing opportunities
"""

import asyncio
import httpx
from datetime import datetime, timedelta
import time
import os
from swing_trading_system import SwingTradingSystem

class SwingMonitorAlerts:
    """
    Real-time monitor for swing trading opportunities
    """
    
    def __init__(self):
        self.system = SwingTradingSystem(capital=220)
        self.symbols = ["SOLUSDT", "BNBUSDT", "ETHUSDT", "BTCUSDT", "ADAUSDT", "DOGEUSDT"]
        self.last_signals = {}
        self.check_interval = 60  # Check every minute
        self.alert_cooldown = 3600  # Don't repeat same alert for 1 hour
        
    def clear_screen(self):
        """Clear terminal screen"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def print_header(self):
        """Print monitor header"""
        self.clear_screen()
        print("="*80)
        print("🎯 SWING TRADING MONITOR - LIVE ALERTS")
        print("="*80)
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"💰 Capital: ${self.system.capital:.2f}")
        print(f"📊 Monitoring: {', '.join([s.replace('USDT', '') for s in self.symbols])}")
        print(f"⏱️  Check interval: {self.check_interval}s")
        print("-"*80)
    
    def print_signal_alert(self, signal):
        """Print trading signal alert"""
        print("\n" + "🚨"*20)
        print(f"\n🎯 NEW SWING SIGNAL DETECTED!")
        print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
        print("\n" + "="*60)
        
        print(f"📊 Symbol: {signal['symbol']}")
        print(f"📈 Setup: {signal['setup_type']}")
        print(f"🎯 Direction: {signal['direction']}")
        print(f"⭐ Confidence: {signal['confidence']}")
        
        print("\n💹 TRADE LEVELS:")
        print(f"   Entry: ${signal['entry_price']:.2f}")
        print(f"   Stop Loss: ${signal['stop_loss']:.2f} (-{signal['risk_pct']:.2f}%)")
        print(f"   Target 1: ${signal['take_profit_1']:.2f} (+{signal['reward_pct_1']:.2f}%)")
        print(f"   Target 2: ${signal['take_profit_2']:.2f} (+{signal['reward_pct_2']:.2f}%)")
        print(f"   Target 3: ${signal['take_profit_3']:.2f} (+{signal['reward_pct_3']:.2f}%)")
        
        print(f"\n📊 RISK MANAGEMENT:")
        print(f"   Position Size: {signal['position_size']:.4f} units")
        print(f"   Position Value: ${signal['position_value']:.2f}")
        print(f"   Risk/Reward: 1:{signal['rr_ratio']:.2f}")
        print(f"   Max Risk: ${self.system.capital * self.system.risk_per_trade:.2f}")
        
        # Market structure summary
        structure = signal.get('market_structure', {})
        daily = structure.get('macro', {})
        h4 = structure.get('swing', {})
        
        print(f"\n📈 MARKET CONTEXT:")
        print(f"   Daily Trend: {daily.get('trend', 'N/A')}")
        print(f"   4H RSI: {h4.get('rsi', 0):.1f}")
        print(f"   4H Momentum: {h4.get('momentum', 'N/A')}")
        
        # Liquidity data
        liquidity = signal.get('liquidity_data', {})
        print(f"\n💧 LIQUIDITY:")
        print(f"   Imbalance: {liquidity.get('imbalance', 0):.1f}%")
        print(f"   Whale Activity: {'✅ YES' if liquidity.get('whale_activity') else '❌ NO'}")
        
        print("\n" + "="*60)
        
        # Execution plan
        print("\n📋 EXECUTION PLAN:")
        print(f"1. Place LIMIT order at ${signal['entry_price']:.2f}")
        print(f"2. Set STOP LOSS at ${signal['stop_loss']:.2f}")
        print(f"3. Take 40% profit at TP1 (${signal['take_profit_1']:.2f})")
        print(f"4. Take 40% profit at TP2 (${signal['take_profit_2']:.2f})")
        print(f"5. Let 20% run to TP3 (${signal['take_profit_3']:.2f})")
        
        print("\n" + "🚨"*20)
        print("\n✅ Signal logged. Continue monitoring...")
        
        # Play alert sound (if available)
        try:
            os.system('echo -e "\a"')  # Terminal bell
        except:
            pass
    
    async def check_market_conditions(self):
        """Quick market condition check"""
        async with httpx.AsyncClient() as client:
            conditions = {}
            
            for symbol in self.symbols:
                try:
                    # Get current price
                    ticker = await client.get(
                        f"https://api.binance.com/api/v3/ticker/24hr",
                        params={"symbol": symbol}
                    )
                    
                    if ticker.status_code == 200:
                        data = ticker.json()
                        conditions[symbol] = {
                            "price": float(data["lastPrice"]),
                            "change_24h": float(data["priceChangePercent"]),
                            "volume": float(data["volume"])
                        }
                except:
                    pass
            
            return conditions
    
    async def monitor_loop(self):
        """Main monitoring loop"""
        print("🚀 Starting Swing Trading Monitor...")
        print("📡 Connecting to markets...")
        await asyncio.sleep(2)
        
        scan_count = 0
        
        while True:
            try:
                scan_count += 1
                self.print_header()
                
                print(f"\n🔍 Scan #{scan_count}")
                print("-"*40)
                
                # Quick market check
                conditions = await self.check_market_conditions()
                
                # Display market overview
                print("\n📊 MARKET OVERVIEW:")
                for symbol, data in conditions.items():
                    if data:
                        coin = symbol.replace("USDT", "")
                        change = data['change_24h']
                        emoji = "📈" if change > 0 else "📉"
                        print(f"   {coin}: ${data['price']:.2f} {emoji} {change:+.1f}%")
                
                print("\n🔎 Scanning for swing setups...")
                
                # Scan for opportunities
                found_signals = False
                
                for symbol in self.symbols:
                    # Check if we should scan this symbol (cooldown)
                    last_signal_time = self.last_signals.get(symbol, 0)
                    if time.time() - last_signal_time < self.alert_cooldown:
                        continue
                    
                    # Generate signal
                    signal = await self.system.generate_swing_signal(symbol)
                    
                    if signal and signal.get('confidence') in ['HIGH', 'MEDIUM']:
                        found_signals = True
                        self.print_signal_alert(signal)
                        self.last_signals[symbol] = time.time()
                        
                        # Log to file
                        self.log_signal(signal)
                        
                        # Wait a bit before checking next
                        await asyncio.sleep(2)
                
                if not found_signals:
                    print("\n⏳ No swing opportunities detected")
                    print("   Market conditions:")
                    
                    # Show why no signals
                    btc_change = conditions.get("BTCUSDT", {}).get("change_24h", 0)
                    if abs(btc_change) < 1:
                        print("   - BTC sideways (low volatility)")
                    
                    high_performers = [s for s, d in conditions.items() 
                                      if d and d.get("change_24h", 0) > 5]
                    if high_performers:
                        print(f"   - {len(high_performers)} coins overbought")
                    
                    low_performers = [s for s, d in conditions.items() 
                                     if d and d.get("change_24h", 0) < -5]
                    if low_performers:
                        print(f"   - {len(low_performers)} coins oversold")
                
                # Status line
                print(f"\n⏰ Next scan in {self.check_interval} seconds...")
                print("🛑 Press Ctrl+C to stop monitoring")
                
                # Wait for next scan
                await asyncio.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                print("\n\n👋 Monitor stopped by user")
                break
            except Exception as e:
                print(f"\n⚠️ Error: {e}")
                print("Retrying in 10 seconds...")
                await asyncio.sleep(10)
    
    def log_signal(self, signal):
        """Log signal to file for review"""
        try:
            filename = f"swing_signals_{datetime.now().strftime('%Y%m%d')}.txt"
            with open(filename, 'a') as f:
                f.write("\n" + "="*60 + "\n")
                f.write(f"Timestamp: {signal['timestamp']}\n")
                f.write(f"Symbol: {signal['symbol']}\n")
                f.write(f"Setup: {signal['setup_type']}\n")
                f.write(f"Direction: {signal['direction']}\n")
                f.write(f"Entry: ${signal['entry_price']:.2f}\n")
                f.write(f"Stop: ${signal['stop_loss']:.2f}\n")
                f.write(f"TP1: ${signal['take_profit_1']:.2f}\n")
                f.write(f"TP2: ${signal['take_profit_2']:.2f}\n")
                f.write(f"TP3: ${signal['take_profit_3']:.2f}\n")
                f.write(f"R/R: 1:{signal['rr_ratio']:.2f}\n")
                f.write(f"Confidence: {signal['confidence']}\n")
        except:
            pass

async def main():
    """Run the swing monitor"""
    monitor = SwingMonitorAlerts()
    await monitor.monitor_loop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✅ Monitor stopped successfully")