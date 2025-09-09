#!/usr/bin/env python3
"""
TEST ENHANCED DISPLAY - Prueba rápida del sistema de visualización mejorado
"""

import asyncio
from datetime import datetime
from multi_timeframe_signal_detector import Signal, PatternType, PatternStage
from terminal_signal_display import TerminalSignalDisplay

# Crear señales de prueba
test_signals = [
    Signal(
        id="test1",
        symbol="BTCUSDT",
        timeframe="4h",
        pattern_type=PatternType.BREAKOUT,
        stage=PatternStage.CONFIRMED,
        confidence=85.5,
        entry_price=95250.50,
        stop_loss=94000.00,
        take_profit_1=97000.00,
        take_profit_2=98500.00,
        risk_reward_ratio=2.3,
        formation_start=datetime.now(),
        current_timestamp=datetime.now(),
        notes={'volume_ratio': 2.5, 'breakout_strength': 15.2}
    ),
    Signal(
        id="test2",
        symbol="ETHUSDT",
        timeframe="1h",
        pattern_type=PatternType.DOUBLE_BOTTOM,
        stage=PatternStage.NEARLY_COMPLETE,
        confidence=72.3,
        entry_price=3350.25,
        stop_loss=3280.00,
        take_profit_1=3450.00,
        take_profit_2=3550.00,
        risk_reward_ratio=2.0,
        formation_start=datetime.now(),
        current_timestamp=datetime.now(),
        notes={'support_level': 3300.00}
    ),
    Signal(
        id="test3",
        symbol="AVAXUSDT",
        timeframe="15m",
        pattern_type=PatternType.TRIANGLE_ASC,
        stage=PatternStage.FORMING,
        confidence=65.8,
        entry_price=35.50,
        stop_loss=34.00,
        take_profit_1=37.00,
        take_profit_2=38.50,
        risk_reward_ratio=2.0,
        formation_start=datetime.now(),
        current_timestamp=datetime.now(),
        notes={}
    ),
    Signal(
        id="test4",
        symbol="LINKUSDT",
        timeframe="5m",
        pattern_type=PatternType.HAMMER,
        stage=PatternStage.CONFIRMED,
        confidence=78.9,
        entry_price=22.35,
        stop_loss=21.80,
        take_profit_1=23.20,
        take_profit_2=23.80,
        risk_reward_ratio=1.8,
        formation_start=datetime.now(),
        current_timestamp=datetime.now(),
        notes={'volume_ratio': 1.8}
    ),
    Signal(
        id="test5",
        symbol="DOGEUSDT",
        timeframe="1h",
        pattern_type=PatternType.SUPPORT_BOUNCE,
        stage=PatternStage.NEARLY_COMPLETE,
        confidence=70.5,
        entry_price=0.3825,
        stop_loss=0.3750,
        take_profit_1=0.3950,
        take_profit_2=0.4050,
        risk_reward_ratio=2.2,
        formation_start=datetime.now(),
        current_timestamp=datetime.now(),
        notes={}
    )
]

# Estadísticas de prueba
test_statistics = {
    'scans_completed': 42,
    'signals_detected': 127,
    'signals_confirmed': 23,
    'patterns_by_type': {
        'breakout': 15,
        'double_bottom': 12,
        'support_bounce': 10,
        'triangle_asc': 8,
        'hammer': 6
    },
    'best_performers': {
        'BTCUSDT': 8,
        'ETHUSDT': 6,
        'AVAXUSDT': 5,
        'LINKUSDT': 4,
        'DOGEUSDT': 3
    }
}

def test_display():
    """Prueba el display mejorado"""
    
    print("\n🧪 PRUEBA DE VISUALIZACIÓN MEJORADA")
    print("="*60)
    
    display = TerminalSignalDisplay()
    
    # Mostrar señales con estadísticas
    display.display_signals(test_signals, test_statistics)
    
    print("\n✅ Prueba completada")
    print("\nCaracterísticas del display mejorado:")
    print("  • Tarjetas visuales para señales confirmadas")
    print("  • Tabla resumen con todas las señales")
    print("  • Panel de estadísticas")
    print("  • Colores según stage y confianza")
    print("  • Formato de precios adaptativo")
    print("  • Agrupación por prioridad")

if __name__ == "__main__":
    test_display()