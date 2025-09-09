#!/usr/bin/env python3
"""
QUICK BACKTEST ENHANCED - Backtesting rápido del sistema enriquecido
Versión optimizada para prueba rápida (30 días, pares principales)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio
import json
from typing import Dict, List
import warnings
warnings.filterwarnings('ignore')

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from enhanced_backtesting_360days import EnhancedBacktester, BacktestTrade

console = Console()

async def quick_backtest():
    """Ejecuta un backtesting rápido con parámetros reducidos"""
    
    # Configuración reducida para prueba rápida
    TEST_PAIRS = ["BTCUSDT", "ETHUSDT", "AVAXUSDT", "DOGEUSDT", "PENGUUSDT"]  # 5 pares principales
    TEST_DAYS = 30  # Últimos 30 días
    
    console.print(Panel(
        "[bold cyan]🚀 BACKTESTING RÁPIDO - SISTEMA ENRIQUECIDO[/bold cyan]\n"
        f"Período: Últimos {TEST_DAYS} días\n"
        f"Pares de prueba: {', '.join([p.replace('USDT', '') for p in TEST_PAIRS])}\n"
        f"Capital inicial: $10,000\n"
        f"Configuración: RSI 73/28 | R:R Dinámico | Apalancamiento Inteligente",
        expand=False
    ))
    
    # Crear backtester
    backtester = EnhancedBacktester(initial_capital=10000)
    
    # Sobrescribir la lista de pares para prueba rápida
    original_pairs = backtester.detector.trading_pairs if hasattr(backtester.detector, 'trading_pairs') else []
    
    all_trades = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        task = progress.add_task(
            f"[cyan]Analizando {len(TEST_PAIRS)} pares...", 
            total=len(TEST_PAIRS)
        )
        
        for symbol in TEST_PAIRS:
            progress.update(task, description=f"[cyan]Analizando {symbol}...")
            
            try:
                # Backtest del símbolo
                symbol_trades = await backtester.backtest_symbol(symbol, days=TEST_DAYS)
                all_trades.extend(symbol_trades)
                
                # Mostrar progreso
                if symbol_trades:
                    console.print(f"  ✓ {symbol}: {len(symbol_trades)} señales encontradas")
                
            except Exception as e:
                console.print(f"  ✗ Error en {symbol}: {str(e)[:50]}")
            
            progress.update(task, advance=1)
    
    # Procesar resultados
    backtester.trades = all_trades
    backtester.calculate_statistics()
    
    # Mostrar resultados resumidos
    console.print("\n" + "="*60)
    console.print("[bold cyan]📊 RESULTADOS DEL BACKTESTING RÁPIDO[/bold cyan]")
    console.print("="*60 + "\n")
    
    if all_trades:
        # Métricas principales
        total_trades = len(all_trades)
        winning_trades = len([t for t in all_trades if t.result == "WIN"])
        losing_trades = len([t for t in all_trades if t.result == "LOSS"])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        # PnL promedio
        avg_win = np.mean([t.pnl_with_leverage for t in all_trades if t.result == "WIN"]) if winning_trades > 0 else 0
        avg_loss = np.mean([t.pnl_with_leverage for t in all_trades if t.result == "LOSS"]) if losing_trades > 0 else 0
        
        # Tabla de resultados
        results_table = Table(show_header=False, show_lines=True)
        results_table.add_column("Métrica", style="cyan", width=30)
        results_table.add_column("Valor", justify="right", style="yellow")
        
        results_table.add_row("Total de Señales", str(total_trades))
        results_table.add_row("Señales Ganadoras", f"{winning_trades} ({win_rate:.1f}%)")
        results_table.add_row("Señales Perdedoras", f"{losing_trades} ({100-win_rate:.1f}%)")
        results_table.add_row("Ganancia Promedio", f"+{avg_win:.2f}%" if avg_win > 0 else f"{avg_win:.2f}%")
        results_table.add_row("Pérdida Promedio", f"{avg_loss:.2f}%")
        
        # Apalancamiento promedio
        avg_leverage = np.mean([t.leverage for t in all_trades])
        results_table.add_row("Apalancamiento Promedio", f"{avg_leverage:.1f}x")
        
        # R:R promedio
        avg_rr = np.mean([t.risk_reward_ratio for t in all_trades])
        results_table.add_row("R:R Promedio", f"{avg_rr:.2f}:1")
        
        console.print(results_table)
        
        # Desglose por símbolo
        console.print("\n[bold]📊 DESGLOSE POR SÍMBOLO:[/bold]\n")
        
        symbol_table = Table(show_header=True, header_style="bold magenta")
        symbol_table.add_column("Símbolo", style="cyan")
        symbol_table.add_column("Trades", justify="center")
        symbol_table.add_column("Win Rate", justify="right")
        symbol_table.add_column("Apal. Prom", justify="center")
        symbol_table.add_column("R:R Prom", justify="center")
        
        for symbol in TEST_PAIRS:
            symbol_trades = [t for t in all_trades if t.symbol == symbol]
            if symbol_trades:
                sym_wins = len([t for t in symbol_trades if t.result == "WIN"])
                sym_wr = (sym_wins / len(symbol_trades) * 100) if len(symbol_trades) > 0 else 0
                sym_lev = np.mean([t.leverage for t in symbol_trades])
                sym_rr = np.mean([t.risk_reward_ratio for t in symbol_trades])
                
                symbol_table.add_row(
                    symbol.replace("USDT", ""),
                    str(len(symbol_trades)),
                    f"{sym_wr:.1f}%",
                    f"{sym_lev:.1f}x",
                    f"{sym_rr:.1f}:1"
                )
        
        console.print(symbol_table)
        
        # Mejores trades
        if all_trades:
            best_trades = sorted(all_trades, key=lambda t: t.pnl_with_leverage, reverse=True)[:3]
            
            console.print("\n[bold]🏆 TOP 3 MEJORES TRADES:[/bold]\n")
            
            for i, trade in enumerate(best_trades, 1):
                console.print(
                    f"{i}. {trade.symbol} - {trade.pattern_type} ({trade.timeframe})\n"
                    f"   PnL: [green]+{trade.pnl_with_leverage:.2f}%[/green] | "
                    f"Leverage: {trade.leverage}x | R:R: {trade.risk_reward_ratio:.1f}:1"
                )
        
        # Conclusión rápida
        console.print("\n" + "="*60)
        
        conclusion = "✅ SISTEMA RENTABLE" if win_rate > 50 else "⚠️ SISTEMA NECESITA OPTIMIZACIÓN"
        color = "green" if win_rate > 50 else "yellow"
        
        console.print(Panel(
            f"[bold {color}]{conclusion}[/bold {color}]\n\n"
            f"Win Rate: {win_rate:.1f}%\n"
            f"El sistema muestra {'buenos' if win_rate > 50 else 'moderados'} resultados en el período analizado.\n"
            f"R:R dinámico promedio: {avg_rr:.2f}:1\n"
            f"Apalancamiento adaptativo promedio: {avg_leverage:.1f}x\n\n"
            f"[dim]Nota: Este es un backtesting rápido de 30 días.\n"
            f"Para resultados completos, ejecute el backtesting de 360 días.[/dim]",
            border_style=color
        ))
        
    else:
        console.print("[red]No se encontraron señales en el período analizado[/red]")
        console.print("[yellow]Esto puede deberse a:[/yellow]")
        console.print("  • Mercado lateral sin patrones claros")
        console.print("  • Umbrales RSI 73/28 muy estrictos")
        console.print("  • Período de análisis muy corto")

if __name__ == "__main__":
    asyncio.run(quick_backtest())