#!/usr/bin/env python3
"""
Script para forzar un trade de prueba con $11
Para verificar que todo funciona correctamente
"""

import requests
import hmac
import hashlib
import time
from urllib.parse import urlencode
import os
from dotenv import load_dotenv

load_dotenv()

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

def execute_test_trade():
    """Ejecutar un trade de prueba pequeño"""
    
    print("="*60)
    print("🧪 EJECUTANDO TRADE DE PRUEBA")
    print("="*60)
    
    # 1. Obtener precio actual de ETH
    ticker = make_request('GET', '/fapi/v1/ticker/price', 
                         params={'symbol': 'ETHUSDT'})
    
    if not ticker:
        print("❌ No se pudo obtener el precio")
        return
    
    current_price = float(ticker['price'])
    print(f"📊 Precio ETH/USDT: ${current_price:.2f}")
    
    # 2. Configurar apalancamiento a 5x
    leverage_result = make_request('POST', '/fapi/v1/leverage',
                                  params={'symbol': 'ETHUSDT', 'leverage': 5},
                                  signed=True)
    
    if leverage_result:
        print(f"⚙️ Apalancamiento configurado: 5x")
    
    # 3. Calcular cantidad para $11 de margen
    margin = 11.0  # $11 de margen
    exposure = margin * 5  # $55 de exposición con 5x
    quantity = round(exposure / current_price, 3)
    
    print(f"\n💎 DETALLES DEL TRADE:")
    print(f"  Margen: ${margin:.2f}")
    print(f"  Exposición: ${exposure:.2f}")
    print(f"  Cantidad: {quantity} ETH")
    print(f"  Tipo: LONG (compra)")
    
    # 4. Ejecutar orden de compra
    order_params = {
        'symbol': 'ETHUSDT',
        'side': 'BUY',
        'type': 'MARKET',
        'quantity': quantity
    }
    
    print(f"\n📤 Enviando orden...")
    order = make_request('POST', '/fapi/v1/order', 
                        params=order_params, signed=True)
    
    if order:
        print(f"✅ ORDEN EJECUTADA EXITOSAMENTE!")
        print(f"  Order ID: {order['orderId']}")
        print(f"  Status: {order['status']}")
        print(f"  Símbolo: {order['symbol']}")
        print(f"  Cantidad ejecutada: {order.get('executedQty', quantity)}")
        
        # 5. Configurar stop loss y take profit mentalmente
        stop_loss = current_price * 0.98  # -2%
        take_profit = current_price * 1.03  # +3%
        
        print(f"\n🎯 NIVELES SUGERIDOS:")
        print(f"  Stop Loss: ${stop_loss:.2f} (-2%)")
        print(f"  Take Profit: ${take_profit:.2f} (+3%)")
        
        print(f"\n📊 PARA CERRAR LA POSICIÓN:")
        print(f"  Ejecuta una orden SELL de {quantity} ETH")
        print(f"  O espera a que el bot la gestione")
        
        return order
    else:
        print("❌ Error ejecutando la orden")
        return None

def check_positions():
    """Verificar posiciones abiertas"""
    print("\n📊 VERIFICANDO POSICIONES...")
    
    positions = make_request('GET', '/fapi/v2/positionRisk', signed=True)
    
    if positions:
        open_positions = []
        for pos in positions:
            amt = float(pos.get('positionAmt', 0))
            if amt != 0:
                open_positions.append({
                    'symbol': pos['symbol'],
                    'amount': amt,
                    'entry': float(pos['entryPrice']),
                    'mark': float(pos['markPrice']),
                    'pnl': float(pos['unRealizedProfit'])
                })
        
        if open_positions:
            print("\n✅ POSICIONES ABIERTAS:")
            for p in open_positions:
                print(f"  {p['symbol']}: {p['amount']} @ ${p['entry']:.2f}")
                print(f"    Precio actual: ${p['mark']:.2f}")
                print(f"    PnL: ${p['pnl']:.2f}")
        else:
            print("✅ No hay posiciones abiertas")
    
    # Ver balance
    account = make_request('GET', '/fapi/v2/account', signed=True)
    if account:
        print(f"\n💰 BALANCE:")
        print(f"  Total: ${float(account['totalWalletBalance']):.2f}")
        print(f"  Disponible: ${float(account['availableBalance']):.2f}")
        print(f"  En posiciones: ${float(account['totalPositionInitialMargin']):.2f}")

def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║         🧪 TRADE DE PRUEBA - ETH/USDT 🧪               ║
║                                                          ║
║  Este script ejecutará un trade de prueba:              ║
║  • Símbolo: ETH/USDT                                    ║
║  • Tipo: LONG (compra)                                  ║
║  • Margen: $11                                          ║
║  • Apalancamiento: 5x                                   ║
║  • Exposición: $55                                      ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    choice = input("\n¿Ejecutar trade de prueba? (s/n): ")
    
    if choice.lower() == 's':
        result = execute_test_trade()
        if result:
            print("\n✅ Trade ejecutado. Verificando posiciones...")
            time.sleep(2)
            check_positions()
    else:
        print("👍 Solo verificando posiciones...")
        check_positions()

if __name__ == "__main__":
    main()