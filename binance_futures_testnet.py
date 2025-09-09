#!/usr/bin/env python3
"""
BOTPHIA - BINANCE FUTURES TESTNET TRADER
Trading de futuros en Binance Futures Testnet
"""

import os
import ccxt
import pandas as pd
import numpy as np
from datetime import datetime
import time
import logging
from typing import Dict, Optional
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BinanceFuturesTestnetBot:
    """Bot para Binance Futures Testnet"""
    
    def __init__(self):
        """Inicializar bot de futuros"""
        
        # Configuración
        self.initial_balance = 1000.0  # USDT simulado
        self.leverage = 5  # Apalancamiento 5x (conservador)
        self.risk_per_trade = 0.02  # 2% de riesgo por trade
        self.max_positions = 2  # Máximo 2 posiciones simultáneas
        
        # Símbolos de futuros
        self.symbols = ['BTC/USDT', 'ETH/USDT']
        
        # Configurar exchange
        self.setup_exchange()
        
        # Estado
        self.positions = {}
        self.running = False
        
        logger.info("🚀 Bot de Futuros Testnet inicializado")
    
    def setup_exchange(self):
        """Configurar conexión con Binance Futures Testnet"""
        
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_SECRET_KEY')
        
        if not api_key or not api_secret:
            raise ValueError("API keys no encontradas en .env")
        
        # Configurar CCXT para Binance Futures Testnet
        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',  # IMPORTANTE: Usar futuros
                'adjustForTimeDifference': True,
            },
            'urls': {
                'api': {
                    'fapiPublic': 'https://testnet.binancefuture.com/fapi/v1',
                    'fapiPrivate': 'https://testnet.binancefuture.com/fapi/v1',
                }
            }
        })
        
        logger.info("✅ Conectado a Binance FUTURES Testnet")
    
    def test_connection(self):
        """Probar la conexión"""
        try:
            # Probar API pública
            logger.info("\n🔌 Probando conexión...")
            
            # Obtener información del mercado
            markets = self.exchange.load_markets()
            btc_market = markets.get('BTC/USDT')
            
            if btc_market:
                logger.info(f"✅ Mercado BTC/USDT encontrado")
                logger.info(f"   Tipo: {btc_market['type']}")
                logger.info(f"   Activo: {btc_market['active']}")
            
            # Obtener precio actual
            ticker = self.exchange.fetch_ticker('BTC/USDT')
            logger.info(f"📊 Precio BTC/USDT: ${ticker['last']:,.2f}")
            
            # Probar API privada (balance)
            try:
                balance = self.exchange.fetch_balance()
                usdt_balance = balance['USDT']['free'] if 'USDT' in balance else 0
                logger.info(f"💰 Balance USDT: {usdt_balance:.2f}")
                
                if usdt_balance < 100:
                    logger.warning("⚠️ Balance bajo. Obtén fondos de prueba en:")
                    logger.warning("   https://testnet.binancefuture.com/en/futures/BTCUSDT")
                    logger.warning("   Click en 'Deposit' para obtener USDT de prueba")
                
                return True
                
            except Exception as e:
                logger.error(f"⚠️ Error con API privada: {e}")
                logger.info("💡 Verifica que las API keys sean correctas")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error de conexión: {e}")
            return False
    
    def get_market_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Obtener datos del mercado"""
        try:
            # Obtener velas de 5 minutos (más frecuente para futuros)
            ohlcv = self.exchange.fetch_ohlcv(symbol, '5m', limit=100)
            
            if not ohlcv:
                return None
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Indicadores técnicos
            df['sma_10'] = df['close'].rolling(window=10).mean()
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['rsi'] = self.calculate_rsi(df['close'], period=14)
            
            # ATR para volatilidad
            df['tr'] = pd.DataFrame({
                'hl': df['high'] - df['low'],
                'hc': abs(df['high'] - df['close'].shift()),
                'lc': abs(df['low'] - df['close'].shift())
            }).max(axis=1)
            df['atr'] = df['tr'].rolling(window=14).mean()
            
            return df
            
        except Exception as e:
            logger.error(f"Error obteniendo datos de {symbol}: {e}")
            return None
    
    def calculate_rsi(self, prices, period=14):
        """Calcular RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def generate_signal(self, df: pd.DataFrame, symbol: str) -> Optional[Dict]:
        """Generar señal de trading para futuros"""
        if df is None or len(df) < 20:
            return None
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Estrategia para futuros: más agresiva, timeframes cortos
        signal = None
        confidence = 0
        reasoning = []
        position_type = None  # 'long' o 'short'
        
        # SEÑAL LONG
        if (current['sma_10'] > current['sma_20'] and 
            prev['sma_10'] <= prev['sma_20'] and
            current['rsi'] < 65):
            
            signal = 'BUY'
            position_type = 'long'
            confidence = 75
            reasoning.append("Cruce alcista SMA10/20")
            
            if current['rsi'] < 40:
                confidence += 15
                reasoning.append("RSI oversold")
        
        # SEÑAL SHORT (ventaja de futuros)
        elif (current['sma_10'] < current['sma_20'] and 
              prev['sma_10'] >= prev['sma_20'] and
              current['rsi'] > 35):
            
            signal = 'SELL'
            position_type = 'short'
            confidence = 75
            reasoning.append("Cruce bajista SMA10/20")
            
            if current['rsi'] > 60:
                confidence += 15
                reasoning.append("RSI overbought")
        
        if signal and confidence >= 70:
            # Calcular stop loss basado en ATR
            atr = current['atr']
            stop_distance = atr * 1.5
            
            if position_type == 'long':
                stop_loss = current['close'] - stop_distance
                take_profit = current['close'] + (stop_distance * 2)
            else:  # short
                stop_loss = current['close'] + stop_distance
                take_profit = current['close'] - (stop_distance * 2)
            
            return {
                'symbol': symbol,
                'action': signal,
                'position_type': position_type,
                'price': current['close'],
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'confidence': confidence,
                'reasoning': ' | '.join(reasoning),
                'timestamp': datetime.now().isoformat()
            }
        
        return None
    
    def execute_futures_order(self, signal: Dict):
        """Ejecutar orden de futuros"""
        try:
            symbol = signal['symbol']
            
            # Obtener balance
            balance = self.exchange.fetch_balance()
            usdt_free = balance['USDT']['free'] if 'USDT' in balance else 0
            
            # Calcular tamaño de posición
            position_value = usdt_free * self.risk_per_trade * self.leverage
            
            # Obtener precio actual
            ticker = self.exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            
            # Calcular cantidad (contratos)
            amount = position_value / current_price
            
            # Ajustar precisión
            markets = self.exchange.load_markets()
            market = markets[symbol]
            amount = self.exchange.amount_to_precision(symbol, amount)
            
            logger.info(f"\n📋 EJECUTANDO ORDEN DE FUTUROS:")
            logger.info(f"  Símbolo: {symbol}")
            logger.info(f"  Tipo: {signal['position_type'].upper()}")
            logger.info(f"  Apalancamiento: {self.leverage}x")
            logger.info(f"  Precio entrada: ${current_price:.2f}")
            logger.info(f"  Cantidad: {amount} contratos")
            logger.info(f"  Stop Loss: ${signal['stop_loss']:.2f}")
            logger.info(f"  Take Profit: ${signal['take_profit']:.2f}")
            
            # Configurar apalancamiento
            self.exchange.fapiPrivate_post_leverage({
                'symbol': symbol.replace('/', ''),
                'leverage': self.leverage
            })
            
            # Ejecutar orden de mercado
            if signal['position_type'] == 'long':
                order = self.exchange.create_market_buy_order(symbol, amount)
            else:  # short
                order = self.exchange.create_market_sell_order(symbol, amount)
            
            logger.info(f"✅ Orden ejecutada: {order['id']}")
            
            # Configurar stop loss y take profit
            # NOTA: En producción real, deberías usar órdenes OCO o stop orders
            
            # Guardar posición
            self.positions[symbol] = {
                'order_id': order['id'],
                'type': signal['position_type'],
                'entry_price': current_price,
                'amount': amount,
                'stop_loss': signal['stop_loss'],
                'take_profit': signal['take_profit'],
                'entry_time': datetime.now()
            }
            
            return order
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando orden de futuros: {e}")
            
            # Si el error es por API keys inválidas
            if "Invalid API-key" in str(e):
                logger.error("🔑 Las API keys no son válidas para Futures Testnet")
                logger.info("📝 Necesitas:")
                logger.info("1. Ir a https://testnet.binancefuture.com")
                logger.info("2. Crear cuenta y generar NUEVAS API keys")
                logger.info("3. Actualizar el archivo .env con las nuevas keys")
            
            return None
    
    def check_positions(self):
        """Verificar y gestionar posiciones abiertas"""
        for symbol, position in list(self.positions.items()):
            try:
                ticker = self.exchange.fetch_ticker(symbol)
                current_price = ticker['last']
                
                # Calcular PnL según tipo de posición
                if position['type'] == 'long':
                    pnl_pct = ((current_price - position['entry_price']) / position['entry_price']) * 100
                    
                    # Verificar stop loss y take profit
                    if current_price <= position['stop_loss']:
                        logger.warning(f"⛔ STOP LOSS alcanzado en {symbol}")
                        self.close_position(symbol, 'stop_loss')
                    elif current_price >= position['take_profit']:
                        logger.info(f"🎯 TAKE PROFIT alcanzado en {symbol}")
                        self.close_position(symbol, 'take_profit')
                        
                else:  # short
                    pnl_pct = ((position['entry_price'] - current_price) / position['entry_price']) * 100
                    
                    if current_price >= position['stop_loss']:
                        logger.warning(f"⛔ STOP LOSS alcanzado en {symbol}")
                        self.close_position(symbol, 'stop_loss')
                    elif current_price <= position['take_profit']:
                        logger.info(f"🎯 TAKE PROFIT alcanzado en {symbol}")
                        self.close_position(symbol, 'take_profit')
                
                # Mostrar estado
                pnl_with_leverage = pnl_pct * self.leverage
                logger.info(f"📊 {symbol} ({position['type']}): ${current_price:.2f} | PnL: {pnl_with_leverage:+.2f}%")
                
            except Exception as e:
                logger.error(f"Error verificando posición {symbol}: {e}")
    
    def close_position(self, symbol: str, reason: str):
        """Cerrar una posición de futuros"""
        try:
            position = self.positions[symbol]
            
            # Crear orden contraria para cerrar
            if position['type'] == 'long':
                order = self.exchange.create_market_sell_order(symbol, position['amount'])
            else:  # short
                order = self.exchange.create_market_buy_order(symbol, position['amount'])
            
            logger.info(f"✅ Posición cerrada: {symbol} - Razón: {reason}")
            
            # Eliminar de posiciones activas
            del self.positions[symbol]
            
        except Exception as e:
            logger.error(f"Error cerrando posición: {e}")
    
    def run(self):
        """Bucle principal"""
        logger.info("\n" + "="*60)
        logger.info("🚀 INICIANDO BOT DE BINANCE FUTURES TESTNET")
        logger.info("="*60)
        
        # Probar conexión
        if not self.test_connection():
            logger.error("❌ No se pudo establecer conexión")
            return
        
        self.running = True
        cycle = 0
        
        while self.running:
            try:
                cycle += 1
                logger.info(f"\n{'='*50}")
                logger.info(f"📍 Ciclo #{cycle} - {datetime.now().strftime('%H:%M:%S')}")
                logger.info(f"📈 Posiciones: {len(self.positions)}/{self.max_positions}")
                
                # Verificar posiciones existentes
                if self.positions:
                    self.check_positions()
                
                # Buscar nuevas señales
                if len(self.positions) < self.max_positions:
                    for symbol in self.symbols:
                        if symbol not in self.positions:
                            df = self.get_market_data(symbol)
                            if df is not None:
                                signal = self.generate_signal(df, symbol)
                                
                                if signal:
                                    logger.info(f"\n🔔 SEÑAL DETECTADA:")
                                    logger.info(f"  {signal['symbol']} - {signal['position_type'].upper()}")
                                    logger.info(f"  Confianza: {signal['confidence']}%")
                                    logger.info(f"  Razón: {signal['reasoning']}")
                                    
                                    self.execute_futures_order(signal)
                            
                            time.sleep(2)
                
                # Esperar 30 segundos
                logger.info(f"\n⏳ Esperando 30 segundos...")
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
║      🚀 BOTPHIA - BINANCE FUTURES TESTNET 🚀           ║
║                                                          ║
║  Trading de FUTUROS con apalancamiento                  ║
║  Usando tus API keys de testnet.binancefuture.com       ║
║                                                          ║
║  Características:                                       ║
║  • Apalancamiento 5x (conservador)                      ║
║  • Posiciones LONG y SHORT                              ║
║  • Stop Loss y Take Profit automáticos                  ║
║                                                          ║
║  Presiona Ctrl+C para detener                           ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    try:
        bot = BinanceFuturesTestnetBot()
        bot.run()
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()