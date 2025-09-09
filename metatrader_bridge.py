#!/usr/bin/env python3
"""
MetaTrader Bridge - Conecta las señales de Python con MT4/MT5
"""

import MetaTrader5 as mt5
import json
import time
from datetime import datetime
import socket
import threading

class MetaTraderBridge:
    def __init__(self):
        self.connected = False
        self.account = None
        self.symbols = []
        
    def connect_mt5(self, login, password, server):
        """Conecta con MetaTrader 5"""
        # Inicializar MT5
        if not mt5.initialize():
            print("❌ Error inicializando MT5")
            return False
        
        # Login
        authorized = mt5.login(login, password=password, server=server)
        if authorized:
            self.account = mt5.account_info()
            print(f"✅ Conectado a MT5")
            print(f"   Cuenta: {self.account.login}")
            print(f"   Balance: ${self.account.balance:.2f}")
            print(f"   Broker: {self.account.company}")
            self.connected = True
            return True
        else:
            print("❌ Error de autenticación")
            return False
    
    def send_order(self, symbol, action, volume, sl=None, tp=None):
        """Envía orden a MetaTrader"""
        if not self.connected:
            print("❌ No conectado a MT5")
            return None
        
        # Obtener info del símbolo
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            print(f"❌ Símbolo {symbol} no encontrado")
            return None
        
        # Si el símbolo no está visible, hacerlo visible
        if not symbol_info.visible:
            if not mt5.symbol_select(symbol, True):
                print(f"❌ No se pudo seleccionar {symbol}")
                return None
        
        # Obtener precio actual
        price = mt5.symbol_info_tick(symbol).ask if action == "BUY" else mt5.symbol_info_tick(symbol).bid
        
        # Preparar request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": mt5.ORDER_TYPE_BUY if action == "BUY" else mt5.ORDER_TYPE_SELL,
            "price": price,
            "deviation": 20,
            "magic": 234000,
            "comment": "Python Trading Bot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        # Agregar SL y TP si se especifican
        if sl:
            request["sl"] = sl
        if tp:
            request["tp"] = tp
        
        # Enviar orden
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ Error enviando orden: {result.comment}")
            return None
        else:
            print(f"✅ Orden ejecutada: {result.order}")
            return result
    
    def get_positions(self):
        """Obtiene posiciones abiertas"""
        if not self.connected:
            return []
        
        positions = mt5.positions_get()
        if positions is None:
            return []
        
        return [{
            'ticket': p.ticket,
            'symbol': p.symbol,
            'type': 'BUY' if p.type == 0 else 'SELL',
            'volume': p.volume,
            'price': p.price_open,
            'profit': p.profit,
            'sl': p.sl,
            'tp': p.tp
        } for p in positions]
    
    def close_position(self, ticket):
        """Cierra una posición específica"""
        position = mt5.positions_get(ticket=ticket)
        if not position:
            print(f"❌ Posición {ticket} no encontrada")
            return False
        
        position = position[0]
        symbol = position.symbol
        volume = position.volume
        
        # Tipo opuesto para cerrar
        trade_type = mt5.ORDER_TYPE_SELL if position.type == 0 else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).bid if position.type == 0 else mt5.symbol_info_tick(symbol).ask
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": ticket,
            "symbol": symbol,
            "volume": volume,
            "type": trade_type,
            "price": price,
            "deviation": 20,
            "magic": 234000,
            "comment": "Python close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"❌ Error cerrando posición: {result.comment}")
            return False
        else:
            print(f"✅ Posición {ticket} cerrada")
            return True
    
    def modify_position(self, ticket, sl=None, tp=None):
        """Modifica SL/TP de una posición"""
        position = mt5.positions_get(ticket=ticket)
        if not position:
            return False
        
        position = position[0]
        
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": sl if sl else position.sl,
            "tp": tp if tp else position.tp,
        }
        
        result = mt5.order_send(request)
        return result.retcode == mt5.TRADE_RETCODE_DONE


class SignalReceiver:
    """Recibe señales de nuestros scripts Python y las ejecuta en MT5"""
    
    def __init__(self, mt_bridge):
        self.bridge = mt_bridge
        self.running = False
        self.port = 9999
        
    def start_server(self):
        """Inicia servidor para recibir señales"""
        self.running = True
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(('localhost', self.port))
        server_socket.listen(5)
        
        print(f"📡 Servidor de señales escuchando en puerto {self.port}")
        
        while self.running:
            try:
                client, address = server_socket.accept()
                data = client.recv(1024).decode()
                
                if data:
                    signal = json.loads(data)
                    self.process_signal(signal)
                
                client.close()
            except Exception as e:
                print(f"Error: {e}")
    
    def process_signal(self, signal):
        """Procesa y ejecuta señal recibida"""
        print(f"\n📨 Señal recibida: {signal['symbol']} - {signal['action']}")
        
        # Convertir símbolo si es necesario (ej: BTC -> BTCUSD)
        mt_symbol = self.convert_symbol(signal['symbol'])
        
        # Calcular tamaño de posición
        volume = self.calculate_volume(signal.get('risk', 100))
        
        # Ejecutar orden
        result = self.bridge.send_order(
            symbol=mt_symbol,
            action=signal['action'],
            volume=volume,
            sl=signal.get('stop_loss'),
            tp=signal.get('take_profit')
        )
        
        if result:
            print(f"✅ Trade ejecutado: {result.order}")
    
    def convert_symbol(self, symbol):
        """Convierte símbolo de Binance a formato MT5"""
        conversions = {
            'BTC': 'BTCUSD',
            'ETH': 'ETHUSD',
            'DOGE': 'DOGEUSD',
            'SOL': 'SOLUSD',
            'BNB': 'BNBUSD',
            'XRP': 'XRPUSD'
        }
        return conversions.get(symbol, symbol)
    
    def calculate_volume(self, risk_amount):
        """Calcula el tamaño de la posición basado en el riesgo"""
        # Por defecto 0.01 lotes, ajustar según tu broker
        return 0.01


class SignalSender:
    """Envía señales desde Python a MetaTrader"""
    
    def __init__(self, host='localhost', port=9999):
        self.host = host
        self.port = port
    
    def send_signal(self, symbol, action, stop_loss=None, take_profit=None, risk=100):
        """Envía señal al bridge de MT5"""
        signal = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'action': action,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'risk': risk
        }
        
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((self.host, self.port))
            client.send(json.dumps(signal).encode())
            client.close()
            print(f"✅ Señal enviada: {symbol} {action}")
            return True
        except Exception as e:
            print(f"❌ Error enviando señal: {e}")
            return False


# CONFIGURACIÓN Y USO
"""
REQUISITOS DE INSTALACIÓN:

1. Instalar MetaTrader 5:
   - Descargar MT5 de tu broker
   - Crear cuenta demo o real

2. Instalar librería Python:
   pip install MetaTrader5

3. Configurar credenciales:
   LOGIN = tu_numero_de_cuenta
   PASSWORD = "tu_contraseña"
   SERVER = "servidor_de_tu_broker"

4. Ejecutar bridge:
   python metatrader_bridge.py

EJEMPLO DE USO:

# Conectar con MT5
bridge = MetaTraderBridge()
bridge.connect_mt5(login=12345678, password="tupass", server="ICMarkets-Demo")

# Enviar orden
bridge.send_order("EURUSD", "BUY", 0.01, sl=1.0800, tp=1.0900)

# Desde otro script Python, enviar señal
sender = SignalSender()
sender.send_signal("BTC", "BUY", stop_loss=108000, take_profit=115000)
"""

if __name__ == "__main__":
    print("=" * 70)
    print("METATRADER BRIDGE - CONFIGURACIÓN")
    print("=" * 70)
    print("\n📋 PASOS PARA CONECTAR:")
    print("\n1. INSTALAR MT5:")
    print("   - Descargar MetaTrader 5 de tu broker")
    print("   - Abrir cuenta demo para pruebas")
    print("\n2. INSTALAR LIBRERÍA:")
    print("   pip install MetaTrader5")
    print("\n3. CONFIGURAR CREDENCIALES:")
    print("   - Login: Número de cuenta MT5")
    print("   - Password: Contraseña de la cuenta")
    print("   - Server: Servidor del broker")
    print("\n4. MODIFICAR ESTE SCRIPT con tus credenciales")
    print("\n5. EJECUTAR: python metatrader_bridge.py")
    print("\n✅ Las señales de tus scripts se ejecutarán automáticamente en MT5!")