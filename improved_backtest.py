#!/usr/bin/env python3
"""
Sistema de Backtesting MEJORADO con filtros para reducir errores
Incluye: Filtro de tendencia, ATR dinámico, confirmación de señales
"""

import asyncio
import httpx
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =====================================
# CONFIGURACIÓN MEJORADA
# =====================================
INITIAL_CAPITAL = 220.0
MAX_RISK_PER_TRADE = 0.02  # 2%
DEFAULT_LEVERAGE = 3
COMMISSION = 0.0004  # 0.04% por trade
MIN_CONFIDENCE = 65  # Balance entre calidad y cantidad

class ImprovedBacktestEngine:
    """Motor de backtesting mejorado con filtros adicionales"""
    
    def __init__(self, capital: float = INITIAL_CAPITAL):
        self.initial_capital = capital
        self.capital = capital
        self.trades = []
        self.positions = []
        self.equity_curve = []
        
    async def fetch_historical_data(self, symbol: str, interval: str, days: int = 90) -> pd.DataFrame:
        """Obtiene datos históricos de Binance"""
        
        interval_map = {
            '15m': '15m',
            '1h': '1h', 
            '4h': '4h'
        }
        
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
                    logger.error(f"Error fetching {symbol} data: {e}")
                    break
                
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
        
        # =====================================
        # NUEVOS INDICADORES TÉCNICOS
        # =====================================
        
        # 1. Media móviles para tendencia
        df['ma_20'] = df['close'].rolling(20).mean()
        df['ma_50'] = df['close'].rolling(50).mean()
        df['ma_200'] = df['close'].rolling(200).mean()
        
        # 2. ATR para volatilidad
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['atr'] = true_range.rolling(14).mean()
        df['atr_percent'] = (df['atr'] / df['close']) * 100
        
        # 3. RSI para sobrecompra/sobreventa
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # 4. Volumen promedio
        df['volume_ma'] = df['quote_volume'].rolling(20).mean()
        df['volume_ratio'] = df['quote_volume'] / df['volume_ma']
        
        # 5. Tendencia
        df['trend'] = 'NEUTRAL'
        df.loc[df['close'] > df['ma_50'], 'trend'] = 'UP'
        df.loc[df['close'] < df['ma_50'], 'trend'] = 'DOWN'
        
        # 6. Detectar rango lateral
        df['high_20'] = df['high'].rolling(20).max()
        df['low_20'] = df['low'].rolling(20).min()
        df['range_percent'] = ((df['high_20'] - df['low_20']) / df['close']) * 100
        df['is_ranging'] = df['range_percent'] < 5  # Menos de 5% de rango = lateral
        
        # Indicadores originales
        df['returns'] = df['close'].pct_change()
        df['price_change_pct'] = ((df['close'] - df['open']) / df['open']) * 100
        df['range_position'] = (df['close'] - df['low']) / (df['high'] - df['low'])
        df['range_position'].fillna(0.5, inplace=True)
        
        # Cambio 24h
        periods_24h = {
            '15m': 96,
            '1h': 24,
            '4h': 6
        }
        
        df['change_24h'] = df['close'].pct_change(periods_24h[interval]) * 100
        df['volume_24h'] = df['quote_volume'].rolling(periods_24h[interval]).sum()
        df['high_24h'] = df['high'].rolling(periods_24h[interval]).max()
        df['low_24h'] = df['low'].rolling(periods_24h[interval]).min()
        
        return df
    
    def generate_improved_signal(self, row: pd.Series, prev_row: pd.Series = None) -> Optional[Dict]:
        """
        Genera señal MEJORADA con múltiples filtros
        """
        
        # Verificar que tenemos todos los datos necesarios
        required_cols = ['change_24h', 'range_position', 'trend', 'rsi', 
                        'volume_ratio', 'atr_percent', 'is_ranging']
        
        for col in required_cols:
            if col not in row or pd.isna(row[col]):
                return None
        
        price = row['close']
        change = row['change_24h']
        price_position = row['range_position']
        volume = row['volume_24h'] if not pd.isna(row['volume_24h']) else row['quote_volume']
        
        signal_type = None
        confidence = 0
        reasons = []
        
        # =====================================
        # FILTRO 1: NO OPERAR EN RANGO LATERAL EXTREMO
        # =====================================
        if row['is_ranging'] and row['range_percent'] < 3:  # Solo si rango muy estrecho
            return None
        
        # =====================================
        # FILTRO 2: VOLUMEN MÍNIMO
        # =====================================
        if row['volume_ratio'] < 0.5:  # Relajado a 50% del promedio
            return None
        
        # =====================================
        # SEÑALES MEJORADAS CON CONFIRMACIÓN
        # =====================================
        
        # LONG SIGNALS
        if row['trend'] == 'UP':  # Solo LONG en tendencia alcista
            
            # Señal 1: Pullback en tendencia alcista
            if change < -1 and change > -3 and row['rsi'] < 40:
                signal_type = "LONG"
                confidence = 75
                reasons.append("Pullback en tendencia alcista con RSI oversold")
            
            # Señal 2: Rebote desde soporte con volumen
            elif change < -2 and price_position < 0.3 and row['volume_ratio'] > 1.5:
                signal_type = "LONG"
                confidence = 80
                reasons.append("Rebote desde soporte con alto volumen")
                
            # Señal 3: Continuación de tendencia
            elif change > 0 and change < 2 and row['rsi'] > 45 and row['rsi'] < 70:
                signal_type = "LONG"
                confidence = 65
                reasons.append("Continuación de tendencia alcista")
        
        # SHORT SIGNALS
        elif row['trend'] == 'DOWN':  # Solo SHORT en tendencia bajista
            
            # Señal 1: Rally en tendencia bajista
            if change > 1 and change < 3 and row['rsi'] > 60:
                signal_type = "SHORT"
                confidence = 75
                reasons.append("Rally en tendencia bajista con RSI overbought")
            
            # Señal 2: Rechazo desde resistencia con volumen
            elif change > 2 and price_position > 0.7 and row['volume_ratio'] > 1.5:
                signal_type = "SHORT"
                confidence = 80
                reasons.append("Rechazo desde resistencia con alto volumen")
                
            # Señal 3: Continuación bajista
            elif change < 0 and change > -2 and row['rsi'] < 50 and row['rsi'] > 30:
                signal_type = "SHORT"
                confidence = 70
                reasons.append("Continuación de tendencia bajista")
        
        # =====================================
        # SEÑALES ESPECIALES (Alta probabilidad)
        # =====================================
        
        # Reversión extrema con divergencia
        if row['rsi'] < 25 and change < -4 and price_position < 0.2:
            if prev_row is not None and row['low'] > prev_row['low']:  # Higher low
                signal_type = "LONG"
                confidence = 85
                reasons.append("Divergencia alcista con RSI extremo")
        
        elif row['rsi'] > 75 and change > 4 and price_position > 0.8:
            if prev_row is not None and row['high'] < prev_row['high']:  # Lower high
                signal_type = "SHORT"
                confidence = 85
                reasons.append("Divergencia bajista con RSI extremo")
        
        # =====================================
        # VALIDACIÓN FINAL
        # =====================================
        
        if signal_type and confidence >= MIN_CONFIDENCE:
            
            # Calcular Stop Loss dinámico basado en ATR
            atr_multiplier = 2.0  # 2x ATR para stop loss
            atr_stop = row['atr'] * atr_multiplier
            
            if signal_type == "LONG":
                stop_loss = price - atr_stop
                take_profit = price + (atr_stop * 2)  # Risk:Reward 1:2
                
                # Validar que stop no sea muy ajustado
                if (price - stop_loss) / price < 0.015:  # Mínimo 1.5% de stop
                    stop_loss = price * 0.985
                    take_profit = price * 1.03
                    
            else:  # SHORT
                stop_loss = price + atr_stop
                take_profit = price - (atr_stop * 2)
                
                if (stop_loss - price) / price < 0.015:
                    stop_loss = price * 1.015
                    take_profit = price * 0.97
            
            # Verificar Risk:Reward mínimo
            risk = abs(price - stop_loss)
            reward = abs(take_profit - price)
            if reward / risk < 1.5:
                return None  # No operar si R:R < 1.5
            
            return {
                'timestamp': row['timestamp'],
                'type': signal_type,
                'entry_price': price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'confidence': confidence,
                'change_24h': change,
                'price_position': price_position,
                'volume': volume,
                'rsi': row['rsi'],
                'trend': row['trend'],
                'atr_percent': row['atr_percent'],
                'reasons': reasons
            }
        
        return None
    
    def execute_trade(self, signal: Dict, current_price: float) -> Dict:
        """Ejecuta un trade y calcula resultado"""
        
        # Calcular tamaño de posición basado en riesgo
        risk_amount = self.capital * MAX_RISK_PER_TRADE
        stop_distance = abs(signal['entry_price'] - signal['stop_loss']) / signal['entry_price']
        position_size = (risk_amount / stop_distance) * DEFAULT_LEVERAGE
        
        # Limitar posición al 50% del capital con leverage
        max_position = self.capital * 0.5 * DEFAULT_LEVERAGE
        position_size = min(position_size, max_position)
        
        # Comisión de entrada
        entry_commission = position_size * COMMISSION
        
        # Calcular resultado
        if signal['type'] == 'LONG':
            if current_price >= signal['take_profit']:
                pnl_pct = (signal['take_profit'] - signal['entry_price']) / signal['entry_price']
                exit_price = signal['take_profit']
                result = 'TP'
            elif current_price <= signal['stop_loss']:
                pnl_pct = (signal['stop_loss'] - signal['entry_price']) / signal['entry_price']
                exit_price = signal['stop_loss']
                result = 'SL'
            else:
                pnl_pct = (current_price - signal['entry_price']) / signal['entry_price']
                exit_price = current_price
                result = 'CLOSE'
        else:  # SHORT
            if current_price <= signal['take_profit']:
                pnl_pct = (signal['entry_price'] - signal['take_profit']) / signal['entry_price']
                exit_price = signal['take_profit']
                result = 'TP'
            elif current_price >= signal['stop_loss']:
                pnl_pct = (signal['entry_price'] - signal['stop_loss']) / signal['entry_price']
                exit_price = signal['stop_loss']
                result = 'SL'
            else:
                pnl_pct = (signal['entry_price'] - current_price) / signal['entry_price']
                exit_price = current_price
                result = 'CLOSE'
        
        # Calcular PnL real (corregido)
        pnl_amount = risk_amount * (pnl_pct / stop_distance) * DEFAULT_LEVERAGE
        exit_commission = position_size * COMMISSION
        net_pnl = pnl_amount - entry_commission - exit_commission
        
        # Actualizar capital
        self.capital += net_pnl
        
        return {
            'entry_time': signal['timestamp'],
            'type': signal['type'],
            'entry_price': signal['entry_price'],
            'exit_price': exit_price,
            'stop_loss': signal['stop_loss'],
            'take_profit': signal['take_profit'],
            'result': result,
            'gross_pnl': pnl_amount,
            'commission': entry_commission + exit_commission,
            'net_pnl': net_pnl,
            'capital_after': self.capital,
            'confidence': signal['confidence'],
            'trend': signal.get('trend', 'UNKNOWN'),
            'rsi': signal.get('rsi', 0),
            'reasons': signal.get('reasons', [])
        }
    
    async def run_backtest(self, symbol: str, interval: str) -> Dict:
        """Ejecuta backtest mejorado"""
        
        logger.info(f"Starting improved backtest for {symbol} on {interval}")
        
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
        bars_since_trade = 0
        
        for idx in range(1, len(df)):
            row = df.iloc[idx]
            prev_row = df.iloc[idx-1]
            
            bars_since_trade += 1
            
            # Si hay posición activa, verificar salida
            if active_position:
                trade_result = self.execute_trade(active_position, row['close'])
                
                if trade_result['result'] in ['TP', 'SL']:
                    self.trades.append(trade_result)
                    active_position = None
                    self.equity_curve.append(self.capital)
                    bars_since_trade = 0
            
            # Buscar nueva señal (con cooldown de 3 barras)
            if not active_position and bars_since_trade >= 3:
                signal = self.generate_improved_signal(row, prev_row)
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
        
        # Max drawdown
        equity_series = pd.Series(self.equity_curve)
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max * 100
        max_drawdown = drawdown.min()
        
        # Profit factor
        total_wins = winning_trades['net_pnl'].sum() if len(winning_trades) > 0 else 0
        total_losses = abs(losing_trades['net_pnl'].sum()) if len(losing_trades) > 0 else 1
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Sharpe Ratio
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

async def run_improved_backtest():
    """Ejecuta backtest mejorado"""
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT']
    intervals = ['15m', '1h', '4h']
    
    all_results = []
    
    print("="*60)
    print("BACKTEST MEJORADO - SISTEMA CON FILTROS")
    print(f"Capital Inicial: ${INITIAL_CAPITAL}")
    print(f"Período: Últimos 90 días")
    print(f"Riesgo por Trade: {MAX_RISK_PER_TRADE*100}%")
    print(f"Leverage: {DEFAULT_LEVERAGE}x")
    print(f"Confianza Mínima: {MIN_CONFIDENCE}%")
    print("="*60)
    print("\nFILTROS APLICADOS:")
    print("✓ Filtro de tendencia (MA50)")
    print("✓ Stop loss dinámico (ATR)")
    print("✓ RSI para sobrecompra/sobreventa")
    print("✓ Filtro de volumen")
    print("✓ Detección de rango lateral")
    print("✓ Confirmación de señales")
    print("="*60)
    
    for symbol in symbols:
        print(f"\n📊 Testing {symbol}...")
        
        for interval in intervals:
            engine = ImprovedBacktestEngine(INITIAL_CAPITAL)
            result = await engine.run_backtest(symbol, interval)
            
            if result:
                all_results.append(result)
                
                print(f"\n  ⏱️ {interval}:")
                print(f"    • Trades: {result['total_trades']}")
                if result['total_trades'] > 0:
                    print(f"    • Win Rate: {result.get('win_rate', 0)}%")
                    print(f"    • Return: {result['total_return']}%")
                    print(f"    • Final Capital: ${result['final_capital']}")
                    print(f"    • Max Drawdown: {result.get('max_drawdown', 0)}%")
                    print(f"    • Profit Factor: {result.get('profit_factor', 0)}")
                    print(f"    • Sharpe: {result.get('sharpe_ratio', 0)}")
                else:
                    print(f"    • No trades executed (filters too strict)")
    
    # Resumen general
    print("\n" + "="*60)
    print("RESUMEN GENERAL - SISTEMA MEJORADO")
    print("="*60)
    
    if all_results:
        results_df = pd.DataFrame(all_results)
        
        # Mejor configuración
        if not results_df.empty and len(results_df) > 0:
            best_idx = results_df['total_return'].idxmax()
            best_result = results_df.loc[best_idx]
            
            print(f"\n🏆 MEJOR CONFIGURACIÓN:")
            print(f"   Symbol: {best_result['symbol']}")
            print(f"   Timeframe: {best_result['interval']}")
            print(f"   Return: {best_result['total_return']}%")
            print(f"   Win Rate: {best_result['win_rate']}%")
            print(f"   Profit Factor: {best_result['profit_factor']}")
        
        # Comparación con sistema anterior
        print(f"\n📊 COMPARACIÓN CON SISTEMA ANTERIOR:")
        print(f"   Sistema Original:")
        print(f"     • Win Rate Promedio: ~35%")
        print(f"     • Muchas señales falsas")
        print(f"   Sistema Mejorado:")
        print(f"     • Win Rate Promedio: {results_df['win_rate'].mean():.1f}%")
        print(f"     • Señales filtradas y confirmadas")
        
        # Promedios por timeframe
        print(f"\n📈 PROMEDIOS POR TIMEFRAME:")
        for interval in intervals:
            interval_results = results_df[results_df['interval'] == interval]
            if not interval_results.empty:
                avg_return = interval_results['total_return'].mean()
                avg_winrate = interval_results['win_rate'].mean()
                avg_trades = interval_results['total_trades'].mean()
                avg_pf = interval_results['profit_factor'].mean()
                
                print(f"\n  {interval}:")
                print(f"    • Avg Return: {avg_return:.2f}%")
                print(f"    • Avg Win Rate: {avg_winrate:.2f}%")
                print(f"    • Avg Trades: {avg_trades:.0f}")
                print(f"    • Avg Profit Factor: {avg_pf:.2f}")
        
        # Guardar resultados
        results_df.to_csv('improved_backtest_results.csv', index=False)
        print(f"\n💾 Resultados guardados en improved_backtest_results.csv")
        
        # Estadísticas finales
        print(f"\n📊 ESTADÍSTICAS GLOBALES MEJORADAS:")
        print(f"   Total configuraciones: {len(all_results)}")
        print(f"   Configuraciones rentables: {len(results_df[results_df['total_return'] > 0])}")
        print(f"   Retorno promedio: {results_df['total_return'].mean():.2f}%")
        print(f"   Win Rate promedio: {results_df['win_rate'].mean():.2f}%")
        print(f"   Profit Factor promedio: {results_df['profit_factor'].mean():.2f}")
        
        # Recomendación final
        print(f"\n✅ RECOMENDACIÓN FINAL:")
        if results_df['win_rate'].mean() > 50:
            print("   El sistema mejorado muestra resultados prometedores")
            print("   Win rate > 50% indica buena probabilidad de éxito")
        else:
            print("   El sistema necesita ajustes adicionales")
            print("   Considerar agregar más filtros o cambiar estrategia")
    
    return results_df if all_results else pd.DataFrame()

if __name__ == "__main__":
    asyncio.run(run_improved_backtest())