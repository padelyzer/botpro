#!/usr/bin/env python3
"""
TERMINAL SIGNAL DISPLAY - BotphIA
Sistema mejorado de visualización de señales en terminal
"""

import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.columns import Columns
from rich.align import Align
import os

from multi_timeframe_signal_detector import Signal, PatternStage, PatternType

class TerminalSignalDisplay:
    """Display mejorado para señales en terminal"""
    
    def __init__(self):
        self.console = Console()
        self.signals_by_stage = {
            PatternStage.CONFIRMED: [],
            PatternStage.NEARLY_COMPLETE: [],
            PatternStage.FORMING: [],
            PatternStage.POTENTIAL: []
        }
        
    def get_stage_color(self, stage: PatternStage) -> str:
        """Obtiene el color según el stage"""
        colors = {
            PatternStage.CONFIRMED: "bright_green",
            PatternStage.NEARLY_COMPLETE: "yellow",
            PatternStage.FORMING: "cyan",
            PatternStage.POTENTIAL: "blue",
            PatternStage.FAILED: "red"
        }
        return colors.get(stage, "white")
    
    def get_stage_emoji(self, stage: PatternStage) -> str:
        """Obtiene emoji según el stage"""
        emojis = {
            PatternStage.CONFIRMED: "✅",
            PatternStage.NEARLY_COMPLETE: "⏰",
            PatternStage.FORMING: "📈",
            PatternStage.POTENTIAL: "🔍",
            PatternStage.FAILED: "❌"
        }
        return emojis.get(stage, "📊")
    
    def get_action_emoji(self, pattern_type: PatternType) -> str:
        """Obtiene emoji de acción según el patrón"""
        bullish_patterns = [
            PatternType.DOUBLE_BOTTOM,
            PatternType.SUPPORT_BOUNCE,
            PatternType.BREAKOUT,
            PatternType.HAMMER,
            PatternType.ENGULFING_BULL,
            PatternType.TRIANGLE_ASC
        ]
        
        if pattern_type in bullish_patterns:
            return "🟢 BUY"
        else:
            return "🔴 SELL"
    
    def format_price(self, price: float) -> str:
        """Formatea precio con precisión apropiada"""
        if price > 1000:
            return f"${price:,.2f}"
        elif price > 10:
            return f"${price:.3f}"
        else:
            return f"${price:.4f}"
    
    def create_signal_card(self, signal: Signal) -> Panel:
        """Crea una tarjeta visual para una señal"""
        
        # Color según stage
        color = self.get_stage_color(signal.stage)
        emoji = self.get_stage_emoji(signal.stage)
        action = self.get_action_emoji(signal.pattern_type)
        
        # Crear contenido de la tarjeta
        content = f"""
[bold {color}]{emoji} {signal.stage.value.upper()}[/bold {color}]

[bold white]📊 {signal.symbol}[/bold white] • ⏱ {signal.timeframe}
[dim]Patrón: {signal.pattern_type.value.replace('_', ' ').title()}[/dim]

{action} [bold]Entry: {self.format_price(signal.entry_price)}[/bold]
🛑 SL: {self.format_price(signal.stop_loss)}
🎯 TP1: {self.format_price(signal.take_profit_1)}
🎯 TP2: {self.format_price(signal.take_profit_2)}

📊 R:R: [yellow]{signal.risk_reward_ratio:.2f}:1[/yellow]
💪 Confianza: [{color}]{signal.confidence:.1f}%[/{color}]
"""
        
        # Agregar notas si existen
        if signal.notes:
            notes_text = []
            if 'volume_ratio' in signal.notes:
                notes_text.append(f"Vol: {signal.notes['volume_ratio']:.1f}x")
            if 'breakout_strength' in signal.notes:
                notes_text.append(f"Fuerza: {signal.notes['breakout_strength']:.1f}%")
            if notes_text:
                content += f"\n[dim italic]{' | '.join(notes_text)}[/dim italic]"
        
        # Crear panel con borde coloreado
        panel = Panel(
            content.strip(),
            title=f"[bold]{signal.symbol}[/bold]",
            border_style=color,
            width=35,
            padding=(0, 1)
        )
        
        return panel
    
    def create_summary_table(self, signals: List[Signal]) -> Table:
        """Crea tabla resumen de señales"""
        
        table = Table(
            title="📊 RESUMEN DE SEÑALES ACTIVAS",
            show_header=True,
            header_style="bold magenta",
            border_style="blue",
            show_lines=True
        )
        
        # Columnas
        table.add_column("Par", style="cyan", width=10)
        table.add_column("TF", justify="center", width=5)
        table.add_column("Patrón", width=15)
        table.add_column("Stage", justify="center", width=12)
        table.add_column("Conf", justify="right", width=6)
        table.add_column("Entry", justify="right", width=10)
        table.add_column("R:R", justify="center", width=6)
        table.add_column("Acción", justify="center", width=8)
        
        # Ordenar señales por confianza
        sorted_signals = sorted(signals, key=lambda s: s.confidence, reverse=True)
        
        for signal in sorted_signals[:20]:  # Mostrar máximo 20
            stage_color = self.get_stage_color(signal.stage)
            stage_emoji = self.get_stage_emoji(signal.stage)
            action = "BUY" if "🟢" in self.get_action_emoji(signal.pattern_type) else "SELL"
            action_color = "green" if action == "BUY" else "red"
            
            table.add_row(
                signal.symbol,
                signal.timeframe,
                signal.pattern_type.value.replace('_', ' ').title()[:15],
                f"[{stage_color}]{stage_emoji} {signal.stage.value[:8]}[/{stage_color}]",
                f"[yellow]{signal.confidence:.0f}%[/yellow]",
                self.format_price(signal.entry_price),
                f"{signal.risk_reward_ratio:.1f}:1",
                f"[{action_color}]{action}[/{action_color}]"
            )
        
        return table
    
    def create_statistics_panel(self, stats: Dict) -> Panel:
        """Crea panel de estadísticas"""
        
        content = f"""
[bold cyan]📊 ESTADÍSTICAS DEL MONITOR[/bold cyan]

✅ Escaneos: [yellow]{stats.get('scans_completed', 0)}[/yellow]
📊 Señales detectadas: [cyan]{stats.get('signals_detected', 0)}[/cyan]
✅ Confirmadas: [green]{stats.get('signals_confirmed', 0)}[/green]

[bold]Top Patrones:[/bold]
"""
        
        # Top patrones
        patterns = stats.get('patterns_by_type', {})
        if patterns:
            top_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:5]
            for pattern, count in top_patterns:
                content += f"  • {pattern[:20]}: {count}\n"
        
        content += "\n[bold]Mejores Pares:[/bold]\n"
        
        # Mejores performers
        performers = stats.get('best_performers', {})
        if performers:
            top_performers = sorted(performers.items(), key=lambda x: x[1], reverse=True)[:5]
            for symbol, count in top_performers:
                content += f"  • {symbol}: {count} señales\n"
        
        return Panel(
            content.strip(),
            title="[bold]Estadísticas[/bold]",
            border_style="blue",
            padding=(1, 2)
        )
    
    def display_signals(self, signals: List[Signal], statistics: Dict = None):
        """Muestra las señales con formato mejorado"""
        
        self.console.clear()
        
        # Header
        header = Panel(
            Align.center(
                Text("🤖 BotphIA - Monitor de Señales Multi-Timeframe", 
                     style="bold cyan"),
                vertical="middle"
            ),
            border_style="cyan",
            padding=(1, 0)
        )
        self.console.print(header)
        
        # Separar señales por stage
        self.signals_by_stage = {
            PatternStage.CONFIRMED: [],
            PatternStage.NEARLY_COMPLETE: [],
            PatternStage.FORMING: [],
            PatternStage.POTENTIAL: []
        }
        
        for signal in signals:
            if signal.stage in self.signals_by_stage:
                self.signals_by_stage[signal.stage].append(signal)
        
        # Mostrar señales CONFIRMADAS primero
        if self.signals_by_stage[PatternStage.CONFIRMED]:
            self.console.print("\n[bold green]✅ SEÑALES CONFIRMADAS - EJECUTAR AHORA[/bold green]")
            self.console.print("─" * 80)
            
            cards = [self.create_signal_card(s) for s in self.signals_by_stage[PatternStage.CONFIRMED][:6]]
            
            # Mostrar en columnas
            for i in range(0, len(cards), 2):
                row_cards = cards[i:i+2]
                self.console.print(Columns(row_cards, equal=True, expand=False))
        
        # Mostrar señales CASI COMPLETAS
        if self.signals_by_stage[PatternStage.NEARLY_COMPLETE]:
            self.console.print("\n[bold yellow]⏰ SEÑALES CASI COMPLETAS - PREPARAR ORDEN[/bold yellow]")
            self.console.print("─" * 80)
            
            cards = [self.create_signal_card(s) for s in self.signals_by_stage[PatternStage.NEARLY_COMPLETE][:4]]
            
            for i in range(0, len(cards), 2):
                row_cards = cards[i:i+2]
                self.console.print(Columns(row_cards, equal=True, expand=False))
        
        # Tabla resumen de todas las señales
        if len(signals) > 0:
            self.console.print("\n")
            self.console.print(self.create_summary_table(signals))
        
        # Panel de estadísticas
        if statistics:
            self.console.print("\n")
            self.console.print(self.create_statistics_panel(statistics))
        
        # Footer con timestamp
        footer_text = f"[dim]Última actualización: {datetime.now().strftime('%H:%M:%S')}[/dim]"
        self.console.print(f"\n{footer_text}", justify="center")
    
    def display_live_update(self, message: str, level: str = "info"):
        """Muestra una actualización en vivo sin limpiar la pantalla"""
        
        colors = {
            "info": "blue",
            "alert": "yellow",
            "warning": "orange1",
            "critical": "red"
        }
        
        emojis = {
            "info": "ℹ️",
            "alert": "⚠️",
            "warning": "🔴",
            "critical": "🚨"
        }
        
        color = colors.get(level, "white")
        emoji = emojis.get(level, "📊")
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Crear mensaje formateado
        formatted_message = f"[{color}]{emoji} [{timestamp}] {message}[/{color}]"
        
        # Mostrar en una línea nueva sin limpiar
        self.console.print(formatted_message)
    
    async def create_live_dashboard(self, monitor):
        """Crea un dashboard en vivo que se actualiza automáticamente"""
        
        with Live(console=self.console, refresh_per_second=1) as live:
            while monitor.is_running:
                # Obtener señales activas
                signals = list(monitor.active_signals.values())
                
                # Crear layout
                layout = Layout()
                layout.split_column(
                    Layout(name="header", size=3),
                    Layout(name="body"),
                    Layout(name="footer", size=3)
                )
                
                # Header
                header = Panel(
                    Align.center(
                        Text(f"🤖 BotphIA Monitor - {datetime.now().strftime('%H:%M:%S')}", 
                             style="bold cyan"),
                        vertical="middle"
                    ),
                    border_style="cyan"
                )
                layout["header"].update(header)
                
                # Body con señales
                if signals:
                    # Crear tabla de señales
                    table = self.create_summary_table(signals)
                    layout["body"].update(table)
                else:
                    layout["body"].update(
                        Panel(
                            Align.center(
                                Text("🔍 Escaneando mercados...", style="yellow"),
                                vertical="middle"
                            ),
                            border_style="yellow"
                        )
                    )
                
                # Footer con estadísticas
                stats_text = f"""
Escaneos: {monitor.statistics.get('scans_completed', 0)} | 
Detectadas: {monitor.statistics.get('signals_detected', 0)} | 
Confirmadas: {monitor.statistics.get('signals_confirmed', 0)}
                """
                footer = Panel(
                    Align.center(Text(stats_text.strip(), style="dim")),
                    border_style="blue"
                )
                layout["footer"].update(footer)
                
                # Actualizar display
                live.update(layout)
                
                # Esperar antes de actualizar
                await asyncio.sleep(1)

# Función helper para integración
def display_signals_enhanced(signals: List[Signal], statistics: Dict = None):
    """Función para mostrar señales mejoradas desde otros módulos"""
    display = TerminalSignalDisplay()
    display.display_signals(signals, statistics)