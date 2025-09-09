#!/usr/bin/env python3
"""
Backtest del Sistema Balanceado - Con filtros adaptativos por timeframe
"""

import asyncio
import httpx
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

# Configuración adaptativa por timeframe (igual que en balanced_futures_system.py)
TIMEFRAME_CONFIG = {
    '15m': {
        'min_change_pct': 2.0,
        'rsi_oversold': 35,
        'rsi_overbought': 65,
        'min_volume_ratio': 1.1,
        'max_volatility': 12,
        'atr_multiplier': 2.0,
        'min_confidence': 55,
        'trend_filter_strength': 0.5
    },
    '1h': {
        'min_change_pct': 2.5,
        'rsi_oversold': 32,
        'rsi_overbought': 68,
        'min_volume_ratio': 1.15,
        'max_volatility': 11,
        'atr_multiplier': 2.2,
        'min_confidence': 58,
        'trend_filter_strength': 0.7
    },
    '4h': {
        'min_change_pct': 3.0,
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'min_volume_ratio': 1.2,
        'max_volatility': 10,
        'atr_multiplier': 2.5,
        'min_confidence': 60,
        'trend_filter_strength': 1.0
    }
}

INITIAL_CAPITAL = 220.0
MAX_RISK_PER_TRADE = 0.02
DEFAULT_LEVERAGE = 3
COMMISSION = 0.0004

class BalancedBacktest:
    """Backtest con sistema balanceado adaptativo"""
    
    def __init__(self, capital: float = INITIAL_CAPITAL):
        self.initial_capital = capital
        self.capital = capital
        self.trades = []
        self.current_position = None
        self.max_drawdown = 0
        self.peak_capital = capital
        
    async def fetch_historical_data(self, symbol: str, interval: str, days: int = 90):
        """Obtiene datos históricos de Binance"""
        
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
                    print(f"Error fetching data: {e}")
                    break
        
        return all_data
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula todos los indicadores necesarios"""
        
        # Cambio porcentual
        df['change_pct'] = df['close'].pct_change() * 100
        
        # Posición en rango
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
        
        # Volatilidad
        df['volatility'] = ((df['high'] - df['low']) / df['close']) * 100
        
        # Volumen relativo
        df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        
        # Tendencia
        df['trend_strength'] = abs(df['ema_20'] - df['ema_50']) / df['close'] * 100
        df['is_uptrend'] = df['ema_20'] > df['ema_50']
        
        return df
    
    def check_signal_balanced(self, row, interval: str):
        """Genera señales con filtros balanceados por timeframe"""
        
        # Obtener configuración del timeframe
        config = TIMEFRAME_CONFIG[interval]
        
        # Verificar datos válidos
        if pd.isna(row['atr']) or pd.isna(row['rsi']):
            return None
        
        # FILTRO 1: Volatilidad máxima adaptativa
        if row['volatility'] > config['max_volatility']:
            return None
        
        signal = None
        confidence = 0
        
        # SEÑAL LONG
        if (row['change_pct'] < -config['min_change_pct'] and 
            row['range_position'] < 0.3):
            
            # RSI adaptativo
            if row['rsi'] < config['rsi_oversold']:
                
                # Filtro de tendencia adaptativo
                trend_ok = True
                if not row['is_uptrend'] and row['trend_strength'] > (1.5 * config['trend_filter_strength']):
                    # Solo filtrar si la tendencia bajista es muy fuerte
                    trend_ok = False
                
                if trend_ok:
                    # Volumen adaptativo
                    if row['volume_ratio'] > config['min_volume_ratio']:
                        
                        confidence = config['min_confidence']
                        
                        # Bonus confianza
                        if row['rsi'] < (config['rsi_oversold'] - 5):
                            confidence += 10
                        if row['volume_ratio'] > (config['min_volume_ratio'] + 0.3):
                            confidence += 5
                        if row['range_position'] < 0.2:
                            confidence += 5
                        
                        signal = {
                            'type': 'LONG',
                            'confidence': min(confidence, 90),
                            'entry_price': row['close'],
                            'atr': row['atr'],
                            'volatility': row['volatility']
                        }
        
        # SEÑAL SHORT
        elif (row['change_pct'] > config['min_change_pct'] and 
              row['range_position'] > 0.7):
            
            # RSI adaptativo
            if row['rsi'] > config['rsi_overbought']:
                
                # Filtro de tendencia adaptativo
                trend_ok = True
                if row['is_uptrend'] and row['trend_strength'] > (1.5 * config['trend_filter_strength']):
                    # Solo filtrar si la tendencia alcista es muy fuerte
                    trend_ok = False
                
                if trend_ok:
                    # Volumen adaptativo
                    if row['volume_ratio'] > config['min_volume_ratio']:
                        
                        confidence = config['min_confidence']
                        
                        # Bonus confianza
                        if row['rsi'] > (config['rsi_overbought'] + 5):
                            confidence += 10
                        if row['volume_ratio'] > (config['min_volume_ratio'] + 0.3):
                            confidence += 5
                        if row['range_position'] > 0.8:
                            confidence += 5
                        
                        signal = {
                            'type': 'SHORT',
                            'confidence': min(confidence, 90),
                            'entry_price': row['close'],
                            'atr': row['atr'],
                            'volatility': row['volatility']
                        }
        
        # Solo retornar si cumple confianza mínima
        if signal and signal['confidence'] >= config['min_confidence']:
            return signal
        
        return None
    
    def calculate_dynamic_stops(self, signal, interval: str):
        """Calcula stops dinámicos basados en ATR y timeframe"""
        
        config = TIMEFRAME_CONFIG[interval]
        
        # ATR multiplier adaptativo
        atr_mult = config['atr_multiplier']
        
        # Ajustar según volatilidad
        if signal['volatility'] > 8:
            atr_mult += 0.3
        
        stop_distance = signal['atr'] * atr_mult
        
        if signal['type'] == 'LONG':
            stop_loss = signal['entry_price'] - stop_distance
            take_profit = signal['entry_price'] + (stop_distance * 1.5)
        else:
            stop_loss = signal['entry_price'] + stop_distance
            take_profit = signal['entry_price'] - (stop_distance * 1.5)
        
        return stop_loss, take_profit
    
    def run_backtest(self, df: pd.DataFrame, symbol: str, interval: str):
        """Ejecuta el backtest con sistema balanceado"""
        
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
                signal = self.check_signal_balanced(df.iloc[i], interval)
                
                if signal:
                    # Calcular stops
                    stop_loss, take_profit = self.calculate_dynamic_stops(signal, interval)
                    
                    # Tamaño de posición
                    risk_amount = self.capital * MAX_RISK_PER_TRADE
                    position_size = (risk_amount * DEFAULT_LEVERAGE) / signal['entry_price']
                    
                    # Comisión
                    commission = position_size * signal['entry_price'] * COMMISSION
                    
                    self.current_position = {
                        'type': signal['type'],
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
                
                # Time exit después de muchas velas
                if not exit_price and (i - self.current_position['entry_index']) > 20:
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
                        'type': self.current_position['type'],
                        'entry_price': self.current_position['entry_price'],
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct * 100,
                        'exit_reason': exit_reason,
                        'confidence': self.current_position['confidence']
                    })
                    
                    self.current_position = None
    
    def get_statistics(self) -> dict:
        """Calcula estadísticas del backtest"""
        
        if not self.trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'total_return': 0,
                'final_capital': self.capital,
                'max_drawdown': 0,
                'sharpe_ratio': 0
            }
        
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] <= 0]
        
        total_return = ((self.capital - self.initial_capital) / self.initial_capital) * 100
        
        avg_win = np.mean([t['pnl'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl'] for t in losing_trades]) if losing_trades else 0
        
        # Profit factor
        total_wins = sum([t['pnl'] for t in winning_trades]) if winning_trades else 0
        total_losses = abs(sum([t['pnl'] for t in losing_trades])) if losing_trades else 1
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Sharpe ratio simplificado
        returns = [t['pnl_pct'] for t in self.trades]
        if len(returns) > 1:
            sharpe = np.mean(returns) / (np.std(returns) + 0.00001)
        else:
            sharpe = 0
        
        # Análisis por tipo de salida
        exit_analysis = {}
        for trade in self.trades:
            reason = trade['exit_reason']
            if reason not in exit_analysis:
                exit_analysis[reason] = {'count': 0, 'wins': 0}
            exit_analysis[reason]['count'] += 1
            if trade['pnl'] > 0:
                exit_analysis[reason]['wins'] += 1
        
        return {
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': (len(winning_trades) / len(self.trades)) * 100 if self.trades else 0,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'total_return': total_return,
            'final_capital': self.capital,
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': sharpe,
            'exit_analysis': exit_analysis,
            'avg_confidence': np.mean([t['confidence'] for t in self.trades]) if self.trades else 0
        }

async def main():
    """Ejecuta backtests del sistema balanceado"""
    
    print("="*60)
    print("BACKTEST DEL SISTEMA BALANCEADO")
    print("="*60)
    print(f"Capital inicial: ${INITIAL_CAPITAL}")
    print(f"Período: 90 días")
    print(f"Sistema: Filtros adaptativos por timeframe")
    print("="*60)
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    intervals = ['15m', '1h', '4h']
    
    all_results = []
    
    for symbol in symbols:
        print(f"\n📊 {symbol}:")
        print("-" * 40)
        
        for interval in intervals:
            backtest = BalancedBacktest()
            
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
                
                print(f"\n  {interval}:")
                print(f"    Trades: {stats['total_trades']}")
                print(f"    Win Rate: {stats['win_rate']:.1f}%")
                print(f"    Profit Factor: {stats['profit_factor']:.2f}")
                print(f"    Return: {stats['total_return']:.2f}%")
                print(f"    Max Drawdown: {stats['max_drawdown']:.2f}%")
                print(f"    Final Capital: ${stats['final_capital']:.2f}")
                
                # Análisis de salidas
                if stats['exit_analysis']:
                    print(f"    Salidas:")
                    for reason, data in stats['exit_analysis'].items():
                        wr = (data['wins'] / data['count']) * 100 if data['count'] > 0 else 0
                        print(f"      • {reason}: {data['count']} trades ({wr:.1f}% win)")
                
                all_results.append({
                    'symbol': symbol,
                    'interval': interval,
                    **stats
                })
    
    # Resumen comparativo
    print("\n" + "="*60)
    print("RESUMEN POR TIMEFRAME")
    print("="*60)
    
    for interval in intervals:
        interval_results = [r for r in all_results if r['interval'] == interval]
        
        if interval_results:
            avg_trades = np.mean([r['total_trades'] for r in interval_results])
            avg_win_rate = np.mean([r['win_rate'] for r in interval_results])
            avg_return = np.mean([r['total_return'] for r in interval_results])
            avg_profit_factor = np.mean([r['profit_factor'] for r in interval_results])
            
            print(f"\n{interval}:")
            print(f"  Promedio trades: {avg_trades:.0f}")
            print(f"  Promedio win rate: {avg_win_rate:.1f}%")
            print(f"  Promedio profit factor: {avg_profit_factor:.2f}")
            print(f"  Promedio return: {avg_return:.2f}%")
    
    # Guardar resultados
    df_results = pd.DataFrame(all_results)
    df_results.to_csv('balanced_backtest_results.csv', index=False)
    print("\n✅ Resultados guardados en balanced_backtest_results.csv")
    
    # Comparación con sistemas anteriores
    print("\n" + "="*60)
    print("COMPARACIÓN DE SISTEMAS")
    print("="*60)
    
    try:
        # Cargar resultados anteriores
        df_original = pd.read_csv('backtest_results.csv')
        df_optimized = pd.read_csv('optimized_backtest_results.csv')
        
        for interval in intervals:
            orig_wr = df_original[df_original['interval'] == interval]['win_rate'].mean()
            orig_trades = df_original[df_original['interval'] == interval]['total_trades'].mean()
            
            opt_wr = df_optimized[df_optimized['interval'] == interval]['win_rate'].mean()
            opt_trades = df_optimized[df_optimized['interval'] == interval]['total_trades'].mean()
            
            bal_wr = df_results[df_results['interval'] == interval]['win_rate'].mean()
            bal_trades = df_results[df_results['interval'] == interval]['total_trades'].mean()
            
            print(f"\n{interval}:")
            print(f"  Original   : {orig_trades:3.0f} trades, {orig_wr:5.1f}% WR")
            print(f"  Optimizado : {opt_trades:3.0f} trades, {opt_wr:5.1f}% WR")
            print(f"  Balanceado : {bal_trades:3.0f} trades, {bal_wr:5.1f}% WR ⭐")
            
            # Indicar mejora
            if bal_trades > opt_trades and bal_wr > 40:
                print(f"  ✅ Mejor balance entre cantidad y calidad!")
                
    except Exception as e:
        print(f"No se pudieron cargar resultados anteriores: {e}")

if __name__ == "__main__":
    asyncio.run(main())