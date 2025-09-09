#!/usr/bin/env python3
"""
Profit Maximizer Bot - Sistema automatizado para maximizar ganancias
"""

import json
import time
import requests
from datetime import datetime, timedelta
import sqlite3
import threading

class ProfitMaximizerBot:
    def __init__(self):
        self.db_path = 'trading_bot.db'
        self.running = False
        self.positions = {}
        self.profit_targets = {
            'conservative': 0.02,  # 2%
            'moderate': 0.03,      # 3%
            'aggressive': 0.05     # 5%
        }
        self.mode = 'moderate'
        self.max_positions = 3
        self.risk_per_trade = 0.02  # 2% del capital
        
    def analyze_symbol(self, symbol):
        """Analiza un símbolo para detectar oportunidad de entrada"""
        try:
            # Obtener datos de Binance
            url = f'https://api.binance.com/api/v3/klines'
            params = {
                'symbol': f'{symbol}USDT',
                'interval': '15m',
                'limit': 100
            }
            response = requests.get(url, params=params)
            candles = response.json()
            
            # Calcular indicadores
            closes = [float(c[4]) for c in candles]
            volumes = [float(c[5]) for c in candles]
            
            # RSI
            rsi = self.calculate_rsi(closes)
            
            # MACD
            macd, signal = self.calculate_macd(closes)
            
            # Volumen promedio
            avg_volume = sum(volumes[-20:]) / 20
            current_volume = volumes[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            # Precio actual y cambio
            current_price = closes[-1]
            change_1h = ((closes[-1] / closes[-4]) - 1) * 100 if len(closes) > 4 else 0
            
            # SEÑALES DE COMPRA
            buy_signals = 0
            
            # RSI oversold
            if rsi < 35:
                buy_signals += 2
            elif rsi < 45:
                buy_signals += 1
                
            # MACD bullish
            if macd > signal and macd < 0:
                buy_signals += 2
            elif macd > signal:
                buy_signals += 1
                
            # Volumen alto
            if volume_ratio > 1.5:
                buy_signals += 1
            if volume_ratio > 2:
                buy_signals += 1
                
            # Momentum
            if -5 < change_1h < -2:
                buy_signals += 1
            elif change_1h > 2 and change_1h < 5:
                buy_signals += 1
                
            # Calcular fuerza de la señal
            signal_strength = (buy_signals / 7) * 100
            
            return {
                'symbol': symbol,
                'price': current_price,
                'rsi': rsi,
                'macd': macd > signal,
                'volume_ratio': volume_ratio,
                'change_1h': change_1h,
                'signal_strength': signal_strength,
                'action': 'BUY' if signal_strength > 50 else 'HOLD'
            }
            
        except Exception as e:
            print(f"Error analizando {symbol}: {e}")
            return None
    
    def calculate_rsi(self, prices, period=14):
        """Calcula RSI"""
        if len(prices) < period + 1:
            return 50
            
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
            
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_macd(self, prices, fast=12, slow=26, signal=9):
        """Calcula MACD"""
        if len(prices) < slow:
            return 0, 0
            
        # EMA rápida
        ema_fast = self.calculate_ema(prices, fast)
        # EMA lenta  
        ema_slow = self.calculate_ema(prices, slow)
        
        # MACD line
        macd = ema_fast - ema_slow
        
        # Signal line (EMA del MACD)
        macd_values = []
        for i in range(slow, len(prices)):
            ema_f = self.calculate_ema(prices[:i+1], fast)
            ema_s = self.calculate_ema(prices[:i+1], slow)
            macd_values.append(ema_f - ema_s)
            
        signal_line = self.calculate_ema(macd_values, signal) if len(macd_values) > signal else macd
        
        return macd, signal_line
    
    def calculate_ema(self, prices, period):
        """Calcula EMA"""
        if len(prices) < period:
            return prices[-1] if prices else 0
            
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
            
        return ema
    
    def execute_trade(self, signal):
        """Ejecuta una operación basada en la señal"""
        symbol = signal['symbol']
        
        # Calcular tamaño de posición
        capital = 1000  # Capital demo
        position_size = capital * self.risk_per_trade
        
        # Calcular stops y targets
        entry_price = signal['price']
        stop_loss = entry_price * 0.98  # -2%
        take_profit = entry_price * (1 + self.profit_targets[self.mode])
        
        # Registrar posición
        self.positions[symbol] = {
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'size': position_size,
            'entry_time': datetime.now(),
            'signal_strength': signal['signal_strength']
        }
        
        # Guardar en base de datos
        self.save_signal(signal)
        
        print(f"\n✅ TRADE EJECUTADO: {symbol}")
        print(f"   Entrada: ${entry_price:.4f}")
        print(f"   Stop: ${stop_loss:.4f} (-2%)")
        print(f"   Target: ${take_profit:.4f} (+{self.profit_targets[self.mode]*100:.1f}%)")
        print(f"   Fuerza: {signal['signal_strength']:.0f}%")
        
        return True
    
    def check_positions(self):
        """Verifica posiciones abiertas para stops y targets"""
        for symbol in list(self.positions.keys()):
            pos = self.positions[symbol]
            
            # Obtener precio actual
            try:
                url = f'https://api.binance.com/api/v3/ticker/price'
                params = {'symbol': f'{symbol}USDT'}
                response = requests.get(url, params=params)
                current_price = float(response.json()['price'])
                
                # Check stop loss
                if current_price <= pos['stop_loss']:
                    profit = -0.02  # -2%
                    print(f"🔴 STOP LOSS: {symbol} @ ${current_price:.4f} ({profit*100:.1f}%)")
                    del self.positions[symbol]
                    
                # Check take profit
                elif current_price >= pos['take_profit']:
                    profit = self.profit_targets[self.mode]
                    print(f"🟢 TAKE PROFIT: {symbol} @ ${current_price:.4f} (+{profit*100:.1f}%)")
                    del self.positions[symbol]
                    
                # Trailing stop si está en profit
                elif current_price > pos['entry_price'] * 1.01:
                    new_stop = current_price * 0.99
                    if new_stop > pos['stop_loss']:
                        pos['stop_loss'] = new_stop
                        print(f"📈 Trailing stop {symbol}: ${new_stop:.4f}")
                        
            except Exception as e:
                print(f"Error verificando {symbol}: {e}")
    
    def save_signal(self, signal):
        """Guarda señal en la base de datos"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Crear tabla si no existe
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS profit_signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    symbol TEXT,
                    price REAL,
                    signal_strength REAL,
                    rsi REAL,
                    action TEXT,
                    mode TEXT
                )
            ''')
            
            # Insertar señal
            cursor.execute('''
                INSERT INTO profit_signals 
                (timestamp, symbol, price, signal_strength, rsi, action, mode)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                signal['symbol'],
                signal['price'],
                signal['signal_strength'],
                signal['rsi'],
                signal['action'],
                self.mode
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error guardando señal: {e}")
    
    def run(self):
        """Loop principal del bot"""
        self.running = True
        symbols = ['BTC', 'ETH', 'SOL', 'BNB', 'DOGE', 'XRP', 'ADA', 'AVAX']
        
        print("🤖 PROFIT MAXIMIZER BOT INICIADO")
        print(f"   Modo: {self.mode.upper()}")
        print(f"   Target: {self.profit_targets[self.mode]*100:.1f}%")
        print(f"   Max posiciones: {self.max_positions}")
        print("="*50)
        
        while self.running:
            try:
                # Verificar posiciones existentes
                self.check_positions()
                
                # Buscar nuevas oportunidades si hay espacio
                if len(self.positions) < self.max_positions:
                    for symbol in symbols:
                        if symbol not in self.positions:
                            signal = self.analyze_symbol(symbol)
                            
                            if signal and signal['action'] == 'BUY':
                                if signal['signal_strength'] > 60:
                                    self.execute_trade(signal)
                                    time.sleep(1)
                
                # Status update
                if self.positions:
                    print(f"\n📊 Posiciones abiertas: {len(self.positions)}")
                    for sym, pos in self.positions.items():
                        elapsed = (datetime.now() - pos['entry_time']).seconds / 60
                        print(f"   • {sym}: ${pos['entry_price']:.4f} ({elapsed:.0f} min)")
                
                # Esperar antes del próximo ciclo
                time.sleep(30)
                
            except KeyboardInterrupt:
                print("\n⛔ Bot detenido por usuario")
                self.running = False
                break
            except Exception as e:
                print(f"Error en loop principal: {e}")
                time.sleep(10)

if __name__ == "__main__":
    bot = ProfitMaximizerBot()
    bot.run()