#!/usr/bin/env python3
"""
SHOW CURRENT SIGNALS - Muestra todas las señales actuales del mercado
"""

import asyncio
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns

from binance_integration import BinanceConnector
from multi_timeframe_signal_detector import PatternDetector, TRADING_PAIRS, TIMEFRAMES

console = Console()

async def get_all_current_signals():
    """Obtiene todas las señales actuales del mercado"""
    
    connector = BinanceConnector(testnet=False)
    detector = PatternDetector()
    
    all_signals = []
    
    # Escanear todos los pares
    for symbol in TRADING_PAIRS:
        for timeframe in TIMEFRAMES.keys():
            try:
                df = connector.get_historical_data(symbol, timeframe, limit=100)
                
                if not df.empty and len(df) >= 50:
                    signals = detector.detect_all_patterns(df, symbol, timeframe)
                    
                    # Filtrar señales con confianza mínima de 60%
                    for signal in signals:
                        if signal.confidence >= 60:
                            all_signals.append(signal)
                            
            except Exception as e:
                pass
    
    return all_signals

async def display_signals():
    """Muestra las señales de forma organizada"""
    
    console.print(Panel(
        "[bold cyan]🤖 BotphIA - Señales Actuales del Mercado[/bold cyan]\n" +
        f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        expand=False
    ))
    
    console.print("\n[yellow]Escaneando todos los pares...[/yellow]\n")
    
    signals = await get_all_current_signals()
    
    if not signals:
        console.print("[red]No se encontraron señales[/red]")
        return
    
    # Separar por stage
    confirmed = [s for s in signals if s.stage.value == "confirmed"]
    nearly = [s for s in signals if s.stage.value == "nearly"]
    forming = [s for s in signals if s.stage.value == "forming"]
    
    # SEÑALES CONFIRMADAS
    if confirmed:
        console.print("\n[bold green]✅ SEÑALES CONFIRMADAS - EJECUTAR AHORA[/bold green]")
        console.print("[green]Estas señales están listas para entrada inmediata[/green]\n")
        
        for sig in confirmed:
            action = "🟢 COMPRA" if "bottom" in sig.pattern_type.value or "support" in sig.pattern_type.value or "breakout" in sig.pattern_type.value else "🔴 VENTA"
            
            panel = Panel(
                f"[bold]{sig.symbol}[/bold] - {sig.timeframe}\n"
                f"Patrón: [yellow]{sig.pattern_type.value}[/yellow]\n"
                f"Confianza: [green]{sig.confidence:.1f}%[/green]\n"
                f"\n{action}\n"
                f"Entry: [bold]${sig.entry_price:.4f}[/bold]\n"
                f"Stop Loss: ${sig.stop_loss:.4f}\n"
                f"Take Profit 1: ${sig.take_profit_1:.4f}\n"
                f"Take Profit 2: ${sig.take_profit_2:.4f}\n"
                f"Risk/Reward: {sig.risk_reward_ratio:.2f}:1",
                title=f"[bold green]CONFIRMADA[/bold green]",
                border_style="green"
            )
            console.print(panel)
    
    # SEÑALES CASI COMPLETAS
    if nearly:
        console.print("\n[bold yellow]⏰ SEÑALES CASI COMPLETAS - PREPARAR ORDEN[/bold yellow]")
        console.print("[yellow]Estas señales están a punto de confirmarse[/yellow]\n")
        
        table = Table(show_lines=True)
        table.add_column("Par", style="cyan", width=10)
        table.add_column("TF", justify="center", width=5)
        table.add_column("Patrón", style="yellow", width=20)
        table.add_column("Conf %", justify="right", width=8)
        table.add_column("Entry", justify="right", width=12)
        table.add_column("Stop Loss", justify="right", width=12)
        table.add_column("TP1", justify="right", width=12)
        table.add_column("R:R", justify="center", width=6)
        
        for sig in nearly:
            table.add_row(
                sig.symbol,
                sig.timeframe,
                sig.pattern_type.value,
                f"{sig.confidence:.1f}%",
                f"${sig.entry_price:.4f}",
                f"${sig.stop_loss:.4f}",
                f"${sig.take_profit_1:.4f}",
                f"{sig.risk_reward_ratio:.2f}:1"
            )
        
        console.print(table)
    
    # SEÑALES FORMÁNDOSE
    if forming:
        console.print("\n[bold cyan]📈 SEÑALES FORMÁNDOSE - MONITOREAR[/bold cyan]")
        console.print("[cyan]Estas señales están en desarrollo[/cyan]\n")
        
        table = Table(show_lines=False)
        table.add_column("Par", style="cyan")
        table.add_column("TF", justify="center")
        table.add_column("Patrón", style="dim")
        table.add_column("Conf %", justify="right")
        
        for sig in forming[:10]:  # Solo mostrar las primeras 10
            table.add_row(
                sig.symbol,
                sig.timeframe,
                sig.pattern_type.value,
                f"{sig.confidence:.1f}%"
            )
        
        console.print(table)
    
    # RESUMEN
    console.print("\n" + "="*60)
    console.print("[bold]📊 RESUMEN[/bold]")
    console.print("="*60)
    console.print(f"Total señales detectadas: [bold]{len(signals)}[/bold]")
    console.print(f"  • Confirmadas: [green]{len(confirmed)}[/green]")
    console.print(f"  • Casi completas: [yellow]{len(nearly)}[/yellow]")
    console.print(f"  • Formándose: [cyan]{len(forming)}[/cyan]")
    
    # Top pares con señales
    pairs_count = {}
    for sig in signals:
        if sig.symbol not in pairs_count:
            pairs_count[sig.symbol] = 0
        pairs_count[sig.symbol] += 1
    
    if pairs_count:
        console.print("\n[bold]🏆 Pares más activos:[/bold]")
        sorted_pairs = sorted(pairs_count.items(), key=lambda x: x[1], reverse=True)
        for pair, count in sorted_pairs[:5]:
            console.print(f"  • {pair}: {count} señales")

if __name__ == "__main__":
    asyncio.run(display_signals())