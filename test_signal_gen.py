#!/usr/bin/env python3
"""Test simple de generación de señales"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from philosophers import PhilosophicalTradingSystem
from philosophers_extended import register_extended_philosophers
from binance_integration import BinanceConnector

# Test básico
try:
    print("1. Creando conector...")
    connector = BinanceConnector(testnet=True)
    
    print("2. Creando sistema de trading...")
    trading_system = PhilosophicalTradingSystem()
    
    print("3. Registrando filósofos extendidos...")
    register_extended_philosophers()
    
    print("4. Filósofos disponibles:")
    for name in trading_system.philosophers.keys():
        print(f"   - {name}")
    
    print("✅ Sistema inicializado correctamente")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()