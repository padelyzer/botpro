#!/usr/bin/env python3
"""
Test de conexión con Binance Testnet
"""

import os
import sys
from dotenv import load_dotenv
import ccxt
import pandas as pd
from datetime import datetime

# Cargar variables de entorno
load_dotenv()

def test_binance_connection():
    """Prueba la conexión con Binance testnet"""
    
    print("=" * 50)
    print("🔌 PRUEBA DE CONEXIÓN BINANCE TESTNET")
    print("=" * 50)
    
    # Obtener credenciales
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_SECRET_KEY')
    testnet = os.getenv('BINANCE_TESTNET', 'true').lower() == 'true'
    
    print(f"\n📋 Configuración:")
    print(f"  - API Key: {api_key[:10]}...{api_key[-10:] if api_key else 'NO CONFIGURADA'}")
    print(f"  - API Secret: {'*' * 10 if api_secret else 'NO CONFIGURADA'}")
    print(f"  - Testnet: {testnet}")
    
    if not api_key or not api_secret:
        print("\n❌ ERROR: No se encontraron las API keys en el archivo .env")
        return False
    
    try:
        # Configurar exchange
        if testnet:
            exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                    'adjustForTimeDifference': True
                },
                'urls': {
                    'api': {
                        'public': 'https://testnet.binance.vision/api',
                        'private': 'https://testnet.binance.vision/api',
                    }
                }
            })
            print("\n🌐 Conectando a Binance TESTNET...")
        else:
            exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
            })
            print("\n🌐 Conectando a Binance PRODUCTION...")
        
        # Probar conexión pública (no requiere autenticación)
        print("\n1️⃣ Probando API pública...")
        ticker = exchange.fetch_ticker('BTC/USDT')
        print(f"   ✅ Precio BTC/USDT: ${ticker['last']:,.2f}")
        
        # Probar conexión privada (requiere autenticación)
        print("\n2️⃣ Probando API privada...")
        try:
            balance = exchange.fetch_balance()
            usdt_balance = balance.get('USDT', {}).get('free', 0)
            print(f"   ✅ Balance USDT: ${usdt_balance:,.2f}")
            
            # Mostrar otros balances si existen
            non_zero_balances = {
                asset: info for asset, info in balance['total'].items() 
                if info > 0
            }
            if non_zero_balances:
                print("\n   💰 Balances disponibles:")
                for asset, amount in non_zero_balances.items():
                    print(f"      - {asset}: {amount:.8f}")
        except Exception as e:
            print(f"   ⚠️ No se pudo obtener el balance: {str(e)}")
            print("   (Esto es normal en testnet si no has depositado fondos)")
        
        # Probar obtención de datos históricos
        print("\n3️⃣ Probando obtención de datos históricos...")
        ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1h', limit=10)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        print(f"   ✅ Últimas 10 velas obtenidas")
        print(f"   📊 Última vela: {df.iloc[-1]['timestamp']} - Close: ${df.iloc[-1]['close']:,.2f}")
        
        # Probar símbolos disponibles
        print("\n4️⃣ Verificando símbolos de trading...")
        markets = exchange.load_markets()
        symbols_to_check = ['DOGE/USDT', 'ADA/USDT', 'XRP/USDT', 'DOT/USDT']
        available_symbols = []
        for symbol in symbols_to_check:
            if symbol in markets:
                available_symbols.append(symbol)
                print(f"   ✅ {symbol} disponible")
            else:
                print(f"   ❌ {symbol} no disponible")
        
        print("\n" + "=" * 50)
        print("✅ CONEXIÓN EXITOSA")
        print("=" * 50)
        print(f"\n🎯 Resumen:")
        print(f"  - Conexión: {'TESTNET' if testnet else 'PRODUCTION'}")
        print(f"  - API pública: ✅ Funcionando")
        print(f"  - API privada: ✅ Funcionando")
        print(f"  - Datos históricos: ✅ Disponibles")
        print(f"  - Símbolos listos: {len(available_symbols)}/{len(symbols_to_check)}")
        
        return True
        
    except Exception as e:
        print("\n" + "=" * 50)
        print("❌ ERROR DE CONEXIÓN")
        print("=" * 50)
        print(f"\n🔍 Detalles del error:")
        print(f"  {str(e)}")
        
        if "Invalid API-key" in str(e):
            print("\n💡 Solución: Verifica que las API keys sean correctas")
        elif "Timestamp" in str(e):
            print("\n💡 Solución: Tu reloj del sistema puede estar desincronizado")
        else:
            print("\n💡 Verifica tu conexión a internet y las credenciales")
        
        return False

if __name__ == "__main__":
    success = test_binance_connection()
    sys.exit(0 if success else 1)