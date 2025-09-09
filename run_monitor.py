#!/usr/bin/env python3
"""
RUN MONITOR - Ejecutor simple del monitor de precisión
"""

import asyncio
import sys
from precision_signal_monitor import PrecisionSignalMonitor

async def main():
    print("\n🤖 BotphIA Precision Monitor")
    print("=" * 50)
    print("Monitor de señales de alta precisión")
    print("Solo notifica señales con alta probabilidad de éxito")
    print("=" * 50)
    print("\nConfiguracion:")
    print("  • Confianza mínima: 65%")
    print("  • Risk/Reward mínimo: 1.5:1")
    print("  • Requiere confirmación de volumen")
    print("  • Requiere alineación con tendencia")
    print("\nPresiona Ctrl+C para detener\n")
    
    monitor = PrecisionSignalMonitor()
    
    try:
        await monitor.run()
    except KeyboardInterrupt:
        print("\n✅ Monitor detenido correctamente")
        sys.exit(0)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Hasta luego!")