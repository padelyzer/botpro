#!/usr/bin/env python3
"""
CHECK MARKET SIGNALS - Verificación rápida de señales en el mercado
"""

import asyncio
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from binance_integration import BinanceConnector
from multi_timeframe_signal_detector import PatternDetector, TRADING_PAIRS, TIMEFRAMES

console = Console()

async def check_current_market():
    """Verifica el estado actual del mercado y señales disponibles"""
    
    console.print(Panel("[bold cyan]🔍 Verificación de Señales del Mercado[/bold cyan]", expand=False))
    
    connector = BinanceConnector(testnet=False)
    detector = PatternDetector()
    
    all_signals = []
    signals_by_confidence = {
        "high": [],      # > 70%
        "medium": [],    # 50-70%
        "low": []        # < 50%
    }
    
    # Verificar algunos pares principales
    test_pairs = ["BTCUSDT", "ETHUSDT", "AVAXUSDT", "LINKUSDT", "NEARUSDT"]
    test_timeframes = ["15m", "1h", "4h"]
    
    console.print("\n[yellow]Escaneando mercado...[/yellow]\n")
    
    for symbol in test_pairs:
        console.print(f"📊 Analizando {symbol}...")
        
        for timeframe in test_timeframes:
            try:
                # Obtener datos
                df = connector.get_historical_data(symbol, timeframe, limit=100)
                
                if not df.empty and len(df) >= 50:
                    # Detectar patrones SIN FILTROS
                    signals = detector.detect_all_patterns(df, symbol, timeframe)
                    
                    if signals:
                        for signal in signals:
                            all_signals.append(signal)
                            
                            # Clasificar por confianza
                            if signal.confidence >= 70:
                                signals_by_confidence["high"].append(signal)
                            elif signal.confidence >= 50:
                                signals_by_confidence["medium"].append(signal)
                            else:
                                signals_by_confidence["low"].append(signal)
                            
                            # Mostrar información inmediata
                            console.print(
                                f"   ✓ {timeframe}: {signal.pattern_type.value} "
                                f"({signal.stage.value}) - {signal.confidence:.1f}%"
                            )
                
            except Exception as e:
                console.print(f"   ✗ Error en {timeframe}: {e}")
    
    # Mostrar resumen
    console.print("\n" + "="*60)
    console.print("[bold]📊 RESUMEN DE DETECCIÓN[/bold]")
    console.print("="*60)
    
    console.print(f"\nTotal señales detectadas: [bold]{len(all_signals)}[/bold]")
    console.print(f"  • Alta confianza (>70%): [green]{len(signals_by_confidence['high'])}[/green]")
    console.print(f"  • Media confianza (50-70%): [yellow]{len(signals_by_confidence['medium'])}[/yellow]")
    console.print(f"  • Baja confianza (<50%): [red]{len(signals_by_confidence['low'])}[/red]")
    
    # Tabla de señales de alta confianza
    if signals_by_confidence["high"]:
        console.print("\n[bold green]✅ SEÑALES DE ALTA CONFIANZA[/bold green]")
        
        table = Table(show_lines=True)
        table.add_column("Par", style="cyan")
        table.add_column("TF", justify="center")
        table.add_column("Patrón", style="yellow")
        table.add_column("Stage", style="green")
        table.add_column("Conf %", justify="right")
        table.add_column("Entry", justify="right")
        table.add_column("R:R", justify="center")
        
        for sig in signals_by_confidence["high"][:10]:
            table.add_row(
                sig.symbol,
                sig.timeframe,
                sig.pattern_type.value[:20],
                sig.stage.value,
                f"{sig.confidence:.1f}%",
                f"${sig.entry_price:.4f}",
                f"{sig.risk_reward_ratio:.2f}:1"
            )
        
        console.print(table)
    
    # Análisis del problema
    console.print("\n[bold]🔍 ANÁLISIS DE DETECCIÓN[/bold]")
    
    if len(all_signals) == 0:
        console.print("[red]❌ No se detectaron señales en absoluto[/red]")
        console.print("\nPosibles causas:")
        console.print("  1. Mercado muy lateral sin patrones claros")
        console.print("  2. Problema en los algoritmos de detección")
        console.print("  3. Datos insuficientes")
        
    elif len(signals_by_confidence["high"]) == 0:
        console.print("[yellow]⚠️ Se detectaron señales pero ninguna de alta confianza[/yellow]")
        console.print("\nEl monitor de precisión (65% mínimo) no las mostraría")
        console.print("Esto es NORMAL en mercados sin tendencia clara")
        
    else:
        console.print("[green]✅ Hay señales de alta calidad disponibles[/green]")
        console.print("El monitor debería detectarlas")
    
    # Verificar umbrales
    console.print("\n[bold]📊 VERIFICACIÓN DE UMBRALES[/bold]")
    console.print("\nUmbrales del Monitor de Precisión:")
    console.print("  • Confianza mínima: 65%")
    console.print("  • Risk/Reward mínimo: 1.5:1")
    console.print("  • Requiere volumen > 1.2x")
    console.print("  • Requiere alineación con tendencia")
    
    # Contar cuántas pasarían el filtro de 65%
    signals_above_65 = [s for s in all_signals if s.confidence >= 65]
    console.print(f"\nSeñales que pasarían filtro de 65%: [bold]{len(signals_above_65)}[/bold]")
    
    if signals_above_65:
        console.print("\n[green]✅ Deberías ver estas señales en el monitor:[/green]")
        for sig in signals_above_65[:5]:
            console.print(
                f"  • {sig.symbol} {sig.timeframe} - {sig.pattern_type.value} "
                f"({sig.confidence:.1f}%)"
            )
    
    return all_signals, signals_by_confidence

if __name__ == "__main__":
    asyncio.run(check_current_market())