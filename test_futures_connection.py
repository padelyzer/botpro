#!/usr/bin/env python3
"""
Test de conexión directa con Binance Futures Testnet
Usando la API REST directamente
"""

import requests
import hmac
import hashlib
import time
from urllib.parse import urlencode
import json

# API Keys
API_KEY = "b8b5bf65e907c1f14f4348e96be46867e74039ab8659ea882f9acf69e852dd51"
API_SECRET = "b7d343263cd5059484056142ebfa5f1bf1b01ce725b298cd2e39d9b41e2338e4"

# Base URL para Futures Testnet
BASE_URL = "https://testnet.binancefuture.com"

def create_signature(params, secret):
    """Crear firma HMAC SHA256"""
    query_string = urlencode(params)
    signature = hmac.new(
        secret.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def test_public_endpoint():
    """Probar endpoint público (no requiere autenticación)"""
    print("\n1️⃣ Probando API Pública...")
    print("-" * 40)
    
    # Obtener precio de BTC
    url = f"{BASE_URL}/fapi/v1/ticker/price"
    params = {"symbol": "BTCUSDT"}
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Precio BTC/USDT: ${float(data['price']):,.2f}")
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

def test_server_time():
    """Obtener tiempo del servidor"""
    print("\n2️⃣ Obteniendo tiempo del servidor...")
    print("-" * 40)
    
    url = f"{BASE_URL}/fapi/v1/time"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            server_time = response.json()['serverTime']
            local_time = int(time.time() * 1000)
            diff = abs(server_time - local_time)
            
            print(f"✅ Tiempo del servidor: {server_time}")
            print(f"   Tiempo local: {local_time}")
            print(f"   Diferencia: {diff}ms")
            
            if diff > 5000:
                print("⚠️ ADVERTENCIA: Tu reloj está desincronizado")
            
            return server_time
        else:
            print(f"❌ Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_private_endpoint():
    """Probar endpoint privado (requiere autenticación)"""
    print("\n3️⃣ Probando API Privada (Account Info)...")
    print("-" * 40)
    
    url = f"{BASE_URL}/fapi/v2/account"
    
    # Preparar parámetros
    timestamp = int(time.time() * 1000)
    params = {
        "timestamp": timestamp,
        "recvWindow": 5000
    }
    
    # Crear firma
    signature = create_signature(params, API_SECRET)
    params['signature'] = signature
    
    # Headers
    headers = {
        'X-MBX-APIKEY': API_KEY
    }
    
    try:
        response = requests.get(url, params=params, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Conexión exitosa!")
            print(f"   Total Balance: {data.get('totalWalletBalance', 0)} USDT")
            print(f"   Available Balance: {data.get('availableBalance', 0)} USDT")
            
            # Mostrar posiciones si existen
            positions = data.get('positions', [])
            open_positions = [p for p in positions if float(p.get('positionAmt', 0)) != 0]
            
            if open_positions:
                print(f"\n📊 Posiciones abiertas:")
                for pos in open_positions:
                    print(f"   - {pos['symbol']}: {pos['positionAmt']} contratos")
            else:
                print("   No hay posiciones abiertas")
            
            return True
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            
            # Analizar error específico
            try:
                error_data = response.json()
                error_code = error_data.get('code')
                error_msg = error_data.get('msg')
                
                if error_code == -2008:
                    print("\n💡 Las API keys son inválidas o no están activas")
                    print("   Solución:")
                    print("   1. Ve a https://testnet.binancefuture.com")
                    print("   2. Inicia sesión")
                    print("   3. Ve a 'API Management'")
                    print("   4. Verifica que las keys estén activas")
                    print("   5. O genera nuevas keys")
                elif error_code == -1021:
                    print("\n💡 Timestamp inválido - tu reloj está desincronizado")
                elif error_code == -1022:
                    print("\n💡 Firma inválida - verifica el API Secret")
                
            except:
                pass
            
            return False
            
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return False

def test_balance():
    """Obtener balance de la cuenta"""
    print("\n4️⃣ Obteniendo Balance...")
    print("-" * 40)
    
    url = f"{BASE_URL}/fapi/v2/balance"
    
    timestamp = int(time.time() * 1000)
    params = {
        "timestamp": timestamp,
        "recvWindow": 5000
    }
    
    signature = create_signature(params, API_SECRET)
    params['signature'] = signature
    
    headers = {
        'X-MBX-APIKEY': API_KEY
    }
    
    try:
        response = requests.get(url, params=params, headers=headers)
        
        if response.status_code == 200:
            balances = response.json()
            print("✅ Balances obtenidos:")
            
            for balance in balances:
                if float(balance.get('balance', 0)) > 0:
                    asset = balance['asset']
                    free = balance.get('balance', 0)
                    print(f"   {asset}: {free}")
            
            # Si no hay balance, mostrar cómo obtener fondos
            usdt_balance = next((b for b in balances if b['asset'] == 'USDT'), None)
            if not usdt_balance or float(usdt_balance.get('balance', 0)) == 0:
                print("\n💰 Para obtener fondos de prueba:")
                print("   1. Ve a https://testnet.binancefuture.com")
                print("   2. Haz clic en tu balance (arriba a la derecha)")
                print("   3. Busca el botón 'Deposit' o 'Recharge'")
                print("   4. Te darán 100,000 USDT de prueba")
            
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("=" * 50)
    print("🔌 TEST DE CONEXIÓN - BINANCE FUTURES TESTNET")
    print("=" * 50)
    
    print(f"\n📋 Configuración:")
    print(f"   URL: {BASE_URL}")
    print(f"   API Key: {API_KEY[:10]}...{API_KEY[-10:]}")
    print(f"   API Secret: {'*' * 10}")
    
    # Ejecutar pruebas
    public_ok = test_public_endpoint()
    
    if public_ok:
        server_time = test_server_time()
        
        if server_time:
            private_ok = test_private_endpoint()
            
            if private_ok:
                test_balance()
                
                print("\n" + "=" * 50)
                print("✅ TODAS LAS PRUEBAS EXITOSAS")
                print("=" * 50)
                print("\n🎯 Tu configuración está lista para:")
                print("   - Ejecutar órdenes en Futures Testnet")
                print("   - Ver las posiciones en la web")
                print("   - Hacer paper trading con datos reales")
            else:
                print("\n" + "=" * 50)
                print("⚠️ API PRIVADA NO FUNCIONA")
                print("=" * 50)
                print("\nVerifica tus API keys en:")
                print("https://testnet.binancefuture.com")
    else:
        print("\n" + "=" * 50)
        print("❌ NO HAY CONEXIÓN CON TESTNET")
        print("=" * 50)

if __name__ == "__main__":
    main()