#!/usr/bin/env python3
"""
Professional Scalping Bot System
Multi-timeframe analysis with liquidity edge
"""

import asyncio
import httpx
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScalpingBot:
    """
    Multi-timeframe scalping bot with order book analysis
    """
    
    def __init__(self, capital: float = 220.0):
        # API endpoints
        self.binance_futures = "https://fapi.binance.com/fapi/v1"
        self.binance_spot = "https://api.binance.com/api/v3"
        self.liquidity_api = "http://localhost:8002/api/liquidity"
        
        # Capital management
        self.capital = capital
        self.risk_per_trade = 0.02  # 2% risk per trade
        self.max_positions = 2       # Max concurrent positions
        self.leverage = 3            # Conservative leverage
        
        # Scalping parameters
        self.min_profit_target = 0.004  # 0.4% minimum
        self.max_risk = 0.003           # 0.3% stop loss
        self.min_imbalance = 20        # 20% minimum imbalance
        self.min_rr_ratio = 1.3        # 1.3:1 minimum
        
        # Timeframe configuration
        self.timeframes = {
            "trend": "15m",    # Overall trend
            "setup": "5m",     # Pullback detection
            "trigger": "1m"    # Entry confirmation
        }
        
        # Position tracking
        self.positions = {}
        self.trade_history = []
        
    async def get_multi_timeframe_data(self, symbol: str) -> Dict:
        """
        Get data from multiple timeframes
        """
        async with httpx.AsyncClient() as client:
            data = {}
            
            for tf_name, interval in self.timeframes.items():
                try:
                    response = await client.get(
                        f"{self.binance_futures}/klines",
                        params={
                            "symbol": symbol,
                            "interval": interval,
                            "limit": 100
                        }
                    )
                    
                    if response.status_code == 200:
                        klines = response.json()
                        df = pd.DataFrame(klines, columns=[
                            'timestamp', 'open', 'high', 'low', 'close', 
                            'volume', 'close_time', 'quote_volume', 'trades',
                            'taker_buy_base', 'taker_buy_quote', 'ignore'
                        ])
                        
                        # Convert to numeric
                        for col in ['open', 'high', 'low', 'close', 'volume']:
                            df[col] = df[col].astype(float)
                        
                        data[tf_name] = df
                        
                except Exception as e:
                    logger.error(f"Error fetching {interval} data: {e}")
                    
            return data
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators for scalping
        """
        # EMAs for trend
        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        # RSI for momentum
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Volume analysis
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # ATR for volatility
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        df['atr'] = ranges.max(axis=1).rolling(window=14).mean()
        
        # Support/Resistance levels
        df['resistance'] = df['high'].rolling(window=20).max()
        df['support'] = df['low'].rolling(window=20).min()
        
        return df
    
    async def get_order_book_edge(self, symbol: str) -> Dict:
        """
        Get order book analysis for entry/exit optimization
        """
        async with httpx.AsyncClient() as client:
            try:
                # Get liquidity data
                response = await client.get(f"{self.liquidity_api}/{symbol}")
                
                if response.status_code == 200:
                    data = response.json()
                    ob_analysis = data.get("order_book_analysis", {})
                    
                    return {
                        "imbalance": ob_analysis.get("imbalance", 0),
                        "whale_activity": ob_analysis.get("large_orders", {}).get("whale_activity", False),
                        "bid_liquidity": ob_analysis.get("liquidity_score", {}).get("0.5%", {}).get("bid_liquidity", 0),
                        "ask_liquidity": ob_analysis.get("liquidity_score", {}).get("0.5%", {}).get("ask_liquidity", 0),
                        "spread_bps": ob_analysis.get("spread_bps", 0),
                        "support_levels": ob_analysis.get("support_levels", []),
                        "resistance_levels": ob_analysis.get("resistance_levels", [])
                    }
                    
            except Exception as e:
                logger.error(f"Error getting order book data: {e}")
                
        return {}
    
    def identify_trend(self, df_15m: pd.DataFrame) -> str:
        """
        Identify overall trend from 15m timeframe
        """
        if len(df_15m) < 50:
            return "NEUTRAL"
        
        df = df_15m.iloc[-1]  # Latest candle
        
        # EMA alignment
        if df['ema_9'] > df['ema_21'] > df['ema_50']:
            trend = "BULLISH"
        elif df['ema_9'] < df['ema_21'] < df['ema_50']:
            trend = "BEARISH"
        else:
            trend = "NEUTRAL"
        
        # Confirm with price action
        if trend == "BULLISH" and df['close'] < df['ema_9']:
            trend = "BULLISH_PULLBACK"  # Good for long entry
        elif trend == "BEARISH" and df['close'] > df['ema_9']:
            trend = "BEARISH_PULLBACK"  # Good for short entry
            
        return trend
    
    def detect_pullback(self, df_5m: pd.DataFrame, trend: str) -> bool:
        """
        Detect pullback in 5m timeframe
        """
        if len(df_5m) < 20:
            return False
        
        latest = df_5m.iloc[-1]
        prev = df_5m.iloc[-2]
        
        if "BULLISH" in trend:
            # Look for pullback to support
            pullback_to_ema = latest['low'] <= latest['ema_21'] <= latest['high']
            rsi_oversold = latest['rsi'] < 40
            volume_decrease = latest['volume_ratio'] < 0.8
            
            return pullback_to_ema and (rsi_oversold or volume_decrease)
            
        elif "BEARISH" in trend:
            # Look for pullback to resistance
            pullback_to_ema = latest['low'] <= latest['ema_21'] <= latest['high']
            rsi_overbought = latest['rsi'] > 60
            volume_decrease = latest['volume_ratio'] < 0.8
            
            return pullback_to_ema and (rsi_overbought or volume_decrease)
            
        return False
    
    def confirm_reversal(self, df_1m: pd.DataFrame, trend: str) -> bool:
        """
        Confirm reversal in 1m timeframe
        """
        if len(df_1m) < 10:
            return False
        
        latest = df_1m.iloc[-1]
        prev = df_1m.iloc[-2]
        
        if "BULLISH" in trend:
            # Bullish reversal signals
            price_bounce = latest['close'] > prev['close'] and latest['low'] > prev['low']
            volume_spike = latest['volume_ratio'] > 1.5
            rsi_turn = latest['rsi'] > prev['rsi'] and latest['rsi'] > 30
            
            return price_bounce and (volume_spike or rsi_turn)
            
        elif "BEARISH" in trend:
            # Bearish reversal signals
            price_reject = latest['close'] < prev['close'] and latest['high'] < prev['high']
            volume_spike = latest['volume_ratio'] > 1.5
            rsi_turn = latest['rsi'] < prev['rsi'] and latest['rsi'] < 70
            
            return price_reject and (volume_spike or rsi_turn)
            
        return False
    
    async def generate_scalp_signal(self, symbol: str) -> Optional[Dict]:
        """
        Generate scalping signal combining all analysis
        """
        # Get multi-timeframe data
        mtf_data = await self.get_multi_timeframe_data(symbol)
        
        if not all(tf in mtf_data for tf in ["trend", "setup", "trigger"]):
            return None
        
        # Calculate indicators
        df_15m = self.calculate_indicators(mtf_data["trend"])
        df_5m = self.calculate_indicators(mtf_data["setup"])
        df_1m = self.calculate_indicators(mtf_data["trigger"])
        
        # Get order book edge
        ob_data = await self.get_order_book_edge(symbol)
        
        # 1. Check trend (15m)
        trend = self.identify_trend(df_15m)
        if trend == "NEUTRAL":
            return None
        
        # 2. Check for pullback (5m)
        pullback = self.detect_pullback(df_5m, trend)
        if not pullback:
            return None
        
        # 3. Confirm reversal (1m)
        reversal = self.confirm_reversal(df_1m, trend)
        if not reversal:
            return None
        
        # 4. Check order book conditions
        imbalance = ob_data.get("imbalance", 0)
        whale_activity = ob_data.get("whale_activity", False)
        
        # Validate imbalance aligns with trend
        if "BULLISH" in trend and imbalance < self.min_imbalance:
            return None
        elif "BEARISH" in trend and imbalance > -self.min_imbalance:
            return None
        
        # 5. Calculate entry, stop, and target
        current_price = df_1m.iloc[-1]['close']
        atr = df_1m.iloc[-1]['atr']
        
        if "BULLISH" in trend:
            # Find nearest support from order book
            support_levels = ob_data.get("support_levels", [])
            entry_price = current_price
            
            if support_levels:
                nearest_support = min(support_levels, 
                                     key=lambda x: abs(x['price'] - current_price))
                stop_loss = nearest_support['price'] * 0.998  # Just below support
            else:
                stop_loss = current_price - (atr * 0.5)  # ATR-based stop
            
            # Target based on resistance or ATR
            resistance_levels = ob_data.get("resistance_levels", [])
            if resistance_levels:
                nearest_resistance = min(resistance_levels,
                                        key=lambda x: x['price'] if x['price'] > current_price else float('inf'))
                take_profit = nearest_resistance['price'] * 0.998
            else:
                take_profit = current_price + (atr * 1.0)
            
            direction = "LONG"
            
        else:  # BEARISH
            # Find nearest resistance from order book
            resistance_levels = ob_data.get("resistance_levels", [])
            entry_price = current_price
            
            if resistance_levels:
                nearest_resistance = min(resistance_levels,
                                        key=lambda x: abs(x['price'] - current_price))
                stop_loss = nearest_resistance['price'] * 1.002  # Just above resistance
            else:
                stop_loss = current_price + (atr * 0.5)
            
            # Target based on support or ATR
            support_levels = ob_data.get("support_levels", [])
            if support_levels:
                nearest_support = min(support_levels,
                                     key=lambda x: x['price'] if x['price'] < current_price else 0)
                take_profit = nearest_support['price'] * 1.002
            else:
                take_profit = current_price - (atr * 1.0)
            
            direction = "SHORT"
        
        # Calculate risk/reward
        risk = abs(entry_price - stop_loss) / entry_price
        reward = abs(take_profit - entry_price) / entry_price
        rr_ratio = reward / risk if risk > 0 else 0
        
        # Validate minimum requirements
        if reward < self.min_profit_target or risk > self.max_risk or rr_ratio < self.min_rr_ratio:
            return None
        
        # Calculate position size
        risk_amount = self.capital * self.risk_per_trade
        position_size = (risk_amount / (risk * entry_price)) * self.leverage
        
        signal = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "direction": direction,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "position_size": position_size,
            "risk_pct": risk * 100,
            "reward_pct": reward * 100,
            "rr_ratio": rr_ratio,
            "confidence": self.calculate_confidence(trend, imbalance, whale_activity, rr_ratio),
            "analysis": {
                "trend_15m": trend,
                "pullback_5m": pullback,
                "reversal_1m": reversal,
                "imbalance": imbalance,
                "whale_activity": whale_activity
            }
        }
        
        return signal
    
    def calculate_confidence(self, trend: str, imbalance: float, whale_activity: bool, rr_ratio: float) -> str:
        """
        Calculate signal confidence
        """
        score = 0
        
        # Trend strength
        if "PULLBACK" in trend:
            score += 2  # Best setup
        else:
            score += 1
        
        # Imbalance strength
        if abs(imbalance) > 40:
            score += 2
        elif abs(imbalance) > 25:
            score += 1
        
        # Whale activity
        if whale_activity:
            score += 1
        
        # Risk/Reward
        if rr_ratio > 2:
            score += 2
        elif rr_ratio > 1.5:
            score += 1
        
        # Determine confidence
        if score >= 6:
            return "HIGH"
        elif score >= 4:
            return "MEDIUM"
        else:
            return "LOW"
    
    async def execute_trade(self, signal: Dict) -> Dict:
        """
        Execute trade (paper trading for now)
        """
        trade_id = f"{signal['symbol']}_{datetime.now().timestamp()}"
        
        self.positions[trade_id] = {
            "signal": signal,
            "status": "OPEN",
            "entry_time": datetime.now(),
            "entry_price": signal['entry_price'],
            "current_price": signal['entry_price'],
            "pnl": 0,
            "pnl_pct": 0
        }
        
        logger.info(f"📈 Trade Opened: {signal['symbol']} {signal['direction']} @ {signal['entry_price']:.2f}")
        
        return {"trade_id": trade_id, "status": "executed"}
    
    async def monitor_positions(self):
        """
        Monitor open positions and manage exits
        """
        while True:
            for trade_id, position in list(self.positions.items()):
                if position['status'] != "OPEN":
                    continue
                
                symbol = position['signal']['symbol']
                
                # Get current price
                async with httpx.AsyncClient() as client:
                    try:
                        response = await client.get(
                            f"{self.binance_spot}/ticker/price",
                            params={"symbol": symbol}
                        )
                        
                        if response.status_code == 200:
                            current_price = float(response.json()['price'])
                            position['current_price'] = current_price
                            
                            # Calculate P&L
                            if position['signal']['direction'] == "LONG":
                                pnl_pct = ((current_price - position['entry_price']) / position['entry_price']) * 100
                            else:
                                pnl_pct = ((position['entry_price'] - current_price) / position['entry_price']) * 100
                            
                            position['pnl_pct'] = pnl_pct
                            position['pnl'] = pnl_pct * position['signal']['position_size'] * position['entry_price'] / 100
                            
                            # Check exit conditions
                            if position['signal']['direction'] == "LONG":
                                if current_price <= position['signal']['stop_loss']:
                                    await self.close_position(trade_id, "STOP_LOSS")
                                elif current_price >= position['signal']['take_profit']:
                                    await self.close_position(trade_id, "TAKE_PROFIT")
                            else:  # SHORT
                                if current_price >= position['signal']['stop_loss']:
                                    await self.close_position(trade_id, "STOP_LOSS")
                                elif current_price <= position['signal']['take_profit']:
                                    await self.close_position(trade_id, "TAKE_PROFIT")
                                    
                    except Exception as e:
                        logger.error(f"Error monitoring position {trade_id}: {e}")
            
            await asyncio.sleep(5)  # Check every 5 seconds
    
    async def close_position(self, trade_id: str, reason: str):
        """
        Close position and record results
        """
        if trade_id not in self.positions:
            return
        
        position = self.positions[trade_id]
        position['status'] = "CLOSED"
        position['close_time'] = datetime.now()
        position['close_reason'] = reason
        
        # Record to history
        self.trade_history.append(position)
        
        # Log results
        emoji = "✅" if position['pnl'] > 0 else "❌"
        logger.info(
            f"{emoji} Trade Closed: {position['signal']['symbol']} "
            f"{reason} | P&L: {position['pnl_pct']:.2f}% (${position['pnl']:.2f})"
        )
        
        # Remove from active positions
        del self.positions[trade_id]
    
    def get_statistics(self) -> Dict:
        """
        Calculate trading statistics
        """
        if not self.trade_history:
            return {"message": "No trades completed yet"}
        
        wins = [t for t in self.trade_history if t['pnl'] > 0]
        losses = [t for t in self.trade_history if t['pnl'] <= 0]
        
        total_pnl = sum(t['pnl'] for t in self.trade_history)
        win_rate = len(wins) / len(self.trade_history) * 100 if self.trade_history else 0
        
        avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t['pnl'] for t in losses) / len(losses) if losses else 0
        
        profit_factor = abs(sum(t['pnl'] for t in wins) / sum(t['pnl'] for t in losses)) if losses else 0
        
        return {
            "total_trades": len(self.trade_history),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "current_capital": self.capital + total_pnl
        }

# Testing function
async def test_scalping_bot():
    """
    Test the scalping bot with real-time data
    """
    bot = ScalpingBot(capital=220)
    
    # Test symbols
    symbols = ["SOLUSDT", "BNBUSDT", "BTCUSDT"]
    
    print("🤖 SCALPING BOT TEST")
    print("="*50)
    
    for symbol in symbols:
        print(f"\n📊 Analyzing {symbol}...")
        signal = await bot.generate_scalp_signal(symbol)
        
        if signal:
            print(f"✅ SIGNAL FOUND!")
            print(f"   Direction: {signal['direction']}")
            print(f"   Entry: ${signal['entry_price']:.2f}")
            print(f"   Stop: ${signal['stop_loss']:.2f}")
            print(f"   Target: ${signal['take_profit']:.2f}")
            print(f"   Risk: {signal['risk_pct']:.2f}%")
            print(f"   Reward: {signal['reward_pct']:.2f}%")
            print(f"   R/R: 1:{signal['rr_ratio']:.2f}")
            print(f"   Confidence: {signal['confidence']}")
            print(f"   Position Size: {signal['position_size']:.4f}")
        else:
            print(f"❌ No signal - conditions not met")
    
    print("\n" + "="*50)
    print("Test complete!")

if __name__ == "__main__":
    asyncio.run(test_scalping_bot())