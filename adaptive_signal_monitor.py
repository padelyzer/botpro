#!/usr/bin/env python3
"""
ADAPTIVE SIGNAL MONITOR - BotphIA
Monitor adaptativo que ajusta sensibilidad según condiciones del mercado
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Dict
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.align import Align
from rich.text import Text

# Componentes del sistema
from binance_integration import BinanceConnector
from multi_timeframe_signal_detector import (
    PatternDetector, Signal, PatternStage,
    TRADING_PAIRS, TIMEFRAMES
)
from terminal_signal_display import TerminalSignalDisplay

logger = logging.getLogger(__name__)

class AdaptiveSignalMonitor:
    """Monitor que se adapta a las condiciones del mercado"""
    
    def __init__(self, sensitivity: str = "auto"):
        self.console = Console()
        self.connector = BinanceConnector(testnet=False)
        self.detector = PatternDetector()
        self.display = TerminalSignalDisplay()
        
        # Configuración de sensibilidad
        self.sensitivity = sensitivity
        self.configure_sensitivity()
        
        # Estado
        self.is_running = True
        self.signals_found = []
        self.market_conditions = {}
        self.stats = {
            'scans': 0,
            'signals': 0,
            'pairs_analyzed': set()
        }
        
    def configure_sensitivity(self):
        """Configura umbrales según sensibilidad"""
        
        sensitivities = {
            "ultra_high": {
                "min_confidence": 30,
                "pattern_threshold": 0.5,
                "volume_threshold": 0.8
            },
            "high": {
                "min_confidence": 40,
                "pattern_threshold": 0.6,
                "volume_threshold": 1.0
            },
            "medium": {
                "min_confidence": 50,
                "pattern_threshold": 0.7,
                "volume_threshold": 1.2
            },
            "low": {
                "min_confidence": 60,
                "pattern_threshold": 0.8,
                "volume_threshold": 1.5
            },
            "auto": {
                "min_confidence": 45,
                "pattern_threshold": 0.65,
                "volume_threshold": 1.1
            }
        }
        
        self.thresholds = sensitivities.get(self.sensitivity, sensitivities["auto"])
        
    async def analyze_market_conditions(self):
        """Analiza las condiciones generales del mercado"""
        
        try:
            # Analizar BTC como indicador principal
            btc_data = self.connector.get_historical_data("BTCUSDT", "1h", limit=24)
            
            if not btc_data.empty:
                # Calcular volatilidad
                returns = btc_data['close'].pct_change().dropna()
                volatility = returns.std() * 100
                
                # Determinar tendencia
                sma_20 = btc_data['close'].rolling(20).mean().iloc[-1]
                current_price = btc_data['close'].iloc[-1]
                
                if current_price > sma_20 * 1.02:
                    trend = "BULLISH"
                elif current_price < sma_20 * 0.98:
                    trend = "BEARISH"
                else:
                    trend = "NEUTRAL"
                
                self.market_conditions = {
                    'btc_price': current_price,
                    'volatility': volatility,
                    'trend': trend,
                    'volume_avg': btc_data['volume'].mean()
                }
                
                # Ajustar sensibilidad automáticamente
                if self.sensitivity == "auto":
                    if volatility > 3:  # Alta volatilidad
                        self.thresholds["min_confidence"] = 35
                    elif volatility < 1:  # Baja volatilidad
                        self.thresholds["min_confidence"] = 55
                    
        except Exception as e:
            logger.error(f"Error analizando condiciones: {e}")
    
    async def quick_scan(self, pairs_limit: int = 6):
        """Escaneo rápido de los principales pares"""
        
        signals = []
        
        # Seleccionar pares prioritarios
        priority_pairs = ["BTCUSDT", "ETHUSDT", "AVAXUSDT", "LINKUSDT", "NEARUSDT", "XRPUSDT"]
        
        for pair in priority_pairs[:pairs_limit]:
            for timeframe in ["15m", "1h"]:  # Solo timeframes principales
                try:
                    df = self.connector.get_historical_data(
                        pair,
                        timeframe=timeframe,
                        limit=100
                    )
                    
                    if not df.empty:
                        # Detectar con umbral ajustado
                        detected = self.detector.detect_all_patterns(df, pair, timeframe)
                        
                        # Filtrar por confianza mínima
                        filtered = [
                            s for s in detected 
                            if s.confidence >= self.thresholds["min_confidence"]
                        ]
                        
                        signals.extend(filtered)
                        
                except Exception as e:
                    logger.debug(f"Error escaneando {pair} {timeframe}: {e}")
        
        return signals
    
    async def force_signal_detection(self):
        """Fuerza la detección bajando temporalmente los umbrales"""
        
        self.console.print("\n[yellow]🔍 Modo de detección forzada activado...[/yellow]")
        
        # Guardar umbrales originales
        original_threshold = self.thresholds["min_confidence"]
        
        # Bajar umbral temporalmente
        self.thresholds["min_confidence"] = 25
        
        # Escanear con umbral bajo
        signals = await self.quick_scan(pairs_limit=10)
        
        # Restaurar umbral
        self.thresholds["min_confidence"] = original_threshold
        
        if signals:
            self.console.print(f"[green]✅ Encontradas {len(signals)} señales con detección forzada[/green]")
        else:
            self.console.print("[yellow]⚠️ No hay señales incluso con umbrales bajos - Mercado muy lateral[/yellow]")
        
        return signals
    
    def create_live_display(self) -> Layout:
        """Crea el layout para visualización en vivo"""
        
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", ratio=3),
            Layout(name="stats", size=8),
            Layout(name="footer", size=3)
        )
        
        # Header
        header = Panel(
            Align.center(
                Text(
                    f"🤖 BotphIA Adaptive Monitor | "
                    f"Sensibilidad: {self.sensitivity.upper()} | "
                    f"{datetime.now().strftime('%H:%M:%S')}",
                    style="bold cyan"
                ),
                vertical="middle"
            ),
            border_style="cyan"
        )
        layout["header"].update(header)
        
        # Main - Señales
        if self.signals_found:
            # Crear tabla de señales
            table = Table(title="📊 Señales Detectadas", show_lines=True)
            table.add_column("Par", style="cyan", width=10)
            table.add_column("TF", justify="center", width=5)
            table.add_column("Patrón", width=18)
            table.add_column("Stage", justify="center")
            table.add_column("Conf", justify="right", width=6)
            table.add_column("Entry", justify="right")
            table.add_column("R:R", justify="center")
            
            for signal in self.signals_found[:10]:
                stage_color = "green" if signal.stage == PatternStage.CONFIRMED else "yellow"
                table.add_row(
                    signal.symbol,
                    signal.timeframe,
                    signal.pattern_type.value[:18],
                    f"[{stage_color}]{signal.stage.value[:8]}[/{stage_color}]",
                    f"{signal.confidence:.0f}%",
                    f"${signal.entry_price:.4f}",
                    f"{signal.risk_reward_ratio:.1f}:1"
                )
            
            layout["main"].update(Panel(table, border_style="green"))
        else:
            # Sin señales
            no_signals = Panel(
                Align.center(
                    Text(
                        "🔍 Escaneando mercados...\n"
                        "No hay señales en este momento\n\n"
                        "[dim]Presiona 'f' para forzar detección[/dim]",
                        style="yellow"
                    ),
                    vertical="middle"
                ),
                border_style="yellow"
            )
            layout["main"].update(no_signals)
        
        # Stats
        conditions_text = ""
        if self.market_conditions:
            conditions_text = f"""
🎯 Condiciones del Mercado:
  BTC: ${self.market_conditions.get('btc_price', 0):,.2f}
  Tendencia: {self.market_conditions.get('trend', 'N/A')}
  Volatilidad: {self.market_conditions.get('volatility', 0):.2f}%
  
📊 Estadísticas:
  Escaneos: {self.stats['scans']}
  Señales totales: {self.stats['signals']}
  Pares analizados: {len(self.stats['pairs_analyzed'])}
  Umbral confianza: {self.thresholds['min_confidence']}%
"""
        
        stats_panel = Panel(
            Text(conditions_text.strip()),
            title="Estadísticas",
            border_style="blue"
        )
        layout["stats"].update(stats_panel)
        
        # Footer
        footer = Panel(
            Align.center(
                Text(
                    "Ctrl+C: Salir | F: Forzar detección | A: Auto-ajuste",
                    style="dim"
                )
            ),
            border_style="dim"
        )
        layout["footer"].update(footer)
        
        return layout
    
    async def run(self):
        """Ejecuta el monitor adaptativo"""
        
        self.console.print(Panel(
            "[bold cyan]🤖 BotphIA Adaptive Signal Monitor[/bold cyan]\n"
            f"Sensibilidad: {self.sensitivity} | "
            f"Umbral mínimo: {self.thresholds['min_confidence']}%",
            expand=False
        ))
        
        scan_count = 0
        
        with Live(self.create_live_display(), refresh_per_second=1, console=self.console) as live:
            while self.is_running:
                try:
                    # Analizar condiciones cada 5 escaneos
                    if scan_count % 5 == 0:
                        await self.analyze_market_conditions()
                    
                    # Escanear señales
                    new_signals = await self.quick_scan()
                    
                    if new_signals:
                        self.signals_found = new_signals
                        self.stats['signals'] += len(new_signals)
                        
                        # Actualizar pares analizados
                        for signal in new_signals:
                            self.stats['pairs_analyzed'].add(signal.symbol)
                    
                    # Si no hay señales después de 3 escaneos, forzar detección
                    if scan_count > 3 and not self.signals_found:
                        self.signals_found = await self.force_signal_detection()
                    
                    self.stats['scans'] += 1
                    scan_count += 1
                    
                    # Actualizar display
                    live.update(self.create_live_display())
                    
                    # Esperar antes del próximo escaneo
                    await asyncio.sleep(30)
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error(f"Error en monitor: {e}")
                    await asyncio.sleep(5)
        
        self.console.print("\n[bold green]Monitor detenido[/bold green]")
        
        if self.signals_found:
            self.console.print(f"\nÚltimas {len(self.signals_found)} señales detectadas")
            self.display.display_signals(self.signals_found, self.stats)

async def main():
    """Función principal"""
    
    console = Console()
    
    console.print("\n[bold cyan]🤖 BotphIA Adaptive Monitor[/bold cyan]")
    console.print("\nSelecciona el nivel de sensibilidad:")
    console.print("[1] 🔴 Ultra Alta - Detecta todo (muchos falsos positivos)")
    console.print("[2] 🟠 Alta - Más señales")
    console.print("[3] 🟡 Media - Balanceado")
    console.print("[4] 🟢 Baja - Solo señales fuertes")
    console.print("[5] 🔵 Auto - Se ajusta al mercado\n")
    
    choice = input("Selección [5]: ").strip() or "5"
    
    sensitivity_map = {
        "1": "ultra_high",
        "2": "high",
        "3": "medium",
        "4": "low",
        "5": "auto"
    }
    
    sensitivity = sensitivity_map.get(choice, "auto")
    
    monitor = AdaptiveSignalMonitor(sensitivity=sensitivity)
    
    try:
        await monitor.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitor detenido por el usuario[/yellow]")

if __name__ == "__main__":
    asyncio.run(main())