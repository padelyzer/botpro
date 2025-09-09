#!/usr/bin/env python3
"""
Backtest Completo - Todos los 6 pares con sus estrategias específicas
BTC, ETH, SOL, BNB, ADA, DOGE
"""

import asyncio
import httpx
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

# Configuración completa de todos los pares
PAIR_CONFIG = {
    'BTCUSDT': {
        '15m': {'min_change_pct': 1.5, 'rsi_oversold': 38, 'rsi_overbought': 62, 'min_volume_ratio': 1.2, 'max_volatility': 8, 'atr_multiplier': 1.8, 'min_confidence': 60, 'trend_filter_strength': 0.8, 'use_trend_following': True},
        '1h': {'min_change_pct': 2.0, 'rsi_oversold': 35, 'rsi_overbought': 65, 'min_volume_ratio': 1.15, 'max_volatility': 9, 'atr_multiplier': 2.0, 'min_confidence': 58, 'trend_filter_strength': 1.0, 'use_trend_following': True},
        '4h': {'min_change_pct': 2.5, 'rsi_oversold': 32, 'rsi_overbought': 68, 'min_volume_ratio': 1.1, 'max_volatility': 10, 'atr_multiplier': 2.2, 'min_confidence': 55, 'trend_filter_strength': 1.2, 'use_trend_following': True}
    },
    'ETHUSDT': {
        '15m': {'min_change_pct': 2.0, 'rsi_oversold': 35, 'rsi_overbought': 65, 'min_volume_ratio': 1.1, 'max_volatility': 11, 'atr_multiplier': 2.0, 'min_confidence': 55, 'trend_filter_strength': 0.6, 'use_mean_reversion': True},
        '1h': {'min_change_pct': 2.5, 'rsi_oversold': 33, 'rsi_overbought': 67, 'min_volume_ratio': 1.15, 'max_volatility': 12, 'atr_multiplier': 2.2, 'min_confidence': 57, 'trend_filter_strength': 0.8, 'use_mean_reversion': True},
        '4h': {'min_change_pct': 3.0, 'rsi_oversold': 30, 'rsi_overbought': 70, 'min_volume_ratio': 1.2, 'max_volatility': 13, 'atr_multiplier': 2.5, 'min_confidence': 60, 'trend_filter_strength': 1.0, 'use_mean_reversion': True}
    },
    'SOLUSDT': {
        '15m': {'min_change_pct': 2.5, 'rsi_oversold': 32, 'rsi_overbought': 68, 'min_volume_ratio': 1.0, 'max_volatility': 15, 'atr_multiplier': 2.3, 'min_confidence': 52, 'trend_filter_strength': 0.4, 'use_momentum': True},
        '1h': {'min_change_pct': 3.0, 'rsi_oversold': 30, 'rsi_overbought': 70, 'min_volume_ratio': 1.05, 'max_volatility': 16, 'atr_multiplier': 2.5, 'min_confidence': 55, 'trend_filter_strength': 0.5, 'use_momentum': True},
        '4h': {'min_change_pct': 3.5, 'rsi_oversold': 28, 'rsi_overbought': 72, 'min_volume_ratio': 1.1, 'max_volatility': 17, 'atr_multiplier': 2.8, 'min_confidence': 58, 'trend_filter_strength': 0.7, 'use_momentum': True}
    },
    'BNBUSDT': {
        '15m': {'min_change_pct': 1.8, 'rsi_oversold': 36, 'rsi_overbought': 64, 'min_volume_ratio': 1.15, 'max_volatility': 9, 'atr_multiplier': 1.9, 'min_confidence': 58, 'trend_filter_strength': 0.7, 'use_range_trading': True},
        '1h': {'min_change_pct': 2.2, 'rsi_oversold': 34, 'rsi_overbought': 66, 'min_volume_ratio': 1.2, 'max_volatility': 10, 'atr_multiplier': 2.1, 'min_confidence': 60, 'trend_filter_strength': 0.9, 'use_range_trading': True},
        '4h': {'min_change_pct': 2.8, 'rsi_oversold': 31, 'rsi_overbought': 69, 'min_volume_ratio': 1.25, 'max_volatility': 11, 'atr_multiplier': 2.3, 'min_confidence': 62, 'trend_filter_strength': 1.1, 'use_range_trading': True}
    },
    'ADAUSDT': {
        '15m': {'min_change_pct': 2.2, 'rsi_oversold': 34, 'rsi_overbought': 66, 'min_volume_ratio': 1.1, 'max_volatility': 13, 'atr_multiplier': 2.1, 'min_confidence': 54, 'trend_filter_strength': 0.5, 'use_mean_reversion': True},
        '1h': {'min_change_pct': 2.8, 'rsi_oversold': 32, 'rsi_overbought': 68, 'min_volume_ratio': 1.15, 'max_volatility': 14, 'atr_multiplier': 2.3, 'min_confidence': 56, 'trend_filter_strength': 0.7, 'use_mean_reversion': True},
        '4h': {'min_change_pct': 3.2, 'rsi_oversold': 30, 'rsi_overbought': 70, 'min_volume_ratio': 1.2, 'max_volatility': 15, 'atr_multiplier': 2.6, 'min_confidence': 59, 'trend_filter_strength': 0.9, 'use_mean_reversion': True}
    },
    'DOGEUSDT': {
        '15m': {'min_change_pct': 3.0, 'rsi_oversold': 30, 'rsi_overbought': 70, 'min_volume_ratio': 0.9, 'max_volatility': 20, 'atr_multiplier': 3.0, 'min_confidence': 50, 'trend_filter_strength': 0.3, 'use_momentum': True, 'extra_caution': True},
        '1h': {'min_change_pct': 3.5, 'rsi_oversold': 28, 'rsi_overbought': 72, 'min_volume_ratio': 0.95, 'max_volatility': 22, 'atr_multiplier': 3.2, 'min_confidence': 52, 'trend_filter_strength': 0.4, 'use_momentum': True, 'extra_caution': True},
        '4h': {'min_change_pct': 4.0, 'rsi_oversold': 25, 'rsi_overbought': 75, 'min_volume_ratio': 1.0, 'max_volatility': 25, 'atr_multiplier': 3.5, 'min_confidence': 55, 'trend_filter_strength': 0.5, 'use_momentum': True, 'extra_caution': True}
    }
}

INITIAL_CAPITAL = 220.0
MAX_RISK_PER_TRADE = 0.02
DEFAULT_LEVERAGE = 3
COMMISSION = 0.0004

class CompletePairBacktest:
    """Backtest completo de todos los pares"""
    
    def __init__(self, capital: float = INITIAL_CAPITAL):
        self.initial_capital = capital
        self.capital = capital
        self.trades = []
        self.current_position = None
        self.max_drawdown = 0
        self.peak_capital = capital
        
    async def fetch_historical_data(self, symbol: str, interval: str, days: int = 90):
        """Obtiene datos históricos con reintentos"""
        
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        all_data = []
        current_start = start_time
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            while current_start < end_time:
                try:
                    response = await client.get(
                        'https://fapi.binance.com/fapi/v1/klines',
                        params={
                            'symbol': symbol,
                            'interval': interval,
                            'startTime': current_start,
                            'endTime': end_time,
                            'limit': 1500
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if not data:
                            break
                        all_data.extend(data)
                        current_start = data[-1][0] + 1
                    else:
                        print(f"Error {response.status_code} fetching {symbol} {interval}")
                        break
                        
                except Exception as e:
                    print(f"Exception fetching {symbol} {interval}: {e}")
                    break
                
                # Pequeña pausa para no sobrecargar API
                await asyncio.sleep(0.1)
        
        return all_data
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula todos los indicadores"""
        
        # Básicos
        df['change_pct'] = df['close'].pct_change() * 100
        df['range_position'] = (df['close'] - df['low']) / (df['high'] - df['low'] + 0.00001)
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        df['atr'] = ranges.max(axis=1).rolling(14).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 0.00001)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # EMAs
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        # MACD
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(20).mean()
        df['bb_std'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * 2)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * 2)
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'] + 0.00001)
        
        # Volatilidad y volumen
        df['volatility'] = ((df['high'] - df['low']) / df['close']) * 100
        df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        df['volume_trend'] = df['volume'].rolling(5).mean() / df['volume'].rolling(20).mean()
        
        # Tendencia
        df['trend_strength'] = abs(df['ema_20'] - df['ema_50']) / df['close'] * 100
        df['is_uptrend'] = df['ema_20'] > df['ema_50']
        
        return df
    
    def generate_strategy_signal(self, row, prev_row, symbol: str, interval: str):
        """Genera señal específica por estrategia del par"""
        
        config = PAIR_CONFIG[symbol][interval]
        
        # Verificar datos válidos
        if pd.isna(row['atr']) or pd.isna(row['rsi']):
            return None
        
        # Filtro de volatilidad
        if row['volatility'] > config['max_volatility']:
            return None
        
        signal = None
        confidence = 0
        
        # TREND FOLLOWING (BTC)
        if config.get('use_trend_following'):
            if (row['is_uptrend'] and row['macd_histogram'] > 0 and
                row['change_pct'] > config['min_change_pct'] * 0.5 and
                row['rsi'] < 70 and row['rsi'] > 45):
                
                confidence = config['min_confidence'] + 10
                if row['macd_histogram'] > prev_row['macd_histogram']:
                    confidence += 5
                if row['volume_ratio'] > config['min_volume_ratio']:
                    confidence += 5
                
                signal = {'type': 'LONG', 'strategy': 'TREND_FOLLOWING', 'confidence': min(confidence, 85)}
            
            elif (not row['is_uptrend'] and row['macd_histogram'] < 0 and
                  row['change_pct'] < -config['min_change_pct'] * 0.5 and
                  row['rsi'] > 30 and row['rsi'] < 55):
                
                confidence = config['min_confidence'] + 10
                if row['macd_histogram'] < prev_row['macd_histogram']:
                    confidence += 5
                if row['volume_ratio'] > config['min_volume_ratio']:
                    confidence += 5
                
                signal = {'type': 'SHORT', 'strategy': 'TREND_FOLLOWING', 'confidence': min(confidence, 85)}
        
        # MEAN REVERSION (ETH, ADA)
        elif config.get('use_mean_reversion'):
            if (row['change_pct'] < -config['min_change_pct'] and
                row['rsi'] < config['rsi_oversold'] and
                row['bb_position'] < 0.2 and
                row['volume_ratio'] > config['min_volume_ratio']):
                
                confidence = config['min_confidence']
                if row['rsi'] < config['rsi_oversold'] - 5:
                    confidence += 15
                if row['bb_position'] < 0.1:
                    confidence += 10
                
                signal = {'type': 'LONG', 'strategy': 'MEAN_REVERSION', 'confidence': min(confidence, 80)}
            
            elif (row['change_pct'] > config['min_change_pct'] and
                  row['rsi'] > config['rsi_overbought'] and
                  row['bb_position'] > 0.8 and
                  row['volume_ratio'] > config['min_volume_ratio']):
                
                confidence = config['min_confidence']
                if row['rsi'] > config['rsi_overbought'] + 5:
                    confidence += 15
                if row['bb_position'] > 0.9:
                    confidence += 10
                
                signal = {'type': 'SHORT', 'strategy': 'MEAN_REVERSION', 'confidence': min(confidence, 80)}
        
        # MOMENTUM (SOL, DOGE)
        elif config.get('use_momentum'):
            if (row['change_pct'] > config['min_change_pct'] and
                row['volume_ratio'] > config['min_volume_ratio'] and
                row['macd_histogram'] > prev_row['macd_histogram'] and
                row['rsi'] > 50 and row['rsi'] < config['rsi_overbought'] and
                row['volume_trend'] > 1.2):
                
                confidence = config['min_confidence']
                if row['volume_trend'] > 1.5:
                    confidence += 10
                if row['change_pct'] > config['min_change_pct'] * 1.5:
                    confidence += 8
                
                # Extra caution para DOGE
                if config.get('extra_caution'):
                    confidence = min(confidence, 70)
                
                signal = {'type': 'LONG', 'strategy': 'MOMENTUM', 'confidence': confidence}
            
            elif (row['change_pct'] < -config['min_change_pct'] and
                  row['volume_ratio'] > config['min_volume_ratio'] and
                  row['macd_histogram'] < prev_row['macd_histogram'] and
                  row['rsi'] < 50 and row['rsi'] > config['rsi_oversold'] and
                  row['volume_trend'] > 1.2):
                
                confidence = config['min_confidence']
                if row['volume_trend'] > 1.5:
                    confidence += 10
                if abs(row['change_pct']) > config['min_change_pct'] * 1.5:
                    confidence += 8
                
                if config.get('extra_caution'):
                    confidence = min(confidence, 70)
                
                signal = {'type': 'SHORT', 'strategy': 'MOMENTUM', 'confidence': confidence}
        
        # RANGE TRADING (BNB)
        elif config.get('use_range_trading'):
            if (row['bb_position'] < 0.2 and
                row['rsi'] < config['rsi_oversold'] + 5 and
                row['change_pct'] < -config['min_change_pct'] * 0.7):
                
                confidence = config['min_confidence']
                if row['bb_position'] < 0.1:
                    confidence += 10
                if row['rsi'] < config['rsi_oversold']:
                    confidence += 8
                
                signal = {'type': 'LONG', 'strategy': 'RANGE_TRADING', 'confidence': confidence}
            
            elif (row['bb_position'] > 0.8 and
                  row['rsi'] > config['rsi_overbought'] - 5 and
                  row['change_pct'] > config['min_change_pct'] * 0.7):
                
                confidence = config['min_confidence']
                if row['bb_position'] > 0.9:
                    confidence += 10
                if row['rsi'] > config['rsi_overbought']:
                    confidence += 8
                
                signal = {'type': 'SHORT', 'strategy': 'RANGE_TRADING', 'confidence': confidence}
        
        # Solo retornar si cumple confianza mínima
        if signal and signal['confidence'] >= config['min_confidence']:
            signal.update({
                'entry_price': row['close'],
                'atr': row['atr'],
                'volatility': row['volatility']
            })
            return signal
        
        return None
    
    def calculate_stops(self, signal, config):
        """Calcula stops específicos"""
        
        atr_mult = config['atr_multiplier']
        
        # Ajustes por volatilidad y estrategia
        if signal['volatility'] > config['max_volatility'] * 0.8:
            atr_mult += 0.3
        
        if signal['strategy'] in ['MOMENTUM', 'RANGE_TRADING']:
            atr_mult *= 1.1
        
        stop_distance = signal['atr'] * atr_mult
        
        if signal['type'] == 'LONG':
            stop_loss = signal['entry_price'] - stop_distance
            tp_ratio = 2.0 if signal['strategy'] == 'MOMENTUM' else 1.5
            take_profit = signal['entry_price'] + (stop_distance * tp_ratio)
        else:
            stop_loss = signal['entry_price'] + stop_distance
            tp_ratio = 2.0 if signal['strategy'] == 'MOMENTUM' else 1.5
            take_profit = signal['entry_price'] - (stop_distance * tp_ratio)
        
        return stop_loss, take_profit
    
    def run_backtest(self, df: pd.DataFrame, symbol: str, interval: str):
        """Ejecuta backtest"""
        
        config = PAIR_CONFIG[symbol][interval]
        df = self.calculate_indicators(df)
        
        for i in range(50, len(df) - 1):
            
            # Drawdown tracking
            if self.capital > self.peak_capital:
                self.peak_capital = self.capital
            
            drawdown = ((self.peak_capital - self.capital) / self.peak_capital) * 100
            if drawdown > self.max_drawdown:
                self.max_drawdown = drawdown
            
            # Buscar señal si no hay posición
            if self.current_position is None:
                signal = self.generate_strategy_signal(df.iloc[i], df.iloc[i-1], symbol, interval)
                
                if signal:
                    stop_loss, take_profit = self.calculate_stops(signal, config)
                    
                    risk_amount = self.capital * MAX_RISK_PER_TRADE
                    position_size = (risk_amount * DEFAULT_LEVERAGE) / signal['entry_price']
                    commission = position_size * signal['entry_price'] * COMMISSION
                    
                    self.current_position = {
                        'type': signal['type'],
                        'strategy': signal['strategy'],
                        'entry_price': signal['entry_price'],
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'position_size': position_size,
                        'entry_time': df.iloc[i]['timestamp'],
                        'confidence': signal['confidence'],
                        'entry_index': i
                    }
                    
                    self.capital -= commission
            
            # Verificar salida si hay posición
            elif self.current_position:
                current_price = df.iloc[i]['close']
                exit_price = None
                exit_reason = None
                
                if self.current_position['type'] == 'LONG':
                    if current_price <= self.current_position['stop_loss']:
                        exit_price = self.current_position['stop_loss']
                        exit_reason = 'Stop Loss'
                    elif current_price >= self.current_position['take_profit']:
                        exit_price = self.current_position['take_profit']
                        exit_reason = 'Take Profit'
                else:
                    if current_price >= self.current_position['stop_loss']:
                        exit_price = self.current_position['stop_loss']
                        exit_reason = 'Stop Loss'
                    elif current_price <= self.current_position['take_profit']:
                        exit_price = self.current_position['take_profit']
                        exit_reason = 'Take Profit'
                
                # Time exit
                bars_elapsed = i - self.current_position['entry_index']
                max_bars = 30 if interval == '15m' else (15 if interval == '1h' else 10)
                
                if not exit_price and bars_elapsed > max_bars:
                    exit_price = current_price
                    exit_reason = 'Time Exit'
                
                if exit_price:
                    # Calcular PnL
                    if self.current_position['type'] == 'LONG':
                        pnl_pct = ((exit_price - self.current_position['entry_price']) / 
                                  self.current_position['entry_price']) * DEFAULT_LEVERAGE
                    else:
                        pnl_pct = ((self.current_position['entry_price'] - exit_price) / 
                                  self.current_position['entry_price']) * DEFAULT_LEVERAGE
                    
                    pnl = self.capital * pnl_pct
                    commission = self.current_position['position_size'] * exit_price * COMMISSION
                    
                    self.capital += pnl - commission
                    
                    self.trades.append({
                        'symbol': symbol,
                        'interval': interval,
                        'strategy': self.current_position['strategy'],
                        'type': self.current_position['type'],
                        'entry_price': self.current_position['entry_price'],
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct * 100,
                        'exit_reason': exit_reason,
                        'confidence': self.current_position['confidence'],
                        'bars_held': bars_elapsed
                    })
                    
                    self.current_position = None
    
    def get_statistics(self) -> dict:
        """Estadísticas completas"""
        
        if not self.trades:
            return {
                'total_trades': 0, 'winning_trades': 0, 'losing_trades': 0,
                'win_rate': 0, 'total_return': 0, 'final_capital': self.capital,
                'max_drawdown': 0, 'by_strategy': {}
            }
        
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] <= 0]
        
        total_return = ((self.capital - self.initial_capital) / self.initial_capital) * 100
        
        # Por estrategia
        strategy_stats = {}
        for trade in self.trades:
            strategy = trade['strategy']
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {'trades': 0, 'wins': 0, 'total_pnl': 0}
            
            strategy_stats[strategy]['trades'] += 1
            strategy_stats[strategy]['total_pnl'] += trade['pnl']
            if trade['pnl'] > 0:
                strategy_stats[strategy]['wins'] += 1
        
        for strategy in strategy_stats:
            trades = strategy_stats[strategy]['trades']
            wins = strategy_stats[strategy]['wins']
            strategy_stats[strategy]['win_rate'] = (wins / trades * 100) if trades > 0 else 0
        
        return {
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': (len(winning_trades) / len(self.trades)) * 100 if self.trades else 0,
            'total_return': total_return,
            'final_capital': self.capital,
            'max_drawdown': self.max_drawdown,
            'by_strategy': strategy_stats
        }

async def main():
    """Backtest completo de todos los 6 pares"""
    
    print("="*80)
    print("BACKTEST COMPLETO - TODOS LOS PARES")
    print("="*80)
    print(f"Capital inicial: ${INITIAL_CAPITAL}")
    print(f"Pares: BTC, ETH, SOL, BNB, ADA, DOGE")
    print(f"Estrategias: Trend Following, Mean Reversion, Momentum, Range Trading")
    print("="*80)
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'ADAUSDT', 'DOGEUSDT']
    intervals = ['15m', '1h', '4h']
    
    all_results = []
    
    for symbol in symbols:
        strategy_name = "TREND_FOLLOWING" if PAIR_CONFIG[symbol]['1h'].get('use_trend_following') else \
                      "MEAN_REVERSION" if PAIR_CONFIG[symbol]['1h'].get('use_mean_reversion') else \
                      "MOMENTUM" if PAIR_CONFIG[symbol]['1h'].get('use_momentum') else \
                      "RANGE_TRADING" if PAIR_CONFIG[symbol]['1h'].get('use_range_trading') else "UNKNOWN"
        
        print(f"\n🔸 {symbol} - Estrategia: {strategy_name}")
        print("-" * 60)
        
        for interval in intervals:
            print(f"Fetching {symbol} {interval} data...")
            
            backtest = CompletePairBacktest()
            data = await backtest.fetch_historical_data(symbol, interval, 90)
            
            if data and len(data) > 100:
                df = pd.DataFrame(data, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 
                    'volume', 'close_time', 'quote_volume', 'trades',
                    'taker_buy_volume', 'taker_buy_quote', 'ignore'
                ])
                
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = df[col].astype(float)
                
                backtest.run_backtest(df, symbol, interval)
                stats = backtest.get_statistics()
                
                print(f"  {interval}: {stats['total_trades']} trades, {stats['win_rate']:.1f}% WR, {stats['total_return']:.2f}% return")
                
                all_results.append({
                    'symbol': symbol,
                    'interval': interval,
                    'strategy': strategy_name,
                    **stats
                })
            else:
                print(f"  {interval}: No data or insufficient data")
                all_results.append({
                    'symbol': symbol, 'interval': interval, 'strategy': strategy_name,
                    'total_trades': 0, 'win_rate': 0, 'total_return': 0,
                    'final_capital': INITIAL_CAPITAL, 'max_drawdown': 0
                })
    
    # Análisis final
    print("\n" + "="*80)
    print("RESUMEN POR ESTRATEGIA")
    print("="*80)
    
    strategy_summary = {}
    for result in all_results:
        strat = result['strategy']
        if strat not in strategy_summary:
            strategy_summary[strat] = []
        strategy_summary[strat].append(result)
    
    for strategy, results in strategy_summary.items():
        results_with_trades = [r for r in results if r['total_trades'] > 0]
        
        if results_with_trades:
            avg_trades = np.mean([r['total_trades'] for r in results_with_trades])
            avg_wr = np.mean([r['win_rate'] for r in results_with_trades])
            avg_return = np.mean([r['total_return'] for r in results_with_trades])
            
            print(f"\n{strategy}:")
            print(f"  Configuraciones con trades: {len(results_with_trades)}/{len(results)}")
            print(f"  Promedio trades: {avg_trades:.1f}")
            print(f"  Promedio win rate: {avg_wr:.1f}%")
            print(f"  Promedio return: {avg_return:.2f}%")
            
            # Top performers
            top_performers = sorted(results_with_trades, key=lambda x: x['win_rate'], reverse=True)[:3]
            print(f"  Top performers:")
            for i, perf in enumerate(top_performers, 1):
                print(f"    {i}. {perf['symbol']} {perf['interval']}: {perf['win_rate']:.1f}% WR, {perf['total_return']:.2f}%")
        else:
            print(f"\n{strategy}: No trades generated")
    
    # Guardar resultados
    df_results = pd.DataFrame(all_results)
    df_results.to_csv('complete_pair_backtest_results.csv', index=False)
    print(f"\n✅ Resultados completos guardados en complete_pair_backtest_results.csv")

if __name__ == "__main__":
    asyncio.run(main())