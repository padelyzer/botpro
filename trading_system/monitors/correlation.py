"""
BTC/SOL Correlation Monitor - Integrated Module
Tracks correlation patterns and identifies optimal entry points
"""

import asyncio
import numpy as np
from datetime import datetime
from collections import deque
from typing import Tuple, List, Dict

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import config
from core.alerts import trading_alerts, AlertType
from core.market_data import market_fetcher


class CorrelationMonitor:
    """BTC/SOL Correlation Monitor with integrated configuration and alerts"""
    
    def __init__(self):
        self.btc_prices = deque(maxlen=100)
        self.sol_prices = deque(maxlen=100)
        self.btc_changes = deque(maxlen=20)
        self.sol_changes = deque(maxlen=20)
        self.correlation_history = deque(maxlen=50)
        
        # Load configuration
        self.sol_target_low = config.get('targets.sol.buy_zones', [{"price": 180}])[0]['price']
        self.btc_recovery_threshold = config.get('targets.btc.recovery_level', 110000)
        self.correlation_threshold = 0.7
        self.min_entry_score = config.get('alerts.min_score_threshold', 60)
        
    def calculate_correlation(self) -> float:
        """Calculate rolling correlation between BTC and SOL"""
        if len(self.btc_changes) < 10 or len(self.sol_changes) < 10:
            return 0
        
        btc_array = np.array(list(self.btc_changes)[-10:])
        sol_array = np.array(list(self.sol_changes)[-10:])
        
        if np.std(btc_array) == 0 or np.std(sol_array) == 0:
            return 0
            
        correlation = np.corrcoef(btc_array, sol_array)[0, 1]
        return correlation if not np.isnan(correlation) else 0
    
    def calculate_rsi(self, prices, period=14) -> float:
        """Calculate RSI for given price series"""
        if len(prices) < period + 1:
            return 50  # Neutral if not enough data
        
        prices_list = list(prices)[-(period+1):]
        gains = []
        losses = []
        
        for i in range(1, len(prices_list)):
            diff = prices_list[i] - prices_list[i-1]
            if diff > 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(diff))
        
        avg_gain = np.mean(gains) if gains else 0
        avg_loss = np.mean(losses) if losses else 0
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def detect_divergence(self) -> str:
        """Detect BTC/SOL divergence patterns"""
        if len(self.btc_changes) < 5 or len(self.sol_changes) < 5:
            return "NO_DATA"
        
        btc_recent = np.mean(list(self.btc_changes)[-5:])
        sol_recent = np.mean(list(self.sol_changes)[-5:])
        
        if btc_recent > 0.5 and sol_recent < -0.5:
            return "BTC_LEADING_UP"
        elif btc_recent < -0.5 and sol_recent > 0.5:
            return "SOL_RESISTANT"
        elif btc_recent > 0.5 and sol_recent > 1.0:
            return "BOTH_BULLISH"
        elif btc_recent < -0.5 and sol_recent < -1.0:
            return "BOTH_BEARISH"
        else:
            return "NEUTRAL"
    
    def calculate_entry_score(self, btc_price: float, sol_price: float, 
                            btc_data: Dict, sol_data: Dict) -> Tuple[int, List[str]]:
        """Calculate entry score from 0-100"""
        score = 0
        factors = []
        
        # Price levels (30 points)
        if sol_price <= self.sol_target_low:
            score += 20
            factors.append("✅ SOL at target zone")
        elif sol_price <= 185:
            score += 10
            factors.append("🟡 SOL approaching target")
        
        if btc_price >= self.btc_recovery_threshold:
            score += 10
            factors.append("✅ BTC showing strength")
        elif btc_price >= 109000:
            score += 5
            factors.append("🟡 BTC neutral")
        
        # RSI (20 points)
        sol_rsi = self.calculate_rsi(self.sol_prices)
        if sol_rsi < 30:
            score += 20
            factors.append(f"✅ SOL RSI oversold ({sol_rsi:.0f})")
        elif sol_rsi < 40:
            score += 10
            factors.append(f"🟡 SOL RSI low ({sol_rsi:.0f})")
        
        # Correlation (20 points)
        correlation = self.calculate_correlation()
        self.correlation_history.append(correlation)
        
        if correlation > 0.7:
            score += 20
            factors.append(f"✅ Strong correlation ({correlation:.2f})")
        elif correlation > 0.5:
            score += 10
            factors.append(f"🟡 Moderate correlation ({correlation:.2f})")
        
        # Volume (15 points)
        if sol_data:
            sol_volume = float(sol_data['quoteVolume'])
            if sol_volume > 2_000_000_000:
                score += 15
                factors.append("✅ High volume")
            elif sol_volume > 1_500_000_000:
                score += 8
                factors.append("🟡 Normal volume")
        
        # Divergence patterns (15 points)
        divergence = self.detect_divergence()
        if divergence == "BTC_LEADING_UP":
            score += 15
            factors.append("✅ BTC leading recovery")
        elif divergence == "BOTH_BULLISH":
            score += 10
            factors.append("🟡 Both turning bullish")
        elif divergence == "BOTH_BEARISH":
            factors.append("🔴 Both bearish")
        
        return score, factors
    
    async def monitor_step(self) -> Dict:
        """Single monitoring step - returns current status"""
        btc_data, sol_data = await market_fetcher.get_btc_sol_data()
        
        if not btc_data or not sol_data:
            return {"error": "Failed to fetch market data"}
        
        # Parse data
        btc_price = float(btc_data['lastPrice'])
        btc_change_24h = float(btc_data['priceChangePercent'])
        
        sol_price = float(sol_data['lastPrice'])
        sol_change_24h = float(sol_data['priceChangePercent'])
        
        # Update price history
        self.btc_prices.append(btc_price)
        self.sol_prices.append(sol_price)
        
        # Calculate price changes
        if len(self.btc_prices) > 1:
            btc_change = ((btc_price / self.btc_prices[-2]) - 1) * 100
            sol_change = ((sol_price / self.sol_prices[-2]) - 1) * 100
            self.btc_changes.append(btc_change)
            self.sol_changes.append(sol_change)
        
        # Analysis
        correlation = self.calculate_correlation()
        btc_rsi = self.calculate_rsi(self.btc_prices)
        sol_rsi = self.calculate_rsi(self.sol_prices)
        divergence = self.detect_divergence()
        
        # Entry score calculation
        entry_score, factors = self.calculate_entry_score(
            btc_price, sol_price, btc_data, sol_data
        )
        
        # Generate recommendation
        recommendation = "WAIT"
        confidence = "LOW"
        suggested_entry = None
        
        if entry_score >= 70:
            recommendation = "STRONG BUY"
            confidence = "HIGH"
            suggested_entry = {
                "entry_price": sol_price,
                "position_size": "60-80 USD",
                "stop_loss": sol_price * 0.97,
                "target_1": sol_price * 1.05,
                "target_2": sol_price * 1.08
            }
            
            # Send alert
            trading_alerts.entry_signal(
                "SOL", sol_price, entry_score, "STRONG - Correlation Analysis"
            )
            
        elif entry_score >= 50:
            recommendation = "MODERATE BUY"
            confidence = "MODERATE"
            suggested_entry = {
                "entry_price": sol_price,
                "position_size": "30-40 USD",
                "stop_loss": sol_price * 0.97,
                "target_1": sol_price * 1.04,
                "target_2": sol_price * 1.06
            }
        
        # Correlation trend
        corr_trend = "STABLE"
        if len(self.correlation_history) >= 5:
            recent_corr = list(self.correlation_history)[-5:]
            corr_change = recent_corr[-1] - recent_corr[0]
            if corr_change > 0.1:
                corr_trend = "STRENGTHENING"
            elif corr_change < -0.1:
                corr_trend = "WEAKENING"
        
        return {
            "timestamp": datetime.now().isoformat(),
            "prices": {
                "btc": btc_price,
                "sol": sol_price
            },
            "changes_24h": {
                "btc": btc_change_24h,
                "sol": sol_change_24h
            },
            "analysis": {
                "correlation": correlation,
                "correlation_trend": corr_trend,
                "btc_rsi": btc_rsi,
                "sol_rsi": sol_rsi,
                "divergence": divergence,
                "entry_score": entry_score,
                "factors": factors
            },
            "recommendation": {
                "action": recommendation,
                "confidence": confidence,
                "entry_details": suggested_entry
            },
            "key_levels": {
                "btc_support": 108000,
                "btc_resistance": 112000,
                "sol_support": self.sol_target_low,
                "sol_resistance": 195
            }
        }
    
    async def monitor_continuous(self):
        """Continuous monitoring with terminal display"""
        print('='*70)
        print('🔬 BTC/SOL CORRELATION MONITOR - INTEGRATED VERSION')
        print('='*70)
        print('Collecting initial data...\n')
        
        # Collect initial data
        for i in range(20):
            try:
                btc_data, sol_data = await market_fetcher.get_btc_sol_data()
                if btc_data and sol_data:
                    btc_price = float(btc_data['lastPrice'])
                    sol_price = float(sol_data['lastPrice'])
                    
                    self.btc_prices.append(btc_price)
                    self.sol_prices.append(sol_price)
                    
                    if len(self.btc_prices) > 1:
                        btc_change = ((btc_price / self.btc_prices[-2]) - 1) * 100
                        sol_change = ((sol_price / self.sol_prices[-2]) - 1) * 100
                        self.btc_changes.append(btc_change)
                        self.sol_changes.append(sol_change)
                
                await asyncio.sleep(3)
            except Exception as e:
                print(f"Error collecting initial data: {e}")
                break
        
        print('\nStarting real-time monitoring...\n')
        
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
                print(f'⏰ {timestamp} - BTC/SOL CORRELATION ANALYSIS')
                print('='*70)
                
                # Current prices
                prices = status['prices']
                changes = status['changes_24h']
                print(f'\n📊 CURRENT PRICES:')
                print(f'BTC: ${prices["btc"]:,.2f} ({changes["btc"]:+.2f}%)')
                print(f'SOL: ${prices["sol"]:.2f} ({changes["sol"]:+.2f}%)')
                
                # Analysis
                analysis = status['analysis']
                correlation = analysis['correlation']
                print(f'\n🔗 CORRELATION (10 periods): {correlation:.3f}')
                
                if correlation > 0.8:
                    print('   → Very strong positive correlation')
                elif correlation > 0.6:
                    print('   → Strong positive correlation')
                elif correlation > 0.3:
                    print('   → Moderate correlation')
                elif correlation > -0.3:
                    print('   → Weak/No correlation')
                else:
                    print('   → Negative correlation (divergence)')
                
                # RSI indicators
                print(f'\n📊 RSI INDICATORS:')
                btc_rsi = analysis['btc_rsi']
                sol_rsi = analysis['sol_rsi']
                print(f'BTC RSI: {btc_rsi:.1f} {"(Oversold)" if btc_rsi < 30 else "(Overbought)" if btc_rsi > 70 else ""}')
                print(f'SOL RSI: {sol_rsi:.1f} {"(Oversold)" if sol_rsi < 30 else "(Overbought)" if sol_rsi > 70 else ""}')
                
                # Divergence pattern
                print(f'\n🔄 DIVERGENCE PATTERN: {analysis["divergence"]}')
                
                # Entry score
                entry_score = analysis['entry_score']
                print(f'\n🎯 ENTRY SCORE: {entry_score}/100')
                
                # Show factors
                if analysis['factors']:
                    print('\n📋 FACTORS:')
                    for factor in analysis['factors']:
                        print(f'   {factor}')
                
                # Recommendation
                rec = status['recommendation']
                print(f'\n💡 RECOMMENDATION: {rec["action"]} ({rec["confidence"]} confidence)')
                
                if rec['entry_details']:
                    details = rec['entry_details']
                    print(f'   → Entry: ${details["entry_price"]:.2f}')
                    print(f'   → Size: {details["position_size"]}')
                    print(f'   → Stop: ${details["stop_loss"]:.2f}')
                    print(f'   → Target: ${details["target_1"]:.2f}-${details["target_2"]:.2f}')
                
                # Key levels
                levels = status['key_levels']
                print(f'\n📍 KEY LEVELS TO WATCH:')
                print(f'BTC support: ${levels["btc_support"]:,} | resistance: ${levels["btc_resistance"]:,}')
                print(f'SOL support: ${levels["sol_support"]} | resistance: ${levels["sol_resistance"]}')
                
                # Correlation trend
                print(f'\n📈 CORRELATION TREND: {analysis["correlation_trend"]}')
                
                print(f'\n{"="*70}')
                print(f'Refreshing in 30 seconds... (Ctrl+C to stop)')
                
                await asyncio.sleep(30)
                
            except KeyboardInterrupt:
                print('\n\n⏹️ Correlation monitor stopped')
                break
            except Exception as e:
                print(f'\n❌ Error: {e}')
                await asyncio.sleep(10)


# Export the monitor for use by main controller
correlation_monitor = CorrelationMonitor()