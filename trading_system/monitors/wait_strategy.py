"""
Wait Strategy Monitor - Integrated Module
NO ACTION until BTC shows strength - monitors wait conditions
"""

import asyncio
from datetime import datetime
from typing import Dict

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import config
from core.alerts import trading_alerts, AlertType
from core.market_data import market_fetcher


class WaitStrategyMonitor:
    """Wait Strategy Monitor with integrated configuration and alerts"""
    
    def __init__(self):
        # Load configuration
        self.sol_target = config.get('targets.sol.buy_zones', [{"price": 180}])[0]['price']
        self.btc_recovery_level = config.get('targets.btc.recovery_level', 110000)
        self.btc_critical_support = config.get('targets.btc.critical_support', 108000)
        self.current_liquidation = config.get('position.current_liquidation', 152.05)
        self.breakeven_price = config.get('position.breakeven_price', 204.0)
        self.current_size = config.get('position.current_size', 29.82)
    
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
        sol_low = float(sol_data['lowPrice'])
        
        # BTC recovery analysis
        recovery_signals = 0
        btc_signals = []
        
        if btc_price > self.btc_recovery_level:
            btc_signals.append("✅ Above recovery level")
            recovery_signals += 1
        else:
            btc_signals.append(f"❌ Below recovery level (${self.btc_recovery_level:,.0f})")
        
        if btc_change > 0:
            btc_signals.append("✅ Positive 24h change")
            recovery_signals += 1
        else:
            btc_signals.append(f"❌ Negative 24h ({btc_change:.2f}%)")
        
        if btc_price > 112000:
            btc_signals.append("✅ Strong momentum >$112k")
            recovery_signals += 1
        else:
            btc_signals.append("❌ No strong momentum")
        
        btc_ready = recovery_signals >= 2
        
        # SOL target analysis
        sol_at_target = sol_price <= self.sol_target + 0.50  # Small buffer
        
        # Position analysis
        distance_to_liq = ((sol_price - self.current_liquidation) / sol_price) * 100
        current_pnl = (sol_price - self.breakeven_price) * self.current_size
        
        # Market sentiment
        if btc_change < -2 and sol_change < -5:
            market_mood = "🔴 BEARISH - Continued selling"
        elif btc_change > 2 and sol_change > 2:
            market_mood = "🟢 BULLISH - Recovery in progress"
        else:
            market_mood = "🟡 MIXED - Consolidation phase"
        
        # Action determination
        action_status = "WAIT"
        action_description = "Continue monitoring"
        suggested_action = None
        
        if sol_at_target and btc_ready:
            action_status = "ACTION_TRIGGER"
            action_description = "Both conditions met - consider recompra"
            suggested_action = {
                "action": "BUY",
                "amount": "40-60 USD",
                "entry": sol_price,
                "stop_loss": 175,
                "target": "190-195"
            }
            
            # Send alert for action trigger
            trading_alerts.entry_signal(
                "SOL", sol_price, 75, "STRONG - Wait strategy conditions met"
            )
            
        elif sol_at_target and not btc_ready:
            action_status = "SOL_READY"
            action_description = "SOL at target but BTC weak - high risk"
            
        elif not sol_at_target and btc_ready:
            action_status = "BTC_READY"
            action_description = "BTC recovering but SOL not at target - consider $183-185"
        
        return {
            "timestamp": datetime.now().isoformat(),
            "btc": {
                "price": btc_price,
                "change_24h": btc_change,
                "recovery_signals": recovery_signals,
                "signals": btc_signals,
                "ready": btc_ready,
                "status": "🟢 RECOVERY" if btc_price > 112000 else "🟡 NEUTRAL" if btc_price > self.btc_critical_support else "🔴 BEARISH"
            },
            "sol": {
                "price": sol_price,
                "change_24h": sol_change,
                "low_24h": sol_low,
                "target": self.sol_target,
                "distance_to_target": ((sol_price - self.sol_target) / sol_price) * 100,
                "at_target": sol_at_target
            },
            "position": {
                "liquidation_price": self.current_liquidation,
                "breakeven_price": self.breakeven_price,
                "current_size": self.current_size,
                "distance_to_liquidation": distance_to_liq,
                "current_pnl": current_pnl,
                "safety_status": "✅ Safe distance" if distance_to_liq > 15 else "⚠️ WARNING: Getting close!"
            },
            "analysis": {
                "action_status": action_status,
                "action_description": action_description,
                "suggested_action": suggested_action,
                "market_mood": market_mood,
                "conditions_met": sol_at_target and btc_ready
            }
        }
    
    async def monitor_continuous(self):
        """Continuous monitoring with terminal display"""
        print('='*60)
        print('⏳ STRATEGY: WAIT FOR $180 SOL + BTC RECOVERY')
        print('='*60)
        print('\n🎯 PLAN DEFINIDO:')
        print('1. ESPERAR SOL a $180 (liquidaciones)')
        print('2. NO MOVER hasta que BTC muestre recuperación') 
        print('3. HOLD posición actual - liquidación segura')
        print('='*60)
        
        while True:
            try:
                status = await self.monitor_step()
                
                if "error" in status:
                    print(f'❌ {status["error"]}')
                    await asyncio.sleep(30)
                    continue
                
                # Clear screen for clean display
                print('\033[2J\033[H')
                
                timestamp = datetime.now().strftime('%H:%M:%S')
                print(f'⏰ {timestamp} - MONITORING WAIT STRATEGY')
                print('='*60)
                
                # BTC Status
                btc = status['btc']
                print(f'\n₿ BTC: ${btc["price"]:,.2f} ({btc["change_24h"]:+.2f}%)')
                print(f'Status: {btc["status"]}')
                print(f'Key levels: $108k | $110k | $112k')
                
                # BTC recovery signals
                print(f'\n📊 BTC RECOVERY SIGNALS ({btc["recovery_signals"]}/3):')
                for signal in btc["signals"]:
                    print(f'   {signal}')
                
                # SOL Status
                sol = status['sol']
                print(f'\n📉 SOL: ${sol["price"]:.2f} ({sol["change_24h"]:+.2f}%)')
                print(f'24h Low: ${sol["low_24h"]:.2f}')
                print(f'Distance to ${sol["target"]}: {sol["distance_to_target"]:+.1f}%')
                
                # Conditions check
                print(f'\n🎯 CONDITIONS CHECK:')
                sol_status = "✅ READY" if sol["at_target"] else f"❌ Wait (${sol['price']:.2f})"
                btc_ready_status = "✅ CONFIRMED" if btc["ready"] else f"❌ Wait ({btc['recovery_signals']}/3 signals)"
                
                print(f'SOL ≤ ${sol["target"]}: {sol_status}')
                print(f'BTC Recovery: {btc_ready_status}')
                
                # Action status
                analysis = status['analysis']
                if analysis['action_status'] == "ACTION_TRIGGER":
                    print(f'\n🚨 ACTION TRIGGER! 🚨')
                    print(f'✅ SOL at target zone!')
                    print(f'✅ BTC showing recovery!')
                    print(f'→ CONSIDERAR RECOMPRA AHORA')
                    
                    if analysis['suggested_action']:
                        action = analysis['suggested_action']
                        print(f'\n💰 SUGGESTED BUY:')
                        print(f'• Amount: {action["amount"]}')
                        print(f'• Entry: ${action["entry"]:.2f}')
                        print(f'• Stop loss: ${action["stop_loss"]}')
                        print(f'• Target: ${action["target"]}')
                
                elif analysis['action_status'] == "SOL_READY":
                    print(f'\n⚠️ SOL AT TARGET BUT BTC WEAK')
                    print(f'→ WAIT for BTC recovery')
                    print(f'→ Risk of more downside')
                
                elif analysis['action_status'] == "BTC_READY":
                    print(f'\n📈 BTC RECOVERING BUT SOL NOT AT TARGET')
                    print(f'→ May not reach ${sol["target"]}')
                    print(f'→ Consider $183-185 entry')
                
                else:
                    print(f'\n⏳ WAITING...')
                    print(f'→ {analysis["action_description"]}')
                
                # Position status
                pos = status['position']
                print(f'\n💼 YOUR POSITION:')
                print(f'Current P&L: ~${pos["current_pnl"]:.2f}')
                print(f'Liquidation: ${pos["liquidation_price"]}')
                print(f'Safety buffer: {pos["distance_to_liquidation"]:.1f}%')
                print(f'{pos["safety_status"]}')
                
                # Market overview
                print(f'\n🌍 MARKET MOOD: {analysis["market_mood"]}')
                
                # Key levels reminder
                print(f'\n📍 KEY LEVELS:')
                print(f'SOL targets: ${sol["target"]} → $183 → $185')
                print(f'BTC signals: $108k → $110k → $112k')
                
                print(f'\n{"="*60}')
                print(f'Refreshing in 30 seconds... (Ctrl+C to stop)')
                
                await asyncio.sleep(30)
                
            except KeyboardInterrupt:
                print('\n\n⏹️ Wait strategy monitor stopped')
                break
            except Exception as e:
                print(f'\n❌ Error: {e}')
                await asyncio.sleep(10)


# Export the monitor for use by main controller
wait_strategy_monitor = WaitStrategyMonitor()