#!/usr/bin/env python3
"""
Monitor en vivo de señales con generación de Pine Script
"""

import asyncio
import sqlite3
from datetime import datetime, timedelta
import os
import sys

class LiveSignalMonitor:
    def __init__(self):
        self.db_path = "trading_bot.db"
        self.last_signal_id = None
        
    def get_latest_signals(self, limit=5):
        """Obtener las últimas señales con Pine Script"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, symbol, action, confidence, entry_price,
                   stop_loss, take_profit, philosopher, 
                   pinescript_file, timestamp
            FROM signals
            WHERE timestamp > datetime('now', '-1 hour')
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))
        
        signals = cursor.fetchall()
        conn.close()
        return signals
    
    def display_signal(self, signal):
        """Mostrar señal formateada"""
        # Calcular R:R
        risk = abs(signal[4] - signal[5])
        reward = abs(signal[6] - signal[4])
        rr_ratio = reward / risk if risk > 0 else 0
        
        # Colores ANSI
        GREEN = '\033[92m'
        RED = '\033[91m'
        YELLOW = '\033[93m'
        BLUE = '\033[94m'
        RESET = '\033[0m'
        
        action_color = GREEN if signal[2] == 'BUY' else RED
        conf_color = GREEN if signal[3] > 70 else YELLOW if signal[3] > 50 else RED
        
        print(f"\n{'='*60}")
        print(f"🔔 NUEVA SEÑAL DETECTADA - {signal[9]}")
        print(f"{'='*60}")
        print(f"📊 Symbol: {BLUE}{signal[1]}{RESET}")
        print(f"🎯 Action: {action_color}{signal[2]}{RESET}")
        print(f"💪 Confidence: {conf_color}{signal[3]:.1f}%{RESET}")
        print(f"💰 Entry: ${signal[4]:,.2f}")
        print(f"🛑 Stop Loss: ${signal[5]:,.2f}")
        print(f"✅ Take Profit: ${signal[6]:,.2f}")
        print(f"📈 R:R Ratio: {rr_ratio:.2f}:1")
        print(f"🧠 Philosopher: {signal[7]}")
        
        if signal[8]:
            print(f"📄 Pine Script: {BLUE}{signal[8]}{RESET}")
            
            # Mostrar comando para copiar
            if sys.platform == "darwin":  # macOS
                print(f"\n💡 Copiar Pine Script al portapapeles:")
                print(f"   {YELLOW}cat {signal[8]} | pbcopy{RESET}")
        
        print(f"{'='*60}")
    
    async def monitor_signals(self):
        """Monitorear señales continuamente"""
        print("🔍 MONITOR DE SEÑALES EN VIVO")
        print("================================")
        print("Esperando nuevas señales...")
        print("(Presiona Ctrl+C para salir)\n")
        
        displayed_ids = set()
        
        while True:
            try:
                signals = self.get_latest_signals()
                
                for signal in signals:
                    signal_id = signal[0]
                    if signal_id not in displayed_ids:
                        self.display_signal(signal)
                        displayed_ids.add(signal_id)
                        
                        # Notificación de sistema (macOS)
                        if sys.platform == "darwin":
                            os.system(f"""
                                osascript -e 'display notification "Nueva señal: {signal[1]} - {signal[2]} ({signal[3]:.0f}%)" with title "BotphIA Trading Signal"'
                            """)
                
                # Limpiar IDs antiguos (mantener solo últimos 100)
                if len(displayed_ids) > 100:
                    displayed_ids = set(list(displayed_ids)[-50:])
                
                await asyncio.sleep(5)  # Verificar cada 5 segundos
                
            except KeyboardInterrupt:
                print("\n\n👋 Monitor detenido")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                await asyncio.sleep(10)

async def main():
    monitor = LiveSignalMonitor()
    await monitor.monitor_signals()

if __name__ == "__main__":
    asyncio.run(main())