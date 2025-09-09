#!/usr/bin/env python3
"""
BOTPHIA FUTURES TRADER - CON TRACKING DESDE $220
Bot mejorado con sistema de tracking personalizado
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
import sqlite3
from urllib.parse import urlencode
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BotphiaTracker:
    def __init__(self):
        # API Configuration
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.api_secret = os.getenv('BINANCE_SECRET_KEY')
        self.base_url = "https://testnet.binancefuture.com"
        
        # Cargar configuración de tracking
        with open('tracking_config.json', 'r') as f:
            self.tracking = json.load(f)
        
        # Balance inicial para tracking ($220)
        self.initial_tracking_balance = self.tracking['tracking_initial_balance']
        self.real_initial_balance = self.tracking['real_initial_balance']
        self.balance_offset = self.tracking['balance_offset']
        
        # Trading Configuration
        self.leverage = 10
        self.risk_per_trade = 0.02  # 2% del balance tracking ($4.40)
        self.max_positions = 3
        self.min_confidence = 70
        
        # Símbolos
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        
        # Estado
        self.positions = {}
        self.session_stats = {
            'start_time': datetime.now(),
            'trades_today': 0,
            'pnl_today': 0,
            'winning_trades': 0,
            'losing_trades': 0
        }
        
        # Base de datos
        self.conn = sqlite3.connect('botphia_performance.db')
        self.cursor = self.conn.cursor()
        
        logger.info("="*60)
        logger.info("🤖 BOTPHIA TRACKER INICIALIZADO")
        logger.info("="*60)
        logger.info(f"📊 Balance Inicial (Tracking): ${self.initial_tracking_balance:.2f}")
        logger.info(f"💰 Balance Real (Binance): ${self.real_initial_balance:.2f}")
        logger.info(f"⚙️ Apalancamiento: {self.leverage}x")
        logger.info(f"💎 Riesgo por trade: ${self.initial_tracking_balance * self.risk_per_trade:.2f}")
    
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
    
    def get_tracking_balance(self):
        """Obtener balance ajustado para tracking"""
        account = self.make_request('GET', '/fapi/v2/account', signed=True)
        if account:
            real_balance = float(account['totalWalletBalance'])
            # Calcular balance de tracking
            tracking_balance = real_balance - self.balance_offset
            return tracking_balance, real_balance
        return None, None
    
    def display_performance(self):
        """Mostrar rendimiento con balance de $220"""
        tracking_balance, real_balance = self.get_tracking_balance()
        
        if tracking_balance is None:
            return
        
        # Calcular métricas
        pnl = tracking_balance - self.initial_tracking_balance
        roi = (pnl / self.initial_tracking_balance) * 100
        
        # Determinar emoji según rendimiento
        if roi > 10:
            emoji = "🚀"
            status = "EXCELENTE"
        elif roi > 5:
            emoji = "📈"
            status = "MUY BIEN"
        elif roi > 0:
            emoji = "✅"
            status = "POSITIVO"
        elif roi > -5:
            emoji = "⚠️"
            status = "CUIDADO"
        else:
            emoji = "🔴"
            status = "PÉRDIDA"
        
        logger.info(f"\n{'='*50}")
        logger.info(f"{emoji} RENDIMIENTO (desde $220)")
        logger.info(f"{'='*50}")
        logger.info(f"💰 Balance Tracking: ${tracking_balance:.2f}")
        logger.info(f"📊 PnL: ${pnl:+.2f}")
        logger.info(f"📈 ROI: {roi:+.2f}%")
        logger.info(f"🎯 Status: {status}")
        
        # Mostrar estadísticas de la sesión
        if self.session_stats['trades_today'] > 0:
            win_rate = (self.session_stats['winning_trades'] / self.session_stats['trades_today']) * 100
            logger.info(f"\n📊 Estadísticas de Hoy:")
            logger.info(f"  Trades: {self.session_stats['trades_today']}")
            logger.info(f"  Win Rate: {win_rate:.1f}%")
            logger.info(f"  PnL Hoy: ${self.session_stats['pnl_today']:+.2f}")
        
        # Guardar en base de datos
        self.update_database(tracking_balance, pnl, roi)
    
    def update_database(self, balance, pnl, roi):
        """Actualizar base de datos con rendimiento"""
        try:
            self.cursor.execute('''
                UPDATE trading_sessions 
                SET current_balance = ?, total_pnl = ?, last_update = ?
                WHERE id = ?
            ''', (balance, pnl, datetime.now().isoformat(), 
                  self.tracking['session_id']))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error actualizando DB: {e}")
    
    def calculate_position_size(self):
        """Calcular tamaño de posición basado en balance tracking"""
        tracking_balance, _ = self.get_tracking_balance()
        if tracking_balance:
            # 2% del balance tracking
            risk_amount = tracking_balance * self.risk_per_trade
            return risk_amount
        return 4.40  # Default $4.40 (2% de $220)
    
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
        
        # Estrategia simple
        if current['rsi'] < 30 and current['close'] > current['sma_20']:
            return {
                'symbol': symbol,
                'signal': 'LONG',
                'confidence': 75,
                'reason': 'RSI oversold + Above SMA20'
            }
        elif current['rsi'] > 70 and current['close'] < current['sma_20']:
            return {
                'symbol': symbol,
                'signal': 'SHORT',
                'confidence': 75,
                'reason': 'RSI overbought + Below SMA20'
            }
        
        return None
    
    def execute_trade(self, signal):
        """Ejecutar trade con tracking ajustado"""
        symbol = signal['symbol']
        
        # Calcular tamaño basado en balance tracking
        risk_amount = self.calculate_position_size()
        
        # Obtener precio actual
        ticker = self.make_request('GET', '/fapi/v1/ticker/price', 
                                  params={'symbol': symbol})
        if not ticker:
            return
        
        current_price = float(ticker['price'])
        
        # Calcular cantidad real para Binance
        # Pero mostrar como si fuera del balance tracking
        real_risk = risk_amount * (self.real_initial_balance / self.initial_tracking_balance)
        notional_value = real_risk * self.leverage
        quantity = round(notional_value / current_price, 3)
        
        logger.info(f"\n💎 EJECUTANDO TRADE (Tracking desde $220)")
        logger.info(f"  Símbolo: {symbol}")
        logger.info(f"  Señal: {signal['signal']}")
        logger.info(f"  Riesgo (tracking): ${risk_amount:.2f}")
        logger.info(f"  Cantidad: {quantity}")
        
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
            
            self.positions[symbol] = {
                'type': signal['signal'],
                'entry_price': current_price,
                'quantity': quantity,
                'risk_amount': risk_amount,
                'entry_time': datetime.now()
            }
            
            self.session_stats['trades_today'] += 1
    
    def check_positions(self):
        """Verificar posiciones con tracking ajustado"""
        for symbol, position in list(self.positions.items()):
            ticker = self.make_request('GET', '/fapi/v1/ticker/price', 
                                      params={'symbol': symbol})
            if not ticker:
                continue
            
            current_price = float(ticker['price'])
            entry_price = position['entry_price']
            
            # Calcular PnL en términos del balance tracking
            if position['type'] == 'LONG':
                price_change_pct = ((current_price - entry_price) / entry_price) * 100
            else:
                price_change_pct = ((entry_price - current_price) / entry_price) * 100
            
            pnl_tracking = position['risk_amount'] * (price_change_pct / 100) * self.leverage
            
            # Mostrar como si fuera del balance de $220
            logger.info(f"📊 {symbol}: PnL ${pnl_tracking:+.2f} ({price_change_pct * self.leverage:+.2f}%)")
            
            # Cerrar si alcanza límites (basado en tracking)
            if pnl_tracking > position['risk_amount'] * 2:  # Take profit 200%
                self.close_position(symbol, pnl_tracking, 'TAKE_PROFIT')
            elif pnl_tracking < -position['risk_amount']:  # Stop loss 100%
                self.close_position(symbol, pnl_tracking, 'STOP_LOSS')
    
    def close_position(self, symbol, pnl_tracking, reason):
        """Cerrar posición y actualizar tracking"""
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
            # Actualizar estadísticas
            self.session_stats['pnl_today'] += pnl_tracking
            
            if pnl_tracking > 0:
                self.session_stats['winning_trades'] += 1
                logger.info(f"✅ {symbol} cerrado: +${pnl_tracking:.2f} ({reason})")
            else:
                self.session_stats['losing_trades'] += 1
                logger.info(f"❌ {symbol} cerrado: ${pnl_tracking:.2f} ({reason})")
            
            del self.positions[symbol]
    
    def run(self):
        """Bucle principal con tracking desde $220"""
        logger.info("\n🚀 Iniciando trading con tracking desde $220...")
        
        cycle = 0
        while True:
            try:
                cycle += 1
                
                # Mostrar rendimiento cada ciclo
                self.display_performance()
                
                # Verificar posiciones
                if self.positions:
                    self.check_positions()
                
                # Buscar nuevas señales
                if len(self.positions) < self.max_positions:
                    for symbol in self.symbols:
                        if symbol not in self.positions:
                            df = self.get_klines(symbol)
                            signal = self.analyze_market(df, symbol)
                            
                            if signal and signal['confidence'] >= self.min_confidence:
                                self.execute_trade(signal)
                                break
                
                # Esperar 30 segundos
                time.sleep(30)
                
            except KeyboardInterrupt:
                logger.info("\n⛔ Bot detenido")
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                time.sleep(30)

def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║        💎 BOTPHIA TRACKER - DESDE $220 USD 💎           ║
║                                                          ║
║  El bot opera con tu balance real pero muestra          ║
║  el rendimiento como si empezaras con $220              ║
║                                                          ║
║  • PnL calculado desde $220                             ║
║  • ROI basado en $220                                   ║
║  • +$22 = +10% ROI                                      ║
║  • +$220 = +100% ROI                                    ║
║                                                          ║
║  Presiona Ctrl+C para detener                           ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    bot = BotphiaTracker()
    bot.run()

if __name__ == "__main__":
    main()