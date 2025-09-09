#!/usr/bin/env python3
"""
WORKFLOW COMPLETO DE PRUEBA - Sistema de Señales con Pine Script
"""

import asyncio
import sqlite3
import json
from datetime import datetime
import time
import os

def print_section(title):
    """Helper para imprimir secciones"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

async def test_signal_generation():
    """Paso 1: Generar una señal de prueba"""
    print_section("PASO 1: GENERANDO SEÑAL DE PRUEBA")
    
    from signal_generator import SignalGenerator
    
    # Crear generador
    generator = SignalGenerator()
    
    # Generar señales para BTC
    print("🔄 Generando señal para BTCUSDT...")
    await generator.generate_signals_for_symbol('BTCUSDT')
    
    # Esperar un momento
    await asyncio.sleep(2)
    
    # Verificar señales generadas
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, symbol, action, confidence, entry_price, 
               stop_loss, take_profit, philosopher, pinescript_file,
               timestamp
        FROM signals 
        WHERE symbol = 'BTCUSDT'
        ORDER BY timestamp DESC 
        LIMIT 3
    """)
    
    signals = cursor.fetchall()
    
    if signals:
        print(f"\n✅ Se generaron {len(signals)} señales:")
        for sig in signals:
            print(f"   📊 {sig[1]} - {sig[2]} - {sig[7]} - Conf: {sig[3]:.1f}%")
            if sig[8]:  # pinescript_file
                print(f"      📄 Pine Script: {sig[8]}")
    else:
        print("⚠️ No se generaron señales (puede ser normal si no hay oportunidades)")
    
    conn.close()
    return len(signals) > 0

def check_pinescript_files():
    """Paso 2: Verificar archivos Pine Script generados"""
    print_section("PASO 2: VERIFICANDO ARCHIVOS PINE SCRIPT")
    
    # Listar archivos en /tmp
    import glob
    pine_files = glob.glob('/tmp/*pine')
    
    if pine_files:
        print(f"✅ Encontrados {len(pine_files)} archivos Pine Script:")
        for file in pine_files[-5:]:  # Mostrar últimos 5
            size = os.path.getsize(file)
            print(f"   📄 {os.path.basename(file)} ({size} bytes)")
            
        # Mostrar preview del último archivo
        if pine_files:
            latest_file = max(pine_files, key=os.path.getctime)
            print(f"\n📋 Preview de {os.path.basename(latest_file)}:")
            print("-"*50)
            with open(latest_file, 'r') as f:
                content = f.read()
                print(content[:500] + "...")
            return latest_file
    else:
        print("⚠️ No se encontraron archivos Pine Script")
        return None

def view_signal_details():
    """Paso 3: Ver detalles de las señales con Pine Script"""
    print_section("PASO 3: DETALLES DE SEÑALES CON PINE SCRIPT")
    
    conn = sqlite3.connect('trading_bot.db')
    cursor = conn.cursor()
    
    # Obtener última señal con Pine Script
    cursor.execute("""
        SELECT symbol, action, confidence, entry_price, 
               stop_loss, take_profit, philosopher,
               pinescript_file, timestamp, reasoning
        FROM signals 
        WHERE pinescript_file IS NOT NULL AND pinescript_file != ''
        ORDER BY timestamp DESC 
        LIMIT 1
    """)
    
    signal = cursor.fetchone()
    
    if signal:
        print("📊 ÚLTIMA SEÑAL CON PINE SCRIPT:")
        print(f"   Symbol: {signal[0]}")
        print(f"   Action: {signal[1]}")
        print(f"   Confidence: {signal[2]:.1f}%")
        print(f"   Entry: ${signal[3]:,.2f}")
        print(f"   Stop Loss: ${signal[4]:,.2f}")
        print(f"   Take Profit: ${signal[5]:,.2f}")
        print(f"   Philosopher: {signal[6]}")
        print(f"   Pine Script: {signal[7]}")
        print(f"   Timestamp: {signal[8]}")
        
        # Calcular R:R
        risk = abs(signal[3] - signal[4])
        reward = abs(signal[5] - signal[3])
        rr_ratio = reward / risk if risk > 0 else 0
        print(f"   R:R Ratio: {rr_ratio:.2f}:1")
        
        return signal[7]  # Retornar path del Pine Script
    else:
        print("⚠️ No hay señales con Pine Script generado")
    
    conn.close()
    return None

def test_manual_signal():
    """Paso 4: Crear una señal manual para probar"""
    print_section("PASO 4: CREANDO SEÑAL MANUAL DE PRUEBA")
    
    from pinescript_generator import PineScriptGenerator
    
    generator = PineScriptGenerator()
    
    # Crear señal manual
    test_signal = {
        'symbol': 'ETHUSDT',
        'action': 'BUY',
        'confidence': 85.5,
        'entry_price': 3250.50,
        'stop_loss': 3150.00,
        'take_profit': 3450.00,
        'philosopher': 'test_manual',
        'timestamp': datetime.now().isoformat(),
        'reasoning': 'Prueba manual del sistema',
        'market_trend': 'BULLISH',
        'rsi': 42.5,
        'volume_ratio': 1.8
    }
    
    print("📝 Generando Pine Script para señal manual...")
    print(f"   {test_signal['symbol']} - {test_signal['action']} @ ${test_signal['entry_price']}")
    
    # Generar Pine Script
    script = generator.generate_signal_script(test_signal)
    filename = f"manual_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pine"
    filepath = generator.save_to_file(script, filename)
    
    print(f"✅ Pine Script generado: {filepath}")
    
    return filepath

def show_instructions(pine_file):
    """Mostrar instrucciones para usar en TradingView"""
    print_section("INSTRUCCIONES PARA TRADINGVIEW")
    
    print("📚 CÓMO USAR EL PINE SCRIPT EN TRADINGVIEW:\n")
    print("1️⃣  Abrir el archivo Pine Script:")
    if pine_file:
        print(f"    cat {pine_file}")
    print("\n2️⃣  Ir a TradingView.com y abrir un gráfico")
    print("\n3️⃣  Abrir el Pine Editor:")
    print("    - Click en 'Pine Editor' en la parte inferior")
    print("    - O usar el atajo: Alt+E (Windows) / Cmd+E (Mac)")
    print("\n4️⃣  Pegar el código copiado en el editor")
    print("\n5️⃣  Click en 'Add to Chart' (o Ctrl/Cmd + Enter)")
    print("\n6️⃣  Configurar las opciones:")
    print("    - Show Signal Arrow: Mostrar flecha de señal")
    print("    - Show Levels: Mostrar líneas de Entry/SL/TP")
    print("    - Show Info Box: Mostrar tabla de información")
    print("    - Show RSI Panel: Mostrar panel RSI (opcional)")
    print("\n7️⃣  Configurar alertas (opcional):")
    print("    - Click derecho en el gráfico → 'Add Alert'")
    print("    - Seleccionar condición del indicador BotphIA")

async def run_complete_workflow():
    """Ejecutar el workflow completo"""
    print("\n" + "🚀"*30)
    print("  WORKFLOW COMPLETO - SISTEMA DE SEÑALES CON PINE SCRIPT")
    print("🚀"*30)
    
    # Paso 1: Generar señales
    signals_generated = await test_signal_generation()
    
    # Paso 2: Verificar archivos
    pine_file = check_pinescript_files()
    
    # Paso 3: Ver detalles
    signal_file = view_signal_details()
    
    # Paso 4: Crear señal manual
    manual_file = test_manual_signal()
    
    # Paso 5: Mostrar instrucciones
    show_instructions(manual_file or pine_file)
    
    # Resumen final
    print_section("RESUMEN DE LA PRUEBA")
    print("✅ Workflow completado exitosamente")
    print("\n📁 Archivos disponibles para copiar:")
    if pine_file:
        print(f"   1. {pine_file}")
    if manual_file:
        print(f"   2. {manual_file}")
    
    print("\n💡 Comandos útiles:")
    print("   # Ver contenido del Pine Script:")
    if manual_file:
        print(f"   cat {manual_file}")
    print("\n   # Copiar al portapapeles (Mac):")
    if manual_file:
        print(f"   cat {manual_file} | pbcopy")
    print("\n   # Ver todas las señales recientes:")
    print("   sqlite3 trading_bot.db \"SELECT * FROM signals ORDER BY timestamp DESC LIMIT 5;\"")

if __name__ == "__main__":
    # Ejecutar workflow
    asyncio.run(run_complete_workflow())