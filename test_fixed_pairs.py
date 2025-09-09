#!/usr/bin/env python3
"""
Backtest de las Configuraciones Corregidas
Prueba las soluciones aplicadas a cada par problemático
"""

import asyncio
import httpx
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Importar configuraciones corregidas
from fixed_pair_system import FIXED_PAIR_CONFIG, INITIAL_CAPITAL, MAX_RISK_PER_TRADE, DEFAULT_LEVERAGE
COMMISSION = 0.0004

class TestFixedPairs:
    """Tester de configuraciones corregidas"""
    
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
                        break
                        
                except Exception as e:
                    print(f"Error fetching {symbol} {interval}: {e}")
                    break
                
                await asyncio.sleep(0.1)
        
        return all_data
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores mejorados"""
        
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
    
    def generate_fixed_signal(self, row, prev_row, symbol: str, interval: str):
        """Genera señales con configuraciones corregidas"""
        
        config = FIXED_PAIR_CONFIG[symbol][interval]
        
        if pd.isna(row['atr']) or pd.isna(row['rsi']):
            return None
        
        if row['volatility'] > config['max_volatility']:
            return None
        
        signal = None
        confidence = 0
        
        # TREND FOLLOWING MEJORADO (BTC)
        if config.get('use_trend_following'):
            # Verificar tendencia más fuerte
            trend_strength_ok = True
            if 'trend_strength_min' in config:
                trend_strength_ok = row['trend_strength'] > config['trend_strength_min']
            
            # Verificar MACD más estricto
            macd_ok = True
            if 'macd_threshold' in config:
                if row['is_uptrend']:
                    macd_ok = row['macd_histogram'] > config['macd_threshold']
                else:
                    macd_ok = row['macd_histogram'] < -config['macd_threshold']
            
            if (row['is_uptrend'] and trend_strength_ok and macd_ok and
                row['change_pct'] > config['min_change_pct'] * 0.5 and
                row['rsi'] < config['rsi_overbought'] and row['rsi'] > 45 and
                row['volume_ratio'] > config['min_volume_ratio']):
                
                confidence = config['min_confidence'] + 10
                if row['macd_histogram'] > prev_row['macd_histogram']:
                    confidence += 5
                if row['volume_ratio'] > config['min_volume_ratio'] * 1.2:
                    confidence += 5
                
                signal = {'type': 'LONG', 'strategy': 'TREND_FOLLOWING_IMPROVED', 'confidence': min(confidence, 85)}
        
        # MEAN REVERSION MEJORADO (ETH, ADA)
        elif config.get('use_mean_reversion'):
            bb_threshold = config.get('bb_extreme_threshold', 0.2)
            
            rsi_confirm = True
            if config.get('rsi_confirmation'):
                rsi_confirm = (row['rsi'] < config['rsi_oversold'] - 2) if row['change_pct'] < 0 else \
                             (row['rsi'] > config['rsi_overbought'] + 2)
            
            # Long mejorado
            if (row['change_pct'] < -config['min_change_pct'] and
                row['rsi'] < config['rsi_oversold'] and
                row['bb_position'] < bb_threshold and
                row['volume_ratio'] > config['min_volume_ratio'] and
                rsi_confirm):
                
                confidence = config['min_confidence']
                if row['rsi'] < config['rsi_oversold'] - 5:
                    confidence += 15
                if row['bb_position'] < bb_threshold * 0.7:
                    confidence += 10
                
                signal = {'type': 'LONG', 'strategy': 'MEAN_REVERSION_IMPROVED', 'confidence': min(confidence, 80)}
            
            # Short mejorado
            elif (row['change_pct'] > config['min_change_pct'] and
                  row['rsi'] > config['rsi_overbought'] and
                  row['bb_position'] > (1 - bb_threshold) and
                  row['volume_ratio'] > config['min_volume_ratio'] and
                  rsi_confirm):
                
                confidence = config['min_confidence']
                if row['rsi'] > config['rsi_overbought'] + 5:
                    confidence += 15
                if row['bb_position'] > (1 - bb_threshold * 0.7):
                    confidence += 10
                
                signal = {'type': 'SHORT', 'strategy': 'MEAN_REVERSION_IMPROVED', 'confidence': min(confidence, 80)}
        
        # MOMENTUM RELAJADO (SOL, DOGE)
        elif config.get('use_momentum'):
            if (row['change_pct'] > config['min_change_pct'] and
                row['volume_ratio'] > config['min_volume_ratio'] and
                row['macd_histogram'] > prev_row['macd_histogram'] and
                row['rsi'] > 50 and row['rsi'] < config['rsi_overbought'] and
                row['volume_trend'] > 1.1):
                
                confidence = config['min_confidence']
                if row['volume_trend'] > 1.4:
                    confidence += 10
                if row['change_pct'] > config['min_change_pct'] * 1.3:
                    confidence += 8
                
                if config.get('extra_caution'):
                    confidence = min(confidence, 70)
                
                signal = {'type': 'LONG', 'strategy': 'MOMENTUM_RELAXED', 'confidence': confidence}
        
        # RANGE TRADING (BNB)
        elif config.get('use_range_trading'):
            if (row['bb_position'] < 0.2 and
                row['rsi'] < config['rsi_oversold'] + 5 and
                row['change_pct'] < -config['min_change_pct'] * 0.7):
                
                confidence = config['min_confidence']
                if row['bb_position'] < 0.1:
                    confidence += 10
                
                signal = {'type': 'LONG', 'strategy': 'RANGE_TRADING', 'confidence': confidence}
        
        if signal and signal['confidence'] >= config['min_confidence']:
            signal.update({
                'entry_price': row['close'],
                'atr': row['atr'],
                'volatility': row['volatility']
            })
            return signal
        
        return None
    
    def calculate_stops(self, signal, config):
        """Calcula stops con ATR corregido"""
        
        atr_mult = config['atr_multiplier']
        
        if signal['volatility'] > config['max_volatility'] * 0.8:
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
        """Ejecuta backtest con configuraciones corregidas"""
        
        config = FIXED_PAIR_CONFIG[symbol][interval]
        df = self.calculate_indicators(df)
        
        for i in range(50, len(df) - 1):
            
            # Drawdown tracking
            if self.capital > self.peak_capital:
                self.peak_capital = self.capital
            
            drawdown = ((self.peak_capital - self.capital) / self.peak_capital) * 100
            if drawdown > self.max_drawdown:
                self.max_drawdown = drawdown
            
            # Buscar señal
            if self.current_position is None:
                signal = self.generate_fixed_signal(df.iloc[i], df.iloc[i-1], symbol, interval)
                
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
            
            # Verificar salida
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
                        'confidence': self.current_position['confidence']
                    })
                    
                    self.current_position = None
    
    def get_statistics(self) -> dict:
        """Estadísticas del backtest"""
        
        if not self.trades:
            return {
                'total_trades': 0, 'winning_trades': 0, 'losing_trades': 0,
                'win_rate': 0, 'total_return': 0, 'final_capital': self.capital,
                'max_drawdown': 0
            }
        
        winning_trades = [t for t in self.trades if t['pnl'] > 0]
        losing_trades = [t for t in self.trades if t['pnl'] <= 0]
        
        total_return = ((self.capital - self.initial_capital) / self.initial_capital) * 100
        
        return {
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': (len(winning_trades) / len(self.trades)) * 100 if self.trades else 0,
            'total_return': total_return,
            'final_capital': self.capital,
            'max_drawdown': self.max_drawdown,
            'avg_confidence': np.mean([t['confidence'] for t in self.trades]) if self.trades else 0
        }

async def test_problem_pairs():
    """Testa solo los pares que tenían problemas"""
    
    print("="*70)
    print("TEST DE CONFIGURACIONES CORREGIDAS")
    print("="*70)
    print("Testeando solo pares problemáticos:")
    print("• BTC 15m/1h (era 0% y 37.5% WR)")
    print("• ETH todas (eran negativas)")
    print("• SOL 15m (era 0 trades)")
    print("• ADA 15m/1h (era 26.7% y 33.3% WR)")
    print("="*70)
    
    # Solo testear pares problemáticos
    problem_pairs = {
        'BTCUSDT': ['15m', '1h'],  # 4h ya funcionaba bien
        'ETHUSDT': ['15m', '1h', '4h'],  # Todas eran negativas
        'SOLUSDT': ['15m'],  # Era 0 trades
        'ADAUSDT': ['15m', '1h']  # 4h ya funcionaba (+38.34%)
    }
    
    results = []
    
    for symbol, intervals in problem_pairs.items():
        print(f"\n🔧 {symbol} (configuraciones corregidas):")
        print("-" * 50)
        
        for interval in intervals:
            print(f"Testing {symbol} {interval}...")
            
            backtest = TestFixedPairs()
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
                
                results.append({
                    'symbol': symbol,
                    'interval': interval,
                    'status': 'FIXED',
                    **stats
                })
            else:
                print(f"  {interval}: No data available")
    
    # Comparar con resultados anteriores
    print("\n" + "="*70)
    print("COMPARACIÓN: ANTES vs DESPUÉS DE LAS CORRECCIONES")
    print("="*70)
    
    # Resultados anteriores (problemáticos)
    old_results = {
        ('BTCUSDT', '15m'): {'trades': 3, 'wr': 0.0, 'return': -5.39},
        ('BTCUSDT', '1h'): {'trades': 8, 'wr': 37.5, 'return': -5.66},
        ('ETHUSDT', '15m'): {'trades': 12, 'wr': 33.3, 'return': -11.73},
        ('ETHUSDT', '1h'): {'trades': 10, 'wr': 40.0, 'return': -11.22},
        ('ETHUSDT', '4h'): {'trades': 7, 'wr': 42.9, 'return': -12.85},
        ('SOLUSDT', '15m'): {'trades': 0, 'wr': 0.0, 'return': 0.0},
        ('ADAUSDT', '15m'): {'trades': 15, 'wr': 26.7, 'return': -41.62},
        ('ADAUSDT', '1h'): {'trades': 15, 'wr': 33.3, 'return': -32.08}
    }
    
    improvements = []
    
    for result in results:
        key = (result['symbol'], result['interval'])
        if key in old_results:
            old = old_results[key]
            new_trades = result['total_trades']
            new_wr = result['win_rate']
            new_return = result['total_return']
            
            wr_improvement = new_wr - old['wr']
            return_improvement = new_return - old['return']
            
            print(f"\n{result['symbol']} {result['interval']}:")
            print(f"  ANTES: {old['trades']} trades, {old['wr']:.1f}% WR, {old['return']:.2f}% return")
            print(f"  DESPUÉS: {new_trades} trades, {new_wr:.1f}% WR, {new_return:.2f}% return")
            print(f"  MEJORA: Win Rate {wr_improvement:+.1f}%, Return {return_improvement:+.2f}%")
            
            if new_wr > 50 and new_return > 0:
                print(f"  ✅ CORREGIDO EXITOSAMENTE")
                improvements.append('SUCCESS')
            elif wr_improvement > 10 or return_improvement > 10:
                print(f"  📈 MEJORA SIGNIFICATIVA")
                improvements.append('IMPROVED')
            else:
                print(f"  ⚠️ NECESITA MÁS TRABAJO")
                improvements.append('NEEDS_WORK')
    
    # Resumen final
    success_rate = improvements.count('SUCCESS') / len(improvements) * 100 if improvements else 0
    print(f"\n" + "="*70)
    print("RESUMEN DE CORRECCIONES")
    print("="*70)
    print(f"Configuraciones corregidas exitosamente: {improvements.count('SUCCESS')}/{len(improvements)} ({success_rate:.1f}%)")
    print(f"Mejoras significativas: {improvements.count('IMPROVED')}")
    print(f"Necesitan más trabajo: {improvements.count('NEEDS_WORK')}")
    
    # Guardar resultados
    df_results = pd.DataFrame(results)
    df_results.to_csv('fixed_pairs_test_results.csv', index=False)
    print(f"\n✅ Resultados guardados en fixed_pairs_test_results.csv")

if __name__ == "__main__":
    asyncio.run(test_problem_pairs())