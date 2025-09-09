#!/usr/bin/env python3
"""
BOTPHIA - CONFIGURAR BALANCE INICIAL PERSONALIZADO
Configura el balance inicial para tracking sin cambiar el balance real
"""

import json
import sqlite3
from datetime import datetime
import os

def configure_initial_balance(initial_balance=220.0):
    """Configurar balance inicial personalizado para tracking"""
    
    print("="*60)
    print("⚙️  CONFIGURANDO BALANCE INICIAL PERSONALIZADO")
    print("="*60)
    
    # Leer balance real actual
    try:
        with open('reference_balance.json', 'r') as f:
            real_data = json.load(f)
            real_balance = real_data['balance_actual']
    except:
        real_balance = 16621.03  # Balance que vimos antes
    
    # Crear configuración de tracking personalizada
    tracking_config = {
        'timestamp': datetime.now().isoformat(),
        'tracking_initial_balance': initial_balance,  # Balance inicial para tracking
        'real_initial_balance': real_balance,  # Balance real en Binance
        'balance_offset': real_balance - initial_balance,  # Diferencia para ajustes
        'current_tracking_balance': initial_balance,
        'pnl_total': 0,
        'pnl_percentage': 0,
        'trades_count': 0,
        'winning_trades': 0,
        'losing_trades': 0,
        'positions_open': 0,
        'peak_balance': initial_balance,
        'lowest_balance': initial_balance,
        'max_drawdown': 0,
        'current_drawdown': 0,
        'active': True
    }
    
    # Guardar configuración
    with open('tracking_config.json', 'w') as f:
        json.dump(tracking_config, f, indent=2)
    
    # Crear base de datos para histórico
    conn = sqlite3.connect('botphia_performance.db')
    cursor = conn.cursor()
    
    # Crear tabla de sesiones
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trading_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT,
            initial_balance REAL,
            real_balance REAL,
            current_balance REAL,
            peak_balance REAL,
            lowest_balance REAL,
            total_pnl REAL,
            total_trades INTEGER,
            winning_trades INTEGER,
            losing_trades INTEGER,
            win_rate REAL,
            max_drawdown REAL,
            status TEXT,
            last_update TEXT
        )
    ''')
    
    # Crear tabla de trades
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            timestamp TEXT,
            symbol TEXT,
            philosopher TEXT,
            direction TEXT,
            entry_price REAL,
            exit_price REAL,
            quantity REAL,
            leverage INTEGER,
            pnl_usdt REAL,
            pnl_percentage REAL,
            balance_after REAL,
            reason TEXT,
            FOREIGN KEY (session_id) REFERENCES trading_sessions (id)
        )
    ''')
    
    # Crear tabla de rendimiento por filósofo
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS philosopher_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            philosopher TEXT,
            total_trades INTEGER,
            winning_trades INTEGER,
            losing_trades INTEGER,
            total_pnl REAL,
            average_pnl REAL,
            win_rate REAL,
            best_trade REAL,
            worst_trade REAL,
            FOREIGN KEY (session_id) REFERENCES trading_sessions (id)
        )
    ''')
    
    # Insertar nueva sesión
    cursor.execute('''
        INSERT INTO trading_sessions 
        (start_time, initial_balance, real_balance, current_balance, peak_balance, 
         lowest_balance, total_pnl, total_trades, winning_trades, losing_trades, 
         win_rate, max_drawdown, status, last_update)
        VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0, 0, 0, 0, 'active', ?)
    ''', (datetime.now().isoformat(), initial_balance, real_balance, 
          initial_balance, initial_balance, initial_balance, 
          datetime.now().isoformat()))
    
    session_id = cursor.lastrowid
    
    # Inicializar rendimiento de filósofos
    philosophers = ['SOCRATES', 'ARISTOTELES', 'NIETZSCHE', 'CONFUCIO', 
                   'PLATON', 'KANT', 'DESCARTES', 'SUNTZU']
    
    for philosopher in philosophers:
        cursor.execute('''
            INSERT INTO philosopher_performance
            (session_id, philosopher, total_trades, winning_trades, losing_trades,
             total_pnl, average_pnl, win_rate, best_trade, worst_trade)
            VALUES (?, ?, 0, 0, 0, 0, 0, 0, 0, 0)
        ''', (session_id, philosopher))
    
    conn.commit()
    conn.close()
    
    # Actualizar el archivo de referencia
    reference_update = {
        'timestamp': datetime.now().isoformat(),
        'balance_inicial': initial_balance,  # Para tracking
        'balance_real': real_balance,  # Balance real en Binance
        'balance_actual': initial_balance,  # Para tracking
        'pnl_total': 0,
        'posiciones_abiertas': 0,
        'session_id': session_id,
        'tracking_mode': 'custom',
        'note': f'Tracking desde ${initial_balance} USD (Balance real: ${real_balance:.2f})'
    }
    
    with open('reference_balance.json', 'w') as f:
        json.dump(reference_update, f, indent=2)
    
    print(f"\n✅ CONFIGURACIÓN COMPLETADA")
    print("-"*50)
    print(f"📊 Balance Inicial (Tracking): ${initial_balance:.2f} USD")
    print(f"💰 Balance Real (Binance): ${real_balance:.2f} USD")
    print(f"🔧 Diferencia ajustada: ${real_balance - initial_balance:.2f} USD")
    print(f"🆔 Session ID: {session_id}")
    print(f"📅 Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print(f"\n📈 CÓMO SE CALCULARÁ EL RENDIMIENTO:")
    print(f"  • PnL = Balance Actual - ${initial_balance:.2f}")
    print(f"  • ROI = (PnL / ${initial_balance:.2f}) × 100%")
    print(f"  • Si ganas $22, será +10% ROI")
    print(f"  • Si pierdes $22, será -10% ROI")
    
    print(f"\n💡 IMPORTANTE:")
    print(f"  • El bot opera con tu balance real (${real_balance:.2f})")
    print(f"  • Pero el tracking mostrará como si empezaras con ${initial_balance:.2f}")
    print(f"  • Esto te permite ver el rendimiento proporcional")
    
    print(f"\n📁 ARCHIVOS CREADOS:")
    print(f"  • tracking_config.json - Configuración de tracking")
    print(f"  • reference_balance.json - Balance de referencia")
    print(f"  • botphia_performance.db - Base de datos de rendimiento")
    
    return {
        'session_id': session_id,
        'initial_balance': initial_balance,
        'real_balance': real_balance,
        'status': 'configured'
    }

def show_example():
    """Mostrar ejemplo de cómo se verá el tracking"""
    print(f"\n" + "="*60)
    print("📊 EJEMPLO DE CÓMO SE VERÁ EL TRACKING")
    print("="*60)
    
    print(f"\n🎯 Escenario 1: Ganas $22 (10% de $220)")
    print(f"  Balance mostrado: $242.00")
    print(f"  PnL: +$22.00")
    print(f"  ROI: +10.00%")
    print(f"  Performance: 🟢 EXCELENTE")
    
    print(f"\n😐 Escenario 2: Pierdes $11 (5% de $220)")
    print(f"  Balance mostrado: $209.00")
    print(f"  PnL: -$11.00")
    print(f"  ROI: -5.00%")
    print(f"  Performance: 🟡 CUIDADO")
    
    print(f"\n🚀 Escenario 3: Ganas $220 (100% de $220)")
    print(f"  Balance mostrado: $440.00")
    print(f"  PnL: +$220.00")
    print(f"  ROI: +100.00%")
    print(f"  Performance: 🔥 INCREÍBLE")

if __name__ == "__main__":
    # Configurar con $220 USD
    result = configure_initial_balance(220.0)
    
    # Mostrar ejemplos
    show_example()
    
    print(f"\n" + "="*60)
    print("✅ SISTEMA LISTO PARA TRACKING DESDE $220 USD")
    print("="*60)
    print("\n🚀 Próximo paso: Reiniciar el bot")
    print("   python3 botphia_futures_trader.py")
    print("\nEl bot mostrará el rendimiento como si empezaras con $220")