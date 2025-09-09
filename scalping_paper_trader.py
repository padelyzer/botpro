#!/usr/bin/env python3
"""
Scalping Paper Trader - 96 hours simulation
Optimized parameters for realistic trading
"""

import asyncio
import httpx
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json

class ScalpingPaperTrader:
    """
    Paper trading simulation with optimized parameters
    """
    
    def __init__(self, symbol: str = "SOLUSDT", capital: float = 220.0):
        self.symbol = symbol
        self.initial_capital = capital
        self.capital = capital
        self.binance_futures = "https://fapi.binance.com/fapi/v1"
        
        # OPTIMIZED PARAMETERS for more signals
        self.risk_per_trade = 0.02      # 2% risk
        self.min_profit_target = 0.003  # 0.3% (reduced from 0.4%)
        self.max_risk = 0.004           # 0.4% (increased from 0.3%)
        self.min_rr_ratio = 1.2         # 1.2:1 (reduced from 1.3)
        self.leverage = 3
        
        # Relaxed indicators
        self.rsi_oversold = 35          # More flexible
        self.rsi_overbought = 65        # More flexible
        self.min_imbalance = 10         # Reduced from 20%
        self.min_volume_ratio = 1.1     # Reduced from 1.2
        
        # Commission
        self.commission = 0.0004
        
        # Trade management
        self.max_positions = 2
        self.trades = []
        self.open_positions = {}
        
    async def fetch_data(self, interval: str, hours_back: int = 96) -> pd.DataFrame:
        """
        Fetch historical data for paper trading
        """
        async with httpx.AsyncClient() as client:
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = int((datetime.now() - timedelta(hours=hours_back)).timestamp() * 1000)
            
            try:
                response = await client.get(
                    f"{self.binance_futures}/klines",
                    params={
                        "symbol": self.symbol,
                        "interval": interval,
                        "startTime": start_time,
                        "endTime": end_time,
                        "limit": 1000
                    }
                )
                
                if response.status_code == 200:
                    klines = response.json()
                    df = pd.DataFrame(klines, columns=[
                        'timestamp', 'open', 'high', 'low', 'close', 
                        'volume', 'close_time', 'quote_volume', 'trades',
                        'taker_buy_base', 'taker_buy_quote', 'ignore'
                    ])
                    
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        df[col] = df[col].astype(float)
                    
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    
                    return df
                    
            except Exception as e:
                print(f"Error fetching {interval} data: {e}")
                
        return pd.DataFrame()
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators
        """
        # EMAs
        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Volume
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        df['atr'] = ranges.max(axis=1).rolling(window=14).mean()
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # Price position in range
        df['price_position'] = (df['close'] - df['low'].rolling(20).min()) / (df['high'].rolling(20).max() - df['low'].rolling(20).min())
        
        return df
    
    def simulate_imbalance(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Simulate order book imbalance
        """
        df['price_change'] = df['close'].pct_change()
        
        # Base imbalance on momentum and volume
        df['imbalance'] = 0.0
        
        # Strong bullish
        mask = (df['price_change'] > 0.0005) & (df['volume_ratio'] > self.min_volume_ratio)
        df.loc[mask, 'imbalance'] = 15 + (df.loc[mask, 'volume_ratio'] - 1) * 30
        
        # Moderate bullish
        mask = (df['price_change'] > 0) & (df['volume_ratio'] > 0.9)
        df.loc[mask, 'imbalance'] = 10
        
        # Strong bearish
        mask = (df['price_change'] < -0.0005) & (df['volume_ratio'] > self.min_volume_ratio)
        df.loc[mask, 'imbalance'] = -15 - (df.loc[mask, 'volume_ratio'] - 1) * 30
        
        # Moderate bearish
        mask = (df['price_change'] < 0) & (df['volume_ratio'] > 0.9)
        df.loc[mask, 'imbalance'] = -10
        
        # Add noise for realism
        df['imbalance'] += np.random.normal(0, 5, len(df))
        df['imbalance'] = df['imbalance'].clip(-100, 100)
        
        return df
    
    def identify_signal(self, df_15m: pd.DataFrame, df_5m: pd.DataFrame, df_1m: pd.DataFrame, idx: int) -> Optional[Dict]:
        """
        Identify trading signal at specific index
        """
        # Get corresponding indices
        timestamp = df_1m.index[idx]
        idx_5m = df_5m.index.get_indexer([timestamp], method='ffill')[0]
        idx_15m = df_15m.index.get_indexer([timestamp], method='ffill')[0]
        
        if idx_5m < 20 or idx_15m < 50 or idx < 50:
            return None
        
        # 15m Trend (RELAXED)
        trend = None
        ema_9 = df_15m.iloc[idx_15m]['ema_9']
        ema_21 = df_15m.iloc[idx_15m]['ema_21']
        ema_50 = df_15m.iloc[idx_15m]['ema_50']
        
        if ema_9 > ema_21:  # Simplified - just need short-term bullish
            trend = "BULLISH"
        elif ema_9 < ema_21:  # Simplified - just need short-term bearish
            trend = "BEARISH"
        else:
            return None
        
        # 5m Pullback (RELAXED)
        pullback = False
        rsi_5m = df_5m.iloc[idx_5m]['rsi']
        price_5m = df_5m.iloc[idx_5m]['close']
        
        if trend == "BULLISH":
            # Pullback if RSI < 45 OR price near EMA21
            if rsi_5m < 45 or abs(price_5m - df_5m.iloc[idx_5m]['ema_21']) / price_5m < 0.002:
                pullback = True
        else:  # BEARISH
            # Pullback if RSI > 55 OR price near EMA21
            if rsi_5m > 55 or abs(price_5m - df_5m.iloc[idx_5m]['ema_21']) / price_5m < 0.002:
                pullback = True
        
        if not pullback:
            return None
        
        # 1m Confirmation (RELAXED)
        confirmation = False
        imbalance = df_1m.iloc[idx]['imbalance']
        volume_ratio = df_1m.iloc[idx]['volume_ratio']
        price_change = df_1m.iloc[idx]['price_change']
        
        if trend == "BULLISH":
            # Need positive price action OR positive imbalance
            if (price_change > 0 and volume_ratio > 1.0) or imbalance > self.min_imbalance:
                confirmation = True
                direction = "LONG"
        else:  # BEARISH
            # Need negative price action OR negative imbalance
            if (price_change < 0 and volume_ratio > 1.0) or imbalance < -self.min_imbalance:
                confirmation = True
                direction = "SHORT"
        
        if not confirmation:
            return None
        
        # Calculate entry, stop, target
        entry_price = df_1m.iloc[idx]['close']
        atr = df_1m.iloc[idx]['atr']
        
        # Use Bollinger Bands for additional targets
        bb_upper = df_1m.iloc[idx]['bb_upper']
        bb_lower = df_1m.iloc[idx]['bb_lower']
        
        if direction == "LONG":
            # Stop at recent low or ATR
            recent_low = df_1m.iloc[idx-5:idx]['low'].min()
            stop_loss = min(recent_low * 0.998, entry_price - (atr * 0.6))
            
            # Target at resistance or BB upper
            take_profit = min(bb_upper * 0.998, entry_price + (atr * 1.2))
            
        else:  # SHORT
            # Stop at recent high or ATR
            recent_high = df_1m.iloc[idx-5:idx]['high'].max()
            stop_loss = max(recent_high * 1.002, entry_price + (atr * 0.6))
            
            # Target at support or BB lower
            take_profit = max(bb_lower * 1.002, entry_price - (atr * 1.2))
        
        # Calculate R/R
        risk = abs(entry_price - stop_loss) / entry_price
        reward = abs(take_profit - entry_price) / entry_price
        rr_ratio = reward / risk if risk > 0 else 0
        
        # Filter by minimum requirements
        if reward < self.min_profit_target or risk > self.max_risk or rr_ratio < self.min_rr_ratio:
            return None
        
        # Calculate position size
        risk_amount = self.capital * self.risk_per_trade
        position_value = (risk_amount / risk) * self.leverage
        position_size = position_value / entry_price
        
        return {
            "timestamp": timestamp,
            "direction": direction,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "position_size": position_size,
            "position_value": position_value,
            "risk_pct": risk * 100,
            "reward_pct": reward * 100,
            "rr_ratio": rr_ratio,
            "imbalance": imbalance,
            "trend": trend,
            "rsi_5m": rsi_5m
        }
    
    async def run_paper_trading(self, hours: int = 96):
        """
        Run paper trading simulation
        """
        print(f"\n📊 PAPER TRADING {self.symbol} - Last {hours} hours")
        print("="*60)
        
        # Fetch data
        print("📥 Fetching data...")
        df_15m = await self.fetch_data("15m", hours + 24)  # Extra for indicators
        df_5m = await self.fetch_data("5m", hours + 24)
        df_1m = await self.fetch_data("1m", hours + 24)
        
        if df_15m.empty or df_5m.empty or df_1m.empty:
            print("❌ Failed to fetch data")
            return
        
        # Calculate indicators
        print("📈 Calculating indicators...")
        df_15m = self.calculate_indicators(df_15m)
        df_5m = self.calculate_indicators(df_5m)
        df_1m = self.calculate_indicators(df_1m)
        df_1m = self.simulate_imbalance(df_1m)
        
        # Start from where indicators are ready
        start_idx = 100
        end_idx = len(df_1m) - 1
        
        print(f"🔍 Analyzing {end_idx - start_idx} candles...")
        print("-"*60)
        
        # Simulate trading
        for i in range(start_idx, end_idx):
            # Check for signal
            signal = self.identify_signal(df_15m, df_5m, df_1m, i)
            
            if signal and len(self.open_positions) < self.max_positions:
                # Open trade
                trade_id = f"trade_{len(self.trades) + 1}"
                self.open_positions[trade_id] = {
                    **signal,
                    "entry_idx": i,
                    "status": "OPEN"
                }
                
                print(f"\n🎯 SIGNAL #{len(self.trades) + 1}")
                print(f"   Time: {signal['timestamp'].strftime('%Y-%m-%d %H:%M')}")
                print(f"   Direction: {signal['direction']}")
                print(f"   Entry: ${signal['entry_price']:.2f}")
                print(f"   Stop: ${signal['stop_loss']:.2f} (-{signal['risk_pct']:.2f}%)")
                print(f"   Target: ${signal['take_profit']:.2f} (+{signal['reward_pct']:.2f}%)")
                print(f"   R/R: 1:{signal['rr_ratio']:.2f}")
                print(f"   Imbalance: {signal['imbalance']:.1f}%")
            
            # Check open positions for exit
            for trade_id, position in list(self.open_positions.items()):
                current_price = df_1m.iloc[i]['close']
                
                exit_price = None
                exit_reason = None
                
                if position['direction'] == "LONG":
                    if df_1m.iloc[i]['low'] <= position['stop_loss']:
                        exit_price = position['stop_loss']
                        exit_reason = "STOP_LOSS"
                    elif df_1m.iloc[i]['high'] >= position['take_profit']:
                        exit_price = position['take_profit']
                        exit_reason = "TAKE_PROFIT"
                else:  # SHORT
                    if df_1m.iloc[i]['high'] >= position['stop_loss']:
                        exit_price = position['stop_loss']
                        exit_reason = "STOP_LOSS"
                    elif df_1m.iloc[i]['low'] <= position['take_profit']:
                        exit_price = position['take_profit']
                        exit_reason = "TAKE_PROFIT"
                
                if exit_price:
                    # Calculate P&L
                    if position['direction'] == "LONG":
                        gross_pnl_pct = ((exit_price - position['entry_price']) / position['entry_price'])
                    else:
                        gross_pnl_pct = ((position['entry_price'] - exit_price) / position['entry_price'])
                    
                    net_pnl_pct = gross_pnl_pct - (self.commission * 2)
                    pnl_dollars = net_pnl_pct * position['position_value']
                    
                    # Update capital
                    self.capital += pnl_dollars
                    
                    # Record trade
                    self.trades.append({
                        **position,
                        "exit_price": exit_price,
                        "exit_reason": exit_reason,
                        "exit_time": df_1m.index[i],
                        "gross_pnl_pct": gross_pnl_pct * 100,
                        "net_pnl_pct": net_pnl_pct * 100,
                        "pnl_dollars": pnl_dollars
                    })
                    
                    # Print result
                    emoji = "✅" if pnl_dollars > 0 else "❌"
                    print(f"   {emoji} CLOSED: {exit_reason} | P&L: {net_pnl_pct*100:.2f}% (${pnl_dollars:.2f})")
                    
                    # Remove from open positions
                    del self.open_positions[trade_id]
        
        # Final statistics
        self.print_statistics()
    
    def print_statistics(self):
        """
        Print trading statistics
        """
        print("\n" + "="*60)
        print("📊 PAPER TRADING RESULTS")
        print("="*60)
        
        if not self.trades:
            print("❌ No trades executed")
            return
        
        wins = [t for t in self.trades if t['pnl_dollars'] > 0]
        losses = [t for t in self.trades if t['pnl_dollars'] <= 0]
        
        total_pnl = sum(t['pnl_dollars'] for t in self.trades)
        win_rate = len(wins) / len(self.trades) * 100
        
        avg_win = sum(t['pnl_dollars'] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t['pnl_dollars'] for t in losses) / len(losses) if losses else 0
        
        print(f"💰 Capital: ${self.initial_capital:.2f} → ${self.capital:.2f}")
        print(f"📈 Total Return: {((self.capital - self.initial_capital) / self.initial_capital * 100):.2f}%")
        print(f"📊 Total P&L: ${total_pnl:.2f}")
        print()
        print(f"📝 Total Trades: {len(self.trades)}")
        print(f"✅ Wins: {len(wins)}")
        print(f"❌ Losses: {len(losses)}")
        print(f"🎯 Win Rate: {win_rate:.1f}%")
        print()
        print(f"💚 Avg Win: ${avg_win:.2f}")
        print(f"💔 Avg Loss: ${avg_loss:.2f}")
        
        if losses:
            profit_factor = abs(sum(t['pnl_dollars'] for t in wins) / sum(t['pnl_dollars'] for t in losses))
            print(f"📊 Profit Factor: {profit_factor:.2f}")
        
        # Trade distribution
        print(f"\n📅 Trade Distribution:")
        longs = [t for t in self.trades if t['direction'] == "LONG"]
        shorts = [t for t in self.trades if t['direction'] == "SHORT"]
        print(f"   Longs: {len(longs)} ({len([t for t in longs if t['pnl_dollars'] > 0])} wins)")
        print(f"   Shorts: {len(shorts)} ({len([t for t in shorts if t['pnl_dollars'] > 0])} wins)")
        
        # Best and worst trades
        if self.trades:
            best_trade = max(self.trades, key=lambda x: x['pnl_dollars'])
            worst_trade = min(self.trades, key=lambda x: x['pnl_dollars'])
            
            print(f"\n🏆 Best Trade: ${best_trade['pnl_dollars']:.2f} ({best_trade['net_pnl_pct']:.2f}%)")
            print(f"😔 Worst Trade: ${worst_trade['pnl_dollars']:.2f} ({worst_trade['net_pnl_pct']:.2f}%)")

async def main():
    """
    Run paper trading simulation
    """
    # Create paper trader for SOL
    trader = ScalpingPaperTrader(symbol="SOLUSDT", capital=220)
    
    # Run 96-hour simulation
    await trader.run_paper_trading(hours=96)
    
    print("\n✅ Paper Trading Complete!")

if __name__ == "__main__":
    asyncio.run(main())