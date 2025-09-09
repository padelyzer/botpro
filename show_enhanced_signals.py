#!/usr/bin/env python3
"""
SHOW ENHANCED SIGNALS - Muestra señales con apalancamiento y R:R dinámico
"""

import asyncio
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.columns import Columns
from rich.text import Text

from binance_integration import BinanceConnector
from enhanced_signal_detector import EnhancedPatternDetector
from multi_timeframe_signal_detector import TRADING_PAIRS, TIMEFRAMES

console = Console()

async def get_enhanced_signals():
    """Obtiene señales mejoradas con todas las métricas"""
    
    connector = BinanceConnector(testnet=False)
    detector = EnhancedPatternDetector()
    
    all_signals = []
    
    # Pares prioritarios para análisis rápido
    priority_pairs = ["BTCUSDT", "ETHUSDT", "AVAXUSDT", "DOGEUSDT", "PENGUUSDT", "UNIUSDT"]
    timeframes_to_check = ["15m", "1h", "4h"]
    
    for symbol in priority_pairs:
        for timeframe in timeframes_to_check:
            try:
                df = connector.get_historical_data(symbol, timeframe, limit=100)
                
                if not df.empty and len(df) >= 50:
                    signals = detector.detect_and_enhance_patterns(df, symbol, timeframe)
                    
                    # Filtrar por confianza mínima
                    for signal in signals:
                        if signal.confidence >= 60:
                            all_signals.append(signal)
                            
            except Exception as e:
                console.print(f"[red]Error procesando {symbol} {timeframe}: {e}[/red]")
    
    return all_signals

def create_signal_card(signal) -> Panel:
    """Crea una tarjeta visual para una señal mejorada"""
    
    # Determinar acción
    bullish_patterns = ["double_bottom", "support_bounce", "breakout", "hammer", "engulfing_bull"]
    is_buy = any(pattern in signal.pattern_type.value for pattern in bullish_patterns)
    
    action = "🟢 COMPRA" if is_buy else "🔴 VENTA"
    action_color = "green" if is_buy else "red"
    
    # Color según stage
    stage_colors = {
        "confirmed": "green",
        "nearly": "yellow",
        "forming": "cyan",
        "potential": "blue"
    }
    stage_color = stage_colors.get(signal.stage.value, "white")
    
    # Determinar emoji de riesgo según apalancamiento
    if signal.recommended_leverage <= 3:
        risk_emoji = "🟢"  # Bajo riesgo
        risk_text = "Bajo"
    elif signal.recommended_leverage <= 7:
        risk_emoji = "🟡"  # Riesgo medio
        risk_text = "Medio"
    else:
        risk_emoji = "🔴"  # Alto riesgo
        risk_text = "Alto"
    
    content = f"""
[bold {stage_color}]{signal.stage.value.upper()}[/bold {stage_color}]
[dim]{signal.pattern_type.value}[/dim]

[bold white]{signal.symbol}[/bold white] - {signal.timeframe}
Confianza: [{stage_color}]{signal.confidence:.1f}%[/{stage_color}]

{action}
Entry: [bold]${signal.entry_price:.4f}[/bold]
Stop Loss: ${signal.stop_loss:.4f}
TP1: ${signal.take_profit_1:.4f}
TP2: ${signal.take_profit_2:.4f}

[bold cyan]📊 MÉTRICAS DINÁMICAS[/bold cyan]
R:R Ratio: [yellow]{signal.dynamic_rr_ratio:.1f}:1[/yellow]
Apalancamiento: [bold]{signal.recommended_leverage}x[/bold]
Riesgo: {risk_emoji} {risk_text}

[bold blue]📈 VOLATILIDAD[/bold blue]
ATR: ${signal.atr_value:.4f}
Percentil Vol: {signal.volatility_percentile:.0f}%
ATR%: {signal.market_conditions.get('atr_percentage', 0):.2f}%

[bold magenta]💰 GESTIÓN[/bold magenta]
Tamaño Posición: {signal.position_size_percent:.1f}% capital
Max Pérdida: {signal.max_loss_percent:.1f}%
"""
    
    return Panel(
        content.strip(),
        title=f"[bold {action_color}]{signal.symbol}[/bold {action_color}]",
        border_style=stage_color,
        width=40
    )

async def display_enhanced_signals():
    """Muestra las señales mejoradas con formato rico"""
    
    console.print(Panel(
        "[bold cyan]🤖 BotphIA - Señales Mejoradas con Apalancamiento y R:R Dinámico[/bold cyan]\n" +
        f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        expand=False
    ))
    
    console.print("\n[yellow]Analizando mercados con métricas avanzadas...[/yellow]\n")
    
    signals = await get_enhanced_signals()
    
    if not signals:
        console.print("[red]No se encontraron señales[/red]")
        return
    
    # Separar por stage
    confirmed = [s for s in signals if s.stage.value == "confirmed"]
    nearly = [s for s in signals if s.stage.value == "nearly"]
    forming = [s for s in signals if s.stage.value == "forming"]
    
    # SEÑALES CONFIRMADAS
    if confirmed:
        console.print("\n[bold green]✅ SEÑALES CONFIRMADAS CON APALANCAMIENTO RECOMENDADO[/bold green]\n")
        
        # Mostrar en columnas de 2
        for i in range(0, len(confirmed), 2):
            cards = []
            for j in range(i, min(i+2, len(confirmed))):
                cards.append(create_signal_card(confirmed[j]))
            console.print(Columns(cards, equal=True, expand=False))
    
    # TABLA RESUMEN
    console.print("\n[bold]📊 TABLA RESUMEN DE TODAS LAS SEÑALES[/bold]\n")
    
    table = Table(show_lines=True)
    table.add_column("Par", style="cyan", width=10)
    table.add_column("TF", justify="center", width=5)
    table.add_column("Stage", justify="center", width=10)
    table.add_column("Conf%", justify="right", width=7)
    table.add_column("R:R", justify="center", width=6, style="yellow")
    table.add_column("Apal.", justify="center", width=6, style="magenta")
    table.add_column("Entry", justify="right", width=12)
    table.add_column("SL", justify="right", width=12)
    table.add_column("TP1", justify="right", width=12)
    table.add_column("Vol%", justify="right", width=6)
    
    # Ordenar por confianza
    all_signals_sorted = sorted(signals, key=lambda s: s.confidence, reverse=True)
    
    for sig in all_signals_sorted[:15]:  # Mostrar máximo 15
        # Color de stage
        stage_emoji = {
            "confirmed": "✅",
            "nearly": "⏰",
            "forming": "📈",
            "potential": "🔍"
        }.get(sig.stage.value, "")
        
        # Color de apalancamiento
        lev_color = "green" if sig.recommended_leverage <= 3 else "yellow" if sig.recommended_leverage <= 7 else "red"
        
        table.add_row(
            sig.symbol,
            sig.timeframe,
            f"{stage_emoji} {sig.stage.value[:7]}",
            f"{sig.confidence:.0f}%",
            f"{sig.dynamic_rr_ratio:.1f}:1",
            f"[{lev_color}]{sig.recommended_leverage}x[/{lev_color}]",
            f"${sig.entry_price:.4f}",
            f"${sig.stop_loss:.4f}",
            f"${sig.take_profit_1:.4f}",
            f"{sig.volatility_percentile:.0f}%"
        )
    
    console.print(table)
    
    # ESTADÍSTICAS DE APALANCAMIENTO
    console.print("\n[bold]📊 ANÁLISIS DE APALANCAMIENTO RECOMENDADO[/bold]\n")
    
    leverage_dist = {}
    for sig in signals:
        lev = sig.recommended_leverage
        if lev not in leverage_dist:
            leverage_dist[lev] = 0
        leverage_dist[lev] += 1
    
    console.print("Distribución de apalancamiento:")
    for lev in sorted(leverage_dist.keys()):
        count = leverage_dist[lev]
        bar = "█" * count
        risk = "🟢 Bajo" if lev <= 3 else "🟡 Medio" if lev <= 7 else "🔴 Alto"
        console.print(f"  {lev}x: {bar} ({count} señales) - {risk}")
    
    # RESUMEN
    avg_leverage = sum(s.recommended_leverage for s in signals) / len(signals)
    avg_rr = sum(s.dynamic_rr_ratio for s in signals) / len(signals)
    
    console.print(f"\n[bold]📈 RESUMEN[/bold]")
    console.print(f"  • Total señales: {len(signals)}")
    console.print(f"  • Confirmadas: {len(confirmed)}")
    console.print(f"  • Apalancamiento promedio: {avg_leverage:.1f}x")
    console.print(f"  • R:R promedio: {avg_rr:.1f}:1")
    
    # RECOMENDACIONES
    console.print("\n[bold cyan]💡 RECOMENDACIONES[/bold cyan]")
    console.print("  • Use apalancamiento menor en timeframes cortos (5m, 15m)")
    console.print("  • En alta volatilidad (>80 percentil), reduzca el apalancamiento")
    console.print("  • El R:R dinámico se ajusta a las condiciones del mercado")
    console.print("  • Respete siempre el stop loss calculado")

if __name__ == "__main__":
    asyncio.run(display_enhanced_signals())