#!/usr/bin/env python3
"""
Análisis detallado de trades perdedores
Identifica patrones específicos de pérdidas
"""

import asyncio
import httpx
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INITIAL_CAPITAL = 220.0
MAX_RISK_PER_TRADE = 0.02
DEFAULT_LEVERAGE = 3
COMMISSION = 0.0004

class LossAnalyzer:
    """Analizador de pérdidas en trades"""
    
    def __init__(self):
        self.losing_trades = []
        self.winning_trades = []
        self.all_trades = []
        
    async def fetch_and_analyze(self, symbol: str, interval: str, days: int = 30):
        """Obtiene datos y analiza trades"""
        
        # Obtener datos históricos
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
        
        all_data = []
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    'https://fapi.binance.com/fapi/v1/klines',
                    params={
                        'symbol': symbol,
                        'interval': interval,
                        'startTime': start_time,
                        'endTime': end_time,
                        'limit': 1500
                    }
                )
                
                if response.status_code == 200:
                    all_data = response.json()
            except Exception as e:
                logger.error(f"Error fetching data: {e}")
                return
        
        if not all_data:
            return
        
        # Convertir a DataFrame
        df = pd.DataFrame(all_data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 
            'volume', 'close_time', 'quote_volume', 'trades',
            'taker_buy_volume', 'taker_buy_quote', 'ignore'
        ])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume', 'quote_volume']:
            df[col] = df[col].astype(float)
        
        # Calcular indicadores
        df['change_pct'] = df['close'].pct_change() * 100
        df['range_position'] = (df['close'] - df['low']) / (df['high'] - df['low'])
        df['volatility'] = ((df['high'] - df['low']) / df['close']) * 100
        
        # Media móvil para tendencia
        df['ma_20'] = df['close'].rolling(20).mean()
        df['trend'] = df['close'] > df['ma_20']
        
        # Simular trades basados en nuestras señales
        self.simulate_trades(df, symbol)
    
    def simulate_trades(self, df: pd.DataFrame, symbol: str):
        """Simula trades y registra resultados"""
        
        for i in range(20, len(df) - 5):  # Necesitamos historia y futuro
            row = df.iloc[i]
            
            # Condiciones de entrada LONG (sistema original)
            if row['change_pct'] < -3 and row['range_position'] < 0.3:
                # Simulamos un LONG
                entry_price = row['close']
                stop_loss = entry_price * 0.98
                take_profit = entry_price * 1.04
                
                # Ver qué pasó en las siguientes velas
                future_data = df.iloc[i+1:i+6]  # Siguientes 5 velas
                
                trade_result = self.evaluate_trade(
                    entry_price, stop_loss, take_profit, 
                    future_data, 'LONG', row, df.iloc[i-5:i]
                )
                
                self.all_trades.append(trade_result)
                
                if trade_result['result'] == 'LOSS':
                    self.losing_trades.append(trade_result)
                else:
                    self.winning_trades.append(trade_result)
            
            # Condiciones de entrada SHORT
            elif row['change_pct'] > 3 and row['range_position'] > 0.7:
                entry_price = row['close']
                stop_loss = entry_price * 1.02
                take_profit = entry_price * 0.96
                
                future_data = df.iloc[i+1:i+6]
                
                trade_result = self.evaluate_trade(
                    entry_price, stop_loss, take_profit,
                    future_data, 'SHORT', row, df.iloc[i-5:i]
                )
                
                self.all_trades.append(trade_result)
                
                if trade_result['result'] == 'LOSS':
                    self.losing_trades.append(trade_result)
                else:
                    self.winning_trades.append(trade_result)
    
    def evaluate_trade(self, entry, sl, tp, future_data, direction, entry_row, past_data):
        """Evalúa qué pasó con el trade"""
        
        result = 'OPEN'
        exit_price = entry
        exit_reason = ''
        bars_to_exit = 0
        
        for idx, future_row in future_data.iterrows():
            bars_to_exit += 1
            
            if direction == 'LONG':
                # Verificar stop loss
                if future_row['low'] <= sl:
                    result = 'LOSS'
                    exit_price = sl
                    exit_reason = 'Stop Loss Hit'
                    break
                # Verificar take profit
                elif future_row['high'] >= tp:
                    result = 'WIN'
                    exit_price = tp
                    exit_reason = 'Take Profit Hit'
                    break
            else:  # SHORT
                if future_row['high'] >= sl:
                    result = 'LOSS'
                    exit_price = sl
                    exit_reason = 'Stop Loss Hit'
                    break
                elif future_row['low'] <= tp:
                    result = 'WIN'
                    exit_price = tp
                    exit_reason = 'Take Profit Hit'
                    break
        
        # Si no se cerró, usar último precio
        if result == 'OPEN':
            exit_price = future_data.iloc[-1]['close']
            if direction == 'LONG':
                result = 'WIN' if exit_price > entry else 'LOSS'
            else:
                result = 'WIN' if exit_price < entry else 'LOSS'
            exit_reason = 'Time Exit'
        
        # Analizar contexto de la pérdida
        loss_context = self.analyze_loss_context(
            entry_row, past_data, future_data, direction
        ) if result == 'LOSS' else {}
        
        return {
            'timestamp': entry_row['timestamp'],
            'direction': direction,
            'entry_price': entry,
            'stop_loss': sl,
            'take_profit': tp,
            'exit_price': exit_price,
            'result': result,
            'exit_reason': exit_reason,
            'bars_to_exit': bars_to_exit,
            'entry_conditions': {
                'change_pct': entry_row['change_pct'],
                'range_position': entry_row['range_position'],
                'volatility': entry_row['volatility'],
                'trend': entry_row['trend']
            },
            'loss_context': loss_context
        }
    
    def analyze_loss_context(self, entry_row, past_data, future_data, direction):
        """Analiza el contexto específico de una pérdida"""
        
        context = {
            'pattern': '',
            'main_cause': '',
            'market_condition': '',
            'could_avoid': False,
            'improvement': ''
        }
        
        # 1. ¿Fue una continuación de la tendencia previa?
        past_trend = past_data['close'].iloc[-1] - past_data['close'].iloc[0]
        
        if direction == 'LONG' and past_trend < 0:
            context['pattern'] = 'Cuchillo Cayendo'
            context['main_cause'] = 'Compró en caída continua sin confirmación de reversión'
            context['market_condition'] = 'Tendencia bajista fuerte'
            context['could_avoid'] = True
            context['improvement'] = 'Esperar señal de reversión (divergencia RSI, volumen alto)'
            
        elif direction == 'SHORT' and past_trend > 0:
            context['pattern'] = 'FOMO Rally'
            context['main_cause'] = 'Short en rally alcista sin confirmación de techo'
            context['market_condition'] = 'Tendencia alcista fuerte'
            context['could_avoid'] = True
            context['improvement'] = 'Esperar rechazo claro desde resistencia'
        
        # 2. ¿Volatilidad excesiva?
        if entry_row['volatility'] > 3:
            context['pattern'] += ' + Alta Volatilidad'
            context['main_cause'] += ' + Volatilidad excesiva causó stop prematuro'
            context['improvement'] += ' + Usar stop más amplio en alta volatilidad'
        
        # 3. ¿Entrada en rango lateral?
        price_range = past_data['high'].max() - past_data['low'].min()
        avg_price = past_data['close'].mean()
        range_pct = (price_range / avg_price) * 100
        
        if range_pct < 2:
            context['pattern'] += ' + Rango Lateral'
            context['main_cause'] += ' + Mercado lateralizado sin dirección clara'
            context['market_condition'] = 'Lateralización'
            context['could_avoid'] = True
            context['improvement'] += ' + No operar en rangos menores al 2%'
        
        # 4. ¿Movimiento posterior mostró la dirección correcta?
        if len(future_data) > 0:
            final_move = future_data['close'].iloc[-1] - entry_row['close']
            
            if direction == 'LONG' and final_move > 0:
                context['pattern'] += ' + Stop Hunt'
                context['main_cause'] += ' + Stop loss muy ajustado, dirección correcta'
                context['improvement'] += ' + Stop loss basado en estructura, no % fijo'
                
            elif direction == 'SHORT' and final_move < 0:
                context['pattern'] += ' + Stop Hunt'
                context['main_cause'] += ' + Stop loss muy ajustado, dirección correcta'
                context['improvement'] += ' + Stop loss basado en estructura, no % fijo'
        
        return context
    
    def generate_report(self):
        """Genera reporte detallado de pérdidas"""
        
        if not self.all_trades:
            print("No hay trades para analizar")
            return
        
        total_trades = len(self.all_trades)
        total_losses = len(self.losing_trades)
        total_wins = len(self.winning_trades)
        
        win_rate = (total_wins / total_trades) * 100 if total_trades > 0 else 0
        
        print("\n" + "="*60)
        print("ANÁLISIS DETALLADO DE PÉRDIDAS")
        print("="*60)
        
        print(f"\n📊 ESTADÍSTICAS GENERALES:")
        print(f"   Total trades: {total_trades}")
        print(f"   Trades ganadores: {total_wins} ({win_rate:.1f}%)")
        print(f"   Trades perdedores: {total_losses} ({100-win_rate:.1f}%)")
        
        if self.losing_trades:
            # Analizar patrones de pérdidas
            loss_patterns = {}
            loss_causes = {}
            avoidable_losses = 0
            
            print(f"\n🔍 ANÁLISIS DE {len(self.losing_trades)} PÉRDIDAS:")
            
            for i, loss in enumerate(self.losing_trades[:10], 1):  # Top 10 pérdidas
                print(f"\n  Pérdida #{i}:")
                print(f"    Fecha: {loss['timestamp']}")
                print(f"    Dirección: {loss['direction']}")
                print(f"    Entrada: ${loss['entry_price']:.2f}")
                print(f"    Stop Loss: ${loss['stop_loss']:.2f}")
                print(f"    Salida: {loss['exit_reason']}")
                print(f"    Barras hasta salida: {loss['bars_to_exit']}")
                
                if loss['loss_context']:
                    ctx = loss['loss_context']
                    print(f"    🎯 Patrón: {ctx['pattern']}")
                    print(f"    ❌ Causa: {ctx['main_cause']}")
                    print(f"    📈 Mercado: {ctx['market_condition']}")
                    
                    if ctx['could_avoid']:
                        print(f"    ⚠️ EVITABLE: Sí")
                        print(f"    💡 Mejora: {ctx['improvement']}")
                        avoidable_losses += 1
                    
                    # Contar patrones
                    pattern = ctx['pattern'].split('+')[0].strip() if ctx['pattern'] else 'Unknown'
                    loss_patterns[pattern] = loss_patterns.get(pattern, 0) + 1
                    
                    # Contar causas principales
                    cause = ctx['main_cause'].split('+')[0].strip() if ctx['main_cause'] else 'Unknown'
                    if cause:
                        loss_causes[cause] = loss_causes.get(cause, 0) + 1
                
                print(f"    Condiciones de entrada:")
                print(f"      • Cambio %: {loss['entry_conditions']['change_pct']:.2f}%")
                print(f"      • Posición en rango: {loss['entry_conditions']['range_position']:.2f}")
                print(f"      • Volatilidad: {loss['entry_conditions']['volatility']:.2f}%")
            
            # Resumen de patrones
            print(f"\n📊 PATRONES DE PÉRDIDAS MÁS COMUNES:")
            for pattern, count in sorted(loss_patterns.items(), key=lambda x: x[1], reverse=True):
                pct = (count / total_losses) * 100
                print(f"   • {pattern}: {count} veces ({pct:.1f}%)")
            
            print(f"\n❌ CAUSAS PRINCIPALES DE PÉRDIDAS:")
            for cause, count in sorted(loss_causes.items(), key=lambda x: x[1], reverse=True)[:5]:
                pct = (count / total_losses) * 100
                print(f"   • {cause}: {count} veces ({pct:.1f}%)")
            
            # Estadísticas de pérdidas evitables
            avoidable_pct = (avoidable_losses / total_losses) * 100 if total_losses > 0 else 0
            print(f"\n⚠️ PÉRDIDAS EVITABLES:")
            print(f"   • {avoidable_losses} de {total_losses} ({avoidable_pct:.1f}%)")
            print(f"   • Potencial mejora win rate: {win_rate + avoidable_pct:.1f}%")
            
            # Recomendaciones finales
            print(f"\n✅ RECOMENDACIONES PARA REDUCIR PÉRDIDAS:")
            
            recommendations = [
                ("No operar contra tendencia fuerte", "Cuchillo Cayendo" in loss_patterns),
                ("Usar ATR para stops dinámicos", any('Stop Hunt' in str(l.get('loss_context', {}).get('pattern', '')) for l in self.losing_trades)),
                ("Evitar rangos laterales < 2%", "Rango Lateral" in loss_patterns),
                ("Esperar confirmación de reversión", "Cuchillo Cayendo" in loss_patterns or "FOMO Rally" in loss_patterns),
                ("Ajustar stops en alta volatilidad", any(l['entry_conditions']['volatility'] > 3 for l in self.losing_trades))
            ]
            
            for rec, applies in recommendations:
                if applies:
                    print(f"   ✓ {rec}")

async def main():
    """Ejecuta análisis de pérdidas"""
    
    print("="*60)
    print("ANALIZANDO PÉRDIDAS DEL SISTEMA")
    print("="*60)
    
    analyzer = LossAnalyzer()
    
    # Analizar últimos 30 días
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    intervals = ['1h', '4h']
    
    for symbol in symbols:
        for interval in intervals:
            print(f"\nAnalizando {symbol} en {interval}...")
            await analyzer.fetch_and_analyze(symbol, interval, days=30)
    
    # Generar reporte
    analyzer.generate_report()

if __name__ == "__main__":
    asyncio.run(main())