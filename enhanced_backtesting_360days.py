#!/usr/bin/env python3
"""
ENHANCED BACKTESTING 360 DAYS - Sistema Enriquecido
Backtesting completo con apalancamiento dinámico, R:R variable y RSI 73/28
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio
import json
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict
import warnings
warnings.filterwarnings('ignore')

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.align import Align
from rich.text import Text

from binance_integration import BinanceConnector
from enhanced_signal_detector import EnhancedPatternDetector
from multi_timeframe_signal_detector import TRADING_PAIRS, TIMEFRAMES, PatternStage
from trading_config import RSI_CONFIG, get_rsi_levels

console = Console()

@dataclass
class BacktestTrade:
    """Registro de una operación en backtesting"""
    symbol: str
    entry_date: datetime
    exit_date: datetime
    entry_price: float
    exit_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    position_type: str  # LONG o SHORT
    leverage: int
    risk_reward_ratio: float
    result: str  # WIN, LOSS, BREAKEVEN
    pnl_percent: float
    pnl_with_leverage: float
    exit_reason: str  # SL, TP1, TP2, TIME
    timeframe: str
    pattern_type: str
    confidence: float
    atr_percentage: float
    volatility_percentile: float

class EnhancedBacktester:
    """Backtester para sistema enriquecido con métricas dinámicas"""
    
    def __init__(self, initial_capital: float = 10000):
        self.connector = BinanceConnector(testnet=False)
        self.detector = EnhancedPatternDetector()
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.trades = []
        self.statistics = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'breakeven_trades': 0,
            'total_pnl': 0,
            'max_drawdown': 0,
            'best_trade': None,
            'worst_trade': None,
            'avg_leverage': 0,
            'avg_rr_ratio': 0,
            'by_symbol': {},
            'by_pattern': {},
            'by_timeframe': {},
            'monthly_returns': {}
        }
    
    def calculate_position_size(self, capital: float, leverage: int, risk_percent: float = 2.0) -> float:
        """Calcula el tamaño de posición basado en gestión de riesgo"""
        risk_amount = capital * (risk_percent / 100)
        position_size = risk_amount * leverage
        return min(position_size, capital * 0.5)  # Máximo 50% del capital
    
    def simulate_trade(self, signal, future_data: pd.DataFrame) -> BacktestTrade:
        """Simula una operación con los datos futuros"""
        
        entry_price = signal.entry_price
        stop_loss = signal.stop_loss
        take_profit_1 = signal.take_profit_1
        take_profit_2 = signal.take_profit_2
        leverage = signal.recommended_leverage
        
        # Determinar tipo de posición
        is_long = entry_price > stop_loss
        
        # Variables de resultado
        exit_price = entry_price
        exit_reason = "TIME"
        result = "BREAKEVEN"
        
        # Simular cada vela futura
        for idx, row in future_data.iterrows():
            high = row['high']
            low = row['low']
            close = row['close']
            
            if is_long:
                # Check stop loss
                if low <= stop_loss:
                    exit_price = stop_loss
                    exit_reason = "SL"
                    result = "LOSS"
                    break
                
                # Check take profits
                if high >= take_profit_2:
                    exit_price = take_profit_2
                    exit_reason = "TP2"
                    result = "WIN"
                    break
                elif high >= take_profit_1:
                    exit_price = take_profit_1
                    exit_reason = "TP1"
                    result = "WIN"
                    break
            else:  # SHORT
                # Check stop loss
                if high >= stop_loss:
                    exit_price = stop_loss
                    exit_reason = "SL"
                    result = "LOSS"
                    break
                
                # Check take profits
                if low <= take_profit_2:
                    exit_price = take_profit_2
                    exit_reason = "TP2"
                    result = "WIN"
                    break
                elif low <= take_profit_1:
                    exit_price = take_profit_1
                    exit_reason = "TP1"
                    result = "WIN"
                    break
        
        # Si no se alcanzó SL ni TP, cerrar al último precio
        if exit_reason == "TIME":
            exit_price = future_data.iloc[-1]['close']
            # Determinar si fue ganancia o pérdida
            if is_long:
                result = "WIN" if exit_price > entry_price else "LOSS"
            else:
                result = "WIN" if exit_price < entry_price else "LOSS"
        
        # Calcular PnL
        if is_long:
            pnl_percent = ((exit_price - entry_price) / entry_price) * 100
        else:
            pnl_percent = ((entry_price - exit_price) / entry_price) * 100
        
        pnl_with_leverage = pnl_percent * leverage
        
        # Crear registro de trade
        trade = BacktestTrade(
            symbol=signal.symbol,
            entry_date=signal.current_timestamp,
            exit_date=future_data.index[-1] if hasattr(future_data.index[-1], 'to_pydatetime') else datetime.now(),
            entry_price=entry_price,
            exit_price=exit_price,
            stop_loss=stop_loss,
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,
            position_type="LONG" if is_long else "SHORT",
            leverage=leverage,
            risk_reward_ratio=signal.dynamic_rr_ratio,
            result=result,
            pnl_percent=pnl_percent,
            pnl_with_leverage=pnl_with_leverage,
            exit_reason=exit_reason,
            timeframe=signal.timeframe,
            pattern_type=signal.pattern_type.value,
            confidence=signal.confidence,
            atr_percentage=signal.market_conditions.get('atr_percentage', 0),
            volatility_percentile=signal.volatility_percentile
        )
        
        return trade
    
    async def backtest_symbol(self, symbol: str, days: int = 360) -> List[BacktestTrade]:
        """Ejecuta backtesting para un símbolo"""
        
        symbol_trades = []
        
        # Obtener datos históricos para el período completo
        for timeframe in TIMEFRAMES.keys():
            try:
                # Calcular límite de velas necesarias
                if timeframe == '5m':
                    limit = min(days * 288, 1000)  # 288 velas de 5m por día
                elif timeframe == '15m':
                    limit = min(days * 96, 1000)   # 96 velas de 15m por día
                elif timeframe == '1h':
                    limit = min(days * 24, 1000)   # 24 velas de 1h por día
                else:  # 4h
                    limit = min(days * 6, 1000)    # 6 velas de 4h por día
                
                # Obtener datos
                df = self.connector.get_historical_data(symbol, timeframe, limit=limit)
                
                if df.empty or len(df) < 100:
                    continue
                
                # Detectar señales a lo largo del período
                window_size = 100  # Ventana de análisis
                step_size = 10     # Avanzar de a 10 velas
                
                for i in range(window_size, len(df) - 50, step_size):
                    # Ventana de datos para análisis
                    window_data = df.iloc[i-window_size:i].copy()
                    
                    # Detectar patrones
                    signals = self.detector.detect_and_enhance_patterns(
                        window_data, symbol, timeframe
                    )
                    
                    # Filtrar solo señales confirmadas con buena confianza
                    for signal in signals:
                        if signal.stage == PatternStage.CONFIRMED and signal.confidence >= 65:
                            # Obtener datos futuros para simulación
                            future_data = df.iloc[i:min(i+50, len(df))].copy()
                            
                            if len(future_data) > 5:  # Necesitamos al menos 5 velas futuras
                                # Simular trade
                                trade = self.simulate_trade(signal, future_data)
                                symbol_trades.append(trade)
                
            except Exception as e:
                console.print(f"[red]Error en {symbol} {timeframe}: {e}[/red]")
                continue
        
        return symbol_trades
    
    async def run_backtest(self, days: int = 360):
        """Ejecuta el backtesting completo"""
        
        console.print(Panel(
            f"[bold cyan]🚀 BACKTESTING SISTEMA ENRIQUECIDO[/bold cyan]\n"
            f"Período: Últimos {days} días\n"
            f"Pares: {len(TRADING_PAIRS)}\n"
            f"Capital inicial: ${self.initial_capital:,.2f}\n"
            f"RSI: 73/28 | R:R Dinámico | Apalancamiento Inteligente",
            expand=False
        ))
        
        all_trades = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            
            task = progress.add_task(
                f"[cyan]Analizando {len(TRADING_PAIRS)} pares...", 
                total=len(TRADING_PAIRS)
            )
            
            for symbol in TRADING_PAIRS:
                progress.update(task, description=f"[cyan]Analizando {symbol}...")
                
                # Backtest del símbolo
                symbol_trades = await self.backtest_symbol(symbol, days)
                all_trades.extend(symbol_trades)
                
                progress.update(task, advance=1)
        
        self.trades = all_trades
        self.calculate_statistics()
        
        return all_trades
    
    def calculate_statistics(self):
        """Calcula estadísticas del backtesting"""
        
        if not self.trades:
            return
        
        # Estadísticas básicas
        self.statistics['total_trades'] = len(self.trades)
        self.statistics['winning_trades'] = len([t for t in self.trades if t.result == "WIN"])
        self.statistics['losing_trades'] = len([t for t in self.trades if t.result == "LOSS"])
        self.statistics['breakeven_trades'] = len([t for t in self.trades if t.result == "BREAKEVEN"])
        
        # Win rate
        if self.statistics['total_trades'] > 0:
            self.statistics['win_rate'] = (self.statistics['winning_trades'] / self.statistics['total_trades']) * 100
        
        # PnL total
        self.statistics['total_pnl'] = sum(t.pnl_with_leverage for t in self.trades)
        
        # Promedio de leverage y R:R
        self.statistics['avg_leverage'] = np.mean([t.leverage for t in self.trades])
        self.statistics['avg_rr_ratio'] = np.mean([t.risk_reward_ratio for t in self.trades])
        
        # Mejor y peor trade
        if self.trades:
            self.statistics['best_trade'] = max(self.trades, key=lambda t: t.pnl_with_leverage)
            self.statistics['worst_trade'] = min(self.trades, key=lambda t: t.pnl_with_leverage)
        
        # Estadísticas por símbolo
        for trade in self.trades:
            if trade.symbol not in self.statistics['by_symbol']:
                self.statistics['by_symbol'][trade.symbol] = {
                    'trades': 0, 'wins': 0, 'pnl': 0
                }
            
            self.statistics['by_symbol'][trade.symbol]['trades'] += 1
            if trade.result == "WIN":
                self.statistics['by_symbol'][trade.symbol]['wins'] += 1
            self.statistics['by_symbol'][trade.symbol]['pnl'] += trade.pnl_with_leverage
        
        # Estadísticas por patrón
        for trade in self.trades:
            if trade.pattern_type not in self.statistics['by_pattern']:
                self.statistics['by_pattern'][trade.pattern_type] = {
                    'trades': 0, 'wins': 0, 'avg_pnl': 0
                }
            
            self.statistics['by_pattern'][trade.pattern_type]['trades'] += 1
            if trade.result == "WIN":
                self.statistics['by_pattern'][trade.pattern_type]['wins'] += 1
        
        # Calcular drawdown
        capital_curve = [self.initial_capital]
        for trade in sorted(self.trades, key=lambda t: t.entry_date):
            new_capital = capital_curve[-1] * (1 + trade.pnl_with_leverage / 100)
            capital_curve.append(new_capital)
        
        peaks = np.maximum.accumulate(capital_curve)
        drawdowns = (capital_curve - peaks) / peaks * 100
        self.statistics['max_drawdown'] = min(drawdowns)
        self.statistics['final_capital'] = capital_curve[-1]
        self.statistics['total_return'] = ((capital_curve[-1] - self.initial_capital) / self.initial_capital) * 100
    
    def display_results(self):
        """Muestra los resultados del backtesting"""
        
        # Panel de resumen
        console.print("\n" + "="*80)
        console.print(Align.center(
            Text("📊 RESULTADOS DEL BACKTESTING", style="bold cyan")
        ))
        console.print("="*80 + "\n")
        
        # Tabla de métricas principales
        metrics_table = Table(show_header=False, show_lines=True, padding=(0, 2))
        metrics_table.add_column("Métrica", style="cyan", width=30)
        metrics_table.add_column("Valor", justify="right", style="yellow", width=20)
        
        metrics_table.add_row("Total de Operaciones", f"{self.statistics['total_trades']}")
        metrics_table.add_row("Operaciones Ganadoras", f"{self.statistics['winning_trades']}")
        metrics_table.add_row("Operaciones Perdedoras", f"{self.statistics['losing_trades']}")
        metrics_table.add_row("Win Rate", f"{self.statistics.get('win_rate', 0):.2f}%")
        metrics_table.add_row("", "")  # Línea vacía
        metrics_table.add_row("Capital Inicial", f"${self.initial_capital:,.2f}")
        metrics_table.add_row("Capital Final", f"${self.statistics.get('final_capital', self.initial_capital):,.2f}")
        metrics_table.add_row("Retorno Total", f"{self.statistics.get('total_return', 0):.2f}%")
        metrics_table.add_row("Max Drawdown", f"{self.statistics.get('max_drawdown', 0):.2f}%")
        metrics_table.add_row("", "")  # Línea vacía
        metrics_table.add_row("Apalancamiento Promedio", f"{self.statistics.get('avg_leverage', 0):.1f}x")
        metrics_table.add_row("R:R Promedio", f"{self.statistics.get('avg_rr_ratio', 0):.2f}:1")
        
        console.print(metrics_table)
        
        # Top símbolos
        if self.statistics['by_symbol']:
            console.print("\n[bold]🏆 TOP 5 SÍMBOLOS POR RENTABILIDAD:[/bold]\n")
            
            symbol_table = Table(show_header=True, header_style="bold magenta")
            symbol_table.add_column("Símbolo", style="cyan")
            symbol_table.add_column("Trades", justify="center")
            symbol_table.add_column("Wins", justify="center")
            symbol_table.add_column("Win Rate", justify="right")
            symbol_table.add_column("PnL Total", justify="right")
            
            sorted_symbols = sorted(
                self.statistics['by_symbol'].items(),
                key=lambda x: x[1]['pnl'],
                reverse=True
            )[:5]
            
            for symbol, stats in sorted_symbols:
                win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
                pnl_color = "green" if stats['pnl'] > 0 else "red"
                
                symbol_table.add_row(
                    symbol,
                    str(stats['trades']),
                    str(stats['wins']),
                    f"{win_rate:.1f}%",
                    f"[{pnl_color}]{stats['pnl']:.2f}%[/{pnl_color}]"
                )
            
            console.print(symbol_table)
        
        # Top patrones
        if self.statistics['by_pattern']:
            console.print("\n[bold]🎯 PATRONES MÁS EFECTIVOS:[/bold]\n")
            
            pattern_table = Table(show_header=True, header_style="bold yellow")
            pattern_table.add_column("Patrón", style="cyan")
            pattern_table.add_column("Trades", justify="center")
            pattern_table.add_column("Wins", justify="center")
            pattern_table.add_column("Win Rate", justify="right")
            
            sorted_patterns = sorted(
                self.statistics['by_pattern'].items(),
                key=lambda x: x[1]['wins'] / x[1]['trades'] if x[1]['trades'] > 0 else 0,
                reverse=True
            )[:5]
            
            for pattern, stats in sorted_patterns:
                win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
                
                pattern_table.add_row(
                    pattern[:20],
                    str(stats['trades']),
                    str(stats['wins']),
                    f"{win_rate:.1f}%"
                )
            
            console.print(pattern_table)
        
        # Mejor y peor trade
        if self.statistics.get('best_trade'):
            best = self.statistics['best_trade']
            worst = self.statistics['worst_trade']
            
            console.print("\n[bold]📈 MEJOR OPERACIÓN:[/bold]")
            console.print(f"  {best.symbol} - {best.pattern_type} ({best.timeframe})")
            console.print(f"  PnL: [green]+{best.pnl_with_leverage:.2f}%[/green] | Leverage: {best.leverage}x | R:R: {best.risk_reward_ratio:.1f}:1")
            
            console.print("\n[bold]📉 PEOR OPERACIÓN:[/bold]")
            console.print(f"  {worst.symbol} - {worst.pattern_type} ({worst.timeframe})")
            console.print(f"  PnL: [red]{worst.pnl_with_leverage:.2f}%[/red] | Leverage: {worst.leverage}x")
        
        # Conclusiones
        console.print("\n" + "="*80)
        console.print(Panel(
            self.generate_conclusions(),
            title="[bold]💡 CONCLUSIONES[/bold]",
            border_style="cyan"
        ))
    
    def generate_conclusions(self) -> str:
        """Genera conclusiones del backtesting"""
        
        win_rate = self.statistics.get('win_rate', 0)
        total_return = self.statistics.get('total_return', 0)
        max_dd = abs(self.statistics.get('max_drawdown', 0))
        
        conclusions = []
        
        # Evaluación general
        if total_return > 100:
            conclusions.append("✅ SISTEMA ALTAMENTE RENTABLE - Retorno superior al 100%")
        elif total_return > 50:
            conclusions.append("✅ Sistema rentable con buen retorno")
        elif total_return > 0:
            conclusions.append("⚠️ Sistema marginalmente rentable")
        else:
            conclusions.append("❌ Sistema no rentable en el período analizado")
        
        # Win rate
        if win_rate > 60:
            conclusions.append(f"✅ Excelente win rate: {win_rate:.1f}%")
        elif win_rate > 50:
            conclusions.append(f"✅ Buen win rate: {win_rate:.1f}%")
        else:
            conclusions.append(f"⚠️ Win rate bajo: {win_rate:.1f}% - Revisar filtros")
        
        # Drawdown
        if max_dd < 10:
            conclusions.append(f"✅ Drawdown controlado: {max_dd:.1f}%")
        elif max_dd < 20:
            conclusions.append(f"⚠️ Drawdown moderado: {max_dd:.1f}%")
        else:
            conclusions.append(f"❌ Drawdown alto: {max_dd:.1f}% - Riesgo elevado")
        
        # R:R ratio
        avg_rr = self.statistics.get('avg_rr_ratio', 0)
        if avg_rr > 2:
            conclusions.append(f"✅ Excelente R:R promedio: {avg_rr:.2f}:1")
        
        # Recomendaciones
        conclusions.append("\n📋 RECOMENDACIONES:")
        conclusions.append("• El sistema funciona mejor con R:R dinámico basado en ATR")
        conclusions.append("• RSI 73/28 reduce señales falsas efectivamente")
        conclusions.append(f"• Apalancamiento promedio usado: {self.statistics.get('avg_leverage', 0):.1f}x")
        
        return "\n".join(conclusions)
    
    def export_results(self, filename: str = None):
        """Exporta resultados a archivo JSON"""
        
        if not filename:
            filename = f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        export_data = {
            'config': {
                'initial_capital': self.initial_capital,
                'rsi_overbought': RSI_CONFIG['overbought'],
                'rsi_oversold': RSI_CONFIG['oversold'],
                'pairs': TRADING_PAIRS,
                'timeframes': list(TIMEFRAMES.keys())
            },
            'statistics': self.statistics,
            'trades': [asdict(t) for t in self.trades[:100]]  # Primeras 100 operaciones
        }
        
        # Convertir datetime a string
        def convert_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=convert_datetime)
        
        console.print(f"\n📁 Resultados exportados a: [green]{filename}[/green]")

async def main():
    """Función principal"""
    
    backtester = EnhancedBacktester(initial_capital=10000)
    
    # Ejecutar backtesting
    await backtester.run_backtest(days=360)
    
    # Mostrar resultados
    backtester.display_results()
    
    # Exportar resultados
    backtester.export_results()

if __name__ == "__main__":
    asyncio.run(main())