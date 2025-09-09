"""
SOL Entry Alert Monitor - Integrated Module
Monitors conditions and triggers alerts when action is needed
"""

import httpx
import asyncio
from datetime import datetime
from collections import deque
from typing import Tuple, List, Optional, Dict

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import config
from core.alerts import trading_alerts, AlertType
from core.market_data import market_fetcher


class EntryAlertMonitor:
    """SOL Entry Alert Monitor with integrated configuration and alerts"""
    
    def __init__(self):
        self.alert_triggered = False
        self.last_alert_time = None
        self.price_history = deque(maxlen=10)
        
        # Load configuration
        self.sol_buy_zones = config.get('targets.sol.buy_zones', [
            {"price": 180, "priority": "primary", "position_size": 60},
            {"price": 183, "priority": "secondary", "position_size": 40},
            {"price": 175, "priority": "panic", "position_size": 80}
        ])
        
        self.btc_recovery_level = config.get('targets.btc.recovery_level', 110000)
        self.min_entry_score = config.get('alerts.min_score_threshold', 60)
    
    def calculate_entry_score(self, btc_price: float, sol_price: float, 
                            btc_change: float, sol_change: float, 
                            sol_volume: float) -> Tuple[int, List[str]]:
        """Calculate comprehensive entry score"""
        score = 0
        factors = []
        
        # Price levels (35 points)
        for zone in self.sol_buy_zones:
            target_price = zone['price']
            zone_type = zone['priority']
            
            if sol_price <= target_price:
                if zone_type == "primary":
                    score += 25
                    factors.append(f"✅ SOL at PRIMARY target ${target_price}")
                elif zone_type == "panic":
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
    
    def get_action_recommendation(self, sol_price: float, score: int) -> Tuple[str, str, str]:
        """Get specific action based on price and score"""
        for zone in self.sol_buy_zones:
            target_price = zone['price']
            zone_type = zone['priority']
            amount = zone['position_size']
            
            if sol_price <= target_price:
                if score >= 70:
                    return f"BUY ${amount} NOW", "STRONG", zone_type.upper()
                elif score >= 60:
                    return f"BUY ${amount * 0.75:.0f}", "MODERATE", zone_type.upper()
                elif score >= 50:
                    return f"Consider ${amount * 0.5:.0f}", "WEAK", zone_type.upper()
                break
        
        return "WAIT", "NO_ACTION", "NONE"
    
    async def monitor_step(self) -> Dict:
        """Single monitoring step - returns current status"""
        btc_data, sol_data = await market_fetcher.get_btc_sol_data()
        
        if not btc_data or not sol_data:
            return {"error": "Failed to fetch market data"}
        
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
        
        # Check if alert should be triggered
        should_alert = False
        alert_message = ""
        
        if score >= 70 and action != "WAIT":
            should_alert = True
            alert_message = f"🚨 STRONG BUY SIGNAL at ${sol_price:.2f}"
        elif score >= self.min_entry_score and action != "WAIT":
            should_alert = True
            alert_message = f"⚠️ BUY SIGNAL at ${sol_price:.2f}"
        
        # Trigger alerts if needed
        if should_alert and not self.alert_triggered:
            self.alert_triggered = True
            self.last_alert_time = datetime.now()
            
            # Use centralized alert system
            trading_alerts.entry_signal(
                "SOL", sol_price, score, strength
            )
        
        # Reset alert after 5 minutes
        if self.alert_triggered and self.last_alert_time:
            time_since_alert = (datetime.now() - self.last_alert_time).seconds
            if time_since_alert > 300:  # 5 minutes
                self.alert_triggered = False
        
        # Position status
        current_liq = config.get('position.current_liquidation', 152.05)
        distance_to_liq = ((sol_price - current_liq) / sol_price) * 100
        
        return {
            "timestamp": datetime.now().isoformat(),
            "btc": {
                "price": btc_price,
                "change_24h": btc_change
            },
            "sol": {
                "price": sol_price,
                "change_24h": sol_change,
                "volume": sol_volume,
                "low_24h": sol_low
            },
            "analysis": {
                "entry_score": score,
                "factors": factors,
                "action": action,
                "strength": strength,
                "zone": zone,
                "alert_triggered": self.alert_triggered
            },
            "position": {
                "liquidation_price": current_liq,
                "distance_to_liquidation": distance_to_liq,
                "status": "✅ Safe" if distance_to_liq > 15 else "⚠️ Monitor"
            },
            "targets": [
                {
                    "price": zone['price'],
                    "amount": zone['position_size'],
                    "priority": zone['priority'],
                    "hit": sol_price <= zone['price']
                } for zone in self.sol_buy_zones
            ]
        }
    
    async def monitor_continuous(self):
        """Continuous monitoring with terminal display"""
        print('='*70)
        print('🚨 SOL ENTRY ALERT MONITOR - INTEGRATED VERSION')
        print('='*70)
        print('Will alert you when optimal entry conditions are met\n')
        
        while True:
            try:
                status = await self.monitor_step()
                
                if "error" in status:
                    print(f'❌ {status["error"]}')
                    await asyncio.sleep(20)
                    continue
                
                # Clear screen and display status
                print('\033[2J\033[H')
                
                timestamp = datetime.now().strftime('%H:%M:%S')
                print(f'⏰ {timestamp} - ENTRY ALERT MONITOR')
                print('='*70)
                
                # Market status
                btc = status['btc']
                sol = status['sol']
                print(f'\n📊 MARKET STATUS:')
                print(f'BTC: ${btc["price"]:,.2f} ({btc["change_24h"]:+.2f}%)')
                print(f'SOL: ${sol["price"]:.2f} ({sol["change_24h"]:+.2f}%)')
                print(f'SOL 24h Low: ${sol["low_24h"]:.2f}')
                
                # Analysis
                analysis = status['analysis']
                score = analysis['entry_score']
                print(f'\n🎯 ENTRY SCORE: {score}/100')
                
                # Visual score bar
                bar_length = 40
                filled = int(bar_length * score / 100)
                bar = '█' * filled + '░' * (bar_length - filled)
                color = '\033[92m' if score >= 70 else '\033[93m' if score >= 50 else '\033[91m'
                print(f'{color}[{bar}]\033[0m')
                
                # Factors
                if analysis['factors']:
                    print('\n📋 SIGNALS:')
                    for factor in analysis['factors'][:5]:
                        print(f'   {factor}')
                
                # Action status
                if score >= 70 and analysis['action'] != "WAIT":
                    print(f'\n🚨🚨🚨 ALERT: {analysis["action"]} 🚨🚨🚨')
                    print(f'Confidence: {analysis["strength"]}')
                elif score >= self.min_entry_score and analysis['action'] != "WAIT":
                    print(f'\n⚠️ MODERATE ALERT: {analysis["action"]}')
                    print(f'Confidence: {analysis["strength"]}')
                else:
                    print(f'\n💤 Status: WAITING for better conditions')
                
                # Target zones
                print(f'\n📍 TARGET ZONES:')
                for target in status['targets']:
                    distance = ((sol['price'] - target['price']) / sol['price']) * 100
                    status_text = "✅ HIT" if target['hit'] else f"{distance:+.1f}%"
                    print(f'   ${target["price"]}: ${target["amount"]} position | {status_text}')
                
                # Position status
                pos = status['position']
                print(f'\n💼 YOUR POSITION:')
                print(f'Liquidation: ${pos["liquidation_price"]} ({pos["distance_to_liquidation"]:.1f}% away)')
                print(f'Status: {pos["status"]}')
                
                print(f'\n{"="*70}')
                print(f'Monitoring... Next check in 20 seconds (Ctrl+C to stop)')
                
                await asyncio.sleep(20)
                
            except KeyboardInterrupt:
                print('\n\n⏹️ Entry alert monitor stopped')
                break
            except Exception as e:
                print(f'\n❌ Error: {e}')
                await asyncio.sleep(10)


# Export the monitor for use by main controller
entry_alert_monitor = EntryAlertMonitor()