#!/usr/bin/env python3
"""
Script de prueba para la generación de Pine Script
"""

from pinescript_generator import PineScriptGenerator
from datetime import datetime
import json

def test_single_signal():
    """Prueba generación de Pine Script para una señal individual"""
    
    generator = PineScriptGenerator()
    
    # Señal de prueba
    test_signal = {
        'symbol': 'BTCUSDT',
        'action': 'BUY',
        'confidence': 75.5,
        'entry_price': 95500.25,
        'stop_loss': 93390.25,
        'take_profit': 98265.25,
        'philosopher': 'warren_buffett',
        'timestamp': datetime.now().isoformat(),
        'reasoning': 'Strong support at 95000 level with bullish divergence',
        'market_trend': 'BULLISH',
        'rsi': 45.2,
        'volume_ratio': 1.35
    }
    
    print("🔧 Generando Pine Script para señal individual...")
    print(f"📊 Señal: {test_signal['symbol']} - {test_signal['action']} @ {test_signal['entry_price']}")
    
    # Generar script
    script = generator.generate_signal_script(test_signal)
    
    # Guardar en archivo
    filename = f"test_signal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pine"
    filepath = generator.save_to_file(script, filename)
    
    print(f"✅ Script generado y guardado en: {filepath}")
    print("\n" + "="*50)
    print("PREVIEW DEL SCRIPT:")
    print("="*50)
    print(script[:500] + "...")
    
    return filepath

def test_multiple_signals():
    """Prueba generación de Pine Script para múltiples señales"""
    
    generator = PineScriptGenerator()
    
    # Múltiples señales de prueba
    test_signals = [
        {
            'symbol': 'BTCUSDT',
            'action': 'BUY',
            'confidence': 82.3,
            'entry_price': 95500,
            'stop_loss': 93500,
            'take_profit': 98500,
            'philosopher': 'warren_buffett'
        },
        {
            'symbol': 'BTCUSDT', 
            'action': 'SELL',
            'confidence': 65.8,
            'entry_price': 96200,
            'stop_loss': 98200,
            'take_profit': 93200,
            'philosopher': 'george_soros'
        },
        {
            'symbol': 'BTCUSDT',
            'action': 'BUY',
            'confidence': 71.2,
            'entry_price': 95000,
            'stop_loss': 93000,
            'take_profit': 97500,
            'philosopher': 'ray_dalio'
        }
    ]
    
    print("\n🔧 Generando Pine Script para múltiples señales...")
    print(f"📊 Total de señales: {len(test_signals)}")
    
    # Generar script
    script = generator.generate_multi_signal_script(test_signals)
    
    # Guardar en archivo
    filename = f"test_multi_signals_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pine"
    filepath = generator.save_to_file(script, filename)
    
    print(f"✅ Script multi-señal generado y guardado en: {filepath}")
    print("\n" + "="*50)
    print("PREVIEW DEL SCRIPT:")
    print("="*50)
    print(script[:500] + "...")
    
    return filepath

def test_empty_signals():
    """Prueba generación cuando no hay señales"""
    
    generator = PineScriptGenerator()
    
    print("\n🔧 Generando Pine Script sin señales...")
    
    # Generar script vacío
    script = generator.generate_empty_script()
    
    # Guardar en archivo
    filename = f"test_empty_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pine"
    filepath = generator.save_to_file(script, filename)
    
    print(f"✅ Script vacío generado y guardado en: {filepath}")
    print("\n" + "="*50)
    print("SCRIPT COMPLETO:")
    print("="*50)
    print(script)
    
    return filepath

def main():
    """Ejecutar todas las pruebas"""
    
    print("="*60)
    print("🧪 PRUEBA DE GENERACIÓN DE PINE SCRIPT")
    print("="*60)
    
    # Test 1: Señal individual
    file1 = test_single_signal()
    
    # Test 2: Múltiples señales
    file2 = test_multiple_signals()
    
    # Test 3: Sin señales
    file3 = test_empty_signals()
    
    print("\n" + "="*60)
    print("✅ TODAS LAS PRUEBAS COMPLETADAS")
    print("="*60)
    print("\n📁 Archivos generados:")
    print(f"  1. {file1}")
    print(f"  2. {file2}")
    print(f"  3. {file3}")
    print("\n💡 Instrucciones para usar en TradingView:")
    print("  1. Abrir TradingView (tradingview.com)")
    print("  2. Ir a Pine Editor")
    print("  3. Copiar el contenido del archivo .pine")
    print("  4. Pegar en el editor")
    print("  5. Click en 'Add to Chart'")
    print("\n🎯 Los scripts incluyen:")
    print("  - Visualización de niveles de entrada/SL/TP")
    print("  - Información de la señal en tabla")
    print("  - Alertas configurables")
    print("  - Indicador RSI opcional")
    print("  - Zonas de soporte/resistencia")

if __name__ == "__main__":
    main()