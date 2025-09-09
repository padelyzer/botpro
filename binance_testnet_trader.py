#!/usr/bin/env python3
"""
BOTPHIA - BINANCE TESTNET TRADER
Trading real en Binance Testnet con dinero ficticio
"""

import os
import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import logging
import json
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BinanceTestnetTrader:
    """Bot de trading para Binance Testnet"""
    
    def __init__(self):
        """Inicializar el bot con configuración de testnet"""
        
        # Configuración de trading
        self.initial_balance = 1000.0  # USDT de prueba
        self.risk_per_trade = 0.10    # 10% por trade
        self.max_positions = 3
        self.min_confidence = 65
        
        # Símbolos a operar (verificados en testnet)
        self.symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
        
        # Configurar exchange para Testnet
        self.setup_exchange()
        
        # Estado del bot
        self.positions = {}
        self.orders = {}
        self.running = False
        
        logger.info("🤖 Bot de Binance Testnet inicializado")
    
    def setup_exchange(self):
        """Configurar conexión con Binance Testnet"""
        
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_SECRET_KEY')
        
        if not api_key or not api_secret:
            logger.error("❌ No se encontraron API keys en .env")
            logger.info("📝 Por favor, sigue estos pasos:")
            logger.info("1. Ve a https://testnet.binance.vision/")
            logger.info("2. Crea una cuenta y genera API keys")
            logger.info("3. Agrega las keys al archivo .env")
            raise ValueError("API keys no configuradas")
        
        # Configurar CCXT para Binance Testnet
        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
                'adjustForTimeDifference': True,
            }
        })
        
        # Configurar URLs de testnet
        self.exchange.set_sandbox_mode(True)
        
        logger.info("✅ Conectado a Binance Testnet")
    
    def check_balance(self):
        """Verificar balance en testnet"""
        try:
            balance = self.exchange.fetch_balance()
            
            # Mostrar balances no cero
            logger.info("\n💰 BALANCE EN TESTNET:")
            logger.info("=" * 40)
            
            for currency in ['USDT', 'BTC', 'ETH', 'BNB']:
                if currency in balance['total']:
                    total = balance['total'][currency]
                    free = balance['free'][currency]
                    used = balance['used'][currency]
                    
                    if total > 0:
                        logger.info(f"{currency}:")
                        logger.info(f"  Total: {total:.8f}")
                        logger.info(f"  Libre: {free:.8f}")
                        logger.info(f"  En uso: {used:.8f}")
            
            # Verificar si hay fondos suficientes
            usdt_balance = balance['free'].get('USDT', 0)
            if usdt_balance < 100:
                logger.warning("⚠️ Balance USDT bajo. Necesitas obtener fondos de prueba:")
                logger.warning("1. Inicia sesión en https://testnet.binance.vision/")
                logger.warning("2. Ve a la sección 'Faucet' o 'Get Test Funds'")
                logger.warning("3. Solicita USDT de prueba (normalmente 10,000 USDT)")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error verificando balance: {e}")
            return False
    
    def get_market_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Obtener datos de mercado"""
        try:
            # Obtener velas de 15 minutos
            ohlcv = self.exchange.fetch_ohlcv(symbol, '15m', limit=100)
            
            if not ohlcv:
                return None
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Calcular indicadores
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            df['rsi'] = self.calculate_rsi(df['close'])
            
            # Bollinger Bands
            df['bb_middle'] = df['close'].rolling(window=20).mean()
            bb_std = df['close'].rolling(window=20).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
            
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
        """Generar señal de trading"""
        if df is None or len(df) < 50:
            return None
        
        current = df.iloc[-1]
        prev = df.iloc[-2]
        
        signal = None
        confidence = 0
        reasoning = []
        
        # Estrategia: Cruce de medias + RSI + Bollinger Bands
        
        # Condiciones de COMPRA
        buy_conditions = 0
        
        # 1. Cruce alcista de medias
        if current['sma_20'] > current['sma_50'] and prev['sma_20'] <= prev['sma_50']:
            buy_conditions += 30
            reasoning.append("Cruce alcista SMA20/50")
        
        # 2. RSI saliendo de sobreventa
        if 30 < current['rsi'] < 50 and prev['rsi'] <= 30:
            buy_conditions += 25
            reasoning.append("RSI saliendo de sobreventa")
        
        # 3. Precio tocando banda inferior de Bollinger
        if current['close'] <= current['bb_lower'] * 1.02:
            buy_conditions += 20
            reasoning.append("Precio en banda inferior Bollinger")
        
        # 4. Momentum positivo
        if current['close'] > prev['close'] * 1.005:
            buy_conditions += 15
            reasoning.append("Momentum alcista")
        
        # Condiciones de VENTA
        sell_conditions = 0
        
        # 1. Cruce bajista de medias
        if current['sma_20'] < current['sma_50'] and prev['sma_20'] >= prev['sma_50']:
            sell_conditions += 30
            reasoning.append("Cruce bajista SMA20/50")
        
        # 2. RSI en sobrecompra
        if current['rsi'] > 70:
            sell_conditions += 25
            reasoning.append("RSI en sobrecompra")
        
        # 3. Precio tocando banda superior de Bollinger
        if current['close'] >= current['bb_upper'] * 0.98:
            sell_conditions += 20
            reasoning.append("Precio en banda superior Bollinger")
        
        # Decidir señal
        if buy_conditions >= self.min_confidence:
            signal = 'BUY'
            confidence = min(buy_conditions, 95)
        elif sell_conditions >= self.min_confidence:
            signal = 'SELL'
            confidence = min(sell_conditions, 95)
        
        if signal:
            return {
                'symbol': symbol,
                'action': signal,
                'price': current['close'],
                'confidence': confidence,
                'reasoning': ' | '.join(reasoning),
                'timestamp': datetime.now().isoformat(),
                'rsi': current['rsi'],
                'sma_20': current['sma_20'],
                'sma_50': current['sma_50']
            }
        
        return None
    
    def execute_order(self, signal: Dict):
        """Ejecutar orden en Binance Testnet"""
        try:
            symbol = signal['symbol']
            side = signal['action'].lower()
            
            # Obtener balance disponible
            balance = self.exchange.fetch_balance()
            
            if side == 'buy':
                # Calcular cantidad a comprar
                usdt_available = balance['free']['USDT']
                position_size = min(usdt_available * self.risk_per_trade, 100)  # Máximo 100 USDT por trade
                
                # Obtener precio actual y calcular cantidad
                ticker = self.exchange.fetch_ticker(symbol)
                current_price = ticker['last']
                amount = position_size / current_price
                
                # Redondear según los requisitos del símbolo
                markets = self.exchange.load_markets()
                market = markets[symbol]
                amount = self.exchange.amount_to_precision(symbol, amount)
                
                logger.info(f"\n📋 EJECUTANDO ORDEN DE COMPRA:")
                logger.info(f"  Símbolo: {symbol}")
                logger.info(f"  Precio: ${current_price:.4f}")
                logger.info(f"  Cantidad: {amount}")
                logger.info(f"  Valor: ${float(amount) * current_price:.2f} USDT")
                
                # Ejecutar orden de mercado
                order = self.exchange.create_market_buy_order(symbol, amount)
                
                # Guardar posición
                self.positions[symbol] = {
                    'order_id': order['id'],
                    'entry_price': current_price,
                    'amount': amount,
                    'entry_time': datetime.now(),
                    'stop_loss': current_price * 0.95,
                    'take_profit': current_price * 1.05,
                    'reasoning': signal['reasoning']
                }
                
                logger.info(f"✅ ORDEN EJECUTADA: {order['id']}")
                logger.info(f"  Stop Loss: ${current_price * 0.95:.4f}")
                logger.info(f"  Take Profit: ${current_price * 1.05:.4f}")
                
                return order
                
            elif side == 'sell' and symbol in self.positions:
                # Vender posición existente
                position = self.positions[symbol]
                amount = position['amount']
                
                logger.info(f"\n📋 EJECUTANDO ORDEN DE VENTA:")
                logger.info(f"  Símbolo: {symbol}")
                logger.info(f"  Cantidad: {amount}")
                
                # Ejecutar orden de venta
                order = self.exchange.create_market_sell_order(symbol, amount)
                
                # Calcular PnL
                ticker = self.exchange.fetch_ticker(symbol)
                exit_price = ticker['last']
                pnl_pct = ((exit_price - position['entry_price']) / position['entry_price']) * 100
                pnl_usdt = (exit_price - position['entry_price']) * float(amount)
                
                logger.info(f"✅ POSICIÓN CERRADA: {order['id']}")
                logger.info(f"  Precio entrada: ${position['entry_price']:.4f}")
                logger.info(f"  Precio salida: ${exit_price:.4f}")
                logger.info(f"  PnL: ${pnl_usdt:.2f} USDT ({pnl_pct:.2f}%)")
                
                # Eliminar posición
                del self.positions[symbol]
                
                return order
                
        except Exception as e:
            logger.error(f"❌ Error ejecutando orden: {e}")
            return None
    
    def check_positions(self):
        """Verificar posiciones abiertas y aplicar stop loss/take profit"""
        positions_to_close = []
        
        for symbol, position in self.positions.items():
            try:
                ticker = self.exchange.fetch_ticker(symbol)
                current_price = ticker['last']
                
                # Verificar stop loss
                if current_price <= position['stop_loss']:
                    logger.warning(f"⛔ STOP LOSS activado para {symbol}")
                    positions_to_close.append(symbol)
                    
                # Verificar take profit
                elif current_price >= position['take_profit']:
                    logger.info(f"🎯 TAKE PROFIT alcanzado para {symbol}")
                    positions_to_close.append(symbol)
                    
                # Mostrar estado de la posición
                else:
                    pnl_pct = ((current_price - position['entry_price']) / position['entry_price']) * 100
                    logger.info(f"📊 {symbol}: ${current_price:.4f} | PnL: {pnl_pct:+.2f}%")
                    
            except Exception as e:
                logger.error(f"Error verificando posición {symbol}: {e}")
        
        # Cerrar posiciones marcadas
        for symbol in positions_to_close:
            signal = {'symbol': symbol, 'action': 'SELL'}
            self.execute_order(signal)
    
    def run(self):
        """Bucle principal del bot"""
        logger.info("\n" + "="*50)
        logger.info("🚀 INICIANDO BOT DE BINANCE TESTNET")
        logger.info("="*50)
        
        # Verificar conexión y balance
        if not self.check_balance():
            logger.error("❌ No se puede iniciar sin fondos de prueba")
            return
        
        self.running = True
        cycle = 0
        
        while self.running:
            try:
                cycle += 1
                logger.info(f"\n{'='*50}")
                logger.info(f"📍 Ciclo #{cycle} - {datetime.now().strftime('%H:%M:%S')}")
                logger.info(f"📈 Posiciones abiertas: {len(self.positions)}/{self.max_positions}")
                
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
                                
                                if signal and signal['action'] == 'BUY':
                                    logger.info(f"\n🔔 SEÑAL DETECTADA:")
                                    logger.info(f"  {signal['symbol']} - {signal['action']}")
                                    logger.info(f"  Confianza: {signal['confidence']}%")
                                    logger.info(f"  Razón: {signal['reasoning']}")
                                    
                                    self.execute_order(signal)
                                    time.sleep(2)
                        
                        time.sleep(1)  # Rate limiting
                
                # Esperar antes del siguiente ciclo
                logger.info(f"\n⏳ Esperando 60 segundos...")
                time.sleep(60)
                
            except KeyboardInterrupt:
                logger.info("\n⛔ Bot detenido por el usuario")
                break
            except Exception as e:
                logger.error(f"Error en el bucle principal: {e}")
                time.sleep(30)
        
        logger.info("\n👋 Bot finalizado")

def main():
    """Función principal"""
    print("""
╔══════════════════════════════════════════════════════════╗
║        🚀 BOTPHIA - BINANCE TESTNET TRADER 🚀          ║
║                                                          ║
║  Trading REAL en Testnet con dinero FICTICIO            ║
║  Las órdenes SÍ se ejecutan en Binance Testnet          ║
║                                                          ║
║  ⚠️  IMPORTANTE:                                         ║
║  1. Necesitas API keys de https://testnet.binance.vision ║
║  2. Debes obtener fondos de prueba en el Faucet         ║
║  3. Las órdenes aparecerán en tu cuenta de testnet      ║
║                                                          ║
║  Presiona Ctrl+C para detener                           ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    try:
        bot = BinanceTestnetTrader()
        bot.run()
    except KeyboardInterrupt:
        print("\n👋 Hasta luego!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n📝 Asegúrate de:")
        print("1. Tener API keys válidas de Binance Testnet")
        print("2. Haberlas configurado en el archivo .env")
        print("3. Tener fondos de prueba en tu cuenta testnet")

if __name__ == "__main__":
    main()