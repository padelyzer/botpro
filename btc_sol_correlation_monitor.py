#!/usr/bin/env python3
"""
BTC/SOL Correlation Monitor with Smart Entry Detection
Tracks correlation patterns and identifies optimal entry points
"""

import httpx
import asyncio
import numpy as np
from datetime import datetime, timedelta
from collections import deque
import time

class CorrelationMonitor:
    def __init__(self):
        self.btc_prices = deque(maxlen=100)  # Store last 100 prices
        self.sol_prices = deque(maxlen=100)
        self.btc_changes = deque(maxlen=20)  # Store last 20 5-min changes
        self.sol_changes = deque(maxlen=20)
        self.correlation_history = deque(maxlen=50)
        
        # Entry signal thresholds
        self.sol_oversold_rsi = 30
        self.btc_recovery_threshold = 110000
        self.sol_target_low = 180
        self.correlation_threshold = 0.7
        
    async def get_prices(self, client):
        """Fetch current BTC and SOL prices"""
        try:
            btc = await client.get('https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT', timeout=10.0)
            sol = await client.get('https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT', timeout=10.0)
            
            if btc.status_code != 200 or sol.status_code != 200:
                return None, None
            
            btc_price = float(btc.json()['price'])
            sol_price = float(sol.json()['price'])
            
            return btc_price, sol_price
        except Exception as e:
            print(f"⚠️ Network error getting prices: {e}")
            return None, None
    
    async def get_detailed_data(self, client):
        """Get detailed market data including volume and 24h stats"""
        try:
            btc = await client.get('https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT', timeout=10.0)
            sol = await client.get('https://api.binance.com/api/v3/ticker/24hr?symbol=SOLUSDT', timeout=10.0)
            
            if btc.status_code != 200 or sol.status_code != 200:
                return None, None
            
            return btc.json(), sol.json()
        except Exception as e:
            print(f"⚠️ Network error getting detailed data: {e}")
            return None, None
    
    def calculate_correlation(self):
        """Calculate rolling correlation between BTC and SOL"""
        if len(self.btc_changes) < 10 or len(self.sol_changes) < 10:
            return 0
        
        btc_array = np.array(list(self.btc_changes)[-10:])
        sol_array = np.array(list(self.sol_changes)[-10:])
        
        if np.std(btc_array) == 0 or np.std(sol_array) == 0:
            return 0
            
        correlation = np.corrcoef(btc_array, sol_array)[0, 1]
        return correlation
    
    def calculate_rsi(self, prices, period=14):
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
    
    def detect_divergence(self):
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
    
    def calculate_entry_score(self, btc_price, sol_price, btc_data, sol_data):
        """Calculate entry score from 0-100"""
        score = 0
        factors = []
        
        # 1. Price levels (30 points)
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
        
        # 2. RSI (20 points)
        sol_rsi = self.calculate_rsi(self.sol_prices)
        if sol_rsi < 30:
            score += 20
            factors.append(f"✅ SOL RSI oversold ({sol_rsi:.0f})")
        elif sol_rsi < 40:
            score += 10
            factors.append(f"🟡 SOL RSI low ({sol_rsi:.0f})")
        
        # 3. Correlation (20 points)
        correlation = self.calculate_correlation()
        self.correlation_history.append(correlation)
        
        if correlation > 0.7:
            score += 20
            factors.append(f"✅ Strong correlation ({correlation:.2f})")
        elif correlation > 0.5:
            score += 10
            factors.append(f"🟡 Moderate correlation ({correlation:.2f})")
        
        # 4. Volume (15 points)
        if sol_data:
            sol_volume = float(sol_data['quoteVolume'])
            if sol_volume > 2_000_000_000:  # High volume
                score += 15
                factors.append("✅ High volume")
            elif sol_volume > 1_500_000_000:
                score += 8
                factors.append("🟡 Normal volume")
        
        # 5. Divergence patterns (15 points)
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
    
    async def monitor(self):
        """Main monitoring loop"""
        print('='*70)
        print('🔬 BTC/SOL CORRELATION MONITOR WITH ENTRY DETECTION')
        print('='*70)
        print('Collecting initial data...\n')
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Collect initial data
            retry_count = 0
            for i in range(20):
                btc_price, sol_price = await self.get_prices(client)
                if btc_price and sol_price:
                    self.btc_prices.append(btc_price)
                    self.sol_prices.append(sol_price)
                    
                    if len(self.btc_prices) > 1:
                        btc_change = ((btc_price / self.btc_prices[-2]) - 1) * 100
                        sol_change = ((sol_price / self.sol_prices[-2]) - 1) * 100
                        self.btc_changes.append(btc_change)
                        self.sol_changes.append(sol_change)
                    
                    retry_count = 0  # Reset retry count on success
                else:
                    retry_count += 1
                    print(f"⚠️ Failed to get prices (attempt {retry_count})")
                    if retry_count >= 3:
                        print("❌ Too many failures, extending wait time...")
                        await asyncio.sleep(30)
                        retry_count = 0
                
                await asyncio.sleep(3)
            
            print('\nStarting real-time monitoring...\n')
            
            while True:
                try:
                    # Get current prices
                    btc_price, sol_price = await self.get_prices(client)
                    btc_data, sol_data = await self.get_detailed_data(client)
                    
                    if not btc_price or not sol_price:
                        print("⚠️ Failed to get price data, retrying in 30 seconds...")
                        await asyncio.sleep(30)
                        continue
                    
                    # Update history
                    self.btc_prices.append(btc_price)
                    self.sol_prices.append(sol_price)
                    
                    if len(self.btc_prices) > 1:
                        btc_change = ((btc_price / self.btc_prices[-2]) - 1) * 100
                        sol_change = ((sol_price / self.sol_prices[-2]) - 1) * 100
                        self.btc_changes.append(btc_change)
                        self.sol_changes.append(sol_change)
                    
                    # Clear screen for clean display
                    print('\033[2J\033[H')
                    
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    print(f'⏰ {timestamp} - BTC/SOL CORRELATION ANALYSIS')
                    print('='*70)
                    
                    # Current prices
                    print(f'\n📊 CURRENT PRICES:')
                    print(f'BTC: ${btc_price:,.2f}')
                    print(f'SOL: ${sol_price:.2f}')
                    
                    # 24h changes
                    if btc_data and sol_data:
                        btc_24h = float(btc_data['priceChangePercent'])
                        sol_24h = float(sol_data['priceChangePercent'])
                        print(f'\n📈 24H CHANGES:')
                        print(f'BTC: {btc_24h:+.2f}%')
                        print(f'SOL: {sol_24h:+.2f}%')
                    
                    # Correlation analysis
                    correlation = self.calculate_correlation()
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
                    
                    # RSI
                    btc_rsi = self.calculate_rsi(self.btc_prices)
                    sol_rsi = self.calculate_rsi(self.sol_prices)
                    
                    print(f'\n📊 RSI INDICATORS:')
                    print(f'BTC RSI: {btc_rsi:.1f} {"(Oversold)" if btc_rsi < 30 else "(Overbought)" if btc_rsi > 70 else ""}')
                    print(f'SOL RSI: {sol_rsi:.1f} {"(Oversold)" if sol_rsi < 30 else "(Overbought)" if sol_rsi > 70 else ""}')
                    
                    # Divergence detection
                    divergence = self.detect_divergence()
                    print(f'\n🔄 DIVERGENCE PATTERN: {divergence}')
                    
                    # Entry score calculation
                    entry_score, factors = self.calculate_entry_score(
                        btc_price, sol_price, btc_data, sol_data
                    )
                    
                    print(f'\n🎯 ENTRY SCORE: {entry_score}/100')
                    
                    # Show factors
                    if factors:
                        print('\n📋 FACTORS:')
                        for factor in factors:
                            print(f'   {factor}')
                    
                    # Entry recommendation
                    print(f'\n💡 RECOMMENDATION:')
                    if entry_score >= 70:
                        print('🟢 STRONG BUY SIGNAL!')
                        print(f'   → Entry: ${sol_price:.2f}')
                        print(f'   → Size: $60-80 (high confidence)')
                        print(f'   → Stop: ${sol_price * 0.97:.2f}')
                        print(f'   → Target: ${sol_price * 1.05:.2f}-${sol_price * 1.08:.2f}')
                    elif entry_score >= 50:
                        print('🟡 MODERATE BUY SIGNAL')
                        print(f'   → Entry: ${sol_price:.2f}')
                        print(f'   → Size: $30-40 (moderate confidence)')
                        print(f'   → Stop: ${sol_price * 0.97:.2f}')
                        print(f'   → Target: ${sol_price * 1.04:.2f}-${sol_price * 1.06:.2f}')
                    elif entry_score >= 35:
                        print('⚠️ WEAK SIGNAL - WAIT')
                        print('   → Continue monitoring')
                        print('   → Wait for better setup')
                    else:
                        print('🔴 NO ENTRY - CONDITIONS NOT MET')
                        print('   → Market not favorable')
                        print('   → Keep waiting')
                    
                    # Key levels
                    print(f'\n📍 KEY LEVELS TO WATCH:')
                    print(f'BTC support: $108,000 | resistance: $112,000')
                    print(f'SOL support: $180 | resistance: $195')
                    
                    # Correlation trend
                    if len(self.correlation_history) >= 5:
                        recent_corr = list(self.correlation_history)[-5:]
                        corr_trend = recent_corr[-1] - recent_corr[0]
                        print(f'\n📈 CORRELATION TREND: {"Strengthening" if corr_trend > 0.1 else "Weakening" if corr_trend < -0.1 else "Stable"}')
                    
                    print(f'\n{"="*70}')
                    print(f'Refreshing in 30 seconds... (Ctrl+C to stop)')
                    
                    await asyncio.sleep(30)
                    
                except KeyboardInterrupt:
                    print('\n\n⏹️ Monitor stopped by user')
                    break
                except Exception as e:
                    print(f'\n❌ Error: {e}')
                    print('Retrying in 10 seconds...')
                    await asyncio.sleep(10)

async def main():
    monitor = CorrelationMonitor()
    await monitor.monitor()

if __name__ == "__main__":
    print('🚀 Starting BTC/SOL Correlation Monitor...')
    print('This will analyze correlation patterns and detect entry points')
    print('Press Ctrl+C to stop\n')
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\n👋 Monitor stopped. Good luck with your trades!')