#!/usr/bin/env python3
"""
BOTPHIA LIMITED - SOLO USA $220 DEL BALANCE TOTAL
Bot que opera como si solo tuviera $220 disponibles
"""

import requests
import hmac
import hashlib
import time
import json
import pandas as pd
import numpy as np
from datetime import datetime
import logging
from urllib.parse import urlencode
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BotphiaLimited220:
    def __init__(self):
        # API Configuration
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.api_secret = os.getenv('BINANCE_SECRET_KEY')
        self.base_url = "https://testnet.binancefuture.com"
        
        # LÍMITE ESTRICTO DE $220
        self.MAX_CAPITAL = 220.0  # Solo usaremos $220 del balance total
        self.used_capital = 0.0   # Capital usado actualmente
        self.available_capital = 220.0  # Capital disponible para trades
        
        # Trading Configuration
        self.leverage = 5  # Menor apalancamiento para más control
        self.risk_per_trade = 0.05  # 5% de $220 = $11 por trade
        self.max_positions = 3
        self.min_confidence = 70
        
        # Símbolos
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        
        # Control de posiciones
        self.positions = {}
        self.position_values = {}  # Valor de cada posición para control
        
        # Estadísticas
        self.stats = {
            'initial_balance': 220.0,
            'current_balance': 220.0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'peak_balance': 220.0,
            'lowest_balance': 220.0
        }
        
        # Verificar balance real
        self.verify_real_balance()
        
        logger.info("="*60)
        logger.info("💎 BOTPHIA LIMITED - SOLO $220 USD")
        logger.info("="*60)
        logger.info(f"📊 Capital Máximo: ${self.MAX_CAPITAL:.2f}")
        logger.info(f"💰 Capital Disponible: ${self.available_capital:.2f}")
        logger.info(f"⚙️ Apalancamiento: {self.leverage}x")
        logger.info(f"💎 Riesgo por trade: ${self.MAX_CAPITAL * self.risk_per_trade:.2f}")
        logger.info("⚠️ IMPORTANTE: Solo usaremos $220 del balance total")
    
    def create_signature(self, params):
        query_string = urlencode(params)
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def make_request(self, method, endpoint, params=None, signed=False):
        url = f"{self.base_url}{endpoint}"
        
        if signed:
            if params is None:
                params = {}
            params['timestamp'] = int(time.time() * 1000)
            params['recvWindow'] = 5000
            params['signature'] = self.create_signature(params)
        
        headers = {'X-MBX-APIKEY': self.api_key} if signed else {}
        
        if method == 'GET':
            response = requests.get(url, params=params, headers=headers)
        else:
            response = requests.post(url, params=params, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"API Error: {response.text}")
            return None
    
    def verify_real_balance(self):
        """Verificar que tengamos más de $220 en la cuenta"""
        account = self.make_request('GET', '/fapi/v2/account', signed=True)
        if account:
            real_balance = float(account['totalWalletBalance'])
            available = float(account['availableBalance'])
            
            logger.info(f"\n📊 VERIFICACIÓN DE BALANCE:")
            logger.info(f"  Balance Real Total: ${real_balance:.2f}")
            logger.info(f"  Balance Disponible: ${available:.2f}")
            
            if available < 220:
                logger.warning(f"⚠️ Balance insuficiente. Solo hay ${available:.2f} disponibles")
                logger.warning(f"   Ajustando capital máximo a ${available:.2f}")
                self.MAX_CAPITAL = available
                self.available_capital = available
            else:
                logger.info(f"✅ Balance suficiente. Limitando uso a ${self.MAX_CAPITAL:.2f}")
            
            return True
        return False
    
    def calculate_available_capital(self):
        """Calcular cuánto capital tenemos disponible de los $220"""
        return self.MAX_CAPITAL - self.used_capital
    
    def can_open_position(self, required_capital):
        """Verificar si podemos abrir una posición"""
        available = self.calculate_available_capital()
        
        if required_capital > available:
            logger.warning(f"❌ Capital insuficiente: Necesitas ${required_capital:.2f}, disponible ${available:.2f}")
            return False
        
        if len(self.positions) >= self.max_positions:
            logger.warning(f"❌ Máximo de posiciones alcanzado ({self.max_positions})")
            return False
        
        return True
    
    def get_klines(self, symbol, interval='5m', limit=100):
        """Obtener velas japonesas"""
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        data = self.make_request('GET', '/fapi/v1/klines', params=params)
        
        if data:
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_volume',
                'taker_buy_quote_volume', 'ignore'
            ])
            
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Indicadores
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['rsi'] = self.calculate_rsi(df['close'])
            
            return df
        return None
    
    def calculate_rsi(self, prices, period=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def analyze_market(self, df, symbol):
        """Análisis simple de mercado"""
        if df is None or len(df) < 20:
            return None
        
        current = df.iloc[-1]
        
        # Estrategia conservadora para proteger los $220
        if current['rsi'] < 30 and current['close'] > current['sma_20']:
            return {
                'symbol': symbol,
                'signal': 'LONG',
                'confidence': 80,
                'reason': 'RSI oversold + Above SMA20',
                'price': current['close']
            }
        elif current['rsi'] > 70 and current['close'] < current['sma_20']:
            return {
                'symbol': symbol,
                'signal': 'SHORT',
                'confidence': 80,
                'reason': 'RSI overbought + Below SMA20',
                'price': current['close']
            }
        
        return None
    
    def execute_limited_trade(self, signal):
        """Ejecutar trade con límite estricto de $220"""
        symbol = signal['symbol']
        
        # Calcular capital necesario (5% de $220 = $11)
        risk_capital = self.MAX_CAPITAL * self.risk_per_trade
        
        # Verificar si podemos abrir la posición
        if not self.can_open_position(risk_capital):
            return False
        
        # Obtener precio actual
        current_price = signal['price']
        
        # Calcular cantidad con el capital limitado
        # Con apalancamiento 5x, $11 de margen = $55 de exposición
        exposure = risk_capital * self.leverage
        quantity = round(exposure / current_price, 4)
        
        logger.info(f"\n💎 EJECUTANDO TRADE LIMITADO")
        logger.info(f"  Símbolo: {symbol}")
        logger.info(f"  Señal: {signal['signal']}")
        logger.info(f"  Capital usado: ${risk_capital:.2f} (de ${self.available_capital:.2f} disponibles)")
        logger.info(f"  Exposición: ${exposure:.2f} (con {self.leverage}x)")
        logger.info(f"  Cantidad: {quantity}")
        logger.info(f"  Precio: ${current_price:.2f}")
        
        # Configurar apalancamiento
        self.make_request('POST', '/fapi/v1/leverage', 
                         params={'symbol': symbol, 'leverage': self.leverage}, 
                         signed=True)
        
        # Ejecutar orden
        side = 'BUY' if signal['signal'] == 'LONG' else 'SELL'
        params = {
            'symbol': symbol,
            'side': side,
            'type': 'MARKET',
            'quantity': quantity
        }
        
        order = self.make_request('POST', '/fapi/v1/order', params=params, signed=True)
        
        if order:
            logger.info(f"✅ Orden ejecutada: {order['orderId']}")
            
            # Actualizar control de capital
            self.used_capital += risk_capital
            self.available_capital = self.calculate_available_capital()
            
            # Guardar posición
            self.positions[symbol] = {
                'type': signal['signal'],
                'entry_price': current_price,
                'quantity': quantity,
                'capital_used': risk_capital,
                'entry_time': datetime.now(),
                'stop_loss': current_price * 0.98 if signal['signal'] == 'LONG' else current_price * 1.02,
                'take_profit': current_price * 1.04 if signal['signal'] == 'LONG' else current_price * 0.96
            }
            
            self.position_values[symbol] = risk_capital
            
            logger.info(f"📊 RESUMEN DE CAPITAL:")
            logger.info(f"  Capital Total: ${self.MAX_CAPITAL:.2f}")
            logger.info(f"  Capital Usado: ${self.used_capital:.2f}")
            logger.info(f"  Capital Disponible: ${self.available_capital:.2f}")
            logger.info(f"  Posiciones Abiertas: {len(self.positions)}/{self.max_positions}")
            
            self.stats['total_trades'] += 1
            return True
        
        return False
    
    def check_positions(self):
        """Verificar posiciones y actualizar capital"""
        for symbol, position in list(self.positions.items()):
            ticker = self.make_request('GET', '/fapi/v1/ticker/price', 
                                      params={'symbol': symbol})
            if not ticker:
                continue
            
            current_price = float(ticker['price'])
            entry_price = position['entry_price']
            
            # Calcular PnL
            if position['type'] == 'LONG':
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
                should_close = (current_price <= position['stop_loss'] or 
                              current_price >= position['take_profit'])
            else:
                pnl_pct = ((entry_price - current_price) / entry_price) * 100
                should_close = (current_price >= position['stop_loss'] or 
                              current_price <= position['take_profit'])
            
            # PnL en dólares (sobre el capital usado)
            pnl_dollars = position['capital_used'] * (pnl_pct / 100) * self.leverage
            
            logger.info(f"📊 {symbol}: PnL ${pnl_dollars:+.2f} ({pnl_pct * self.leverage:+.2f}%)")
            
            if should_close:
                self.close_position(symbol, pnl_dollars)
    
    def close_position(self, symbol, pnl):
        """Cerrar posición y liberar capital"""
        position = self.positions[symbol]
        
        # Cerrar en Binance
        side = 'SELL' if position['type'] == 'LONG' else 'BUY'
        params = {
            'symbol': symbol,
            'side': side,
            'type': 'MARKET',
            'quantity': position['quantity']
        }
        
        order = self.make_request('POST', '/fapi/v1/order', params=params, signed=True)
        
        if order:
            # Liberar capital
            self.used_capital -= position['capital_used']
            self.available_capital = self.calculate_available_capital()
            
            # Actualizar balance virtual
            self.stats['current_balance'] += pnl
            self.stats['total_pnl'] += pnl
            
            if pnl > 0:
                self.stats['winning_trades'] += 1
                logger.info(f"✅ {symbol} cerrado: +${pnl:.2f}")
            else:
                self.stats['losing_trades'] += 1
                logger.info(f"❌ {symbol} cerrado: ${pnl:.2f}")
            
            # Actualizar peak y lowest
            if self.stats['current_balance'] > self.stats['peak_balance']:
                self.stats['peak_balance'] = self.stats['current_balance']
            if self.stats['current_balance'] < self.stats['lowest_balance']:
                self.stats['lowest_balance'] = self.stats['current_balance']
            
            del self.positions[symbol]
            del self.position_values[symbol]
            
            self.display_stats()
    
    def display_stats(self):
        """Mostrar estadísticas limitadas a $220"""
        roi = ((self.stats['current_balance'] - 220) / 220) * 100
        
        logger.info(f"\n{'='*50}")
        logger.info(f"📊 ESTADÍSTICAS (CAPITAL LIMITADO $220)")
        logger.info(f"{'='*50}")
        logger.info(f"💰 Balance Virtual: ${self.stats['current_balance']:.2f}")
        logger.info(f"📈 PnL Total: ${self.stats['total_pnl']:+.2f}")
        logger.info(f"📊 ROI: {roi:+.2f}%")
        logger.info(f"🎯 Trades: {self.stats['total_trades']} (W:{self.stats['winning_trades']} L:{self.stats['losing_trades']})")
        
        if self.stats['total_trades'] > 0:
            win_rate = (self.stats['winning_trades'] / self.stats['total_trades']) * 100
            logger.info(f"✨ Win Rate: {win_rate:.1f}%")
        
        logger.info(f"📊 Peak: ${self.stats['peak_balance']:.2f} | Low: ${self.stats['lowest_balance']:.2f}")
    
    def run(self):
        """Bucle principal con límite de $220"""
        logger.info("\n🚀 Iniciando trading limitado a $220...")
        
        cycle = 0
        while True:
            try:
                cycle += 1
                
                logger.info(f"\n{'='*50}")
                logger.info(f"📍 Ciclo #{cycle} - {datetime.now().strftime('%H:%M:%S')}")
                logger.info(f"💎 Capital Disponible: ${self.available_capital:.2f} / ${self.MAX_CAPITAL:.2f}")
                logger.info(f"📈 Posiciones: {len(self.positions)}/{self.max_positions}")
                
                # Mostrar estadísticas cada 5 ciclos
                if cycle % 5 == 0:
                    self.display_stats()
                
                # Verificar posiciones
                if self.positions:
                    self.check_positions()
                
                # Buscar nuevas señales solo si tenemos capital disponible
                if self.available_capital >= (self.MAX_CAPITAL * self.risk_per_trade):
                    for symbol in self.symbols:
                        if symbol not in self.positions:
                            df = self.get_klines(symbol)
                            signal = self.analyze_market(df, symbol)
                            
                            if signal and signal['confidence'] >= self.min_confidence:
                                if self.execute_limited_trade(signal):
                                    break  # Una operación por ciclo
                                
                            time.sleep(1)
                else:
                    logger.info("⚠️ Capital disponible insuficiente para nuevos trades")
                
                # Esperar 30 segundos
                time.sleep(30)
                
            except KeyboardInterrupt:
                logger.info("\n⛔ Bot detenido")
                self.display_stats()
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                time.sleep(30)

def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║        💎 BOTPHIA LIMITED - SOLO $220 USD 💎            ║
║                                                          ║
║  Este bot está LIMITADO a usar solo $220                ║
║  del balance total de tu cuenta                         ║
║                                                          ║
║  • Capital Máximo: $220                                 ║
║  • Riesgo por trade: $11 (5%)                          ║
║  • Máximo 3 posiciones simultáneas                      ║
║  • Apalancamiento: 5x (conservador)                     ║
║                                                          ║
║  El bot NO usará más de $220 sin importar              ║
║  cuánto tengas en la cuenta                             ║
║                                                          ║
║  Presiona Ctrl+C para detener                           ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    bot = BotphiaLimited220()
    bot.run()

if __name__ == "__main__":
    main()