#!/usr/bin/env python3
"""
DISPLAY COMPLETE SIGNALS - Muestra señales completas con todos los detalles
"""

import asyncio
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.columns import Columns
from rich.text import Text
from rich.align import Align

from binance_integration import BinanceConnector
from enhanced_signal_detector import EnhancedPatternDetector
from multi_timeframe_signal_detector import TRADING_PAIRS, TIMEFRAMES

console = Console()

async def get_complete_signals():
    """Obtiene señales con todos los detalles"""
    
    connector = BinanceConnector(testnet=False)
    detector = EnhancedPatternDetector()
    
    all_signals = []
    
    # Todos los pares configurados
    for symbol in TRADING_PAIRS:
        for timeframe in TIMEFRAMES.keys():
            try:
                df = connector.get_historical_data(symbol, timeframe, limit=100)
                
                if not df.empty and len(df) >= 50:
                    signals = detector.detect_and_enhance_patterns(df, symbol, timeframe)
                    
                    # Filtrar por confianza mínima
                    for signal in signals:
                        if signal.confidence >= 60:
                            all_signals.append(signal)
                            
            except Exception as e:
                pass
    
    return all_signals

def format_price(price: float, symbol: str) -> str:
    """Formatea precio según el símbolo"""
    if "BTC" in symbol or "ETH" in symbol:
        return f"${price:,.2f}"
    elif price > 100:
        return f"${price:.2f}"
    elif price > 1:
        return f"${price:.4f}"
    else:
        return f"${price:.6f}"

def create_detailed_signal_panel(signal) -> Panel:
    """Crea un panel detallado para cada señal"""
    
    # Determinar dirección
    bullish_patterns = ["double_bottom", "support_bounce", "breakout", "hammer", "engulfing_bull"]
    is_buy = any(pattern in signal.pattern_type.value for pattern in bullish_patterns)
    
    action = "🟢 LONG/COMPRA" if is_buy else "🔴 SHORT/VENTA"
    action_color = "green" if is_buy else "red"
    
    # Formato de precios
    entry_str = format_price(signal.entry_price, signal.symbol)
    sl_str = format_price(signal.stop_loss, signal.symbol)
    tp1_str = format_price(signal.take_profit_1, signal.symbol)
    tp2_str = format_price(signal.take_profit_2, signal.symbol)
    
    # Calcular distancias
    sl_distance = abs((signal.stop_loss - signal.entry_price) / signal.entry_price * 100)
    tp1_distance = abs((signal.take_profit_1 - signal.entry_price) / signal.entry_price * 100)
    tp2_distance = abs((signal.take_profit_2 - signal.entry_price) / signal.entry_price * 100)
    
    # Color según stage
    stage_colors = {
        "confirmed": "bold green",
        "nearly": "bold yellow",
        "forming": "cyan",
        "potential": "blue"
    }
    stage_color = stage_colors.get(signal.stage.value, "white")
    
    # Emoji de riesgo
    if signal.recommended_leverage <= 3:
        risk_level = "🟢 BAJO"
    elif signal.recommended_leverage <= 7:
        risk_level = "🟡 MEDIO"
    else:
        risk_level = "🔴 ALTO"
    
    content = f"""[{stage_color}]━━━ {signal.stage.value.upper()} ━━━[/{stage_color}]

[bold white]{signal.symbol}[/bold white] | {signal.timeframe} | {signal.pattern_type.value}
Confianza: [bold]{signal.confidence:.1f}%[/bold] | Volatilidad: {signal.volatility_percentile:.0f} percentil

[bold {action_color}]═══════════════════════════════════════[/bold {action_color}]
[bold {action_color}]{action}[/bold {action_color}]
[bold {action_color}]═══════════════════════════════════════[/bold {action_color}]

[bold cyan]📍 NIVELES DE TRADING:[/bold cyan]
┌─────────────────────────────────────┐
│ Entry:     [bold yellow]{entry_str:>12}[/bold yellow]         │
│ Stop Loss: [bold red]{sl_str:>12}[/bold red] (-{sl_distance:.2f}%) │
│ Target 1:  [bold green]{tp1_str:>12}[/bold green] (+{tp1_distance:.2f}%) │
│ Target 2:  [bold green]{tp2_str:>12}[/bold green] (+{tp2_distance:.2f}%) │
└─────────────────────────────────────┘

[bold magenta]⚙️ CONFIGURACIÓN:[/bold magenta]
• R:R Ratio: [bold yellow]{signal.dynamic_rr_ratio:.1f}:1[/bold yellow]
• Apalancamiento: [bold]{signal.recommended_leverage}x[/bold] ({risk_level})
• Tamaño Posición: {signal.position_size_percent:.1f}% del capital
• Pérdida Máxima: {signal.max_loss_percent:.1f}%

[bold blue]📊 MÉTRICAS DE MERCADO:[/bold blue]
• ATR: {format_price(signal.atr_value, signal.symbol)}
• ATR%: {signal.market_conditions.get('atr_percentage', 0):.2f}%
• Volatilidad Histórica: {signal.market_conditions.get('historical_volatility', 0):.1f}%
"""
    
    # Título del panel
    title = f"[bold {action_color}]{signal.symbol} - {signal.timeframe}[/bold {action_color}]"
    
    return Panel(
        content.strip(),
        title=title,
        border_style=stage_color.replace("bold ", ""),
        padding=(1, 2)
    )

async def display_complete_signals():
    """Muestra todas las señales con formato completo"""
    
    # Header
    console.print("\n")
    console.print(Panel(
        Align.center(
            Text("🤖 BotphIA - Sistema Completo de Señales", style="bold cyan"),
            vertical="middle"
        ),
        subtitle=f"[dim]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/dim]",
        border_style="cyan"
    ))
    
    console.print("\n[yellow]⏳ Escaneando todos los pares configurados...[/yellow]\n")
    
    # Obtener señales
    signals = await get_complete_signals()
    
    if not signals:
        console.print(Panel(
            "[red]No se encontraron señales en este momento[/red]\n"
            "[dim]El mercado puede estar en consolidación[/dim]",
            border_style="red"
        ))
        return
    
    # Separar por stage
    confirmed = [s for s in signals if s.stage.value == "confirmed"]
    nearly = [s for s in signals if s.stage.value == "nearly"]
    forming = [s for s in signals if s.stage.value == "forming"]
    
    # SEÑALES CONFIRMADAS - Mostrar paneles detallados
    if confirmed:
        console.print("\n" + "="*80)
        console.print(Align.center(
            Text("✅ SEÑALES CONFIRMADAS - EJECUTAR AHORA", style="bold green on black")
        ))
        console.print("="*80 + "\n")
        
        for signal in confirmed:
            console.print(create_detailed_signal_panel(signal))
            console.print()  # Espacio entre paneles
    
    # SEÑALES CASI COMPLETAS - Tabla compacta
    if nearly:
        console.print("\n" + "="*80)
        console.print(Align.center(
            Text("⏰ SEÑALES CASI COMPLETAS - PREPARAR ÓRDENES", style="bold yellow")
        ))
        console.print("="*80 + "\n")
        
        table = Table(show_lines=True, show_header=True, header_style="bold yellow")
        table.add_column("Par", style="cyan", width=10)
        table.add_column("TF", justify="center", width=5)
        table.add_column("Patrón", width=15)
        table.add_column("Conf", justify="right", width=6)
        table.add_column("Entry", justify="right", width=12, style="yellow")
        table.add_column("Stop Loss", justify="right", width=12, style="red")
        table.add_column("TP1", justify="right", width=12, style="green")
        table.add_column("TP2", justify="right", width=12, style="green")
        table.add_column("R:R", justify="center", width=6, style="yellow")
        table.add_column("Apal.", justify="center", width=6, style="magenta")
        
        for sig in nearly[:10]:
            table.add_row(
                sig.symbol,
                sig.timeframe,
                sig.pattern_type.value[:15],
                f"{sig.confidence:.0f}%",
                format_price(sig.entry_price, sig.symbol),
                format_price(sig.stop_loss, sig.symbol),
                format_price(sig.take_profit_1, sig.symbol),
                format_price(sig.take_profit_2, sig.symbol),
                f"{sig.dynamic_rr_ratio:.1f}:1",
                f"{sig.recommended_leverage}x"
            )
        
        console.print(table)
    
    # RESUMEN EJECUTIVO
    console.print("\n" + "="*80)
    console.print(Align.center(
        Text("📊 RESUMEN EJECUTIVO", style="bold blue")
    ))
    console.print("="*80 + "\n")
    
    # Crear tabla de resumen
    summary_table = Table(show_header=False, show_lines=False, padding=(0, 2))
    summary_table.add_column("Métrica", style="cyan")
    summary_table.add_column("Valor", justify="right", style="yellow")
    
    summary_table.add_row("Total Señales Detectadas", f"{len(signals)}")
    summary_table.add_row("Señales Confirmadas", f"{len(confirmed)}")
    summary_table.add_row("Señales Casi Completas", f"{len(nearly)}")
    summary_table.add_row("Señales Formándose", f"{len(forming)}")
    
    if signals:
        avg_confidence = sum(s.confidence for s in signals) / len(signals)
        avg_leverage = sum(s.recommended_leverage for s in signals) / len(signals)
        avg_rr = sum(s.dynamic_rr_ratio for s in signals) / len(signals)
        
        summary_table.add_row("", "")  # Línea vacía
        summary_table.add_row("Confianza Promedio", f"{avg_confidence:.1f}%")
        summary_table.add_row("Apalancamiento Promedio", f"{avg_leverage:.1f}x")
        summary_table.add_row("R:R Promedio", f"{avg_rr:.1f}:1")
    
    console.print(summary_table)
    
    # TOP OPORTUNIDADES
    if confirmed:
        console.print("\n" + "="*80)
        console.print(Align.center(
            Text("🏆 TOP 3 MEJORES OPORTUNIDADES", style="bold magenta")
        ))
        console.print("="*80 + "\n")
        
        # Ordenar por confianza y R:R
        top_signals = sorted(confirmed, 
                           key=lambda s: s.confidence * s.dynamic_rr_ratio, 
                           reverse=True)[:3]
        
        for i, sig in enumerate(top_signals, 1):
            action = "LONG" if "bottom" in sig.pattern_type.value or "support" in sig.pattern_type.value else "SHORT"
            console.print(
                f"[bold]{i}. {sig.symbol}[/bold] - {action}\n"
                f"   Entry: {format_price(sig.entry_price, sig.symbol)} | "
                f"SL: {format_price(sig.stop_loss, sig.symbol)} | "
                f"TP1: {format_price(sig.take_profit_1, sig.symbol)}\n"
                f"   Apalancamiento: {sig.recommended_leverage}x | "
                f"R:R: {sig.dynamic_rr_ratio:.1f}:1 | "
                f"Confianza: {sig.confidence:.0f}%\n"
            )
    
    # NOTAS Y RECOMENDACIONES
    console.print("\n" + "="*80)
    console.print(Panel(
        "[bold cyan]💡 RECOMENDACIONES DE TRADING[/bold cyan]\n\n"
        "1. [yellow]Entradas:[/yellow] Use órdenes límite en los niveles de Entry indicados\n"
        "2. [red]Stop Loss:[/red] SIEMPRE coloque el SL inmediatamente después de entrar\n"
        "3. [green]Take Profit:[/green] Considere cerrar 50% en TP1 y mover SL a breakeven\n"
        "4. [magenta]Apalancamiento:[/magenta] Los valores son sugerencias basadas en volatilidad\n"
        "5. [blue]Gestión:[/blue] Nunca arriesgue más del 2% de su capital por operación\n\n"
        "[dim]El R:R dinámico se ajusta según la volatilidad actual del mercado[/dim]",
        border_style="cyan"
    ))

if __name__ == "__main__":
    asyncio.run(display_complete_signals())