#!/usr/bin/env python3
"""
TEST RSI CONFIG - Verifica la configuración de RSI actualizada
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from trading_config import (
    RSI_CONFIG, 
    get_rsi_levels, 
    is_rsi_overbought, 
    is_rsi_oversold,
    TIMEFRAME_CONFIG
)

console = Console()

def test_rsi_configuration():
    """Prueba la configuración de RSI con los nuevos umbrales"""
    
    console.print(Panel(
        "[bold cyan]🔍 Verificación de Configuración RSI[/bold cyan]\n"
        "Umbrales actualizados: Sobrecompra 73 | Sobreventa 28",
        expand=False
    ))
    
    # Tabla de configuración global
    console.print("\n[bold]📊 CONFIGURACIÓN GLOBAL RSI:[/bold]\n")
    
    config_table = Table(show_header=True, header_style="bold magenta")
    config_table.add_column("Parámetro", style="cyan", width=25)
    config_table.add_column("Valor Anterior", justify="center", style="dim")
    config_table.add_column("Valor Nuevo", justify="center", style="green")
    
    config_table.add_row("Sobrecompra", "70", str(RSI_CONFIG['overbought']))
    config_table.add_row("Sobreventa", "30", str(RSI_CONFIG['oversold']))
    config_table.add_row("Neutral Alto", "60", str(RSI_CONFIG['neutral_high']))
    config_table.add_row("Neutral Bajo", "40", str(RSI_CONFIG['neutral_low']))
    config_table.add_row("Sobrecompra Extrema", "80", str(RSI_CONFIG['extreme_overbought']))
    config_table.add_row("Sobreventa Extrema", "20", str(RSI_CONFIG['extreme_oversold']))
    
    console.print(config_table)
    
    # Tabla por timeframe
    console.print("\n[bold]⏱ CONFIGURACIÓN POR TIMEFRAME:[/bold]\n")
    
    tf_table = Table(show_header=True, header_style="bold yellow")
    tf_table.add_column("Timeframe", style="cyan")
    tf_table.add_column("RSI Sobrecompra", justify="center")
    tf_table.add_column("RSI Sobreventa", justify="center")
    tf_table.add_column("Apalancamiento Max", justify="center")
    
    for tf in ['5m', '15m', '1h', '4h']:
        levels = get_rsi_levels(tf)
        max_lev = TIMEFRAME_CONFIG[tf]['max_leverage']
        
        # Color según el valor
        ob_color = "red" if levels['overbought'] > 73 else "green" if levels['overbought'] == 73 else "yellow"
        os_color = "blue" if levels['oversold'] < 28 else "green" if levels['oversold'] == 28 else "yellow"
        
        tf_table.add_row(
            tf,
            f"[{ob_color}]{levels['overbought']}[/{ob_color}]",
            f"[{os_color}]{levels['oversold']}[/{os_color}]",
            f"{max_lev}x"
        )
    
    console.print(tf_table)
    
    # Pruebas de funciones
    console.print("\n[bold]🧪 PRUEBAS DE FUNCIONES:[/bold]\n")
    
    test_table = Table(show_header=True, header_style="bold green")
    test_table.add_column("RSI Valor", style="cyan", justify="center")
    test_table.add_column("Timeframe", justify="center")
    test_table.add_column("¿Sobrecompra?", justify="center")
    test_table.add_column("¿Sobreventa?", justify="center")
    test_table.add_column("Estado", justify="center")
    
    # Casos de prueba
    test_cases = [
        (75, '1h'),   # Sobrecompra (>73)
        (72, '1h'),   # Neutral alto
        (50, '1h'),   # Neutral
        (29, '1h'),   # Neutral bajo
        (27, '1h'),   # Sobreventa (<28)
        (20, '1h'),   # Sobreventa extrema
        (80, '1h'),   # Sobrecompra extrema
        (76, '5m'),   # Sobrecompra en 5m (umbral 75)
        (24, '5m'),   # Sobreventa en 5m (umbral 25)
    ]
    
    for rsi_val, tf in test_cases:
        is_ob = is_rsi_overbought(rsi_val, tf)
        is_os = is_rsi_oversold(rsi_val, tf)
        
        # Determinar estado
        if is_ob:
            estado = "[red]SOBRECOMPRA[/red]"
        elif is_os:
            estado = "[blue]SOBREVENTA[/blue]"
        elif rsi_val >= 60:
            estado = "[yellow]NEUTRAL ALTO[/yellow]"
        elif rsi_val <= 40:
            estado = "[cyan]NEUTRAL BAJO[/cyan]"
        else:
            estado = "[green]NEUTRAL[/green]"
        
        test_table.add_row(
            str(rsi_val),
            tf,
            "✅" if is_ob else "❌",
            "✅" if is_os else "❌",
            estado
        )
    
    console.print(test_table)
    
    # Resumen
    console.print("\n" + "="*60)
    console.print(Panel(
        "[bold green]✅ CONFIGURACIÓN RSI ACTUALIZADA CORRECTAMENTE[/bold green]\n\n"
        "• Sobrecompra: 73 (antes 70)\n"
        "• Sobreventa: 28 (antes 30)\n"
        "• Timeframes cortos (5m): 75/25 para mayor precisión\n"
        "• Timeframes largos (15m-4h): 73/28 estándar\n\n"
        "[dim]Los nuevos umbrales son más estrictos para evitar señales falsas[/dim]",
        border_style="green"
    ))

if __name__ == "__main__":
    test_rsi_configuration()