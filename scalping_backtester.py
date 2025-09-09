#!/usr/bin/env python3
"""
Scalping Bot Backtester
Test historical performance with real data
"""

import asyncio
import httpx
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
import json

class ScalpingBacktester:
    """
    Backtest scalping strategies with historical data
    """
    
    def __init__(self, initial_capital: float = 220.0):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.binance_futures = "https://fapi.binance.com/fapi/v1"
        
        # Strategy parameters (from main bot)
        self.risk_per_trade = 0.02
        self.min_profit_target = 0.004
        self.max_risk = 0.003
        self.min_rr_ratio = 1.3
        self.leverage = 3
        
        # Commission
        self.commission = 0.0004  # 0.04% per side
        
        # Results storage
        self.trades = []
        
    async def fetch_historical_data(self, symbol: str, interval: str, days_back: int = 30) -> pd.DataFrame:
        """
        Fetch historical kline data
        """
        async with httpx.AsyncClient() as client:
            # Calculate start time
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1000)
            
            all_klines = []
            current_start = start_time
            
            while current_start < end_time:
                try:
                    response = await client.get(
                        f"{self.binance_futures}/klines",
                        params={
                            "symbol": symbol,
                            "interval": interval,
                            "startTime": current_start,
                            "limit": 1000
                        }
                    )
                    
                    if response.status_code == 200:
                        klines = response.json()
                        if not klines:
                            break
                        all_klines.extend(klines)
                        # Move to next batch
                        current_start = klines[-1][6] + 1  # Close time + 1ms
                    else:
                        break
                        
                except Exception as e:
                    print(f"Error fetching data: {e}")
                    break
            
            if all_klines:
                df = pd.DataFrame(all_klines, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 
                    'volume', 'close_time', 'quote_volume', 'trades',
                    'taker_buy_base', 'taker_buy_quote', 'ignore'
                ])
                
                # Convert to numeric
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = df[col].astype(float)
                
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
                
                return df
            
            return pd.DataFrame()
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all technical indicators
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
        
        # Volume analysis
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
        
        # Support/Resistance
        df['resistance'] = df['high'].rolling(window=20).max()
        df['support'] = df['low'].rolling(window=20).min()
        
        return df
    
    def simulate_order_book_imbalance(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Simulate order book imbalance based on price/volume action
        """
        # Simplified imbalance simulation based on volume and price movement
        df['price_change'] = df['close'].pct_change()
        df['volume_change'] = df['volume'].pct_change()
        
        # Estimate imbalance
        df['imbalance'] = 0.0
        
        # Strong buying pressure
        mask_buy = (df['price_change'] > 0.001) & (df['volume_ratio'] > 1.2)
        df.loc[mask_buy, 'imbalance'] = 20 + (df.loc[mask_buy, 'volume_ratio'] - 1) * 50
        
        # Strong selling pressure
        mask_sell = (df['price_change'] < -0.001) & (df['volume_ratio'] > 1.2)
        df.loc[mask_sell, 'imbalance'] = -20 - (df.loc[mask_sell, 'volume_ratio'] - 1) * 50
        
        # Moderate conditions
        mask_mod_buy = (df['price_change'] > 0) & (df['volume_ratio'] > 0.8)
        df.loc[mask_mod_buy, 'imbalance'] = 10
        
        mask_mod_sell = (df['price_change'] < 0) & (df['volume_ratio'] > 0.8)
        df.loc[mask_mod_sell, 'imbalance'] = -10
        
        # Clip extreme values
        df['imbalance'] = df['imbalance'].clip(-100, 100)
        
        return df
    
    def identify_scalp_opportunities(self, df_15m: pd.DataFrame, df_5m: pd.DataFrame, df_1m: pd.DataFrame) -> List[Dict]:
        """
        Identify scalping opportunities from historical data
        """
        opportunities = []
        
        # Ensure all dataframes have indicators
        df_15m = self.calculate_indicators(df_15m)
        df_5m = self.calculate_indicators(df_5m)
        df_1m = self.calculate_indicators(df_1m)
        df_1m = self.simulate_order_book_imbalance(df_1m)
        
        # Align timeframes (use 1m as base)
        for i in range(100, len(df_1m) - 10):  # Start from 100 to ensure indicators are ready
            timestamp = df_1m.index[i]
            
            # Get corresponding 5m and 15m candles
            idx_5m = df_5m.index.get_indexer([timestamp], method='ffill')[0]
            idx_15m = df_15m.index.get_indexer([timestamp], method='ffill')[0]
            
            if idx_5m < 50 or idx_15m < 50:  # Not enough history
                continue
            
            # 1. Check 15m trend
            ema_trend = None
            if df_15m.iloc[idx_15m]['ema_9'] > df_15m.iloc[idx_15m]['ema_21'] > df_15m.iloc[idx_15m]['ema_50']:
                ema_trend = "BULLISH"
            elif df_15m.iloc[idx_15m]['ema_9'] < df_15m.iloc[idx_15m]['ema_21'] < df_15m.iloc[idx_15m]['ema_50']:
                ema_trend = "BEARISH"
            
            if not ema_trend:
                continue
            
            # 2. Check 5m pullback
            pullback = False
            if ema_trend == "BULLISH":
                # Check if price pulled back to EMA21
                if df_5m.iloc[idx_5m]['low'] <= df_5m.iloc[idx_5m]['ema_21'] <= df_5m.iloc[idx_5m]['high']:
                    if df_5m.iloc[idx_5m]['rsi'] < 45:  # Oversold on pullback
                        pullback = True
            else:  # BEARISH
                if df_5m.iloc[idx_5m]['low'] <= df_5m.iloc[idx_5m]['ema_21'] <= df_5m.iloc[idx_5m]['high']:
                    if df_5m.iloc[idx_5m]['rsi'] > 55:  # Overbought on pullback
                        pullback = True
            
            if not pullback:
                continue
            
            # 3. Check 1m reversal confirmation
            reversal = False
            imbalance = df_1m.iloc[i]['imbalance']
            
            if ema_trend == "BULLISH":
                # Bullish reversal: price bounce + volume
                if (df_1m.iloc[i]['close'] > df_1m.iloc[i-1]['close'] and 
                    df_1m.iloc[i]['low'] > df_1m.iloc[i-1]['low'] and
                    df_1m.iloc[i]['volume_ratio'] > 1.2 and
                    imbalance > 20):
                    reversal = True
                    direction = "LONG"
            else:  # BEARISH
                # Bearish reversal: price rejection + volume
                if (df_1m.iloc[i]['close'] < df_1m.iloc[i-1]['close'] and
                    df_1m.iloc[i]['high'] < df_1m.iloc[i-1]['high'] and
                    df_1m.iloc[i]['volume_ratio'] > 1.2 and
                    imbalance < -20):
                    reversal = True
                    direction = "SHORT"
            
            if not reversal:
                continue
            
            # Calculate entry, stop, target
            entry_price = df_1m.iloc[i]['close']
            atr = df_1m.iloc[i]['atr']
            
            if direction == "LONG":
                stop_loss = entry_price - (atr * 0.5)
                take_profit = entry_price + (atr * 1.0)
            else:  # SHORT
                stop_loss = entry_price + (atr * 0.5)
                take_profit = entry_price - (atr * 1.0)
            
            # Calculate risk/reward
            risk = abs(entry_price - stop_loss) / entry_price
            reward = abs(take_profit - entry_price) / entry_price
            rr_ratio = reward / risk if risk > 0 else 0
            
            # Filter by minimum requirements
            if reward < self.min_profit_target or risk > self.max_risk or rr_ratio < self.min_rr_ratio:
                continue
            
            opportunities.append({
                "timestamp": timestamp,
                "direction": direction,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "risk_pct": risk * 100,
                "reward_pct": reward * 100,
                "rr_ratio": rr_ratio,
                "imbalance": imbalance
            })
        
        return opportunities
    
    def backtest_trades(self, opportunities: List[Dict], df_1m: pd.DataFrame) -> Dict:
        """
        Simulate trades and calculate results
        """
        self.capital = self.initial_capital
        self.trades = []
        
        for opp in opportunities:
            # Skip if not enough capital
            if self.capital < 10:
                break
            
            # Calculate position size
            risk_amount = self.capital * self.risk_per_trade
            risk_pct = opp['risk_pct'] / 100
            position_value = (risk_amount / risk_pct) * self.leverage
            
            # Simulate trade execution
            entry_idx = df_1m.index.get_indexer([opp['timestamp']], method='nearest')[0]
            
            # Find exit
            exit_price = None
            exit_reason = None
            exit_idx = None
            
            for j in range(entry_idx + 1, min(entry_idx + 500, len(df_1m))):  # Max 500 candles
                if opp['direction'] == "LONG":
                    if df_1m.iloc[j]['low'] <= opp['stop_loss']:
                        exit_price = opp['stop_loss']
                        exit_reason = "STOP_LOSS"
                        exit_idx = j
                        break
                    elif df_1m.iloc[j]['high'] >= opp['take_profit']:
                        exit_price = opp['take_profit']
                        exit_reason = "TAKE_PROFIT"
                        exit_idx = j
                        break
                else:  # SHORT
                    if df_1m.iloc[j]['high'] >= opp['stop_loss']:
                        exit_price = opp['stop_loss']
                        exit_reason = "STOP_LOSS"
                        exit_idx = j
                        break
                    elif df_1m.iloc[j]['low'] <= opp['take_profit']:
                        exit_price = opp['take_profit']
                        exit_reason = "TAKE_PROFIT"
                        exit_idx = j
                        break
            
            # If no exit, skip
            if not exit_price:
                continue
            
            # Calculate P&L
            if opp['direction'] == "LONG":
                gross_pnl_pct = ((exit_price - opp['entry_price']) / opp['entry_price'])
            else:  # SHORT
                gross_pnl_pct = ((opp['entry_price'] - exit_price) / opp['entry_price'])
            
            # Apply commission
            commission_cost = self.commission * 2  # Entry + exit
            net_pnl_pct = gross_pnl_pct - commission_cost
            
            # Calculate dollar P&L
            pnl_dollars = net_pnl_pct * position_value
            
            # Update capital
            self.capital += pnl_dollars
            
            # Record trade
            self.trades.append({
                "entry_time": opp['timestamp'],
                "exit_time": df_1m.index[exit_idx] if exit_idx else None,
                "direction": opp['direction'],
                "entry_price": opp['entry_price'],
                "exit_price": exit_price,
                "exit_reason": exit_reason,
                "gross_pnl_pct": gross_pnl_pct * 100,
                "net_pnl_pct": net_pnl_pct * 100,
                "pnl_dollars": pnl_dollars,
                "capital_after": self.capital,
                "rr_ratio": opp['rr_ratio']
            })
        
        # Calculate statistics
        if self.trades:
            wins = [t for t in self.trades if t['pnl_dollars'] > 0]
            losses = [t for t in self.trades if t['pnl_dollars'] <= 0]
            
            total_pnl = sum(t['pnl_dollars'] for t in self.trades)
            win_rate = len(wins) / len(self.trades) * 100
            
            avg_win = sum(t['pnl_dollars'] for t in wins) / len(wins) if wins else 0
            avg_loss = sum(t['pnl_dollars'] for t in losses) / len(losses) if losses else 0
            
            max_drawdown = self.calculate_max_drawdown()
            sharpe_ratio = self.calculate_sharpe_ratio()
            
            return {
                "initial_capital": self.initial_capital,
                "final_capital": self.capital,
                "total_return_pct": ((self.capital - self.initial_capital) / self.initial_capital) * 100,
                "total_trades": len(self.trades),
                "winning_trades": len(wins),
                "losing_trades": len(losses),
                "win_rate": win_rate,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "profit_factor": abs(sum(t['pnl_dollars'] for t in wins) / sum(t['pnl_dollars'] for t in losses)) if losses else 0,
                "max_drawdown": max_drawdown,
                "sharpe_ratio": sharpe_ratio,
                "avg_rr_ratio": np.mean([t['rr_ratio'] for t in self.trades])
            }
        
        return {"message": "No trades executed"}
    
    def calculate_max_drawdown(self) -> float:
        """
        Calculate maximum drawdown
        """
        if not self.trades:
            return 0
        
        peak = self.initial_capital
        max_dd = 0
        
        for trade in self.trades:
            if trade['capital_after'] > peak:
                peak = trade['capital_after']
            
            drawdown = (peak - trade['capital_after']) / peak
            max_dd = max(max_dd, drawdown)
        
        return max_dd * 100
    
    def calculate_sharpe_ratio(self) -> float:
        """
        Calculate Sharpe ratio (simplified)
        """
        if not self.trades:
            return 0
        
        returns = [t['net_pnl_pct'] for t in self.trades]
        
        if len(returns) < 2:
            return 0
        
        avg_return = np.mean(returns)
        std_return = np.std(returns)
        
        if std_return == 0:
            return 0
        
        # Annualized Sharpe (assuming ~250 trading days)
        sharpe = (avg_return / std_return) * np.sqrt(250)
        
        return sharpe
    
    async def run_backtest(self, symbol: str, days: int = 30) -> Dict:
        """
        Run complete backtest for a symbol
        """
        print(f"\n🔄 Backtesting {symbol} for {days} days...")
        
        # Fetch data for all timeframes
        print("   Fetching historical data...")
        df_15m = await self.fetch_historical_data(symbol, "15m", days)
        df_5m = await self.fetch_historical_data(symbol, "5m", days)
        df_1m = await self.fetch_historical_data(symbol, "1m", days)
        
        if df_15m.empty or df_5m.empty or df_1m.empty:
            return {"error": "Failed to fetch historical data"}
        
        print(f"   Data loaded: {len(df_1m)} 1m candles")
        
        # Find opportunities
        print("   Identifying scalp opportunities...")
        opportunities = self.identify_scalp_opportunities(df_15m, df_5m, df_1m)
        print(f"   Found {len(opportunities)} opportunities")
        
        # Backtest trades
        print("   Simulating trades...")
        results = self.backtest_trades(opportunities, df_1m)
        
        return results

# Main execution
async def main():
    """
    Run comprehensive backtest
    """
    print("🤖 SCALPING BOT BACKTESTER")
    print("="*60)
    
    backtester = ScalpingBacktester(initial_capital=220)
    
    # Test multiple symbols
    symbols = ["SOLUSDT", "BNBUSDT", "ETHUSDT"]
    days_to_test = 30
    
    all_results = {}
    
    for symbol in symbols:
        results = await backtester.run_backtest(symbol, days_to_test)
        all_results[symbol] = results
        
        # Print results
        print(f"\n📊 {symbol} RESULTS:")
        print("-"*40)
        
        if "error" in results:
            print(f"   ❌ Error: {results['error']}")
        elif "message" in results:
            print(f"   ⚠️ {results['message']}")
        else:
            print(f"   Initial Capital: ${results['initial_capital']:.2f}")
            print(f"   Final Capital: ${results['final_capital']:.2f}")
            print(f"   Total Return: {results['total_return_pct']:.2f}%")
            print(f"   Total Trades: {results['total_trades']}")
            print(f"   Win Rate: {results['win_rate']:.2f}%")
            print(f"   Avg Win: ${results['avg_win']:.2f}")
            print(f"   Avg Loss: ${results['avg_loss']:.2f}")
            print(f"   Profit Factor: {results['profit_factor']:.2f}")
            print(f"   Max Drawdown: {results['max_drawdown']:.2f}%")
            print(f"   Sharpe Ratio: {results['sharpe_ratio']:.2f}")
            print(f"   Avg R/R: 1:{results['avg_rr_ratio']:.2f}")
    
    # Summary
    print("\n" + "="*60)
    print("📈 BACKTEST SUMMARY")
    print("="*60)
    
    total_return = 0
    total_trades = 0
    
    for symbol, results in all_results.items():
        if "total_return_pct" in results:
            total_return += results['total_return_pct']
            total_trades += results['total_trades']
    
    if total_trades > 0:
        print(f"Average Return: {total_return/len(symbols):.2f}%")
        print(f"Total Trades: {total_trades}")
        print(f"Avg Trades per Symbol: {total_trades/len(symbols):.1f}")
    
    print("\n✅ Backtest Complete!")

if __name__ == "__main__":
    asyncio.run(main())