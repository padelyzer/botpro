#!/usr/bin/env python3
"""
BOTPHIA FUTURES TRADER - BINANCE TESTNET
Bot de trading automático para futuros con las 8 filosofías
"""

import requests
import hmac
import hashlib
import time
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from urllib.parse import urlencode
import logging
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

# Cargar configuración
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BotphiaFuturesTrader:
    """Bot de trading con 8 filosofías para Binance Futures"""
    
    def __init__(self):
        # API Configuration
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.api_secret = os.getenv('BINANCE_SECRET_KEY')
        self.base_url = "https://testnet.binancefuture.com"
        
        # Trading Configuration
        self.initial_balance = 16624.25  # Tu balance actual
        self.leverage = 10  # Apalancamiento moderado
        self.risk_per_trade = 0.01  # 1% de riesgo por trade
        self.max_positions = 3
        self.min_confidence = 70
        
        # Símbolos a operar
        self.symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT']
        
        # Estado
        self.positions = {}
        self.philosophers = {
            'SOCRATES': {'wins': 0, 'losses': 0, 'active': True},
            'ARISTOTELES': {'wins': 0, 'losses': 0, 'active': True},
            'NIETZSCHE': {'wins': 0, 'losses': 0, 'active': True},
            'CONFUCIO': {'wins': 0, 'losses': 0, 'active': True},
            'PLATON': {'wins': 0, 'losses': 0, 'active': True},
            'KANT': {'wins': 0, 'losses': 0, 'active': True},
            'DESCARTES': {'wins': 0, 'losses': 0, 'active': True},
            'SUNTZU': {'wins': 0, 'losses': 0, 'active': True}
        }
        
        logger.info("🤖 BotPhia Futures Trader inicializado")
        logger.info(f"💰 Balance: ${self.initial_balance:.2f} USDT")
        logger.info(f"⚙️ Apalancamiento: {self.leverage}x")
    
    def create_signature(self, params):
        """Crear firma HMAC SHA256"""
        query_string = urlencode(params)
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def make_request(self, method, endpoint, params=None, signed=False):
        """Hacer petición a la API"""
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
    
    def get_account_info(self):
        """Obtener información de la cuenta"""
        data = self.make_request('GET', '/fapi/v2/account', signed=True)
        if data:
            logger.info(f"💰 Balance Total: ${float(data['totalWalletBalance']):.2f}")
            logger.info(f"💵 Balance Disponible: ${float(data['availableBalance']):.2f}")
            return data
        return None
    
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
            
            # Convertir a numérico
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Calcular indicadores
            df = self.calculate_indicators(df)
            
            return df
        return None
    
    def calculate_indicators(self, df):
        """Calcular indicadores técnicos"""
        # Medias móviles
        df['sma_10'] = df['close'].rolling(window=10).mean()
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        
        # ATR
        df['tr'] = pd.DataFrame({
            'hl': df['high'] - df['low'],
            'hc': abs(df['high'] - df['close'].shift()),
            'lc': abs(df['low'] - df['close'].shift())
        }).max(axis=1)
        df['atr'] = df['tr'].rolling(window=14).mean()
        
        return df
    
    def analyze_with_philosophy(self, df, symbol, philosopher):
        """Analizar mercado según cada filósofo"""
        if df is None or len(df) < 50:
            return None
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        confidence = 0
        signal = None
        reasoning = []
        
        if philosopher == 'SOCRATES':
            # Sócrates: Cuestiona los rangos, busca la verdad
            if current['close'] <= current['bb_lower']:
                signal = 'LONG'
                confidence = 75
                reasoning.append("Precio en extremo inferior - ¿Es real la caída?")
            elif current['close'] >= current['bb_upper']:
                signal = 'SHORT'
                confidence = 75
                reasoning.append("Precio en extremo superior - ¿Es sostenible?")
        
        elif philosopher == 'ARISTOTELES':
            # Aristóteles: Lógica pura, sigue la tendencia
            if current['sma_10'] > current['sma_20'] > current['sma_50']:
                signal = 'LONG'
                confidence = 80
                reasoning.append("Tendencia alcista confirmada por lógica")
            elif current['sma_10'] < current['sma_20'] < current['sma_50']:
                signal = 'SHORT'
                confidence = 80
                reasoning.append("Tendencia bajista lógicamente establecida")
        
        elif philosopher == 'NIETZSCHE':
            # Nietzsche: Contrarian, va contra la masa
            if current['rsi'] < 25:
                signal = 'LONG'
                confidence = 85
                reasoning.append("El rebaño vende en pánico - momento de comprar")
            elif current['rsi'] > 75:
                signal = 'SHORT'
                confidence = 85
                reasoning.append("Euforia de las masas - momento de vender")
        
        elif philosopher == 'CONFUCIO':
            # Confucio: Busca el equilibrio
            mean_price = (current['high'] + current['low'] + current['close']) / 3
            if current['close'] < mean_price * 0.98:
                signal = 'LONG'
                confidence = 70
                reasoning.append("Desequilibrio hacia abajo - buscar armonía")
            elif current['close'] > mean_price * 1.02:
                signal = 'SHORT'
                confidence = 70
                reasoning.append("Desequilibrio hacia arriba - restaurar balance")
        
        elif philosopher == 'PLATON':
            # Platón: Busca patrones ideales
            if current['macd'] > current['macd_signal'] and prev['macd'] <= prev['macd_signal']:
                signal = 'LONG'
                confidence = 75
                reasoning.append("Patrón ideal de cruce MACD alcista")
            elif current['macd'] < current['macd_signal'] and prev['macd'] >= prev['macd_signal']:
                signal = 'SHORT'
                confidence = 75
                reasoning.append("Patrón ideal de cruce MACD bajista")
        
        elif philosopher == 'KANT':
            # Kant: Reglas absolutas
            if current['rsi'] < 30 and current['close'] > current['sma_20']:
                signal = 'LONG'
                confidence = 90
                reasoning.append("Imperativo categórico: RSI bajo + precio sobre media")
            elif current['rsi'] > 70 and current['close'] < current['sma_20']:
                signal = 'SHORT'
                confidence = 90
                reasoning.append("Imperativo categórico: RSI alto + precio bajo media")
        
        elif philosopher == 'DESCARTES':
            # Descartes: Duda metódica, confirmaciones múltiples
            long_signals = 0
            short_signals = 0
            
            if current['rsi'] < 40: long_signals += 1
            if current['close'] > current['sma_20']: long_signals += 1
            if current['macd'] > current['macd_signal']: long_signals += 1
            
            if current['rsi'] > 60: short_signals += 1
            if current['close'] < current['sma_20']: short_signals += 1
            if current['macd'] < current['macd_signal']: short_signals += 1
            
            if long_signals >= 3:
                signal = 'LONG'
                confidence = 85
                reasoning.append(f"Triple confirmación alcista ({long_signals}/3)")
            elif short_signals >= 3:
                signal = 'SHORT'
                confidence = 85
                reasoning.append(f"Triple confirmación bajista ({short_signals}/3)")
        
        elif philosopher == 'SUNTZU':
            # Sun Tzu: Timing perfecto, esperar el momento
            volatility = current['atr'] / current['close']
            if volatility < 0.01 and current['rsi'] < 45:
                signal = 'LONG'
                confidence = 80
                reasoning.append("Baja volatilidad - momento de atacar largo")
            elif volatility > 0.02 and current['rsi'] > 55:
                signal = 'SHORT'
                confidence = 80
                reasoning.append("Alta volatilidad - retirada táctica corta")
        
        if signal and confidence >= self.min_confidence:
            return {
                'philosopher': philosopher,
                'symbol': symbol,
                'signal': signal,
                'confidence': confidence,
                'reasoning': reasoning,
                'price': current['close'],
                'timestamp': datetime.now()
            }
        
        return None
    
    def place_order(self, symbol, side, quantity):
        """Colocar orden en Binance Futures"""
        params = {
            'symbol': symbol,
            'side': 'BUY' if side == 'LONG' else 'SELL',
            'type': 'MARKET',
            'quantity': quantity
        }
        
        order = self.make_request('POST', '/fapi/v1/order', params=params, signed=True)
        
        if order:
            logger.info(f"✅ Orden ejecutada: {order['orderId']}")
            return order
        return None
    
    def set_leverage(self, symbol, leverage):
        """Configurar apalancamiento"""
        params = {
            'symbol': symbol,
            'leverage': leverage
        }
        
        result = self.make_request('POST', '/fapi/v1/leverage', params=params, signed=True)
        if result:
            logger.info(f"⚙️ Apalancamiento configurado: {leverage}x para {symbol}")
        return result
    
    def execute_signal(self, analysis):
        """Ejecutar señal de trading"""
        symbol = analysis['symbol']
        philosopher = analysis['philosopher']
        signal_type = analysis['signal']
        
        # Configurar apalancamiento
        self.set_leverage(symbol, self.leverage)
        
        # Calcular tamaño de posición
        account = self.get_account_info()
        if not account:
            return
        
        available_balance = float(account['availableBalance'])
        position_value = available_balance * self.risk_per_trade
        
        # Obtener precio actual
        ticker = self.make_request('GET', '/fapi/v1/ticker/price', 
                                  params={'symbol': symbol})
        if not ticker:
            return
        
        current_price = float(ticker['price'])
        
        # Calcular cantidad (con apalancamiento)
        notional_value = position_value * self.leverage
        quantity = round(notional_value / current_price, 3)
        
        logger.info(f"\n🎯 EJECUTANDO SEÑAL DE {philosopher}")
        logger.info(f"   Símbolo: {symbol}")
        logger.info(f"   Dirección: {signal_type}")
        logger.info(f"   Precio: ${current_price:.2f}")
        logger.info(f"   Cantidad: {quantity}")
        logger.info(f"   Valor: ${notional_value:.2f}")
        logger.info(f"   Razón: {' '.join(analysis['reasoning'])}")
        
        # Ejecutar orden
        order = self.place_order(symbol, signal_type, quantity)
        
        if order:
            # Guardar posición
            self.positions[symbol] = {
                'philosopher': philosopher,
                'type': signal_type,
                'entry_price': current_price,
                'quantity': quantity,
                'entry_time': datetime.now(),
                'order_id': order['orderId']
            }
            
            # Configurar stop loss y take profit
            atr = analysis.get('atr', current_price * 0.01)
            
            if signal_type == 'LONG':
                stop_loss = current_price - (atr * 1.5)
                take_profit = current_price + (atr * 3)
            else:
                stop_loss = current_price + (atr * 1.5)
                take_profit = current_price - (atr * 3)
            
            self.positions[symbol]['stop_loss'] = stop_loss
            self.positions[symbol]['take_profit'] = take_profit
            
            logger.info(f"   Stop Loss: ${stop_loss:.2f}")
            logger.info(f"   Take Profit: ${take_profit:.2f}")
    
    def check_positions(self):
        """Verificar posiciones abiertas"""
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
            
            pnl_with_leverage = pnl_pct * self.leverage
            
            logger.info(f"📊 {symbol} ({position['philosopher']}): ${current_price:.2f} | PnL: {pnl_with_leverage:+.2f}%")
            
            if should_close:
                # Cerrar posición
                side = 'SELL' if position['type'] == 'LONG' else 'BUY'
                close_order = self.place_order(symbol, side, position['quantity'])
                
                if close_order:
                    # Actualizar estadísticas del filósofo
                    if pnl_pct > 0:
                        self.philosophers[position['philosopher']]['wins'] += 1
                        logger.info(f"✅ {position['philosopher']} ganó: +{pnl_with_leverage:.2f}%")
                    else:
                        self.philosophers[position['philosopher']]['losses'] += 1
                        logger.info(f"❌ {position['philosopher']} perdió: {pnl_with_leverage:.2f}%")
                    
                    del self.positions[symbol]
    
    def run(self):
        """Bucle principal del bot"""
        logger.info("\n" + "="*60)
        logger.info("🚀 INICIANDO BOTPHIA FUTURES TRADER")
        logger.info("="*60)
        
        # Verificar cuenta
        account = self.get_account_info()
        if not account:
            logger.error("❌ No se pudo obtener información de la cuenta")
            return
        
        cycle = 0
        while True:
            try:
                cycle += 1
                logger.info(f"\n{'='*50}")
                logger.info(f"📍 Ciclo #{cycle} - {datetime.now().strftime('%H:%M:%S')}")
                logger.info(f"📈 Posiciones: {len(self.positions)}/{self.max_positions}")
                
                # Mostrar rendimiento de filósofos
                logger.info("🏛️ Rendimiento de Filósofos:")
                for name, stats in self.philosophers.items():
                    total = stats['wins'] + stats['losses']
                    if total > 0:
                        wr = (stats['wins'] / total) * 100
                        logger.info(f"   {name}: {stats['wins']}W-{stats['losses']}L ({wr:.1f}%)")
                
                # Verificar posiciones existentes
                if self.positions:
                    self.check_positions()
                
                # Buscar nuevas señales si hay espacio
                if len(self.positions) < self.max_positions:
                    for symbol in self.symbols:
                        if symbol in self.positions:
                            continue
                        
                        # Obtener datos
                        df = self.get_klines(symbol)
                        if df is None:
                            continue
                        
                        # Analizar con cada filósofo
                        for philosopher in self.philosophers.keys():
                            if not self.philosophers[philosopher]['active']:
                                continue
                            
                            analysis = self.analyze_with_philosophy(df, symbol, philosopher)
                            
                            if analysis:
                                logger.info(f"\n🔔 Señal de {philosopher} para {symbol}")
                                logger.info(f"   Confianza: {analysis['confidence']}%")
                                
                                if len(self.positions) < self.max_positions:
                                    self.execute_signal(analysis)
                                    break  # Una señal por símbolo
                        
                        time.sleep(1)  # Rate limiting
                
                # Esperar antes del siguiente ciclo
                logger.info(f"\n⏳ Esperando 30 segundos...")
                time.sleep(30)
                
            except KeyboardInterrupt:
                logger.info("\n⛔ Bot detenido por el usuario")
                break
            except Exception as e:
                logger.error(f"Error en ciclo: {e}")
                time.sleep(30)

def main():
    print("""
╔══════════════════════════════════════════════════════════╗
║        🏛️ BOTPHIA FUTURES TRADER - 8 FILOSOFÍAS 🏛️      ║
║                                                          ║
║  Trading automático con las estrategias de:             ║
║  • SÓCRATES - Cuestiona los extremos                    ║
║  • ARISTÓTELES - Lógica de tendencias                   ║
║  • NIETZSCHE - Contrarian extremo                       ║
║  • CONFUCIO - Busca el equilibrio                       ║
║  • PLATÓN - Patrones ideales                            ║
║  • KANT - Reglas absolutas                              ║
║  • DESCARTES - Confirmaciones múltiples                 ║
║  • SUN TZU - Timing perfecto                            ║
║                                                          ║
║  💰 Balance: $16,624 USDT (Testnet)                     ║
║  ⚙️ Apalancamiento: 10x                                  ║
║  📊 Riesgo por trade: 1%                                ║
║                                                          ║
║  Presiona Ctrl+C para detener                           ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    bot = BotphiaFuturesTrader()
    bot.run()

if __name__ == "__main__":
    main()