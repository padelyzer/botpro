#!/usr/bin/env python3
"""
BALANCED SIGNAL MONITOR - BotphIA
Monitor balanceado que detecta señales reales sin ser demasiado estricto
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import os

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.align import Align
from rich.text import Text

# Componentes del sistema
from binance_integration import BinanceConnector
from multi_timeframe_signal_detector import (
    PatternDetector, Signal, PatternStage, PatternType,
    TRADING_PAIRS, TIMEFRAMES
)
from signal_notification_system import SignalNotificationManager
from terminal_signal_display import TerminalSignalDisplay

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('balanced_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BalancedSignalMonitor:
    """Monitor balanceado para señales confiables"""
    
    def __init__(self):
        self.console = Console()
        self.connector = BinanceConnector(testnet=False)
        self.detector = PatternDetector()
        self.notifier = SignalNotificationManager()
        self.display = TerminalSignalDisplay()
        
        # Configuración BALANCEADA
        self.min_confidence = 60  # Bajamos un poco el umbral
        self.min_risk_reward = 1.5  # Mantenemos R:R razonable
        self.prefer_volume_confirmation = True  # Preferir, no requerir
        self.prefer_trend_alignment = True  # Preferir, no requerir
        
        # Estado
        self.is_running = True
        self.active_signals = {}
        self.confirmed_signals = []
        
        # Estadísticas
        self.stats = {
            'uptime_start': datetime.now(),
            'total_scans': 0,
            'signals_detected': 0,
            'signals_confirmed': 0,
            'signals_by_stage': {
                'confirmed': 0,
                'nearly': 0,
                'forming': 0
            }
        }
        
    async def scan_pair_simplified(self, symbol: str) -> List[Signal]:
        """Escaneo simplificado de un par"""
        
        detected_signals = []
        
        for timeframe in TIMEFRAMES.keys():
            try:
                # Obtener datos
                df = self.connector.get_historical_data(
                    symbol,
                    timeframe=timeframe,
                    limit=TIMEFRAMES[timeframe]['bars']
                )
                
                if df.empty or len(df) < 50:
                    continue
                
                # Detectar patrones
                signals = self.detector.detect_all_patterns(df, symbol, timeframe)
                
                # Filtro SIMPLE: solo confianza y R:R
                for signal in signals:
                    if signal.confidence >= self.min_confidence and \
                       signal.risk_reward_ratio >= self.min_risk_reward:
                        
                        # Bonus si tiene volumen alto
                        if signal.notes and 'volume_ratio' in signal.notes:
                            if signal.notes['volume_ratio'] > 1.2:
                                signal.confidence += 5  # Bonus de 5% por volumen
                        
                        detected_signals.append(signal)
                        
                        logger.info(
                            f"✅ Señal detectada: {symbol} {timeframe} "
                            f"{signal.pattern_type.value} - {signal.stage.value} "
                            f"({signal.confidence:.1f}%)"
                        )
                
            except Exception as e:
                logger.debug(f"Error escaneando {symbol} {timeframe}: {e}")
        
        return detected_signals
    
    async def continuous_scan(self):
        """Escaneo continuo de todos los pares"""
        
        while self.is_running:
            try:
                scan_start = datetime.now()
                all_signals = []
                
                self.console.print(f"\n[cyan]🔍 Escaneo #{self.stats['total_scans'] + 1} iniciado...[/cyan]")
                
                # Escanear todos los pares
                for symbol in TRADING_PAIRS:
                    signals = await self.scan_pair_simplified(symbol)
                    
                    if signals:
                        all_signals.extend(signals)
                        self.console.print(
                            f"  ✓ {symbol}: {len(signals)} señales detectadas"
                        )
                    
                    # Pequeña pausa para no sobrecargar
                    await asyncio.sleep(0.3)
                
                # Procesar señales
                if all_signals:
                    await self.process_signals(all_signals)
                    self.console.print(
                        f"\n[green]✅ Encontradas {len(all_signals)} señales totales[/green]"
                    )
                else:
                    self.console.print(
                        f"\n[yellow]ℹ️ No hay señales en este escaneo[/yellow]"
                    )
                
                # Actualizar estadísticas
                self.stats['total_scans'] += 1
                scan_duration = (datetime.now() - scan_start).total_seconds()
                
                self.console.print(
                    f"[dim]Escaneo completado en {scan_duration:.1f}s[/dim]"
                )
                
                # Mostrar resumen
                self.show_summary()
                
                # Esperar antes del próximo escaneo
                await asyncio.sleep(60)  # Cada minuto
                
            except Exception as e:
                logger.error(f"Error en escaneo: {e}")
                await asyncio.sleep(30)
    
    async def process_signals(self, signals: List[Signal]):
        """Procesa las señales detectadas"""
        
        for signal in signals:
            signal_key = f"{signal.symbol}_{signal.pattern_type.value}_{signal.timeframe}"
            
            # Actualizar estadísticas por stage
            if signal.stage == PatternStage.CONFIRMED:
                self.stats['signals_by_stage']['confirmed'] += 1
            elif signal.stage == PatternStage.NEARLY_COMPLETE:
                self.stats['signals_by_stage']['nearly'] += 1
            elif signal.stage == PatternStage.FORMING:
                self.stats['signals_by_stage']['forming'] += 1
            
            # Guardar señal
            self.active_signals[signal_key] = signal
            self.stats['signals_detected'] += 1
            
            # Si está confirmada, notificar
            if signal.stage == PatternStage.CONFIRMED:
                self.confirmed_signals.append(signal)
                self.stats['signals_confirmed'] += 1
                
                # Notificación destacada
                self.console.print(
                    Panel(
                        f"[bold green]🎯 SEÑAL CONFIRMADA[/bold green]\n\n"
                        f"Par: {signal.symbol}\n"
                        f"Timeframe: {signal.timeframe}\n"
                        f"Patrón: {signal.pattern_type.value}\n"
                        f"Confianza: {signal.confidence:.1f}%\n"
                        f"Entry: ${signal.entry_price:.4f}\n"
                        f"Stop Loss: ${signal.stop_loss:.4f}\n"
                        f"Take Profit: ${signal.take_profit_1:.4f}\n"
                        f"R:R Ratio: {signal.risk_reward_ratio:.2f}:1",
                        border_style="green",
                        title="¡Nueva Oportunidad!"
                    )
                )
                
                await self.notifier.process_signal(signal)
    
    def show_summary(self):
        """Muestra resumen del estado actual"""
        
        if self.active_signals:
            # Usar display mejorado
            signals = list(self.active_signals.values())
            self.display.display_signals(signals, self.stats)
        else:
            # Mostrar estadísticas básicas
            uptime = datetime.now() - self.stats['uptime_start']
            hours = int(uptime.total_seconds() // 3600)
            minutes = int((uptime.total_seconds() % 3600) // 60)
            
            self.console.print(
                Panel(
                    f"📊 Estado del Monitor\n\n"
                    f"Uptime: {hours}h {minutes}m\n"
                    f"Escaneos: {self.stats['total_scans']}\n"
                    f"Señales detectadas: {self.stats['signals_detected']}\n"
                    f"  • Confirmadas: {self.stats['signals_by_stage']['confirmed']}\n"
                    f"  • Casi completas: {self.stats['signals_by_stage']['nearly']}\n"
                    f"  • Formándose: {self.stats['signals_by_stage']['forming']}\n",
                    border_style="blue"
                )
            )
    
    async def run(self):
        """Ejecuta el monitor balanceado"""
        
        self.console.print(
            Panel(
                "[bold cyan]🤖 BotphIA Balanced Signal Monitor[/bold cyan]\n"
                "Monitor balanceado - Detecta señales reales sin ser demasiado estricto\n"
                f"Confianza mínima: {self.min_confidence}% | R:R mínimo: {self.min_risk_reward}:1",
                expand=False,
                border_style="cyan"
            )
        )
        
        logger.info("🚀 Iniciando monitor balanceado...")
        
        try:
            await self.continuous_scan()
        except KeyboardInterrupt:
            self.is_running = False
            
        self.console.print("\n[bold green]Monitor detenido[/bold green]")
        self.console.print(f"Total señales detectadas: {self.stats['signals_detected']}")
        self.console.print(f"Señales confirmadas: {self.stats['signals_confirmed']}")

async def main():
    """Función principal"""
    
    monitor = BalancedSignalMonitor()
    
    try:
        await monitor.run()
    except KeyboardInterrupt:
        print("\n⏹️ Monitor detenido por el usuario")

if __name__ == "__main__":
    asyncio.run(main())