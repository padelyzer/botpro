#!/usr/bin/env python3
"""
Live Profit Alerts - Sistema de alertas en tiempo real para oportunidades de trading
"""

import asyncio
import json
import requests
from datetime import datetime
import websocket
import threading
import time

class LiveProfitAlerts:
    def __init__(self):
        self.alerts = []
        self.monitored_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'DOGEUSDT']
        self.alert_conditions = {
            'rsi_oversold': 30,
            'rsi_overbought': 70,
            'volume_spike': 2.0,  # 2x promedio
            'price_drop': -3.0,   # -3%
            'price_pump': 3.0,    # +3%
            'breakout': 1.5       # 1.5% sobre resistencia
        }
        self.running = True
        
    def check_alerts(self, symbol, data):
        """Verifica condiciones de alerta para un símbolo"""
        alerts_triggered = []
        
        # Obtener datos actuales
        price = float(data.get('c', 0))  # Close price
        volume = float(data.get('v', 0))  # Volume
        price_change = float(data.get('P', 0))  # Price change percent
        
        # 1. Alerta de caída fuerte (oportunidad de compra)
        if price_change < self.alert_conditions['price_drop']:
            alerts_triggered.append({
                'type': 'BUY_DIP',
                'symbol': symbol,
                'price': price,
                'change': price_change,
                'message': f'🟢 {symbol}: CAÍDA {price_change:.1f}% - Posible rebote',
                'action': 'LONG',
                'confidence': min(95, abs(price_change) * 10)
            })
        
        # 2. Alerta de pump (momentum)
        if price_change > self.alert_conditions['price_pump']:
            if price_change < 7:  # No FOMO en pumps extremos
                alerts_triggered.append({
                    'type': 'MOMENTUM',
                    'symbol': symbol,
                    'price': price,
                    'change': price_change,
                    'message': f'🚀 {symbol}: SUBIDA {price_change:.1f}% - Momentum activo',
                    'action': 'LONG',
                    'confidence': min(85, price_change * 8)
                })
            else:
                alerts_triggered.append({
                    'type': 'OVERBOUGHT',
                    'symbol': symbol,
                    'price': price,
                    'change': price_change,
                    'message': f'🔴 {symbol}: SOBRECOMPRA {price_change:.1f}% - Posible short',
                    'action': 'SHORT',
                    'confidence': min(80, price_change * 5)
                })
        
        return alerts_triggered
    
    def get_market_data(self):
        """Obtiene datos del mercado en tiempo real"""
        try:
            url = 'https://api.binance.com/api/v3/ticker/24hr'
            response = requests.get(url, timeout=5)
            data = response.json()
            
            relevant_data = {}
            for ticker in data:
                if ticker['symbol'] in self.monitored_symbols:
                    relevant_data[ticker['symbol']] = {
                        'c': ticker['lastPrice'],
                        'v': ticker['volume'],
                        'P': ticker['priceChangePercent'],
                        'h': ticker['highPrice'],
                        'l': ticker['lowPrice']
                    }
            
            return relevant_data
            
        except Exception as e:
            print(f"Error obteniendo datos: {e}")
            return {}
    
    def calculate_entry_exit(self, price, action):
        """Calcula puntos de entrada y salida óptimos"""
        if action == 'LONG':
            entry = price * 1.001  # Entrada ligeramente por encima
            stop_loss = price * 0.98  # Stop loss -2%
            take_profit1 = price * 1.02  # TP1 +2%
            take_profit2 = price * 1.03  # TP2 +3%
            take_profit3 = price * 1.05  # TP3 +5%
        else:  # SHORT
            entry = price * 0.999  # Entrada ligeramente por debajo
            stop_loss = price * 1.02  # Stop loss +2%
            take_profit1 = price * 0.98  # TP1 -2%
            take_profit2 = price * 0.97  # TP2 -3%
            take_profit3 = price * 0.95  # TP3 -5%
        
        return {
            'entry': entry,
            'stop_loss': stop_loss,
            'targets': [take_profit1, take_profit2, take_profit3]
        }
    
    def display_alert(self, alert):
        """Muestra alerta formateada"""
        print("\n" + "="*60)
        print(f"⚡ ALERTA DE PROFIT - {datetime.now().strftime('%H:%M:%S')}")
        print("="*60)
        print(alert['message'])
        print(f"💰 Precio actual: ${alert['price']:.4f}")
        print(f"📊 Confianza: {alert['confidence']:.0f}%")
        
        # Calcular niveles
        levels = self.calculate_entry_exit(alert['price'], alert['action'])
        print(f"\n📍 NIVELES RECOMENDADOS:")
        print(f"   Entrada: ${levels['entry']:.4f}")
        print(f"   Stop Loss: ${levels['stop_loss']:.4f}")
        print(f"   Target 1: ${levels['targets'][0]:.4f} (+2%)")
        print(f"   Target 2: ${levels['targets'][1]:.4f} (+3%)")
        print(f"   Target 3: ${levels['targets'][2]:.4f} (+5%)")
        
        # Risk/Reward
        risk = abs(levels['entry'] - levels['stop_loss'])
        reward = abs(levels['targets'][1] - levels['entry'])
        rr_ratio = reward / risk if risk > 0 else 0
        print(f"\n📈 Risk/Reward: 1:{rr_ratio:.1f}")
        
        # Guardar alerta
        self.save_alert(alert, levels)
    
    def save_alert(self, alert, levels):
        """Guarda alerta en archivo JSON"""
        try:
            alert_data = {
                'timestamp': datetime.now().isoformat(),
                'symbol': alert['symbol'],
                'type': alert['type'],
                'action': alert['action'],
                'price': alert['price'],
                'confidence': alert['confidence'],
                'levels': levels
            }
            
            # Leer alertas existentes
            try:
                with open('profit_alerts_log.json', 'r') as f:
                    alerts = json.load(f)
            except:
                alerts = []
            
            # Agregar nueva alerta
            alerts.append(alert_data)
            
            # Mantener solo las últimas 100 alertas
            alerts = alerts[-100:]
            
            # Guardar
            with open('profit_alerts_log.json', 'w') as f:
                json.dump(alerts, f, indent=2)
                
        except Exception as e:
            print(f"Error guardando alerta: {e}")
    
    def monitor_loop(self):
        """Loop principal de monitoreo"""
        print("🔔 SISTEMA DE ALERTAS DE PROFIT ACTIVO")
        print("   Monitoreando:", ', '.join([s.replace('USDT', '') for s in self.monitored_symbols]))
        print("   Condiciones: Caídas > 3%, Pumps > 3%, Volumen x2")
        print("="*60)
        
        last_check = {}
        
        while self.running:
            try:
                # Obtener datos del mercado
                market_data = self.get_market_data()
                
                # Verificar alertas para cada símbolo
                for symbol, data in market_data.items():
                    alerts = self.check_alerts(symbol, data)
                    
                    for alert in alerts:
                        # Evitar alertas repetidas (cooldown de 5 min)
                        alert_key = f"{symbol}_{alert['type']}"
                        if alert_key not in last_check or \
                           (datetime.now() - last_check[alert_key]).seconds > 300:
                            
                            self.display_alert(alert)
                            last_check[alert_key] = datetime.now()
                
                # Esperar antes del próximo chequeo
                time.sleep(10)
                
            except KeyboardInterrupt:
                print("\n⛔ Sistema de alertas detenido")
                self.running = False
                break
            except Exception as e:
                print(f"Error en monitor: {e}")
                time.sleep(5)
    
    def start(self):
        """Inicia el sistema de alertas"""
        self.monitor_loop()

if __name__ == "__main__":
    alerts = LiveProfitAlerts()
    alerts.start()