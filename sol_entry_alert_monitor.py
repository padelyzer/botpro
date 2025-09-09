#!/usr/bin/env python3
"""
SOL Entry Alert Monitor - Visual and Audio Alerts
Monitors conditions and triggers alerts when action is needed
"""

import httpx
import asyncio
import os
import subprocess
from datetime import datetime
from collections import deque

class EntryAlertMonitor:
    def __init__(self):
        self.alert_triggered = False
        self.last_alert_time = None
        self.price_history = deque(maxlen=10)
        
        # Alert thresholds
        self.sol_buy_zones = [
            (180, "PRIMARY", 60),    # Primary target, $60 position
            (183, "SECONDARY", 40),  # Secondary target, $40 position  
            (175, "PANIC", 80),      # Panic buy zone, $80 position
        ]
        
        self.btc_recovery_level = 110000
        self.min_entry_score = 60  # Minimum score to trigger alert
        
    def play_alert_sound(self, alert_type="normal"):
        """Play system alert sound"""
        try:
            # macOS system sounds
            if alert_type == "urgent":
                subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"])
                subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"])
            else:
                subprocess.run(["afplay", "/System/Library/Sounds/Ping.aiff"])
        except:
            # Alternative: use terminal bell
            print('\a')  # Terminal bell sound
    
    def show_notification(self, title, message):
        """Show macOS notification"""
        try:
            script = f'''
            display notification "{message}" with title "{title}" sound name "Glass"
            '''
            subprocess.run(["osascript", "-e", script])
        except:
            pass
    
    async def get_market_data(self, client):
        """Fetch current market data"""
        try:
            btc = await client.get('https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT')
            sol = await client.get('https://api.binance.com/api/v3/ticker/24hr?symbol=SOLUSDT')
            
            return btc.json(), sol.json()
        except:
            return None, None
    
    def calculate_entry_score(self, btc_price, sol_price, btc_change, sol_change, sol_volume):
        """Calculate comprehensive entry score"""
        score = 0
        factors = []
        
        # Price levels (35 points)
        for target_price, zone_type, _ in self.sol_buy_zones:
            if sol_price <= target_price:
                if zone_type == "PRIMARY":
                    score += 25
                    factors.append(f"✅ SOL at PRIMARY target ${target_price}")
                elif zone_type == "PANIC":
                    score += 35
                    factors.append(f"🔥 SOL at PANIC zone ${target_price}")
                else:
                    score += 20
                    factors.append(f"✅ SOL at SECONDARY target ${target_price}")
                break
        
        # BTC strength (25 points)
        if btc_price >= self.btc_recovery_level:
            score += 25
            factors.append(f"✅ BTC strong >${self.btc_recovery_level/1000:.0f}k")
        elif btc_price >= 109000:
            score += 15
            factors.append("🟡 BTC neutral zone")
        elif btc_price >= 108000:
            score += 10
            factors.append("⚠️ BTC weak but holding")
        
        # Oversold conditions (20 points)
        if sol_change < -10:
            score += 20
            factors.append(f"✅ SOL extremely oversold ({sol_change:.1f}%)")
        elif sol_change < -7:
            score += 15
            factors.append(f"✅ SOL oversold ({sol_change:.1f}%)")
        elif sol_change < -5:
            score += 10
            factors.append(f"🟡 SOL weak ({sol_change:.1f}%)")
        
        # Volume spike (10 points)
        if sol_volume > 2500000000:
            score += 10
            factors.append("✅ Capitulation volume")
        elif sol_volume > 2000000000:
            score += 7
            factors.append("✅ High volume")
        elif sol_volume > 1500000000:
            score += 5
            factors.append("🟡 Normal volume")
        
        # Momentum (10 points)
        if len(self.price_history) >= 3:
            recent_prices = list(self.price_history)[-3:]
            if sol_price > recent_prices[0]:
                score += 10
                factors.append("✅ Bouncing from lows")
            elif sol_price < recent_prices[-2]:
                score += 5
                factors.append("🟡 Still falling")
        
        return score, factors
    
    def get_action_recommendation(self, sol_price, score):
        """Get specific action based on price and score"""
        for target_price, zone_type, amount in self.sol_buy_zones:
            if sol_price <= target_price:
                if score >= 70:
                    return f"BUY ${amount} NOW", "STRONG", zone_type
                elif score >= 60:
                    return f"BUY ${amount * 0.75:.0f}", "MODERATE", zone_type
                elif score >= 50:
                    return f"Consider ${amount * 0.5:.0f}", "WEAK", zone_type
                break
        
        return "WAIT", "NO_ACTION", "NONE"
    
    async def monitor(self):
        """Main monitoring loop"""
        print('='*70)
        print('🚨 SOL ENTRY ALERT MONITOR - AUDIO/VISUAL ALERTS')
        print('='*70)
        print('Will alert you when optimal entry conditions are met\n')
        
        async with httpx.AsyncClient() as client:
            while True:
                try:
                    btc_data, sol_data = await self.get_market_data(client)
                    
                    if not btc_data or not sol_data:
                        await asyncio.sleep(20)
                        continue
                    
                    # Parse data
                    btc_price = float(btc_data['lastPrice'])
                    btc_change = float(btc_data['priceChangePercent'])
                    
                    sol_price = float(sol_data['lastPrice'])
                    sol_change = float(sol_data['priceChangePercent'])
                    sol_volume = float(sol_data['quoteVolume'])
                    sol_low = float(sol_data['lowPrice'])
                    
                    # Update price history
                    self.price_history.append(sol_price)
                    
                    # Calculate entry score
                    score, factors = self.calculate_entry_score(
                        btc_price, sol_price, btc_change, sol_change, sol_volume
                    )
                    
                    # Get action recommendation
                    action, strength, zone = self.get_action_recommendation(sol_price, score)
                    
                    # Clear screen
                    print('\033[2J\033[H')
                    
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    print(f'⏰ {timestamp} - ENTRY ALERT MONITOR')
                    print('='*70)
                    
                    # Market status
                    print(f'\n📊 MARKET STATUS:')
                    print(f'BTC: ${btc_price:,.2f} ({btc_change:+.2f}%)')
                    print(f'SOL: ${sol_price:.2f} ({sol_change:+.2f}%)')
                    print(f'SOL 24h Low: ${sol_low:.2f}')
                    
                    # Entry score
                    print(f'\n🎯 ENTRY SCORE: {score}/100')
                    
                    # Visual score bar
                    bar_length = 40
                    filled = int(bar_length * score / 100)
                    bar = '█' * filled + '░' * (bar_length - filled)
                    color = '\033[92m' if score >= 70 else '\033[93m' if score >= 50 else '\033[91m'
                    print(f'{color}[{bar}]\033[0m')
                    
                    # Factors
                    if factors:
                        print('\n📋 SIGNALS:')
                        for factor in factors[:5]:  # Show top 5 factors
                            print(f'   {factor}')
                    
                    # Alert logic
                    should_alert = False
                    alert_message = ""
                    
                    if score >= 70 and action != "WAIT":
                        should_alert = True
                        alert_type = "urgent"
                        alert_message = f"🚨 STRONG BUY SIGNAL at ${sol_price:.2f}"
                        print(f'\n🚨🚨🚨 ALERT: {action} 🚨🚨🚨')
                        print(f'Confidence: {strength}')
                    elif score >= 60 and action != "WAIT":
                        should_alert = True
                        alert_type = "normal"
                        alert_message = f"⚠️ BUY SIGNAL at ${sol_price:.2f}"
                        print(f'\n⚠️ MODERATE ALERT: {action}')
                        print(f'Confidence: {strength}')
                    else:
                        print(f'\n💤 Status: WAITING for better conditions')
                    
                    # Trigger alerts
                    if should_alert and not self.alert_triggered:
                        self.alert_triggered = True
                        self.last_alert_time = datetime.now()
                        
                        # Play sound
                        self.play_alert_sound(alert_type)
                        
                        # Show notification
                        self.show_notification(
                            "SOL Entry Alert", 
                            alert_message + f"\nScore: {score}/100\nAction: {action}"
                        )
                        
                        # Big visual alert in terminal
                        print('\n' + '🚨'*35)
                        print(f'    ACTION REQUIRED: {action}')
                        print(f'    Price: ${sol_price:.2f}')
                        print(f'    Zone: {zone}')
                        print('🚨'*35)
                    
                    # Reset alert after 5 minutes
                    if self.alert_triggered and self.last_alert_time:
                        time_since_alert = (datetime.now() - self.last_alert_time).seconds
                        if time_since_alert > 300:  # 5 minutes
                            self.alert_triggered = False
                    
                    # Key levels
                    print(f'\n📍 TARGET ZONES:')
                    for target, zone_type, amount in self.sol_buy_zones:
                        distance = ((sol_price - target) / sol_price) * 100
                        status = "✅ HIT" if sol_price <= target else f"{distance:+.1f}%"
                        print(f'   ${target}: ${amount} position | {status}')
                    
                    # Position status
                    print(f'\n💼 YOUR POSITION:')
                    your_liq = 152.05
                    distance_to_liq = ((sol_price - your_liq) / sol_price) * 100
                    print(f'Liquidation: ${your_liq} ({distance_to_liq:.1f}% away)')
                    print(f'Status: {"✅ Safe" if distance_to_liq > 15 else "⚠️ Monitor"}')
                    
                    # Next update
                    print(f'\n{"="*70}')
                    print(f'Monitoring... Next check in 20 seconds (Ctrl+C to stop)')
                    
                    await asyncio.sleep(20)
                    
                except KeyboardInterrupt:
                    print('\n\n⏹️ Alert monitor stopped')
                    break
                except Exception as e:
                    print(f'\n❌ Error: {e}')
                    await asyncio.sleep(10)

async def main():
    monitor = EntryAlertMonitor()
    await monitor.monitor()

if __name__ == "__main__":
    print('🚀 Starting SOL Entry Alert Monitor...')
    print('You will receive audio/visual alerts when entry conditions are met')
    print('Keep this terminal visible or in background')
    print('Press Ctrl+C to stop\n')
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\n👋 Alert monitor stopped!')