#!/usr/bin/env python3
"""
===========================================
INTEGRACIÓN BINANCE API V1.0
===========================================

Conector modular con Binance para obtener datos históricos,
executar órdenes y gestionar múltiples proyectos simultáneos.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import ccxt
import asyncio
import json
import logging
from dataclasses import dataclass, asdict
import os

# Import SafeMath for secure calculations
from safe_math import SafeMath
from enum import Enum
from binance_api_optimized import OptimizedBinanceAPI

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===========================================
# CONFIGURACIÓN Y ENUMS
# ===========================================

class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

class TimeFrame(Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"

@dataclass
class MarketData:
    """Estructura de datos de mercado"""
    symbol: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    df: pd.DataFrame = None

@dataclass
class Order:
    """Estructura de una orden"""
    symbol: str
    side: OrderSide
    type: OrderType
    amount: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    params: Dict = None
    project_id: str = None
    philosopher: str = None

@dataclass 
class Position:
    """Estructura de una posición abierta"""
    symbol: str
    side: str
    amount: float
    entry_price: float
    current_price: float
    pnl: float
    pnl_percentage: float
    timestamp: datetime
    project_id: str
    philosopher: str

# ===========================================
# CONECTOR BINANCE
# ===========================================

class BinanceConnector:
    """Conector principal con Binance API"""
    
    def __init__(self, api_key: str = None, secret: str = None, testnet: bool = True, use_optimized: bool = True):
        """
        Inicializa conector de Binance
        
        Args:
            api_key: API key de Binance
            secret: Secret key de Binance  
            testnet: Si usar testnet (True) o mainnet (False)
            use_optimized: Usar API optimizada (True) o CCXT tradicional (False)
        """
        
        self.testnet = testnet
        self.use_optimized = use_optimized
        
        # Inicializar API optimizada si está habilitada
        if use_optimized:
            self.optimized_api = OptimizedBinanceAPI(use_data_endpoint=True)
        
        # Configurar exchange
        if testnet:
            # Binance Testnet
            self.exchange = ccxt.binance({
                'apiKey': api_key or os.getenv('BINANCE_TESTNET_API_KEY'),
                'secret': secret or os.getenv('BINANCE_TESTNET_SECRET'),
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',  # o 'future' para futuros
                    'adjustForTimeDifference': True
                }
            })
            self.exchange.set_sandbox_mode(True)
            logger.info("🧪 Usando Binance TESTNET")
        else:
            # Binance Mainnet
            self.exchange = ccxt.binance({
                'apiKey': api_key or os.getenv('BINANCE_API_KEY'),
                'secret': secret or os.getenv('BINANCE_SECRET'),
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                    'adjustForTimeDifference': True
                }
            })
            logger.info("🚀 Usando Binance MAINNET")
        
        # Cache de datos
        self.market_cache = {}
        self.positions = {}
        self.orders_history = []
        
    # ===========================================
    # MÉTODOS DE DATOS DE MERCADO
    # ===========================================
    
    def get_historical_data(self, symbol: str, timeframe: str = '1h', 
                          limit: int = 500) -> pd.DataFrame:
        """
        Obtiene datos históricos de Binance
        
        Args:
            symbol: Símbolo (ej: 'BTC/USDT' o 'BTCUSDT')
            timeframe: Temporalidad ('1m', '5m', '15m', '1h', '4h', '1d')
            limit: Número de velas (máx 1000)
            
        Returns:
            DataFrame con OHLCV
        """
        
        try:
            # Usar API optimizada si está disponible
            if self.use_optimized and hasattr(self, 'optimized_api'):
                # Convertir símbolo al formato requerido (sin '/')
                symbol_clean = symbol.replace('/', '')
                logger.info(f"📊 Usando API optimizada para {symbol_clean} {timeframe}")
                
                df = self.optimized_api.get_klines(
                    symbol=symbol_clean,
                    interval=timeframe,
                    limit=limit
                )
                
                if not df.empty:
                    logger.info(f"📊 Datos obtenidos: {symbol_clean} {timeframe} ({len(df)} velas)")
                    return df
                else:
                    logger.warning(f"⚠️ API optimizada retornó datos vacíos, usando CCXT como fallback")
            
            # Fallback a CCXT tradicional
            ohlcv = self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit
            )
            
            # Convertir a DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            # Convertir timestamp a datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Agregar metadatos
            df.attrs['symbol'] = symbol
            df.attrs['timeframe'] = timeframe
            
            # Cachear
            cache_key = f"{symbol}_{timeframe}"
            self.market_cache[cache_key] = {
                'data': df,
                'updated': datetime.now()
            }
            
            logger.info(f"📊 Datos obtenidos: {symbol} {timeframe} ({len(df)} velas)")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo datos: {e}")
            return pd.DataFrame()
    
    def get_multiple_timeframes(self, symbol: str) -> Dict[str, pd.DataFrame]:
        """
        Obtiene datos en múltiples timeframes para análisis
        
        Args:
            symbol: Símbolo a consultar
            
        Returns:
            Dict con DataFrames por timeframe
        """
        
        timeframes = ['1h', '4h', '1d']
        data = {}
        
        for tf in timeframes:
            df = self.get_historical_data(symbol, tf)
            if not df.empty:
                data[tf] = df
        
        return data
    
    def get_current_price(self, symbol: str) -> float:
        """
        Obtiene precio actual
        
        Args:
            symbol: Símbolo
            
        Returns:
            Precio actual
        """
        
        try:
            # Usar API optimizada si está disponible
            if self.use_optimized and hasattr(self, 'optimized_api'):
                symbol_clean = symbol.replace('/', '')
                price = self.optimized_api.get_current_price(symbol_clean)
                if price > 0:
                    return price
                else:
                    logger.warning(f"⚠️ API optimizada retornó precio 0, usando CCXT como fallback")
            
            # Fallback a CCXT tradicional
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            logger.error(f"Error obteniendo precio: {e}")
            return 0.0
    
    def get_orderbook(self, symbol: str, limit: int = 10) -> Dict:
        """
        Obtiene libro de órdenes
        
        Args:
            symbol: Símbolo
            limit: Profundidad del libro
            
        Returns:
            Dict con bids y asks
        """
        
        try:
            orderbook = self.exchange.fetch_order_book(symbol, limit)
            return {
                'bids': orderbook['bids'][:limit],
                'asks': orderbook['asks'][:limit],
                'spread': orderbook['asks'][0][0] - orderbook['bids'][0][0] if orderbook['bids'] and orderbook['asks'] else 0,
                'timestamp': orderbook['timestamp']
            }
        except Exception as e:
            logger.error(f"Error obteniendo orderbook: {e}")
            return {}
    
    # ===========================================
    # MÉTODOS DE TRADING
    # ===========================================
    
    def place_order(self, order: Order) -> Dict:
        """
        Coloca una orden en Binance
        
        Args:
            order: Objeto Order con detalles
            
        Returns:
            Dict con respuesta de Binance
        """
        
        try:
            if self.testnet:
                logger.info(f"🧪 TESTNET - Simulando orden: {order}")
                # En testnet, simular la orden
                return self._simulate_order(order)
            
            # Orden real
            if order.type == OrderType.MARKET:
                result = self.exchange.create_market_order(
                    symbol=order.symbol,
                    side=order.side.value,
                    amount=order.amount
                )
            elif order.type == OrderType.LIMIT:
                result = self.exchange.create_limit_order(
                    symbol=order.symbol,
                    side=order.side.value,
                    amount=order.amount,
                    price=order.price
                )
            else:
                logger.error(f"Tipo de orden no soportado: {order.type}")
                return {}
            
            # Registrar en historial
            self.orders_history.append({
                'order': order,
                'result': result,
                'timestamp': datetime.now()
            })
            
            logger.info(f"✅ Orden ejecutada: {result['id']}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error colocando orden: {e}")
            return {'error': str(e)}
    
    def _simulate_order(self, order: Order) -> Dict:
        """Simula una orden para testing"""
        
        current_price = self.get_current_price(order.symbol)
        
        return {
            'id': f"SIM_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'symbol': order.symbol,
            'side': order.side.value,
            'type': order.type.value,
            'amount': order.amount,
            'price': order.price or current_price,
            'status': 'filled',
            'timestamp': datetime.now().isoformat(),
            'simulated': True
        }
    
    def get_balance(self) -> Dict[str, float]:
        """
        Obtiene balance de la cuenta
        
        Returns:
            Dict con balances por moneda
        """
        
        try:
            balance = self.exchange.fetch_balance()
            
            # Filtrar solo monedas con balance
            non_zero = {}
            for currency, amount in balance['total'].items():
                if amount > 0:
                    non_zero[currency] = amount
            
            return non_zero
            
        except Exception as e:
            logger.error(f"Error obteniendo balance: {e}")
            if self.testnet:
                # Balance simulado para testnet
                return {
                    'USDT': 10000.0,
                    'BTC': 0.1,
                    'ETH': 1.0
                }
            return {}
    
    def get_open_orders(self, symbol: str = None) -> List[Dict]:
        """
        Obtiene órdenes abiertas
        
        Args:
            symbol: Filtrar por símbolo (opcional)
            
        Returns:
            Lista de órdenes abiertas
        """
        
        try:
            if symbol:
                orders = self.exchange.fetch_open_orders(symbol)
            else:
                orders = self.exchange.fetch_open_orders()
            
            return orders
            
        except Exception as e:
            logger.error(f"Error obteniendo órdenes: {e}")
            return []
    
    def cancel_order(self, order_id: str, symbol: str) -> bool:
        """
        Cancela una orden
        
        Args:
            order_id: ID de la orden
            symbol: Símbolo
            
        Returns:
            True si se canceló exitosamente
        """
        
        try:
            self.exchange.cancel_order(order_id, symbol)
            logger.info(f"❌ Orden cancelada: {order_id}")
            return True
        except Exception as e:
            logger.error(f"Error cancelando orden: {e}")
            return False
    
    # ===========================================
    # GESTIÓN DE POSICIONES
    # ===========================================
    
    def update_positions(self, project_id: str = None) -> List[Position]:
        """
        Actualiza posiciones abiertas
        
        Args:
            project_id: Filtrar por proyecto (opcional)
            
        Returns:
            Lista de posiciones
        """
        
        positions = []
        
        # Obtener balance actual
        balance = self.get_balance()
        
        for currency, amount in balance.items():
            if currency != 'USDT' and amount > 0:
                symbol = f"{currency}/USDT"
                current_price = self.get_current_price(symbol)
                
                # Buscar precio de entrada en historial
                entry_price = self._find_entry_price(currency)
                
                if current_price > 0:
                    try:
                        # Use SafeMath for PnL calculation
                        pnl_result = SafeMath.safe_pnl_calculation(
                            entry_price=entry_price,
                            current_price=current_price,
                            quantity=amount,
                            position_type='long'
                        )
                        
                        pnl = float(pnl_result['absolute_pnl'])
                        pnl_pct = float(pnl_result['percentage_pnl'])
                        
                    except Exception as e:
                        logging.error(f"Error calculating PnL for {symbol}: {e}")
                        pnl = 0.0
                        pnl_pct = 0.0
                    
                    position = Position(
                        symbol=symbol,
                        side='long',  # Simplificado para spot
                        amount=amount,
                        entry_price=entry_price,
                        current_price=current_price,
                        pnl=pnl,
                        pnl_percentage=pnl_pct,
                        timestamp=datetime.now(),
                        project_id=project_id or 'DEFAULT',
                        philosopher='UNKNOWN'
                    )
                    
                    positions.append(position)
        
        self.positions[project_id or 'DEFAULT'] = positions
        return positions
    
    def _find_entry_price(self, currency: str) -> float:
        """
        Busca precio de entrada en el historial
        
        Args:
            currency: Moneda
            
        Returns:
            Precio de entrada promedio
        """
        
        # Buscar en historial de órdenes
        total_amount = 0
        total_value = 0
        
        for order_record in self.orders_history:
            order = order_record['order']
            result = order_record['result']
            
            if currency in order.symbol and result.get('status') == 'filled':
                amount = result.get('amount', 0)
                price = result.get('price', 0)
                
                total_amount += amount
                total_value += amount * price
        
        if total_amount > 0:
            return total_value / total_amount
        
        # Si no hay historial, usar precio actual
        return self.get_current_price(f"{currency}/USDT")

# ===========================================
# GESTOR DE PROYECTOS MÚLTIPLES
# ===========================================

class MultiProjectManager:
    """Gestiona múltiples proyectos de trading simultáneos"""
    
    def __init__(self, connector: BinanceConnector):
        self.connector = connector
        self.projects = {}  # project_id -> project_config
        self.active_orders = {}  # project_id -> orders
        self.performance = {}  # project_id -> metrics
        
    def add_project(self, project_id: str, config: Dict):
        """
        Añade un nuevo proyecto
        
        Args:
            project_id: ID del proyecto
            config: Configuración del proyecto
        """
        
        self.projects[project_id] = {
            'id': project_id,
            'config': config,
            'created_at': datetime.now(),
            'status': 'ACTIVE',
            'capital_allocated': config.get('capital', 1000),
            'symbols': config.get('symbols', []),
            'philosophers': config.get('philosophers', []),
            'risk_per_trade': config.get('risk_per_trade', 0.01)
        }
        
        self.active_orders[project_id] = []
        self.performance[project_id] = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0,
            'current_capital': config.get('capital', 1000)
        }
        
        logger.info(f"📁 Proyecto añadido: {project_id}")
    
    def execute_signal_for_project(self, project_id: str, signal: Dict) -> Dict:
        """
        Ejecuta una señal para un proyecto específico
        
        Args:
            project_id: ID del proyecto
            signal: Señal a ejecutar
            
        Returns:
            Resultado de la ejecución
        """
        
        if project_id not in self.projects:
            logger.error(f"Proyecto {project_id} no encontrado")
            return {'error': 'Project not found'}
        
        project = self.projects[project_id]
        
        # Calcular tamaño de posición
        position_size = self._calculate_position_size(
            project['capital_allocated'],
            project['risk_per_trade'],
            signal['entry_price'],
            signal['stop_loss']
        )
        
        # Crear orden
        order = Order(
            symbol=signal['symbol'],
            side=OrderSide.BUY if signal['action'] == 'BUY' else OrderSide.SELL,
            type=OrderType.LIMIT,
            amount=position_size,
            price=signal['entry_price'],
            project_id=project_id,
            philosopher=signal.get('philosopher', 'UNKNOWN')
        )
        
        # Ejecutar
        result = self.connector.place_order(order)
        
        if 'error' not in result:
            self.active_orders[project_id].append({
                'order': order,
                'result': result,
                'signal': signal,
                'timestamp': datetime.now()
            })
            
            self.performance[project_id]['total_trades'] += 1
            
            logger.info(f"✅ Orden ejecutada para proyecto {project_id}")
        
        return result
    
    def _calculate_position_size(self, capital: float, risk: float, 
                                entry: float, stop: float) -> float:
        """
        Calcula tamaño de posición basado en riesgo
        
        Args:
            capital: Capital disponible
            risk: Riesgo por trade (0.01 = 1%)
            entry: Precio de entrada
            stop: Stop loss
            
        Returns:
            Tamaño de posición
        """
        
        risk_amount = capital * risk
        stop_distance = abs(entry - stop)
        
        if stop_distance > 0:
            position_size = risk_amount / stop_distance
            return min(position_size, capital * 0.95 / entry)  # Máx 95% del capital
        
        return 0
    
    def get_project_performance(self, project_id: str) -> Dict:
        """
        Obtiene performance de un proyecto
        
        Args:
            project_id: ID del proyecto
            
        Returns:
            Métricas de performance
        """
        
        if project_id not in self.performance:
            return {}
        
        perf = self.performance[project_id]
        
        # Actualizar con posiciones actuales
        positions = self.connector.update_positions(project_id)
        
        current_value = sum(p.amount * p.current_price for p in positions)
        perf['current_value'] = current_value
        perf['unrealized_pnl'] = sum(p.pnl for p in positions)
        
        # Calcular métricas
        if perf['total_trades'] > 0:
            perf['win_rate'] = perf['winning_trades'] / perf['total_trades']
            perf['avg_win'] = perf['total_pnl'] / perf['winning_trades'] if perf['winning_trades'] > 0 else 0
            perf['avg_loss'] = perf['total_pnl'] / perf['losing_trades'] if perf['losing_trades'] > 0 else 0
        
        return perf
    
    def get_all_projects_summary(self) -> Dict:
        """
        Obtiene resumen de todos los proyectos
        
        Returns:
            Resumen consolidado
        """
        
        summary = {
            'total_projects': len(self.projects),
            'active_projects': sum(1 for p in self.projects.values() if p['status'] == 'ACTIVE'),
            'total_capital': sum(p['capital_allocated'] for p in self.projects.values()),
            'projects': {}
        }
        
        for project_id, project in self.projects.items():
            perf = self.get_project_performance(project_id)
            
            summary['projects'][project_id] = {
                'name': project['config'].get('name', project_id),
                'status': project['status'],
                'capital': project['capital_allocated'],
                'performance': perf,
                'philosophers': project['philosophers'],
                'symbols': project['symbols']
            }
        
        return summary

# ===========================================
# FUNCIONES DE UTILIDAD
# ===========================================

def test_binance_connection():
    """Prueba la conexión con Binance"""
    
    print("\n" + "="*60)
    print("TEST DE CONEXIÓN BINANCE")
    print("="*60 + "\n")
    
    # Crear conector (testnet por defecto)
    connector = BinanceConnector(testnet=True)
    
    # Test 1: Obtener datos históricos
    print("📊 Test 1: Datos históricos")
    df = connector.get_historical_data('BTC/USDT', '1h', 100)
    if not df.empty:
        print(f"   ✅ Datos obtenidos: {len(df)} velas")
        print(f"   Último precio: ${df['close'].iloc[-1]:,.2f}")
    else:
        print("   ❌ No se pudieron obtener datos")
    
    # Test 2: Balance
    print("\n💰 Test 2: Balance")
    balance = connector.get_balance()
    print(f"   Balance: {balance}")
    
    # Test 3: Precio actual
    print("\n💲 Test 3: Precio actual")
    price = connector.get_current_price('BTC/USDT')
    print(f"   BTC/USDT: ${price:,.2f}")
    
    # Test 4: Orden simulada
    print("\n📦 Test 4: Orden simulada")
    test_order = Order(
        symbol='BTC/USDT',
        side=OrderSide.BUY,
        type=OrderType.LIMIT,
        amount=0.001,
        price=price * 0.99  # 1% bajo el precio actual
    )
    
    result = connector.place_order(test_order)
    if 'error' not in result:
        print(f"   ✅ Orden simulada: {result['id']}")
    else:
        print(f"   ❌ Error: {result['error']}")
    
    print("\n" + "="*60)
    print("✅ Test completado")

def create_sample_projects():
    """Crea proyectos de ejemplo"""
    
    print("\n" + "="*60)
    print("CREANDO PROYECTOS DE EJEMPLO")
    print("="*60 + "\n")
    
    connector = BinanceConnector(testnet=True)
    manager = MultiProjectManager(connector)
    
    # Proyecto 1: Conservador con Sócrates y Confucio
    manager.add_project('PROJ_CONSERVATIVE', {
        'name': 'Portfolio Conservador',
        'capital': 5000,
        'symbols': ['BTC/USDT', 'ETH/USDT'],
        'philosophers': ['SOCRATES', 'CONFUCIO'],
        'risk_per_trade': 0.005  # 0.5% por trade
    })
    
    # Proyecto 2: Agresivo con Nietzsche y Aristóteles
    manager.add_project('PROJ_AGGRESSIVE', {
        'name': 'Portfolio Agresivo',
        'capital': 3000,
        'symbols': ['SOL/USDT', 'DOGE/USDT'],
        'philosophers': ['NIETZSCHE', 'ARISTOTELES'],
        'risk_per_trade': 0.02  # 2% por trade
    })
    
    # Proyecto 3: Balanceado
    manager.add_project('PROJ_BALANCED', {
        'name': 'Portfolio Balanceado',
        'capital': 2000,
        'symbols': ['BNB/USDT', 'ADA/USDT'],
        'philosophers': ['SOCRATES', 'ARISTOTELES', 'CONFUCIO'],
        'risk_per_trade': 0.01  # 1% por trade
    })
    
    # Mostrar resumen
    summary = manager.get_all_projects_summary()
    
    print(f"📁 Proyectos creados: {summary['total_projects']}")
    print(f"💰 Capital total: ${summary['total_capital']:,.2f}")
    
    for project_id, details in summary['projects'].items():
        print(f"\n📈 {details['name']}:")
        print(f"   Capital: ${details['capital']:,.2f}")
        print(f"   Filósofos: {', '.join(details['philosophers'])}")
        print(f"   Símbolos: {', '.join(details['symbols'])}")
    
    print("\n✅ Proyectos creados exitosamente")

if __name__ == "__main__":
    # Ejecutar tests
    test_binance_connection()
    create_sample_projects()