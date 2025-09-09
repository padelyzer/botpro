#!/usr/bin/env python3
"""
Backtest optimizado con todas las mejoras aplicadas
"""

import asyncio
import httpx
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

# Configuración del sistema optimizado
INITIAL_CAPITAL = 220.0
MAX_RISK_PER_TRADE = 0.02
DEFAULT_LEVERAGE = 3
MAX_LEVERAGE = 5
COMMISSION = 0.0004
MIN_CONFIDENCE = 60

class OptimizedBacktest:
    """Backtest con sistema optimizado"""
    
    def __init__(self, capital: float = INITIAL_CAPITAL):
        self.initial_capital = capital
        self.capital = capital
        self.trades = []
        self.current_position = None
        
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
        
        # Indicadores básicos
        df['change_pct'] = df['close'].pct_change() * 100
        df['range_position'] = (df['close'] - df['low']) / (df['high'] - df['low'] + 0.00001)
        
        # ATR para stops dinámicos
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        df['atr'] = ranges.max(axis=1).rolling(14).mean()
        
        # RSI para confirmación de reversión
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 0.00001)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # EMAs para tendencia
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        # Volatilidad
        df['volatility'] = ((df['high'] - df['low']) / df['close']) * 100
        
        # Volumen relativo
        df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        
        # Tendencia fuerte
        df['trend_strength'] = abs(df['ema_20'] - df['ema_50']) / df['close'] * 100
        df['is_uptrend'] = df['ema_20'] > df['ema_50']
        df['is_downtrend'] = df['ema_20'] < df['ema_50']
        df['strong_trend'] = df['trend_strength'] > 1.5
        
        return df
    
    def check_signal_with_filters(self, row, df_history):
        """Aplica TODOS los filtros del sistema optimizado"""
        
        # No hay señal si no hay suficientes datos
        if pd.isna(row['atr']) or pd.isna(row['rsi']):
            return None
            
        # FILTRO 1: Alta volatilidad
        if row['volatility'] > 10:
            return None
        
        # FILTRO 2: No operar contra tendencia fuerte
        if row['strong_trend']:
            if row['is_uptrend'] and row['change_pct'] > 3:
                # No shorts en tendencia alcista fuerte
                return None
            if row['is_downtrend'] and row['change_pct'] < -3:
                # No longs en tendencia bajista fuerte
                return None
        
        signal = None
        confidence = 0
        
        # Señal LONG con confirmación de reversión
        if row['change_pct'] < -3 and row['range_position'] < 0.3:
            # FILTRO 3: Confirmación de reversión para LONG
            if row['rsi'] < 30:  # RSI oversold
                if not row['is_downtrend'] or not row['strong_trend']:  # No en tendencia bajista fuerte
                    if row['volume_ratio'] > 1.2:  # Volumen confirma interés
                        confidence = 65
                        if row['rsi'] < 25:
                            confidence += 10
                        if row['volume_ratio'] > 1.5:
                            confidence += 5
                        
                        signal = {
                            'type': 'LONG',
                            'confidence': confidence,
                            'entry_price': row['close'],
                            'atr': row['atr'],
                            'volatility': row['volatility']
                        }
        
        # Señal SHORT con confirmación de reversión  
        elif row['change_pct'] > 3 and row['range_position'] > 0.7:
            # FILTRO 3: Confirmación de reversión para SHORT
            if row['rsi'] > 70:  # RSI overbought
                if not row['is_uptrend'] or not row['strong_trend']:  # No en tendencia alcista fuerte
                    if row['volume_ratio'] > 1.2:  # Volumen confirma interés
                        confidence = 65
                        if row['rsi'] > 75:
                            confidence += 10
                        if row['volume_ratio'] > 1.5:
                            confidence += 5
                        
                        signal = {
                            'type': 'SHORT',
                            'confidence': confidence,
                            'entry_price': row['close'],
                            'atr': row['atr'],
                            'volatility': row['volatility']
                        }
        
        # Solo retornar señal si cumple confianza mínima
        if signal and signal['confidence'] >= MIN_CONFIDENCE:
            return signal
        
        return None
    
    def calculate_dynamic_stops(self, signal):
        """Calcula stops dinámicos basados en ATR"""
        
        # MEJORA 1: Stops dinámicos basados en ATR
        atr_multiplier = 2.5 if signal['volatility'] > 5 else 2.0
        stop_distance = signal['atr'] * atr_multiplier
        
        if signal['type'] == 'LONG':
            stop_loss = signal['entry_price'] - stop_distance
            # Take profit con ratio mínimo 1.5:1
            take_profit = signal['entry_price'] + (stop_distance * 1.5)
        else:  # SHORT
            stop_loss = signal['entry_price'] + stop_distance
            take_profit = signal['entry_price'] - (stop_distance * 1.5)
        
        return stop_loss, take_profit
    
    def run_backtest(self, df: pd.DataFrame, symbol: str, interval: str):
        """Ejecuta el backtest con sistema optimizado"""
        
        df = self.calculate_indicators(df)
        
        for i in range(50, len(df) - 1):  # Necesitamos historia para indicadores
            
            # Si no hay posición, buscar señal
            if self.current_position is None:
                signal = self.check_signal_with_filters(df.iloc[i], df.iloc[max(0, i-20):i])
                
                if signal:
                    # Calcular stops dinámicos
                    stop_loss, take_profit = self.calculate_dynamic_stops(signal)
                    
                    # Calcular tamaño de posición
                    risk_amount = self.capital * MAX_RISK_PER_TRADE
                    position_size = (risk_amount * DEFAULT_LEVERAGE) / signal['entry_price']
                    
                    # Comisión de entrada
                    commission = position_size * signal['entry_price'] * COMMISSION
                    
                    self.current_position = {
                        'type': signal['type'],
                        'entry_price': signal['entry_price'],
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'position_size': position_size,
                        'entry_time': df.iloc[i]['timestamp'],
                        'confidence': signal['confidence']
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
                
                if exit_price:
                    # Calcular PnL
                    if self.current_position['type'] == 'LONG':
                        pnl_pct = ((exit_price - self.current_position['entry_price']) / 
                                  self.current_position['entry_price']) * DEFAULT_LEVERAGE
                    else:  # SHORT
                        pnl_pct = ((self.current_position['entry_price'] - exit_price) / 
                                  self.current_position['entry_price']) * DEFAULT_LEVERAGE
                    
                    pnl = self.capital * pnl_pct
                    commission = self.current_position['position_size'] * exit_price * COMMISSION
                    
                    self.capital += pnl - commission
                    
                    self.trades.append({
                        'symbol': symbol,
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
                'total_return': 0,
                'final_capital': self.capital
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
            'avg_confidence': np.mean([t['confidence'] for t in self.trades]) if self.trades else 0
        }

async def main():
    """Ejecuta backtests optimizados"""
    
    print("="*60)
    print("BACKTEST DEL SISTEMA OPTIMIZADO")
    print("="*60)
    print(f"Capital inicial: ${INITIAL_CAPITAL}")
    print(f"Período: 90 días")
    print(f"Con mejoras aplicadas:")
    print("  ✓ Stops dinámicos basados en ATR")
    print("  ✓ Filtro de tendencia fuerte")
    print("  ✓ Confirmación de reversión (RSI + Volumen)")
    print("  ✓ Filtro de alta volatilidad")
    print("="*60)
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    intervals = ['15m', '1h', '4h']
    
    all_results = []
    
    for symbol in symbols:
        print(f"\n📊 {symbol}:")
        print("-" * 40)
        
        for interval in intervals:
            backtest = OptimizedBacktest()
            
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
                if 'profit_factor' in stats:
                    print(f"    Profit Factor: {stats['profit_factor']:.2f}")
                print(f"    Return: {stats['total_return']:.2f}%")
                print(f"    Final Capital: ${stats['final_capital']:.2f}")
                if stats['total_trades'] > 0 and 'avg_confidence' in stats:
                    print(f"    Avg Confidence: {stats['avg_confidence']:.1f}%")
                
                all_results.append({
                    'symbol': symbol,
                    'interval': interval,
                    **stats
                })
    
    # Resumen general
    print("\n" + "="*60)
    print("RESUMEN COMPARATIVO")
    print("="*60)
    
    # Agrupar por timeframe
    for interval in intervals:
        interval_results = [r for r in all_results if r['interval'] == interval]
        
        if interval_results:
            avg_trades = np.mean([r['total_trades'] for r in interval_results])
            avg_win_rate = np.mean([r['win_rate'] for r in interval_results])
            avg_return = np.mean([r['total_return'] for r in interval_results])
            
            print(f"\n{interval}:")
            print(f"  Promedio trades: {avg_trades:.0f}")
            print(f"  Promedio win rate: {avg_win_rate:.1f}%")
            print(f"  Promedio return: {avg_return:.2f}%")
    
    # Guardar resultados
    df_results = pd.DataFrame(all_results)
    df_results.to_csv('optimized_backtest_results.csv', index=False)
    print("\n✅ Resultados guardados en optimized_backtest_results.csv")
    
    # Comparación con backtest anterior
    print("\n" + "="*60)
    print("COMPARACIÓN CON SISTEMA ANTERIOR")
    print("="*60)
    
    # Cargar resultados anteriores si existen
    try:
        df_old = pd.read_csv('backtest_results.csv')
        
        for interval in intervals:
            old_wr = df_old[df_old['interval'] == interval]['win_rate'].mean()
            new_wr = df_results[df_results['interval'] == interval]['win_rate'].mean()
            
            old_trades = df_old[df_old['interval'] == interval]['total_trades'].mean()
            new_trades = df_results[df_results['interval'] == interval]['total_trades'].mean()
            
            print(f"\n{interval}:")
            print(f"  Win Rate: {old_wr:.1f}% → {new_wr:.1f}% ({new_wr-old_wr:+.1f}%)")
            print(f"  Trades: {old_trades:.0f} → {new_trades:.0f} ({new_trades-old_trades:+.0f})")
            
            if new_wr > old_wr:
                print(f"  ✅ Mejora en win rate!")
    except:
        print("No se encontraron resultados anteriores para comparar")

if __name__ == "__main__":
    asyncio.run(main())