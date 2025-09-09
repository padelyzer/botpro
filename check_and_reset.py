#!/usr/bin/env python3
"""
BOTPHIA - CHECK Y RESET AUTOMÁTICO
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
    query_string = urlencode(params)
    return hmac.new(
        API_SECRET.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def make_request(method, endpoint, params=None, signed=False):
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

def check_account():
    """Ver estado actual y crear punto de referencia"""
    print("="*60)
    print("📊 ESTADO ACTUAL DE BINANCE FUTURES TESTNET")
    print("="*60)
    
    # Obtener info de cuenta
    account = make_request('GET', '/fapi/v2/account', signed=True)
    if not account:
        return
    
    balance_total = float(account['totalWalletBalance'])
    balance_disponible = float(account['availableBalance'])
    margen_usado = float(account['totalPositionInitialMargin'])
    pnl_no_realizado = float(account['totalUnrealizedProfit'])
    
    print(f"\n💰 RESUMEN DE CUENTA:")
    print(f"  Balance Total: ${balance_total:.2f} USDT")
    print(f"  Balance Disponible: ${balance_disponible:.2f} USDT")
    print(f"  Margen en Uso: ${margen_usado:.2f} USDT")
    print(f"  PnL No Realizado: ${pnl_no_realizado:+.2f} USDT")
    
    # Obtener posiciones
    positions = make_request('GET', '/fapi/v2/positionRisk', signed=True)
    
    open_positions = []
    if positions:
        for pos in positions:
            amt = float(pos.get('positionAmt', 0))
            if amt != 0:
                open_positions.append({
                    'symbol': pos['symbol'],
                    'side': 'LONG' if amt > 0 else 'SHORT',
                    'amount': abs(amt),
                    'entry_price': float(pos['entryPrice']),
                    'mark_price': float(pos['markPrice']),
                    'pnl': float(pos['unRealizedProfit']),
                    'margin': float(pos['isolatedWallet']) if pos['marginType'] == 'isolated' else margen_usado/len(open_positions) if open_positions else 0
                })
    
    if open_positions:
        print(f"\n📈 POSICIONES ABIERTAS ({len(open_positions)}):")
        print("-"*50)
        for pos in open_positions:
            pnl_pct = ((pos['mark_price'] - pos['entry_price']) / pos['entry_price'] * 100) if pos['side'] == 'LONG' else ((pos['entry_price'] - pos['mark_price']) / pos['entry_price'] * 100)
            print(f"\n  {pos['symbol']} - {pos['side']}")
            print(f"    Cantidad: {pos['amount']}")
            print(f"    Entrada: ${pos['entry_price']:.2f}")
            print(f"    Actual: ${pos['mark_price']:.2f}")
            print(f"    PnL: ${pos['pnl']:.2f} ({pnl_pct:+.2f}%)")
    else:
        print("\n✅ No hay posiciones abiertas")
    
    # Guardar estado de referencia
    reference_state = {
        'timestamp': datetime.now().isoformat(),
        'balance_inicial': balance_total,
        'balance_actual': balance_total,
        'pnl_total': 0,
        'posiciones_abiertas': len(open_positions)
    }
    
    # Guardar en archivo
    with open('reference_balance.json', 'w') as f:
        json.dump(reference_state, f, indent=2)
    
    print("\n" + "="*60)
    print("📝 PUNTO DE REFERENCIA GUARDADO")
    print("="*60)
    print(f"  Fecha/Hora: {reference_state['timestamp']}")
    print(f"  Balance de Referencia: ${balance_total:.2f}")
    print(f"  Archivo: reference_balance.json")
    print("\n💡 Usa este balance como referencia para medir el rendimiento del bot")
    
    # Opciones de reset
    print("\n" + "="*60)
    print("🔄 OPCIONES DE RESET")
    print("="*60)
    
    if open_positions:
        print("\n⚠️ Tienes posiciones abiertas. Para hacer un reset limpio:")
        print("   1. Ejecuta: python3 close_all_positions.py")
        print("   2. Espera a que se cierren todas")
        print("   3. El nuevo balance será tu punto de partida")
    else:
        print("\n✅ No tienes posiciones abiertas")
        print(f"   Balance actual para tracking: ${balance_total:.2f}")
    
    print("\n📊 PARA VER EL RENDIMIENTO:")
    print("   - El bot comparará contra el balance de referencia")
    print("   - PnL = Balance Actual - Balance Referencia")
    print(f"   - ROI = (PnL / {balance_total:.2f}) × 100%")
    
    return reference_state

def close_positions():
    """Script separado para cerrar posiciones"""
    print("\n🔄 CERRANDO POSICIONES...")
    
    positions = make_request('GET', '/fapi/v2/positionRisk', signed=True)
    if not positions:
        print("❌ No se pudieron obtener las posiciones")
        return
    
    closed = 0
    for pos in positions:
        amt = float(pos.get('positionAmt', 0))
        if amt != 0:
            symbol = pos['symbol']
            side = 'SELL' if amt > 0 else 'BUY'
            quantity = abs(amt)
            
            params = {
                'symbol': symbol,
                'side': side,
                'type': 'MARKET',
                'quantity': quantity
            }
            
            order = make_request('POST', '/fapi/v1/order', params=params, signed=True)
            if order:
                print(f"✅ Cerrada {symbol} - Orden: {order['orderId']}")
                closed += 1
                time.sleep(0.5)
    
    if closed > 0:
        print(f"\n✅ Se cerraron {closed} posiciones")
        time.sleep(3)
        print("\n📊 Nuevo estado:")
        check_account()
    else:
        print("✅ No hay posiciones para cerrar")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'close':
        close_positions()
    else:
        check_account()