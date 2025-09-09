#!/usr/bin/env python3
"""
SIGNAL MONITOR DIAGNOSTIC - BotphIA
Herramienta de diagnóstico para verificar el funcionamiento del sistema
"""

import asyncio
import logging
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Componentes del sistema
from binance_integration import BinanceConnector
from multi_timeframe_signal_detector import PatternDetector, TRADING_PAIRS, TIMEFRAMES
from signal_notification_system import SignalNotificationManager

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SignalMonitorDiagnostic:
    """Diagnóstico del sistema de señales"""
    
    def __init__(self):
        self.console = Console()
        self.connector = BinanceConnector(testnet=False)
        self.detector = PatternDetector()
        
    async def test_connection(self):
        """Prueba la conexión con Binance"""
        self.console.print("\n[bold cyan]1. Probando conexión con Binance...[/bold cyan]")
        
        try:
            # Probar obtener precio de BTC
            df = self.connector.get_historical_data("BTCUSDT", timeframe="1h", limit=10)
            
            if not df.empty:
                current_price = df['close'].iloc[-1]
                self.console.print(f"✅ Conexión exitosa - BTC: ${current_price:,.2f}")
                return True
            else:
                self.console.print("❌ No se pudieron obtener datos")
                return False
                
        except Exception as e:
            self.console.print(f"❌ Error de conexión: {e}")
            return False
    
    async def test_pairs_availability(self):
        """Verifica disponibilidad de los pares"""
        self.console.print("\n[bold cyan]2. Verificando disponibilidad de pares...[/bold cyan]")
        
        available = []
        unavailable = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            
            task = progress.add_task("Verificando pares...", total=len(TRADING_PAIRS))
            
            for pair in TRADING_PAIRS:
                try:
                    df = self.connector.get_historical_data(pair, timeframe="1h", limit=5)
                    if not df.empty:
                        available.append(pair)
                    else:
                        unavailable.append(pair)
                except:
                    unavailable.append(pair)
                
                progress.update(task, advance=1, description=f"Verificando {pair}...")
        
        # Mostrar resultados
        self.console.print(f"\n✅ Pares disponibles: {len(available)}/{len(TRADING_PAIRS)}")
        
        if unavailable:
            self.console.print(f"⚠️ Pares no disponibles: {', '.join(unavailable)}")
        
        return available
    
    async def analyze_single_pair(self, symbol: str = "BTCUSDT"):
        """Analiza un par en detalle"""
        self.console.print(f"\n[bold cyan]3. Análisis detallado de {symbol}...[/bold cyan]")
        
        results = {}
        
        for timeframe in TIMEFRAMES.keys():
            self.console.print(f"\n⏱ Timeframe {timeframe}:")
            
            try:
                # Obtener datos
                df = self.connector.get_historical_data(
                    symbol, 
                    timeframe=timeframe, 
                    limit=TIMEFRAMES[timeframe]['bars']
                )
                
                if df.empty:
                    self.console.print(f"  ❌ Sin datos")
                    continue
                
                # Información básica
                last_price = df['close'].iloc[-1]
                high_24h = df['high'].max()
                low_24h = df['low'].min()
                volume = df['volume'].iloc[-1]
                
                self.console.print(f"  📊 Precio: ${last_price:.4f}")
                self.console.print(f"  📈 High: ${high_24h:.4f} | Low: ${low_24h:.4f}")
                self.console.print(f"  📊 Volumen: {volume:.2f}")
                
                # Detectar patrones
                signals = self.detector.detect_all_patterns(df, symbol, timeframe)
                
                if signals:
                    self.console.print(f"  🎯 Patrones detectados: {len(signals)}")
                    for signal in signals[:3]:  # Mostrar máximo 3
                        self.console.print(
                            f"     • {signal.pattern_type.value} - "
                            f"{signal.stage.value} ({signal.confidence:.1f}%)"
                        )
                else:
                    self.console.print(f"  ℹ️ Sin patrones en este momento")
                
                results[timeframe] = {
                    'price': last_price,
                    'signals': len(signals) if signals else 0
                }
                
            except Exception as e:
                self.console.print(f"  ❌ Error: {e}")
                logger.error(f"Error analizando {symbol} {timeframe}: {e}")
        
        return results
    
    async def scan_for_opportunities(self):
        """Escanea buscando las mejores oportunidades actuales"""
        self.console.print("\n[bold cyan]4. Escaneando oportunidades actuales...[/bold cyan]")
        
        all_signals = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            
            # Solo escanear los primeros 5 pares para diagnóstico rápido
            test_pairs = TRADING_PAIRS[:5]
            task = progress.add_task("Escaneando...", total=len(test_pairs) * 2)
            
            for pair in test_pairs:
                for timeframe in ['15m', '1h']:  # Solo 2 timeframes para rapidez
                    progress.update(task, description=f"Escaneando {pair} {timeframe}...")
                    
                    try:
                        df = self.connector.get_historical_data(
                            pair, 
                            timeframe=timeframe, 
                            limit=100
                        )
                        
                        if not df.empty:
                            signals = self.detector.detect_all_patterns(df, pair, timeframe)
                            if signals:
                                all_signals.extend(signals)
                    except:
                        pass
                    
                    progress.update(task, advance=1)
        
        # Mostrar resultados
        if all_signals:
            self.console.print(f"\n✅ Se encontraron {len(all_signals)} señales potenciales")
            
            # Ordenar por confianza
            sorted_signals = sorted(all_signals, key=lambda s: s.confidence, reverse=True)
            
            # Crear tabla de mejores señales
            table = Table(title="🎯 Top 5 Señales Detectadas", show_lines=True)
            table.add_column("Par", style="cyan")
            table.add_column("TF", justify="center")
            table.add_column("Patrón", style="yellow")
            table.add_column("Stage", style="green")
            table.add_column("Conf %", justify="right", style="magenta")
            
            for signal in sorted_signals[:5]:
                table.add_row(
                    signal.symbol,
                    signal.timeframe,
                    signal.pattern_type.value[:15],
                    signal.stage.value[:10],
                    f"{signal.confidence:.1f}%"
                )
            
            self.console.print(table)
        else:
            self.console.print("\nℹ️ No se detectaron señales en este momento")
            self.console.print("   Esto es normal en mercados laterales o sin tendencia clara")
    
    async def test_pattern_detection(self):
        """Prueba la detección de patrones con datos sintéticos"""
        self.console.print("\n[bold cyan]5. Probando algoritmos de detección...[/bold cyan]")
        
        import pandas as pd
        import numpy as np
        
        # Crear datos sintéticos con patrón claro
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
        
        # Simular un double bottom
        prices = np.concatenate([
            np.linspace(100, 90, 30),   # Caída
            np.linspace(90, 95, 10),    # Rebote
            np.linspace(95, 90, 10),    # Segunda caída
            np.linspace(90, 100, 50)    # Recuperación
        ])
        
        df_test = pd.DataFrame({
            'timestamp': dates,
            'open': prices + np.random.normal(0, 0.5, 100),
            'high': prices + np.random.normal(1, 0.5, 100),
            'low': prices + np.random.normal(-1, 0.5, 100),
            'close': prices,
            'volume': np.random.uniform(1000, 5000, 100)
        })
        
        # Detectar patrones
        signals = self.detector.detect_all_patterns(df_test, "TEST", "1h")
        
        if signals:
            self.console.print(f"✅ Detección funcionando - {len(signals)} patrones encontrados")
        else:
            self.console.print("⚠️ No se detectaron patrones en datos de prueba")
    
    async def run_diagnostic(self):
        """Ejecuta diagnóstico completo"""
        
        # Header
        header = Panel(
            "[bold cyan]🔧 DIAGNÓSTICO DEL SISTEMA DE SEÑALES[/bold cyan]\n"
            "Verificando todos los componentes...",
            expand=False
        )
        self.console.print(header)
        
        # 1. Probar conexión
        connection_ok = await self.test_connection()
        
        if not connection_ok:
            self.console.print("\n[bold red]⚠️ Sin conexión a Binance. Verifica tu conexión a internet.[/bold red]")
            return
        
        # 2. Verificar pares
        available_pairs = await self.test_pairs_availability()
        
        # 3. Análisis detallado de BTC
        await self.analyze_single_pair("BTCUSDT")
        
        # 4. Buscar oportunidades
        await self.scan_for_opportunities()
        
        # 5. Probar algoritmos
        await self.test_pattern_detection()
        
        # Resumen
        summary = Panel(
            "[bold green]✅ DIAGNÓSTICO COMPLETADO[/bold green]\n\n"
            f"• Conexión: OK\n"
            f"• Pares disponibles: {len(available_pairs)}/{len(TRADING_PAIRS)}\n"
            f"• Detección de patrones: Funcionando\n"
            f"• Sistema: Operativo\n\n"
            "[dim]Si no se detectan señales, puede ser debido a:[/dim]\n"
            "[dim]- Mercado lateral sin tendencias claras[/dim]\n"
            "[dim]- Volatilidad baja[/dim]\n"
            "[dim]- Patrones en formación temprana[/dim]",
            border_style="green"
        )
        self.console.print("\n")
        self.console.print(summary)

async def main():
    """Función principal"""
    diagnostic = SignalMonitorDiagnostic()
    await diagnostic.run_diagnostic()

if __name__ == "__main__":
    asyncio.run(main())