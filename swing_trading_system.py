#!/usr/bin/env python3
"""
Swing Trading System
Optimized for 1-3 day holds with $220 capital
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

class SwingTradingSystem:
    """
    Swing trading system with multi-timeframe analysis
    Designed for small capital with realistic targets
    """
    
    def __init__(self, capital: float = 220.0):
        # API endpoints
        self.binance_futures = "https://fapi.binance.com/fapi/v1"
        self.binance_spot = "https://api.binance.com/api/v3"
        self.liquidity_api = "http://localhost:8002/api/liquidity"
        
        # Capital management
        self.initial_capital = capital
        self.capital = capital
        self.risk_per_trade = 0.02  # 2% risk per trade
        self.max_positions = 1       # Only 1 position at a time with small capital
        self.leverage = 3            # Conservative leverage
        
        # Swing trading parameters
        self.min_profit_target = 0.02   # 2% minimum target
        self.max_profit_target = 0.05   # 5% maximum target
        self.stop_loss_pct = 0.015      # 1.5% stop loss
        self.min_rr_ratio = 1.5         # Minimum 1.5:1 R/R
        
        # Timeframes for swing trading
        self.timeframes = {
            "macro": "1d",    # Daily for overall trend
            "swing": "4h",    # 4H for swing setups
            "entry": "1h",    # 1H for precise entry
            "fine": "15m"     # 15m for fine-tuning
        }
        
        # Technical parameters
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.min_volume_spike = 1.5  # 50% above average
        self.min_imbalance = 15      # 15% order book imbalance
        
        # Position tracking
        self.current_position = None
        self.trade_history = []
        
    async def fetch_klines(self, symbol: str, interval: str, limit: int = 100) -> pd.DataFrame:
        """
        Fetch historical kline data
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.binance_futures}/klines",
                    params={
                        "symbol": symbol,
                        "interval": interval,
                        "limit": limit
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
                    
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df.set_index('timestamp', inplace=True)
                    
                    return df
                    
            except Exception as e:
                logger.error(f"Error fetching {interval} data: {e}")
                
        return pd.DataFrame()
    
    def calculate_swing_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate indicators for swing trading
        """
        # Moving Averages
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        
        # Volume analysis
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # ATR for volatility
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        df['atr'] = ranges.max(axis=1).rolling(window=14).mean()
        df['atr_pct'] = df['atr'] / df['close'] * 100
        
        # Support and Resistance
        df['resistance'] = df['high'].rolling(window=20).max()
        df['support'] = df['low'].rolling(window=20).min()
        df['range_position'] = (df['close'] - df['support']) / (df['resistance'] - df['support'])
        
        # Trend strength
        df['adx'] = self.calculate_adx(df)
        
        return df
    
    def calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate ADX for trend strength
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        plus_dm = high.diff()
        minus_dm = low.diff().abs()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        tr1 = pd.DataFrame(high - low)
        tr2 = pd.DataFrame(abs(high - close.shift(1)))
        tr3 = pd.DataFrame(abs(low - close.shift(1)))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        atr = tr.rolling(window=period).mean()
        
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return adx
    
    async def get_market_structure(self, symbol: str) -> Dict:
        """
        Analyze market structure across timeframes
        """
        structure = {}
        
        # Fetch data for all timeframes
        for tf_name, interval in self.timeframes.items():
            df = await self.fetch_klines(symbol, interval, 100)
            
            if not df.empty:
                df = self.calculate_swing_indicators(df)
                
                # Get latest values
                latest = df.iloc[-1]
                prev = df.iloc[-2]
                
                structure[tf_name] = {
                    "trend": self.identify_trend(df),
                    "momentum": self.analyze_momentum(df),
                    "volatility": latest['atr_pct'],
                    "volume": latest['volume_ratio'],
                    "rsi": latest['rsi'],
                    "range_position": latest.get('range_position', 0.5),
                    "support": latest['support'],
                    "resistance": latest['resistance']
                }
        
        return structure
    
    def identify_trend(self, df: pd.DataFrame) -> str:
        """
        Identify trend from dataframe
        """
        if len(df) < 50:
            return "NEUTRAL"
        
        latest = df.iloc[-1]
        
        # Multiple confirmations
        ema_trend = "UP" if latest['ema_9'] > latest['ema_21'] else "DOWN"
        sma_trend = "UP" if latest['close'] > latest['sma_50'] else "DOWN"
        
        # ADX for trend strength
        trend_strength = "STRONG" if latest.get('adx', 0) > 25 else "WEAK"
        
        if ema_trend == sma_trend:
            return f"{ema_trend}_{trend_strength}"
        else:
            return "NEUTRAL"
    
    def analyze_momentum(self, df: pd.DataFrame) -> str:
        """
        Analyze momentum indicators
        """
        if len(df) < 26:
            return "NEUTRAL"
        
        latest = df.iloc[-1]
        
        # MACD momentum
        macd_bullish = latest['macd'] > latest['macd_signal'] and latest['macd_histogram'] > 0
        macd_bearish = latest['macd'] < latest['macd_signal'] and latest['macd_histogram'] < 0
        
        # RSI momentum
        rsi_bullish = 40 < latest['rsi'] < 60 and df.iloc[-2]['rsi'] < latest['rsi']
        rsi_bearish = 40 < latest['rsi'] < 60 and df.iloc[-2]['rsi'] > latest['rsi']
        
        if macd_bullish and rsi_bullish:
            return "BULLISH"
        elif macd_bearish and rsi_bearish:
            return "BEARISH"
        else:
            return "NEUTRAL"
    
    async def get_liquidity_edge(self, symbol: str) -> Dict:
        """
        Get liquidity analysis for better entries
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.liquidity_api}/{symbol}")
                
                if response.status_code == 200:
                    data = response.json()
                    ob = data.get("order_book_analysis", {})
                    
                    return {
                        "imbalance": ob.get("imbalance", 0),
                        "whale_activity": ob.get("large_orders", {}).get("whale_activity", False),
                        "spread_bps": ob.get("spread_bps", 0),
                        "bid_liquidity": ob.get("liquidity_score", {}).get("0.5%", {}).get("bid_liquidity", 0),
                        "ask_liquidity": ob.get("liquidity_score", {}).get("0.5%", {}).get("ask_liquidity", 0),
                        "support_levels": ob.get("support_levels", []),
                        "resistance_levels": ob.get("resistance_levels", [])
                    }
                    
            except Exception as e:
                logger.error(f"Error getting liquidity: {e}")
                
        return {}
    
    def identify_swing_setup(self, structure: Dict, liquidity: Dict) -> Optional[str]:
        """
        Identify swing trading setup
        """
        # Check daily trend first
        daily_trend = structure.get("macro", {}).get("trend", "NEUTRAL")
        
        if "NEUTRAL" in daily_trend:
            return None
        
        # Check 4H setup
        h4_data = structure.get("swing", {})
        h4_momentum = h4_data.get("momentum", "NEUTRAL")
        h4_rsi = h4_data.get("rsi", 50)
        h4_range_pos = h4_data.get("range_position", 0.5)
        
        # Check 1H confirmation
        h1_data = structure.get("entry", {})
        h1_volume = h1_data.get("volume", 1.0)
        
        # Liquidity confirmation
        imbalance = liquidity.get("imbalance", 0)
        whale_activity = liquidity.get("whale_activity", False)
        
        # LONG SETUP
        if "UP" in daily_trend:
            # Pullback to support in uptrend
            if (h4_rsi < 45 and  # Oversold on pullback
                h4_range_pos < 0.4 and  # Near support
                h4_momentum != "BEARISH" and  # Not strong bearish
                h1_volume > self.min_volume_spike and  # Volume coming in
                imbalance > self.min_imbalance):  # Buying pressure
                
                return "LONG_PULLBACK"
            
            # Breakout setup
            elif (h4_range_pos > 0.7 and  # Near resistance
                  h4_momentum == "BULLISH" and  # Strong momentum
                  h1_volume > self.min_volume_spike * 1.5 and  # High volume
                  imbalance > self.min_imbalance * 2 and  # Strong buying
                  whale_activity):  # Whale support
                
                return "LONG_BREAKOUT"
        
        # SHORT SETUP
        elif "DOWN" in daily_trend:
            # Pullback to resistance in downtrend
            if (h4_rsi > 55 and  # Overbought on pullback
                h4_range_pos > 0.6 and  # Near resistance
                h4_momentum != "BULLISH" and  # Not strong bullish
                h1_volume > self.min_volume_spike and  # Volume coming in
                imbalance < -self.min_imbalance):  # Selling pressure
                
                return "SHORT_PULLBACK"
            
            # Breakdown setup
            elif (h4_range_pos < 0.3 and  # Near support
                  h4_momentum == "BEARISH" and  # Strong momentum
                  h1_volume > self.min_volume_spike * 1.5 and  # High volume
                  imbalance < -self.min_imbalance * 2 and  # Strong selling
                  whale_activity):  # Whale distribution
                
                return "SHORT_BREAKDOWN"
        
        return None
    
    async def generate_swing_signal(self, symbol: str) -> Optional[Dict]:
        """
        Generate swing trading signal
        """
        # Get market structure
        structure = await self.get_market_structure(symbol)
        
        # Get liquidity data
        liquidity = await self.get_liquidity_edge(symbol)
        
        # Identify setup
        setup = self.identify_swing_setup(structure, liquidity)
        
        if not setup:
            return None
        
        # Get current price
        async with httpx.AsyncClient() as client:
            ticker = await client.get(
                f"{self.binance_spot}/ticker/price",
                params={"symbol": symbol}
            )
            current_price = float(ticker.json()["price"])
        
        # Calculate entry, stop, and targets based on setup
        signal = self.calculate_trade_levels(
            setup, current_price, structure, liquidity
        )
        
        if not signal:
            return None
        
        # Add metadata
        signal.update({
            "symbol": symbol,
            "setup_type": setup,
            "timestamp": datetime.now().isoformat(),
            "market_structure": structure,
            "liquidity_data": liquidity,
            "confidence": self.calculate_confidence(setup, structure, liquidity)
        })
        
        return signal
    
    def calculate_trade_levels(self, setup: str, current_price: float, 
                              structure: Dict, liquidity: Dict) -> Optional[Dict]:
        """
        Calculate entry, stop loss, and take profit levels
        """
        h4_data = structure.get("swing", {})
        h1_data = structure.get("entry", {})
        
        support = h4_data.get("support", current_price * 0.98)
        resistance = h4_data.get("resistance", current_price * 1.02)
        atr = h1_data.get("volatility", 2.0) / 100 * current_price  # ATR in price
        
        # Get liquidity levels
        support_levels = liquidity.get("support_levels", [])
        resistance_levels = liquidity.get("resistance_levels", [])
        
        if "LONG" in setup:
            # Entry
            if "PULLBACK" in setup:
                # Enter near support
                entry_price = current_price
                if support_levels:
                    nearest_support = min(support_levels, 
                                         key=lambda x: abs(x['price'] - current_price))
                    entry_price = nearest_support['price'] * 1.002  # Just above support
            else:  # BREAKOUT
                entry_price = current_price * 1.001  # Quick entry on breakout
            
            # Stop loss - below support or ATR
            stop_loss = max(support * 0.995, entry_price - (atr * 1.5))
            stop_loss = min(stop_loss, entry_price * (1 - self.stop_loss_pct))
            
            # Take profits - multiple targets
            tp1 = entry_price * 1.02  # 2% quick profit
            tp2 = entry_price * 1.035  # 3.5% medium target
            tp3 = min(resistance * 0.995, entry_price * 1.05)  # 5% or resistance
            
            direction = "LONG"
            
        else:  # SHORT
            # Entry
            if "PULLBACK" in setup:
                # Enter near resistance
                entry_price = current_price
                if resistance_levels:
                    nearest_resistance = min(resistance_levels,
                                           key=lambda x: abs(x['price'] - current_price))
                    entry_price = nearest_resistance['price'] * 0.998  # Just below resistance
            else:  # BREAKDOWN
                entry_price = current_price * 0.999  # Quick entry on breakdown
            
            # Stop loss - above resistance or ATR
            stop_loss = min(resistance * 1.005, entry_price + (atr * 1.5))
            stop_loss = max(stop_loss, entry_price * (1 + self.stop_loss_pct))
            
            # Take profits - multiple targets
            tp1 = entry_price * 0.98  # 2% quick profit
            tp2 = entry_price * 0.965  # 3.5% medium target
            tp3 = max(support * 1.005, entry_price * 0.95)  # 5% or support
            
            direction = "SHORT"
        
        # Calculate risk/reward
        risk = abs(entry_price - stop_loss) / entry_price
        reward1 = abs(tp1 - entry_price) / entry_price
        reward2 = abs(tp2 - entry_price) / entry_price
        reward3 = abs(tp3 - entry_price) / entry_price
        
        rr_ratio = reward2 / risk if risk > 0 else 0
        
        # Validate minimum requirements
        if rr_ratio < self.min_rr_ratio:
            return None
        
        # Calculate position size
        risk_amount = self.capital * self.risk_per_trade
        position_value = (risk_amount / risk) * self.leverage
        position_size = position_value / entry_price
        
        return {
            "direction": direction,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit_1": tp1,
            "take_profit_2": tp2,
            "take_profit_3": tp3,
            "position_size": position_size,
            "position_value": position_value,
            "risk_pct": risk * 100,
            "reward_pct_1": reward1 * 100,
            "reward_pct_2": reward2 * 100,
            "reward_pct_3": reward3 * 100,
            "rr_ratio": rr_ratio
        }
    
    def calculate_confidence(self, setup: str, structure: Dict, liquidity: Dict) -> str:
        """
        Calculate signal confidence
        """
        score = 0
        
        # Trend alignment
        daily_trend = structure.get("macro", {}).get("trend", "")
        if "STRONG" in daily_trend:
            score += 2
        elif "WEAK" in daily_trend:
            score += 1
        
        # Momentum confirmation
        h4_momentum = structure.get("swing", {}).get("momentum", "")
        if ("LONG" in setup and h4_momentum == "BULLISH") or \
           ("SHORT" in setup and h4_momentum == "BEARISH"):
            score += 2
        
        # Volume confirmation
        h1_volume = structure.get("entry", {}).get("volume", 1.0)
        if h1_volume > 2.0:
            score += 2
        elif h1_volume > 1.5:
            score += 1
        
        # Liquidity confirmation
        imbalance = abs(liquidity.get("imbalance", 0))
        if imbalance > 30:
            score += 2
        elif imbalance > 20:
            score += 1
        
        # Whale activity
        if liquidity.get("whale_activity", False):
            score += 1
        
        # Determine confidence
        if score >= 7:
            return "HIGH"
        elif score >= 5:
            return "MEDIUM"
        else:
            return "LOW"
    
    async def scan_opportunities(self, symbols: List[str]) -> List[Dict]:
        """
        Scan multiple symbols for swing opportunities
        """
        opportunities = []
        
        for symbol in symbols:
            logger.info(f"Scanning {symbol}...")
            signal = await self.generate_swing_signal(symbol)
            
            if signal:
                opportunities.append(signal)
        
        # Sort by confidence and R/R ratio
        opportunities.sort(key=lambda x: (
            {"HIGH": 3, "MEDIUM": 2, "LOW": 1}[x["confidence"]],
            x["rr_ratio"]
        ), reverse=True)
        
        return opportunities

# Test function
async def test_swing_system():
    """
    Test the swing trading system
    """
    system = SwingTradingSystem(capital=220)
    
    # Symbols to scan
    symbols = ["SOLUSDT", "BNBUSDT", "ETHUSDT", "BTCUSDT", "ADAUSDT"]
    
    print("🎯 SWING TRADING SYSTEM")
    print("="*60)
    print(f"Capital: ${system.capital}")
    print(f"Risk per trade: {system.risk_per_trade*100}%")
    print(f"Target: {system.min_profit_target*100}%-{system.max_profit_target*100}%")
    print(f"Scanning {len(symbols)} symbols...")
    print("-"*60)
    
    opportunities = await system.scan_opportunities(symbols)
    
    if opportunities:
        print(f"\n📊 Found {len(opportunities)} opportunities:\n")
        
        for i, opp in enumerate(opportunities[:3], 1):  # Show top 3
            print(f"#{i} {opp['symbol']} - {opp['setup_type']}")
            print(f"   Direction: {opp['direction']}")
            print(f"   Entry: ${opp['entry_price']:.2f}")
            print(f"   Stop: ${opp['stop_loss']:.2f} (-{opp['risk_pct']:.2f}%)")
            print(f"   TP1: ${opp['take_profit_1']:.2f} (+{opp['reward_pct_1']:.2f}%)")
            print(f"   TP2: ${opp['take_profit_2']:.2f} (+{opp['reward_pct_2']:.2f}%)")
            print(f"   TP3: ${opp['take_profit_3']:.2f} (+{opp['reward_pct_3']:.2f}%)")
            print(f"   R/R: 1:{opp['rr_ratio']:.2f}")
            print(f"   Position: {opp['position_size']:.4f} units")
            print(f"   Confidence: {opp['confidence']}")
            print()
    else:
        print("\n❌ No swing opportunities found currently")
        print("Market conditions may not be favorable for swing trading")
    
    print("="*60)
    print("✅ Scan complete!")

if __name__ == "__main__":
    asyncio.run(test_swing_system())