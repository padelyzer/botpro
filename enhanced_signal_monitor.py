#!/usr/bin/env python3
"""
ENHANCED SIGNAL MONITOR - BotphIA
Monitor mejorado con visualización rich en terminal
"""

import asyncio
import sys
from datetime import datetime
from typing import Optional

# Componentes del sistema
from realtime_signal_monitor import RealTimeSignalMonitor, MonitorMode
from terminal_signal_display import TerminalSignalDisplay

class EnhancedSignalMonitor:
    """Monitor con visualización mejorada"""
    
    def __init__(self, mode: MonitorMode = MonitorMode.BALANCED):
        self.monitor = RealTimeSignalMonitor(mode=mode)
        self.display = TerminalSignalDisplay()
        
    async def run_with_enhanced_display(self):
        """Ejecuta el monitor con display mejorado"""
        
        print("\n🚀 Iniciando Monitor Mejorado BotphIA...")
        print(f"📊 Modo: {self.monitor.mode.value}")
        print(f"📈 Pares: {len(self.monitor.trading_pairs)}")
        print(f"⏱ Timeframes: {', '.join(self.monitor.timeframes.keys())}")
        print("\n" + "="*60)
        
        # Esperar 2 segundos antes de iniciar
        await asyncio.sleep(2)
        
        try:
            while self.monitor.is_running:
                # Escanear señales
                signals = await self.monitor.scan_all_pairs()
                
                # Mostrar con formato mejorado
                self.display.display_signals(
                    list(self.monitor.active_signals.values()),
                    self.monitor.statistics
                )
                
                # Esperar antes del próximo escaneo
                await asyncio.sleep(30)  # Escaneo cada 30 segundos
                
        except KeyboardInterrupt:
            print("\n\n⏹️ Deteniendo monitor...")
            self.monitor.stop()
            
            # Mostrar resumen final
            print("\n📊 RESUMEN FINAL")
            print("="*60)
            print(f"Total escaneos: {self.monitor.statistics['scans_completed']}")
            print(f"Señales detectadas: {self.monitor.statistics['signals_detected']}")
            print(f"Señales confirmadas: {self.monitor.statistics['signals_confirmed']}")
            
            # Preguntar si exportar
            export = input("\n¿Exportar señales? (s/n): ").strip().lower()
            if export == 's':
                self.monitor.export_signals()
    
    async def run_live_dashboard(self):
        """Ejecuta el dashboard en vivo"""
        
        print("\n🚀 Iniciando Dashboard Live BotphIA...")
        print("Presiona Ctrl+C para detener\n")
        
        # Iniciar monitor en background
        monitor_task = asyncio.create_task(self.monitor.run())
        
        # Ejecutar dashboard en vivo
        try:
            await self.display.create_live_dashboard(self.monitor)
        except KeyboardInterrupt:
            self.monitor.stop()
            monitor_task.cancel()

async def main():
    """Función principal con menú mejorado"""
    
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, IntPrompt
    from rich.text import Text
    
    console = Console()
    
    # Limpiar pantalla
    console.clear()
    
    # Mostrar header
    header_text = Text("🤖 BotphIA Signal Monitor - Enhanced Edition", style="bold cyan")
    header = Panel(header_text, expand=False, border_style="cyan")
    console.print(header, justify="center")
    
    # Menú de opciones
    console.print("\n[bold]Selecciona el modo de visualización:[/bold]\n")
    console.print("[1] 📊 Dashboard Estático - Actualización periódica")
    console.print("[2] 🔄 Dashboard Live - Actualización en tiempo real")
    console.print("[3] 📱 Modo Compacto - Para pantallas pequeñas")
    console.print("[4] 🖥️ Modo Completo - Todas las funciones\n")
    
    viz_mode = IntPrompt.ask("Modo de visualización", default=2, choices=["1", "2", "3", "4"])
    
    console.print("\n[bold]Selecciona el modo de trading:[/bold]\n")
    console.print("[1] 🚀 Agresivo - Todas las señales")
    console.print("[2] ⚖️ Balanceado - Balance calidad/cantidad")
    console.print("[3] 🛡️ Conservador - Solo alta confianza\n")
    
    trade_mode = IntPrompt.ask("Modo de trading", default=2, choices=["1", "2", "3"])
    
    # Mapear modos
    trade_modes = {
        1: MonitorMode.AGGRESSIVE,
        2: MonitorMode.BALANCED,
        3: MonitorMode.CONSERVATIVE
    }
    
    # Crear monitor
    monitor = EnhancedSignalMonitor(mode=trade_modes[trade_mode])
    
    # Personalizar pares si lo desea
    console.print("\n[bold]¿Personalizar pares a monitorear?[/bold]")
    customize = Prompt.ask("(s/n)", default="n")
    
    if customize.lower() == 's':
        console.print("\nPares disponibles:")
        console.print("AVAX, LINK, NEAR, XRP, PENGU, ADA, SUI, DOT, DOGE, UNI, ETH, BTC")
        pairs_input = Prompt.ask("\nIngresa los pares separados por coma")
        
        pairs = [p.strip().upper() + "USDT" for p in pairs_input.split(",")]
        monitor.monitor.trading_pairs = pairs
        console.print(f"\n✅ Monitoreando: {', '.join(pairs)}")
    
    # Ejecutar según modo seleccionado
    console.print("\n" + "="*60)
    console.print("[bold cyan]Iniciando monitor...[/bold cyan]")
    console.print("="*60 + "\n")
    
    try:
        if viz_mode == 1:
            # Dashboard estático
            await monitor.run_with_enhanced_display()
        elif viz_mode == 2:
            # Dashboard live
            await monitor.run_live_dashboard()
        elif viz_mode == 3:
            # Modo compacto
            monitor.display.console.width = 80  # Limitar ancho
            await monitor.run_with_enhanced_display()
        else:
            # Modo completo
            await monitor.run_live_dashboard()
            
    except KeyboardInterrupt:
        console.print("\n\n[bold red]Monitor detenido por el usuario[/bold red]")
    except Exception as e:
        console.print(f"\n[bold red]Error: {e}[/bold red]")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Verificar si rich está instalado
    try:
        import rich
    except ImportError:
        print("⚠️ Instalando dependencias necesarias...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "rich"])
        print("✅ Dependencias instaladas. Reiniciando...")
        
    asyncio.run(main())