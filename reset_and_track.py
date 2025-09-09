#!/usr/bin/env python3
"""
BOTPHIA - RESET Y TRACKING DE RENDIMIENTO
Sistema para cerrar posiciones y empezar tracking limpio
"""

import requests
import hmac
import hashlib
import time
import json
import sqlite3
from datetime import datetime
from urllib.parse import urlencode
import os
from dotenv import load_dotenv

load_dotenv()

# API Configuration
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_SECRET_KEY')
BASE_URL = "https://testnet.binancefuture.com"

def create_signature(params):
    """Crear firma HMAC SHA256"""
    query_string = urlencode(params)
    return hmac.new(
        API_SECRET.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def make_request(method, endpoint, params=None, signed=False):
    """Hacer petición a la API"""
    url = f"{BASE_URL}{endpoint}"
    
    if signed:
        if params is None:
            params = {}
        params['timestamp'] = int(time.time() * 1000)
        params['recvWindow'] = 5000
        params['signature'] = create_signature(params)
    
    headers = {'X-MBX-APIKEY': API_KEY} if signed else {}
    
    if method == 'GET':
        response = requests.get(url, params=params, headers=headers)
    else:
        response = requests.post(url, params=params, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.text}")
        return None

def get_account_info():
    """Obtener información de la cuenta"""
    return make_request('GET', '/fapi/v2/account', signed=True)

def get_positions():
    """Obtener posiciones abiertas"""
    return make_request('GET', '/fapi/v2/positionRisk', signed=True)

def close_all_positions():
    """Cerrar todas las posiciones abiertas"""
    print("\n🔄 CERRANDO TODAS LAS POSICIONES...")
    print("="*50)
    
    positions = get_positions()
    if not positions:
        print("❌ No se pudieron obtener las posiciones")
        return False
    
    closed_count = 0
    for position in positions:
        amt = float(position.get('positionAmt', 0))
        if amt != 0:
            symbol = position['symbol']
            
            # Determinar lado para cerrar
            if amt > 0:
                # Posición LONG, vender para cerrar
                side = 'SELL'
                quantity = abs(amt)
            else:
                # Posición SHORT, comprar para cerrar
                side = 'BUY'
                quantity = abs(amt)
            
            print(f"\n📍 Cerrando {symbol}:")
            print(f"   Tipo: {'LONG' if amt > 0 else 'SHORT'}")
            print(f"   Cantidad: {quantity}")
            
            # Crear orden de mercado para cerrar
            params = {
                'symbol': symbol,
                'side': side,
                'type': 'MARKET',
                'quantity': quantity
            }
            
            order = make_request('POST', '/fapi/v1/order', params=params, signed=True)
            
            if order:
                print(f"   ✅ Posición cerrada - Orden ID: {order['orderId']}")
                closed_count += 1
            else:
                print(f"   ❌ Error cerrando posición")
    
    print(f"\n✅ Total posiciones cerradas: {closed_count}")
    return True

def save_initial_state():
    """Guardar el estado inicial para tracking"""
    account = get_account_info()
    if not account:
        print("❌ No se pudo obtener información de la cuenta")
        return None
    
    initial_balance = float(account['totalWalletBalance'])
    
    # Crear base de datos de tracking
    conn = sqlite3.connect('botphia_tracking.db')
    cursor = conn.cursor()
    
    # Crear tablas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracking_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT,
            initial_balance REAL,
            current_balance REAL,
            total_pnl REAL,
            total_trades INTEGER,
            winning_trades INTEGER,
            losing_trades INTEGER,
            active INTEGER DEFAULT 1
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trade_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            timestamp TEXT,
            symbol TEXT,
            philosopher TEXT,
            side TEXT,
            entry_price REAL,
            exit_price REAL,
            quantity REAL,
            pnl REAL,
            pnl_percentage REAL,
            FOREIGN KEY (session_id) REFERENCES tracking_sessions (id)
        )
    ''')
    
    # Insertar nueva sesión
    cursor.execute('''
        INSERT INTO tracking_sessions 
        (start_time, initial_balance, current_balance, total_pnl, total_trades, winning_trades, losing_trades)
        VALUES (?, ?, ?, 0, 0, 0, 0)
    ''', (datetime.now().isoformat(), initial_balance, initial_balance))
    
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # Guardar en archivo JSON también
    state = {
        'session_id': session_id,
        'start_time': datetime.now().isoformat(),
        'initial_balance': initial_balance,
        'current_balance': initial_balance,
        'total_pnl': 0,
        'total_pnl_percentage': 0,
        'peak_balance': initial_balance,
        'lowest_balance': initial_balance,
        'total_trades': 0,
        'winning_trades': 0,
        'losing_trades': 0,
        'win_rate': 0,
        'average_win': 0,
        'average_loss': 0,
        'best_trade': 0,
        'worst_trade': 0,
        'current_drawdown': 0,
        'max_drawdown': 0
    }
    
    with open('tracking_state.json', 'w') as f:
        json.dump(state, f, indent=2)
    
    return state

def display_current_status():
    """Mostrar estado actual de la cuenta"""
    print("\n📊 ESTADO ACTUAL DE LA CUENTA")
    print("="*50)
    
    account = get_account_info()
    if not account:
        return
    
    print(f"💰 Balance Total: ${float(account['totalWalletBalance']):.2f} USDT")
    print(f"💵 Balance Disponible: ${float(account['availableBalance']):.2f} USDT")
    print(f"📈 Balance en Posiciones: ${float(account['totalPositionInitialMargin']):.2f} USDT")
    print(f"💸 PnL No Realizado: ${float(account['totalUnrealizedProfit']):.2f} USDT")
    
    # Mostrar posiciones abiertas
    positions = get_positions()
    if positions:
        print(f"\n📊 POSICIONES ABIERTAS:")
        print("-"*50)
        
        for position in positions:
            amt = float(position.get('positionAmt', 0))
            if amt != 0:
                symbol = position['symbol']
                entry_price = float(position['entryPrice'])
                mark_price = float(position['markPrice'])
                unrealized_pnl = float(position['unRealizedProfit'])
                
                print(f"\n{symbol}:")
                print(f"  Tipo: {'LONG' if amt > 0 else 'SHORT'}")
                print(f"  Cantidad: {abs(amt)}")
                print(f"  Precio Entrada: ${entry_price:.2f}")
                print(f"  Precio Actual: ${mark_price:.2f}")
                print(f"  PnL: ${unrealized_pnl:.2f}")

def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║          🔄 BOTPHIA - RESET Y TRACKING 🔄               ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    while True:
        print("\n📋 MENÚ DE OPCIONES:")
        print("1. Ver estado actual")
        print("2. Cerrar TODAS las posiciones")
        print("3. Iniciar nuevo tracking (reset)")
        print("4. Cerrar posiciones e iniciar tracking")
        print("5. Salir")
        
        choice = input("\nSelecciona opción (1-5): ")
        
        if choice == '1':
            display_current_status()
        
        elif choice == '2':
            confirm = input("\n⚠️ ¿Cerrar TODAS las posiciones? (s/n): ")
            if confirm.lower() == 's':
                close_all_positions()
                time.sleep(2)
                display_current_status()
        
        elif choice == '3':
            state = save_initial_state()
            if state:
                print("\n✅ NUEVO TRACKING INICIADO")
                print(f"📊 Balance Inicial: ${state['initial_balance']:.2f}")
                print(f"🆔 Session ID: {state['session_id']}")
                print(f"📅 Inicio: {state['start_time']}")
                print("\nEl bot ahora trackea rendimiento desde este punto")
        
        elif choice == '4':
            confirm = input("\n⚠️ ¿Cerrar posiciones y resetear tracking? (s/n): ")
            if confirm.lower() == 's':
                close_all_positions()
                time.sleep(3)
                state = save_initial_state()
                if state:
                    print("\n✅ RESET COMPLETO")
                    print(f"📊 Balance Inicial para tracking: ${state['initial_balance']:.2f}")
                    print("\n¡Listo para empezar con tracking limpio!")
        
        elif choice == '5':
            print("\n👋 Hasta luego!")
            break
        
        else:
            print("❌ Opción inválida")

if __name__ == "__main__":
    main()