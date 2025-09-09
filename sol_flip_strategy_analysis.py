#!/usr/bin/env python3
"""
Análisis de la estrategia: Exit LONG @ $199 → Enter SHORT
"""

def analyze_flip_strategy():
    # Current position
    long_entry = 199
    current_price = 196.25
    
    # Strategy parameters
    exit_target = 199
    short_entry = 199
    short_target_1 = 192
    short_target_2 = 190
    short_stop = 202
    
    print("="*60)
    print("📊 ESTRATEGIA: LONG → SHORT FLIP")
    print("="*60)
    
    print("\n1️⃣ SITUACIÓN ACTUAL:")
    print(f"   • Posición LONG: ${long_entry}")
    print(f"   • Precio actual: ${current_price}")
    print(f"   • P&L actual: ${current_price - long_entry:.2f} ({((current_price - long_entry)/long_entry)*100:.2f}%)")
    
    print("\n2️⃣ PLAN DE SALIDA:")
    print(f"   • Esperar rebote a: ${exit_target}")
    print(f"   • Distancia: {((exit_target - current_price)/current_price)*100:.2f}%")
    print(f"   • Resultado: Breakeven (0% pérdida)")
    
    print("\n3️⃣ ENTRADA SHORT (después de salir):")
    print(f"   • Entry: ${short_entry}")
    print(f"   • Target 1: ${short_target_1} ({((short_target_1 - short_entry)/short_entry)*100:.1f}%)")
    print(f"   • Target 2: ${short_target_2} ({((short_target_2 - short_entry)/short_entry)*100:.1f}%)")
    print(f"   • Stop Loss: ${short_stop} ({((short_stop - short_entry)/short_entry)*100:.1f}%)")
    
    # Risk/Reward calculation
    risk = short_stop - short_entry
    reward_1 = short_entry - short_target_1
    reward_2 = short_entry - short_target_2
    
    print("\n4️⃣ RISK/REWARD RATIO:")
    print(f"   • Risk: ${risk:.2f}")
    print(f"   • Reward T1: ${reward_1:.2f} (R:R = 1:{reward_1/risk:.1f})")
    print(f"   • Reward T2: ${reward_2:.2f} (R:R = 1:{reward_2/risk:.1f})")
    
    print("\n5️⃣ ¿POR QUÉ TIENE SENTIDO?")
    print("   ✅ Mercado en STRONG BEARISH")
    print("   ✅ RSI sobrevendido = rebote temporal esperado")
    print("   ✅ Resistencia fuerte en $199-201")
    print("   ✅ Momentum bajista en todos los timeframes")
    print("   ✅ Liquidaciones de longs en $194-196 actuarán como imán")
    
    print("\n6️⃣ ESCENARIOS PROBABLES:")
    print("   📈 MEJOR CASO:")
    print("      • Rebote a $199 → Salir LONG")
    print("      • SHORT desde $199 → Target $190")
    print("      • Ganancia potencial: 4.5% en SHORT")
    
    print("\n   📊 CASO NEUTRAL:")
    print("      • Rebote a $198 → Salir con -$1 pérdida")
    print("      • SHORT desde $198 → Target $192")
    print("      • Ganancia neta: ~3% después de pérdida")
    
    print("\n   📉 PEOR CASO:")
    print("      • No hay rebote, sigue cayendo")
    print("      • Activar stop loss en $194")
    print("      • Pérdida: -2.5%")
    
    print("\n7️⃣ TIMING ESPERADO:")
    print("   • Rebote técnico: 4-12 horas (RSI muy sobrevendido)")
    print("   • Zona crítica: $198.50 - $200.50")
    print("   • Si pasa de $201, cancelar SHORT")
    
    print("\n⚡ ACCIÓN INMEDIATA:")
    print("   1. Monitor activo esperando $199")
    print("   2. Orden de venta lista en $199")
    print("   3. Preparar orden SHORT inmediatamente después")
    print("="*60)

if __name__ == "__main__":
    analyze_flip_strategy()