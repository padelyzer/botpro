#!/usr/bin/env python3
"""
TEST SIGNAL SYSTEM - Prueba rápida del sistema de señales
"""

import asyncio
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_pattern_detection():
    """Prueba la detección de patrones en un par específico"""
    
    print("\n" + "="*60)
    print("🧪 TEST 1: DETECCIÓN DE PATRONES")
    print("="*60)
    
    from binance_integration import BinanceConnector
    from multi_timeframe_signal_detector import PatternDetector
    
    connector = BinanceConnector(testnet=False)
    detector = PatternDetector()
    
    # Probar con BTCUSDT
    symbol = "BTCUSDT"
    timeframe = "15m"
    
    print(f"\n📊 Analizando {symbol} en {timeframe}...")
    
    # Obtener datos
    df = connector.get_historical_data(symbol, timeframe=timeframe, limit=100)
    
    if not df.empty:
        print(f"✅ Datos obtenidos: {len(df)} velas")
        
        # Detectar patrones
        signals = detector.detect_all_patterns(df, symbol, timeframe)
        
        if signals:
            print(f"\n🎯 Se detectaron {len(signals)} patrones:")
            for signal in signals:
                print(f"""
   📊 Patrón: {signal.pattern_type.value}
   📈 Stage: {signal.stage.value}
   💪 Confianza: {signal.confidence:.1f}%
   💰 Entry: ${signal.entry_price:,.2f}
   🛑 Stop Loss: ${signal.stop_loss:,.2f}
   🎯 Target 1: ${signal.take_profit_1:,.2f}
   📈 R:R Ratio: {signal.risk_reward_ratio:.2f}:1
   """)
        else:
            print("ℹ️ No se detectaron patrones en este momento")
    else:
        print("❌ No se pudieron obtener datos")

async def test_notifications():
    """Prueba el sistema de notificaciones"""
    
    print("\n" + "="*60)
    print("🧪 TEST 2: SISTEMA DE NOTIFICACIONES")
    print("="*60)
    
    from multi_timeframe_signal_detector import Signal, PatternType, PatternStage
    from signal_notification_system import SignalNotificationManager
    from enum import Enum
    
    notifier = SignalNotificationManager()
    
    # Crear señal de prueba
    test_signal = Signal(
        id=f"TEST_{datetime.now().timestamp()}",
        symbol="ETHUSDT",
        timeframe="1h",
        pattern_type=PatternType.DOUBLE_BOTTOM,
        stage=PatternStage.CONFIRMED,
        confidence=85.5,
        entry_price=3250.50,
        stop_loss=3150.00,
        take_profit_1=3450.00,
        take_profit_2=3550.00,
        risk_reward_ratio=2.0,
        formation_start=datetime.now(),
        current_timestamp=datetime.now(),
        notes={
            'volume_ratio': 1.5,
            'support_level': 3200.00
        }
    )
    
    print("\n📨 Enviando notificación de prueba...")
    await notifier.process_signal(test_signal)
    print("✅ Notificación enviada")

async def test_multi_pair_scan():
    """Prueba escaneo de múltiples pares"""
    
    print("\n" + "="*60)
    print("🧪 TEST 3: ESCANEO MULTI-PAR")
    print("="*60)
    
    from realtime_signal_monitor import RealTimeSignalMonitor, MonitorMode
    
    # Crear monitor en modo balanceado
    monitor = RealTimeSignalMonitor(mode=MonitorMode.BALANCED)
    
    # Limitar a algunos pares para la prueba
    monitor.trading_pairs = ['BTCUSDT', 'ETHUSDT', 'AVAXUSDT', 'LINKUSDT']
    
    print(f"\n🔍 Escaneando {len(monitor.trading_pairs)} pares...")
    
    # Ejecutar un escaneo
    signals = await monitor.scan_all_pairs()
    
    print(f"\n📊 Resultados del escaneo:")
    print(f"   Total señales detectadas: {len(signals)}")
    
    if signals:
        # Agrupar por símbolo
        by_symbol = {}
        for signal in signals:
            if signal.symbol not in by_symbol:
                by_symbol[signal.symbol] = []
            by_symbol[signal.symbol].append(signal)
        
        for symbol, symbol_signals in by_symbol.items():
            print(f"\n   {symbol}: {len(symbol_signals)} señales")
            for sig in symbol_signals[:2]:  # Mostrar máximo 2 por símbolo
                print(f"      - {sig.pattern_type.value} ({sig.timeframe}) - {sig.confidence:.1f}%")
    
    # Mostrar estadísticas
    monitor.print_statistics()

async def test_pine_script_generation():
    """Prueba la generación de Pine Script"""
    
    print("\n" + "="*60)
    print("🧪 TEST 4: GENERACIÓN DE PINE SCRIPT")
    print("="*60)
    
    from multi_timeframe_signal_detector import Signal, PatternType, PatternStage
    from signal_notification_system import SignalNotificationManager
    
    notifier = SignalNotificationManager()
    
    # Crear señal para generar Pine Script
    test_signal = Signal(
        id=f"PINE_TEST_{datetime.now().timestamp()}",
        symbol="AVAXUSDT",
        timeframe="4h",
        pattern_type=PatternType.BREAKOUT,
        stage=PatternStage.CONFIRMED,
        confidence=78.5,
        entry_price=35.50,
        stop_loss=34.00,
        take_profit_1=37.00,
        take_profit_2=38.50,
        risk_reward_ratio=2.0,
        formation_start=datetime.now(),
        current_timestamp=datetime.now(),
        notes={'breakout_level': 35.00, 'volume_ratio': 2.1}
    )
    
    print("\n📊 Generando Pine Script para señal de prueba...")
    pine_script = notifier.generate_pine_script(test_signal)
    
    if pine_script:
        print("✅ Pine Script generado exitosamente")
        print("\n📋 Preview del script (primeras 10 líneas):")
        lines = pine_script.split('\n')[:10]
        for line in lines:
            print(f"   {line}")
        
        # Guardar en archivo
        filename = f"/tmp/test_signal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pine"
        with open(filename, 'w') as f:
            f.write(pine_script)
        print(f"\n📁 Script guardado en: {filename}")
    else:
        print("❌ Error generando Pine Script")

async def main():
    """Ejecuta todas las pruebas"""
    
    print("\n" + "🤖"*20)
    print("   SISTEMA DE SEÑALES MULTI-TIMEFRAME - PRUEBAS")
    print("🤖"*20)
    
    tests = [
        ("Detección de Patrones", test_pattern_detection),
        ("Sistema de Notificaciones", test_notifications),
        ("Escaneo Multi-Par", test_multi_pair_scan),
        ("Generación Pine Script", test_pine_script_generation)
    ]
    
    print(f"\n📋 Se ejecutarán {len(tests)} pruebas")
    
    for i, (name, test_func) in enumerate(tests, 1):
        try:
            print(f"\n🔄 Ejecutando prueba {i}/{len(tests)}: {name}")
            await test_func()
            print(f"✅ Prueba {i} completada")
        except Exception as e:
            print(f"❌ Error en prueba {i}: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("✅ TODAS LAS PRUEBAS COMPLETADAS")
    print("="*60)
    
    print("\n📚 Para ejecutar el monitor completo:")
    print("   python3 realtime_signal_monitor.py")
    
    print("\n📊 Pares configurados:")
    print("   AVAX, LINK, NEAR, XRP, PENGU, ADA, SUI, DOT, DOGE, UNI, ETH, BTC")
    
    print("\n⏱ Timeframes monitoreados:")
    print("   5m, 15m, 1h, 4h")
    
    print("\n🔔 Notificaciones progresivas:")
    print("   1. Potencial → 2. Formándose → 3. Casi completo → 4. CONFIRMADO")

if __name__ == "__main__":
    asyncio.run(main())