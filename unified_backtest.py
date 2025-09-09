#!/usr/bin/env python3
"""
Sistema de Backtesting para Unified Futures System
Prueba los últimos 90 días en timeframes de 15m, 1h, 4h
"""

import asyncio
import httpx
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =====================================
# CONFIGURACIÓN
# =====================================
INITIAL_CAPITAL = 220.0
MAX_RISK_PER_TRADE = 0.02  # 2%
DEFAULT_LEVERAGE = 3
COMMISSION = 0.0004  # 0.04% por trade (Binance Futures)

class BacktestEngine:
    """Motor de backtesting para el sistema unificado"""
    
    def __init__(self, capital: float = INITIAL_CAPITAL):
        self.initial_capital = capital
        self.capital = capital
        self.trades = []
        self.positions = []
        self.equity_curve = []
        
    async def fetch_historical_data(self, symbol: str, interval: str, days: int = 90) -> pd.DataFrame:
        """Obtiene datos históricos de Binance"""
        
        # Mapeo de intervalos
        interval_map = {
            '15m': '15m',
            '1h': '1h', 
            '4h': '4h'
        }
        
        # Calcular timestamps
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        all_data = []
        
        async with httpx.AsyncClient() as client:
            current_start = start_time
            
            while current_start < end_time:
                try:
                    response = await client.get(
                        'https://fapi.binance.com/fapi/v1/klines',
                        params={
                            'symbol': symbol,
                            'interval': interval_map[interval],
                            'startTime': current_start,
                            'limit': 1500  # Máximo permitido
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if not data:
                            break
                        all_data.extend(data)
                        # Actualizar start time para siguiente batch
                        current_start = data[-1][0] + 1
                    else:
                        logger.error(f"Error fetching data: {response.status_code}")
                        break
                        
                except Exception as e:
                    logger.error(f"Error fetching {symbol} data: {e}")
                    break
                
                # Pequeña pausa para no sobrecargar API
                await asyncio.sleep(0.1)
        
        if not all_data:
            return pd.DataFrame()
        
        # Convertir a DataFrame
        df = pd.DataFrame(all_data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 
            'volume', 'close_time', 'quote_volume', 'trades',
            'taker_buy_volume', 'taker_buy_quote', 'ignore'
        ])
        
        # Convertir tipos
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']:
            df[col] = df[col].astype(float)
        
        # Calcular indicadores adicionales
        df['returns'] = df['close'].pct_change()
        df['price_change_pct'] = ((df['close'] - df['open']) / df['open']) * 100
        df['range_position'] = (df['close'] - df['low']) / (df['high'] - df['low'])
        df['range_position'].fillna(0.5, inplace=True)
        
        # Calcular cambio 24h (aproximado según timeframe)
        periods_24h = {
            '15m': 96,   # 24h = 96 periodos de 15m
            '1h': 24,     # 24h = 24 periodos de 1h
            '4h': 6       # 24h = 6 periodos de 4h
        }
        
        df['change_24h'] = df['close'].pct_change(periods_24h[interval]) * 100
        df['volume_24h'] = df['quote_volume'].rolling(periods_24h[interval]).sum()
        df['high_24h'] = df['high'].rolling(periods_24h[interval]).max()
        df['low_24h'] = df['low'].rolling(periods_24h[interval]).min()
        
        return df
    
    def generate_signal(self, row: pd.Series) -> Dict:
        """Genera señal basada en la lógica del sistema unificado"""
        
        if pd.isna(row['change_24h']) or pd.isna(row['range_position']):
            return None
        
        price = row['close']
        change = row['change_24h']
        price_position = row['range_position']
        volume = row['volume_24h'] if not pd.isna(row['volume_24h']) else row['quote_volume']
        
        signal_type = None
        confidence = 0
        
        # Lógica de señales (igual que el sistema unificado)
        # SEÑAL 1: Reversión en extremos
        if change < -3 and price_position < 0.3:
            signal_type = "LONG"
            confidence = min(85, 60 + abs(change) * 3)
            
        elif change > 3 and price_position > 0.7:
            signal_type = "SHORT"
            confidence = min(85, 60 + change * 3)
        
        # SEÑAL 2: Momentum con volumen
        elif volume > 100_000_000:  # > $100M
            if change < -2 and price_position < 0.4:
                signal_type = "LONG"
                confidence = 70
            elif change > 2 and price_position > 0.6:
                signal_type = "SHORT"
                confidence = 70
        
        # SEÑAL 3: Recuperación moderada
        elif change < -1 and price_position < 0.35:
            signal_type = "LONG"
            confidence = 65
        elif change > 1.5 and price_position > 0.75:
            signal_type = "SHORT"
            confidence = 65
        
        if signal_type and confidence >= 60:
            # Calcular SL y TP
            if signal_type == "LONG":
                stop_loss = price * 0.98  # 2% SL
                take_profit = price * 1.04  # 4% TP
            else:
                stop_loss = price * 1.02
                take_profit = price * 0.96
            
            return {
                'timestamp': row['timestamp'],
                'type': signal_type,
                'entry_price': price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'confidence': confidence,
                'change_24h': change,
                'price_position': price_position,
                'volume': volume
            }
        
        return None
    
    def execute_trade(self, signal: Dict, current_price: float) -> Dict:
        """Ejecuta un trade y calcula resultado"""
        
        position_size = self.capital * MAX_RISK_PER_TRADE * DEFAULT_LEVERAGE
        
        # Comisión de entrada
        entry_commission = position_size * COMMISSION
        
        # Calcular resultado según dirección
        if signal['type'] == 'LONG':
            if current_price >= signal['take_profit']:
                # Take profit alcanzado
                pnl_pct = (signal['take_profit'] - signal['entry_price']) / signal['entry_price']
                exit_price = signal['take_profit']
                result = 'TP'
            elif current_price <= signal['stop_loss']:
                # Stop loss alcanzado
                pnl_pct = (signal['stop_loss'] - signal['entry_price']) / signal['entry_price']
                exit_price = signal['stop_loss']
                result = 'SL'
            else:
                # Cerrar en precio actual
                pnl_pct = (current_price - signal['entry_price']) / signal['entry_price']
                exit_price = current_price
                result = 'CLOSE'
        else:  # SHORT
            if current_price <= signal['take_profit']:
                # Take profit alcanzado
                pnl_pct = (signal['entry_price'] - signal['take_profit']) / signal['entry_price']
                exit_price = signal['take_profit']
                result = 'TP'
            elif current_price >= signal['stop_loss']:
                # Stop loss alcanzado
                pnl_pct = (signal['entry_price'] - signal['stop_loss']) / signal['entry_price']
                exit_price = signal['stop_loss']
                result = 'SL'
            else:
                # Cerrar en precio actual
                pnl_pct = (signal['entry_price'] - current_price) / signal['entry_price']
                exit_price = current_price
                result = 'CLOSE'
        
        # Calcular PnL con leverage y comisiones
        gross_pnl = position_size * pnl_pct * DEFAULT_LEVERAGE
        exit_commission = position_size * COMMISSION
        net_pnl = gross_pnl - entry_commission - exit_commission
        
        # Actualizar capital
        self.capital += net_pnl
        
        return {
            'entry_time': signal['timestamp'],
            'exit_time': datetime.now(),
            'type': signal['type'],
            'entry_price': signal['entry_price'],
            'exit_price': exit_price,
            'result': result,
            'gross_pnl': gross_pnl,
            'commission': entry_commission + exit_commission,
            'net_pnl': net_pnl,
            'capital_after': self.capital,
            'confidence': signal['confidence']
        }
    
    async def run_backtest(self, symbol: str, interval: str) -> Dict:
        """Ejecuta backtest para un símbolo y timeframe"""
        
        logger.info(f"Starting backtest for {symbol} on {interval}")
        
        # Obtener datos históricos
        df = await self.fetch_historical_data(symbol, interval)
        
        if df.empty:
            logger.error(f"No data available for {symbol}")
            return None
        
        # Resetear estado
        self.capital = self.initial_capital
        self.trades = []
        self.equity_curve = [self.initial_capital]
        
        active_position = None
        
        for idx, row in df.iterrows():
            # Si hay posición activa, verificar salida
            if active_position:
                trade_result = self.execute_trade(active_position, row['close'])
                
                if trade_result['result'] in ['TP', 'SL']:
                    self.trades.append(trade_result)
                    active_position = None
                    self.equity_curve.append(self.capital)
                    
                    # Esperar algunas velas antes de nueva entrada
                    continue
            
            # Buscar nueva señal solo si no hay posición
            if not active_position:
                signal = self.generate_signal(row)
                if signal:
                    active_position = signal
        
        # Cerrar posición final si existe
        if active_position:
            trade_result = self.execute_trade(active_position, df.iloc[-1]['close'])
            self.trades.append(trade_result)
            self.equity_curve.append(self.capital)
        
        # Calcular métricas
        return self.calculate_metrics(symbol, interval)
    
    def calculate_metrics(self, symbol: str, interval: str) -> Dict:
        """Calcula métricas de rendimiento"""
        
        if not self.trades:
            return {
                'symbol': symbol,
                'interval': interval,
                'total_trades': 0,
                'final_capital': self.capital,
                'total_return': 0,
                'message': 'No trades executed'
            }
        
        trades_df = pd.DataFrame(self.trades)
        
        winning_trades = trades_df[trades_df['net_pnl'] > 0]
        losing_trades = trades_df[trades_df['net_pnl'] < 0]
        
        total_return = ((self.capital - self.initial_capital) / self.initial_capital) * 100
        win_rate = (len(winning_trades) / len(self.trades)) * 100 if self.trades else 0
        
        avg_win = winning_trades['net_pnl'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['net_pnl'].mean() if len(losing_trades) > 0 else 0
        
        # Calcular max drawdown
        equity_series = pd.Series(self.equity_curve)
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max * 100
        max_drawdown = drawdown.min()
        
        # Profit factor
        total_wins = winning_trades['net_pnl'].sum() if len(winning_trades) > 0 else 0
        total_losses = abs(losing_trades['net_pnl'].sum()) if len(losing_trades) > 0 else 1
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Sharpe Ratio (simplificado)
        if len(trades_df) > 1:
            returns = trades_df['net_pnl'] / self.initial_capital
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0
        else:
            sharpe = 0
        
        return {
            'symbol': symbol,
            'interval': interval,
            'initial_capital': self.initial_capital,
            'final_capital': round(self.capital, 2),
            'total_return': round(total_return, 2),
            'total_trades': len(self.trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': round(win_rate, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'max_drawdown': round(max_drawdown, 2),
            'sharpe_ratio': round(sharpe, 2),
            'commission_paid': round(sum([t['commission'] for t in self.trades]), 2)
        }

async def run_complete_backtest():
    """Ejecuta backtest completo en múltiples timeframes"""
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']
    intervals = ['15m', '1h', '4h']
    
    all_results = []
    
    print("="*60)
    print("BACKTEST DEL SISTEMA UNIFICADO DE FUTUROS")
    print(f"Capital Inicial: ${INITIAL_CAPITAL}")
    print(f"Período: Últimos 90 días")
    print(f"Riesgo por Trade: {MAX_RISK_PER_TRADE*100}%")
    print(f"Leverage: {DEFAULT_LEVERAGE}x")
    print("="*60)
    
    for symbol in symbols:
        print(f"\n📊 Testing {symbol}...")
        
        for interval in intervals:
            engine = BacktestEngine(INITIAL_CAPITAL)
            result = await engine.run_backtest(symbol, interval)
            
            if result:
                all_results.append(result)
                
                # Mostrar resultado
                print(f"\n  ⏱️ {interval}:")
                print(f"    • Trades: {result['total_trades']}")
                print(f"    • Win Rate: {result['win_rate']}%")
                print(f"    • Return: {result['total_return']}%")
                print(f"    • Final Capital: ${result['final_capital']}")
                print(f"    • Max Drawdown: {result['max_drawdown']}%")
                print(f"    • Profit Factor: {result['profit_factor']}")
    
    # Resumen general
    print("\n" + "="*60)
    print("RESUMEN GENERAL")
    print("="*60)
    
    results_df = pd.DataFrame(all_results)
    
    # Mejor configuración
    best_result = results_df.loc[results_df['total_return'].idxmax()]
    print(f"\n🏆 MEJOR CONFIGURACIÓN:")
    print(f"   Symbol: {best_result['symbol']}")
    print(f"   Timeframe: {best_result['interval']}")
    print(f"   Return: {best_result['total_return']}%")
    print(f"   Win Rate: {best_result['win_rate']}%")
    
    # Promedios por timeframe
    print(f"\n📈 PROMEDIOS POR TIMEFRAME:")
    for interval in intervals:
        interval_results = results_df[results_df['interval'] == interval]
        avg_return = interval_results['total_return'].mean()
        avg_winrate = interval_results['win_rate'].mean()
        avg_trades = interval_results['total_trades'].mean()
        
        print(f"\n  {interval}:")
        print(f"    • Avg Return: {avg_return:.2f}%")
        print(f"    • Avg Win Rate: {avg_winrate:.2f}%")
        print(f"    • Avg Trades: {avg_trades:.0f}")
    
    # Guardar resultados
    results_df.to_csv('backtest_results.csv', index=False)
    print(f"\n💾 Resultados guardados en backtest_results.csv")
    
    # Estadísticas finales
    print(f"\n📊 ESTADÍSTICAS GLOBALES:")
    print(f"   Total de configuraciones testeadas: {len(all_results)}")
    print(f"   Configuraciones rentables: {len(results_df[results_df['total_return'] > 0])}")
    print(f"   Retorno promedio: {results_df['total_return'].mean():.2f}%")
    print(f"   Mejor retorno: {results_df['total_return'].max():.2f}%")
    print(f"   Peor retorno: {results_df['total_return'].min():.2f}%")
    
    return results_df

if __name__ == "__main__":
    # Ejecutar backtest
    asyncio.run(run_complete_backtest())