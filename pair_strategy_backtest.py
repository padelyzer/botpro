#!/usr/bin/env python3
"""
Backtest del Sistema Optimizado por Par
Prueba estrategias específicas: Trend Following, Mean Reversion, Momentum, Range Trading
"""

import asyncio
import httpx
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

# Misma configuración que pair_optimized_system.py
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
    }
}

INITIAL_CAPITAL = 220.0
MAX_RISK_PER_TRADE = 0.02
DEFAULT_LEVERAGE = 3
COMMISSION = 0.0004

class PairStrategyBacktest:
    """Backtest con estrategias específicas por par"""
    
    def __init__(self, capital: float = INITIAL_CAPITAL):
        self.initial_capital = capital
        self.capital = capital
        self.trades = []
        self.current_position = None
        self.max_drawdown = 0
        self.peak_capital = capital
        
    async def fetch_historical_data(self, symbol: str, interval: str, days: int = 90):
        """Obtiene datos históricos"""
        
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        all_data = []
        current_start = start_time
        
        async with httpx.AsyncClient() as client:
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
                        break
                        
                except Exception as e:
                    print(f"Error fetching data for {symbol}: {e}")
                    break
        
        return all_data
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula todos los indicadores para todas las estrategias"""
        
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
        
        # MACD para momentum y trend following
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands para mean reversion y range trading
        df['bb_middle'] = df['close'].rolling(20).mean()
        df['bb_std'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * 2)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * 2)
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'] + 0.00001)
        
        # Volatilidad
        df['volatility'] = ((df['high'] - df['low']) / df['close']) * 100
        
        # Volumen
        df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        df['volume_trend'] = df['volume'].rolling(5).mean() / df['volume'].rolling(20).mean()
        
        # Tendencia
        df['trend_strength'] = abs(df['ema_20'] - df['ema_50']) / df['close'] * 100
        df['is_uptrend'] = df['ema_20'] > df['ema_50']
        
        return df
    
    def generate_strategy_signal(self, row, prev_row, symbol: str, interval: str):
        """Genera señal usando la estrategia específica del par"""
        
        config = PAIR_CONFIG[symbol][interval]
        
        # Verificar datos válidos
        if pd.isna(row['atr']) or pd.isna(row['rsi']):
            return None
        
        # Filtro de volatilidad
        if row['volatility'] > config['max_volatility']:
            return None
        
        signal = None
        confidence = 0
        
        # ESTRATEGIA 1: TREND FOLLOWING (BTC)
        if config.get('use_trend_following'):
            # Long en tendencia alcista con momentum
            if (row['is_uptrend'] and 
                row['macd_histogram'] > 0 and
                row['change_pct'] > config['min_change_pct'] * 0.5 and
                row['rsi'] < 70 and row['rsi'] > 45):
                
                confidence = config['min_confidence'] + 10
                if row['macd_histogram'] > prev_row['macd_histogram']:  # Momentum creciente
                    confidence += 5
                if row['volume_ratio'] > config['min_volume_ratio']:
                    confidence += 5
                
                signal = {
                    'type': 'LONG',
                    'strategy': 'TREND_FOLLOWING',
                    'confidence': min(confidence, 85)
                }
            
            # Short en tendencia bajista con momentum
            elif (not row['is_uptrend'] and 
                  row['macd_histogram'] < 0 and
                  row['change_pct'] < -config['min_change_pct'] * 0.5 and
                  row['rsi'] > 30 and row['rsi'] < 55):
                
                confidence = config['min_confidence'] + 10
                if row['macd_histogram'] < prev_row['macd_histogram']:
                    confidence += 5
                if row['volume_ratio'] > config['min_volume_ratio']:
                    confidence += 5
                
                signal = {
                    'type': 'SHORT',
                    'strategy': 'TREND_FOLLOWING',
                    'confidence': min(confidence, 85)
                }
        
        # ESTRATEGIA 2: MEAN REVERSION (ETH, ADA)
        elif config.get('use_mean_reversion'):
            # Long en oversold con confirmación BB
            if (row['change_pct'] < -config['min_change_pct'] and
                row['rsi'] < config['rsi_oversold'] and
                row['bb_position'] < 0.2 and
                row['volume_ratio'] > config['min_volume_ratio']):
                
                confidence = config['min_confidence']
                if row['rsi'] < config['rsi_oversold'] - 5:
                    confidence += 15
                if row['bb_position'] < 0.1:
                    confidence += 10
                if row['volume_ratio'] > config['min_volume_ratio'] * 1.3:
                    confidence += 5
                
                signal = {
                    'type': 'LONG',
                    'strategy': 'MEAN_REVERSION',
                    'confidence': min(confidence, 80)
                }
            
            # Short en overbought con confirmación BB
            elif (row['change_pct'] > config['min_change_pct'] and
                  row['rsi'] > config['rsi_overbought'] and
                  row['bb_position'] > 0.8 and
                  row['volume_ratio'] > config['min_volume_ratio']):
                
                confidence = config['min_confidence']
                if row['rsi'] > config['rsi_overbought'] + 5:
                    confidence += 15
                if row['bb_position'] > 0.9:
                    confidence += 10
                if row['volume_ratio'] > config['min_volume_ratio'] * 1.3:
                    confidence += 5
                
                signal = {
                    'type': 'SHORT',
                    'strategy': 'MEAN_REVERSION',
                    'confidence': min(confidence, 80)
                }
        
        # ESTRATEGIA 3: MOMENTUM (SOL, DOGE)
        elif config.get('use_momentum'):
            # Long momentum breakout
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
                if row['macd_histogram'] > 0:
                    confidence += 5
                
                signal = {
                    'type': 'LONG',
                    'strategy': 'MOMENTUM',
                    'confidence': min(confidence, 75)
                }
            
            # Short momentum breakdown
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
                if row['macd_histogram'] < 0:
                    confidence += 5
                
                signal = {
                    'type': 'SHORT',
                    'strategy': 'MOMENTUM',
                    'confidence': min(confidence, 75)
                }
        
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
        """Calcula stops específicos por estrategia"""
        
        atr_mult = config['atr_multiplier']
        
        # Ajustar multiplicador según volatilidad y estrategia
        if signal['volatility'] > config['max_volatility'] * 0.8:
            atr_mult += 0.3
        
        # Estrategias de momentum necesitan stops más amplios
        if signal['strategy'] == 'MOMENTUM':
            atr_mult *= 1.1
        
        stop_distance = signal['atr'] * atr_mult
        
        if signal['type'] == 'LONG':
            stop_loss = signal['entry_price'] - stop_distance
            # Take profit según estrategia
            tp_ratio = 2.0 if signal['strategy'] == 'MOMENTUM' else 1.5
            take_profit = signal['entry_price'] + (stop_distance * tp_ratio)
        else:
            stop_loss = signal['entry_price'] + stop_distance
            tp_ratio = 2.0 if signal['strategy'] == 'MOMENTUM' else 1.5
            take_profit = signal['entry_price'] - (stop_distance * tp_ratio)
        
        return stop_loss, take_profit
    
    def run_backtest(self, df: pd.DataFrame, symbol: str, interval: str):
        """Ejecuta backtest con estrategia específica por par"""
        
        config = PAIR_CONFIG[symbol][interval]
        df = self.calculate_indicators(df)
        
        for i in range(50, len(df) - 1):
            
            # Actualizar drawdown
            if self.capital > self.peak_capital:
                self.peak_capital = self.capital
            
            drawdown = ((self.peak_capital - self.capital) / self.peak_capital) * 100
            if drawdown > self.max_drawdown:
                self.max_drawdown = drawdown
            
            # Si no hay posición, buscar señal
            if self.current_position is None:
                signal = self.generate_strategy_signal(df.iloc[i], df.iloc[i-1], symbol, interval)
                
                if signal:
                    # Calcular stops
                    stop_loss, take_profit = self.calculate_stops(signal, config)
                    
                    # Tamaño de posición
                    risk_amount = self.capital * MAX_RISK_PER_TRADE
                    position_size = (risk_amount * DEFAULT_LEVERAGE) / signal['entry_price']
                    
                    # Comisión
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
            
            # Si hay posición, verificar salida
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
                else:  # SHORT
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
        """Calcula estadísticas detalladas"""
        
        if not self.trades:
            return {
                'total_trades': 0, 'winning_trades': 0, 'losing_trades': 0,
                'win_rate': 0, 'avg_win': 0, 'avg_loss': 0, 'profit_factor': 0,
                'total_return': 0, 'final_capital': self.capital, 'max_drawdown': 0,
                'by_strategy': {}, 'by_exit_reason': {}
            }
        
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] <= 0]
        
        total_return = ((self.capital - self.initial_capital) / self.initial_capital) * 100
        
        # Estadísticas por estrategia
        strategy_stats = {}
        for trade in self.trades:
            strategy = trade['strategy']
            if strategy not in strategy_stats:
                strategy_stats[strategy] = {'trades': [], 'wins': 0, 'total': 0}
            
            strategy_stats[strategy]['trades'].append(trade)
            strategy_stats[strategy]['total'] += 1
            if trade['pnl'] > 0:
                strategy_stats[strategy]['wins'] += 1
        
        # Procesar stats por estrategia
        for strategy in strategy_stats:
            trades = strategy_stats[strategy]['trades']
            wins = strategy_stats[strategy]['wins']
            total = strategy_stats[strategy]['total']
            
            strategy_stats[strategy].update({
                'win_rate': (wins / total * 100) if total > 0 else 0,
                'avg_pnl': np.mean([t['pnl'] for t in trades]) if trades else 0,
                'total_pnl': sum([t['pnl'] for t in trades]) if trades else 0
            })
        
        # Stats por exit reason
        exit_stats = {}
        for trade in self.trades:
            reason = trade['exit_reason']
            if reason not in exit_stats:
                exit_stats[reason] = {'count': 0, 'wins': 0}
            exit_stats[reason]['count'] += 1
            if trade['pnl'] > 0:
                exit_stats[reason]['wins'] += 1
        
        return {
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': (len(winning_trades) / len(self.trades)) * 100 if self.trades else 0,
            'avg_win': np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0,
            'avg_loss': np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0,
            'profit_factor': (sum([t['pnl'] for t in winning_trades]) / 
                            abs(sum([t['pnl'] for t in losing_trades]))) if losing_trades else float('inf'),
            'total_return': total_return,
            'final_capital': self.capital,
            'max_drawdown': self.max_drawdown,
            'by_strategy': strategy_stats,
            'by_exit_reason': exit_stats,
            'avg_confidence': np.mean([t['confidence'] for t in self.trades]) if self.trades else 0
        }

async def main():
    """Ejecuta backtests por estrategia específica"""
    
    print("="*70)
    print("BACKTEST: SISTEMA OPTIMIZADO POR PAR")
    print("="*70)
    print(f"Capital inicial: ${INITIAL_CAPITAL}")
    print(f"Período: 90 días")
    print(f"Estrategias específicas:")
    print(f"  • BTC: TREND FOLLOWING")
    print(f"  • ETH: MEAN REVERSION") 
    print(f"  • SOL: MOMENTUM")
    print("="*70)
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    intervals = ['15m', '1h', '4h']
    
    all_results = []
    
    for symbol in symbols:
        print(f"\n📊 {symbol}:")
        print("-" * 50)
        
        for interval in intervals:
            backtest = PairStrategyBacktest()
            
            # Obtener datos
            data = await backtest.fetch_historical_data(symbol, interval, 90)
            
            if data:
                # Convertir a DataFrame
                df = pd.DataFrame(data, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 
                    'volume', 'close_time', 'quote_volume', 'trades',
                    'taker_buy_volume', 'taker_buy_quote', 'ignore'
                ])
                
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = df[col].astype(float)
                
                # Ejecutar backtest
                backtest.run_backtest(df, symbol, interval)
                
                # Obtener estadísticas
                stats = backtest.get_statistics()
                
                # Obtener estrategia principal del par
                config = PAIR_CONFIG[symbol][interval]
                strategy_name = "TREND_FOLLOWING" if config.get('use_trend_following') else \
                              "MEAN_REVERSION" if config.get('use_mean_reversion') else \
                              "MOMENTUM" if config.get('use_momentum') else "STANDARD"
                
                print(f"\n  {interval} - Estrategia: {strategy_name}")
                print(f"    Trades: {stats['total_trades']}")
                print(f"    Win Rate: {stats['win_rate']:.1f}%")
                print(f"    Return: {stats['total_return']:.2f}%")
                print(f"    Max DD: {stats['max_drawdown']:.2f}%")
                print(f"    Final Capital: ${stats['final_capital']:.2f}")
                
                # Detalles por estrategia
                if stats['by_strategy']:
                    for strat_name, strat_stats in stats['by_strategy'].items():
                        print(f"      {strat_name}: {strat_stats['total']} trades, {strat_stats['win_rate']:.1f}% WR")
                
                # Detalles por salida
                if stats['by_exit_reason']:
                    print(f"    Salidas:")
                    for reason, reason_stats in stats['by_exit_reason'].items():
                        wr = (reason_stats['wins'] / reason_stats['count'] * 100) if reason_stats['count'] > 0 else 0
                        print(f"      • {reason}: {reason_stats['count']} ({wr:.0f}% win)")
                
                all_results.append({
                    'symbol': symbol,
                    'interval': interval,
                    'strategy': strategy_name,
                    **stats
                })
    
    # Resumen por estrategia
    print("\n" + "="*70)
    print("RENDIMIENTO POR ESTRATEGIA")
    print("="*70)
    
    strategy_summary = {}
    for result in all_results:
        strat = result['strategy']
        if strat not in strategy_summary:
            strategy_summary[strat] = []
        strategy_summary[strat].append(result)
    
    for strategy, results in strategy_summary.items():
        if results:
            avg_trades = np.mean([r['total_trades'] for r in results])
            avg_wr = np.mean([r['win_rate'] for r in results])
            avg_return = np.mean([r['total_return'] for r in results])
            
            print(f"\n{strategy}:")
            print(f"  Promedio trades: {avg_trades:.0f}")
            print(f"  Promedio win rate: {avg_wr:.1f}%")
            print(f"  Promedio return: {avg_return:.2f}%")
            
            # Mejores timeframes para esta estrategia
            best_tf = max(results, key=lambda x: x['win_rate'])
            print(f"  Mejor timeframe: {best_tf['interval']} ({best_tf['win_rate']:.1f}% WR)")
    
    # Guardar resultados
    df_results = pd.DataFrame(all_results)
    df_results.to_csv('pair_strategy_backtest_results.csv', index=False)
    print(f"\n✅ Resultados guardados en pair_strategy_backtest_results.csv")

if __name__ == "__main__":
    asyncio.run(main())