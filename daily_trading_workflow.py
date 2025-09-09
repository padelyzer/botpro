#!/usr/bin/env python3
"""
===========================================
DAILY TRADING WORKFLOW - SISTEMA COMPLETO
===========================================

Flujo de trabajo diario integrando todas las herramientas:
- 10 Filósofos traders
- Binance API para datos y ejecución
- FastAPI para monitoreo
- Sistema de proyectos múltiples
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Optional, Tuple, Any

# Importar todos los componentes
from philosophers import PhilosophicalTradingSystem
from philosophers_extended import register_extended_philosophers
from binance_integration import BinanceConnector, MultiProjectManager, Order, OrderSide, OrderType
import yfinance as yf

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===========================================
# DAILY TRADING MANAGER
# ===========================================

class DailyTradingManager:
    """
    Gestor principal del trading diario
    Coordina todos los sistemas y herramientas
    """
    
    def __init__(self, capital: float = 1000, testnet: bool = True):
        """
        Inicializa el sistema de trading diario
        
        Args:
            capital: Capital inicial
            testnet: Si usar testnet (True) o mainnet (False)
        """
        
        self.capital = capital
        self.testnet = testnet
        
        # 1. Inicializar Binance
        self.binance = BinanceConnector(testnet=testnet)
        self.project_manager = MultiProjectManager(self.binance)
        
        # 2. Inicializar Sistema Filosófico
        self.philosophy_system = register_extended_philosophers()
        
        # 3. Configuración de trading
        self.trading_config = {
            'max_positions': 3,
            'risk_per_trade': 0.01,  # 1% por trade
            'max_daily_loss': 0.05,  # 5% pérdida máxima diaria
            'symbols': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'],
            'timeframes': ['1h', '4h', '1d'],
            'check_interval': 3600  # Revisar cada hora
        }
        
        # 4. Estado del sistema
        self.daily_stats = {
            'date': datetime.now().date(),
            'starting_capital': capital,
            'current_capital': capital,
            'trades_executed': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'daily_pnl': 0,
            'active_positions': []
        }
        
        # 5. Proyectos activos
        self.active_projects = {}
        
        logger.info(f"✅ Sistema de Trading Diario inicializado")
        logger.info(f"💰 Capital: ${capital}")
        logger.info(f"🔧 Modo: {'TESTNET' if testnet else 'MAINNET'}")
    
    # ===========================================
    # SETUP INICIAL DEL DÍA
    # ===========================================
    
    def morning_setup(self):
        """
        Rutina matutina de configuración
        Se ejecuta al inicio del día de trading
        """
        
        print("\n" + "="*60)
        print(f"☀️ BUENOS DÍAS - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("="*60)
        
        # 1. Revisar balance
        balance = self.binance.get_balance()
        print(f"\n💰 BALANCE ACTUAL:")
        for currency, amount in balance.items():
            if amount > 0:
                print(f"   {currency}: {amount:.8f}")
        
        # 2. Revisar posiciones abiertas
        positions = self.binance.update_positions()
        if positions:
            print(f"\n📊 POSICIONES ABIERTAS:")
            for pos in positions:
                print(f"   {pos.symbol}: {pos.amount} @ ${pos.entry_price:.2f}")
                print(f"   P&L: ${pos.pnl:.2f} ({pos.pnl_percentage:.2f}%)")
        else:
            print("\n📊 No hay posiciones abiertas")
        
        # 3. Crear proyectos del día
        self._create_daily_projects()
        
        # 4. Análisis de mercado inicial
        self._initial_market_analysis()
        
        print("\n✅ Setup matutino completado")
    
    def _create_daily_projects(self):
        """Crea los proyectos de trading del día"""
        
        print("\n🗂️ CREANDO PROYECTOS DEL DÍA:")
        
        # Proyecto 1: Conservador (Sócrates + Confucio + Kant)
        self.project_manager.add_project('CONSERVATIVE_DAILY', {
            'name': 'Portfolio Conservador',
            'capital': self.capital * 0.3,  # 30% del capital
            'symbols': ['BTC/USDT', 'ETH/USDT'],
            'philosophers': ['SOCRATES', 'CONFUCIO', 'KANT'],
            'risk_per_trade': 0.005  # 0.5% por trade
        })
        print("   ✅ Proyecto Conservador (30% capital)")
        
        # Proyecto 2: Balanceado (Platón + Descartes + Aristóteles)
        self.project_manager.add_project('BALANCED_DAILY', {
            'name': 'Portfolio Balanceado',
            'capital': self.capital * 0.4,  # 40% del capital
            'symbols': ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'],
            'philosophers': ['PLATON', 'DESCARTES', 'ARISTOTELES'],
            'risk_per_trade': 0.01  # 1% por trade
        })
        print("   ✅ Proyecto Balanceado (40% capital)")
        
        # Proyecto 3: Agresivo (Nietzsche + Sun Tzu + Maquiavelo)
        self.project_manager.add_project('AGGRESSIVE_DAILY', {
            'name': 'Portfolio Agresivo',
            'capital': self.capital * 0.2,  # 20% del capital
            'symbols': ['SOL/USDT', 'DOGE/USDT'],
            'philosophers': ['NIETZSCHE', 'SUNTZU', 'MAQUIAVELO'],
            'risk_per_trade': 0.02  # 2% por trade
        })
        print("   ✅ Proyecto Agresivo (20% capital)")
        
        # Proyecto 4: Adaptativo (Heráclito solo)
        self.project_manager.add_project('ADAPTIVE_DAILY', {
            'name': 'Portfolio Adaptativo',
            'capital': self.capital * 0.1,  # 10% del capital
            'symbols': ['BTC/USDT'],
            'philosophers': ['HERACLITO'],
            'risk_per_trade': 0.015  # 1.5% por trade
        })
        print("   ✅ Proyecto Adaptativo (10% capital)")
    
    def _initial_market_analysis(self):
        """Análisis inicial del mercado"""
        
        print("\n📈 ANÁLISIS DE MERCADO INICIAL:")
        
        for symbol in self.trading_config['symbols']:
            # Obtener datos
            df_1h = self.binance.get_historical_data(symbol, '1h', 100)
            
            if not df_1h.empty:
                current_price = df_1h['close'].iloc[-1]
                change_24h = ((current_price / df_1h['close'].iloc[-24]) - 1) * 100
                
                # Detectar tendencia
                sma_20 = df_1h['close'].rolling(20).mean().iloc[-1]
                trend = "📈 ALCISTA" if current_price > sma_20 else "📉 BAJISTA"
                
                print(f"\n   {symbol}:")
                print(f"   Precio: ${current_price:,.2f}")
                print(f"   24h: {change_24h:+.2f}%")
                print(f"   Tendencia: {trend}")
    
    # ===========================================
    # CICLO DE TRADING PRINCIPAL
    # ===========================================
    
    async def trading_cycle(self):
        """
        Ciclo principal de trading
        Se ejecuta continuamente durante el día
        """
        
        print("\n🔄 INICIANDO CICLO DE TRADING")
        
        while self._should_continue_trading():
            try:
                # 1. Obtener datos de mercado
                market_data = await self._fetch_market_data()
                
                # 2. Análisis filosófico
                philosophical_signals = await self._philosophical_analysis(market_data)
                
                # 3. Consenso y filtrado
                final_signals = self._build_consensus(philosophical_signals)
                
                # 4. Gestión de riesgo
                validated_signals = self._risk_management(final_signals)
                
                # 5. Ejecución de órdenes
                if validated_signals:
                    await self._execute_trades(validated_signals)
                
                # 6. Actualizar posiciones
                self._update_positions()
                
                # 7. Reportar estado
                self._report_status()
                
                # 8. Esperar próximo ciclo
                await asyncio.sleep(self.trading_config['check_interval'])
                
            except Exception as e:
                logger.error(f"❌ Error en ciclo de trading: {e}")
                await asyncio.sleep(60)  # Esperar 1 minuto ante errores
    
    def _should_continue_trading(self) -> bool:
        """Determina si continuar trading"""
        
        # Verificar pérdida diaria máxima
        if self.daily_stats['daily_pnl'] < -self.capital * self.trading_config['max_daily_loss']:
            logger.warning("⚠️ Pérdida diaria máxima alcanzada. Deteniendo trading.")
            return False
        
        # Verificar horario de mercado (24/7 para crypto)
        current_hour = datetime.now().hour
        if current_hour >= 23:  # Parar a las 11 PM
            logger.info("🌙 Fin del día de trading")
            return False
        
        return True
    
    async def _fetch_market_data(self) -> Dict:
        """Obtiene datos de mercado actualizados"""
        
        market_data = {}
        
        for symbol in self.trading_config['symbols']:
            try:
                # Obtener múltiples timeframes
                data = self.binance.get_multiple_timeframes(symbol)
                market_data[symbol] = data
                
            except Exception as e:
                logger.error(f"Error obteniendo datos de {symbol}: {e}")
        
        return market_data
    
    async def _philosophical_analysis(self, market_data: Dict) -> List:
        """Análisis con todos los filósofos"""
        
        all_signals = []
        
        for project_id, project in self.project_manager.projects.items():
            for symbol in project['symbols']:
                if symbol in market_data:
                    # Obtener datos 1H para análisis
                    df = market_data[symbol].get('1h')
                    
                    if df is not None and not df.empty:
                        # Normalizar columnas para los filósofos
                        df.columns = [c.lower() for c in df.columns]
                        
                        # Analizar con los filósofos del proyecto
                        signals = self.philosophy_system.analyze_with_philosophers(
                            df, symbol, project['philosophers']
                        )
                        
                        for signal in signals:
                            signal.metadata['project_id'] = project_id
                            all_signals.append(signal)
        
        logger.info(f"📊 {len(all_signals)} señales filosóficas generadas")
        return all_signals
    
    def _build_consensus(self, signals: List) -> List:
        """Construye consenso entre señales"""
        
        consensus_signals = []
        
        # Agrupar por símbolo y acción
        signal_groups = {}
        for signal in signals:
            key = f"{signal.symbol}_{signal.action}"
            if key not in signal_groups:
                signal_groups[key] = []
            signal_groups[key].append(signal)
        
        # Buscar consenso (al menos 2 filósofos de acuerdo)
        for key, group in signal_groups.items():
            if len(group) >= 2:
                # Crear señal de consenso
                avg_confidence = np.mean([s.confidence for s in group])
                avg_entry = np.mean([s.entry_price for s in group])
                avg_stop = np.mean([s.stop_loss for s in group])
                avg_target = np.mean([s.take_profit for s in group])
                
                consensus = {
                    'symbol': group[0].symbol,
                    'action': group[0].action,
                    'entry_price': avg_entry,
                    'stop_loss': avg_stop,
                    'take_profit': avg_target,
                    'confidence': avg_confidence,
                    'philosophers': [s.philosopher for s in group],
                    'project_id': group[0].metadata.get('project_id')
                }
                
                consensus_signals.append(consensus)
                
                logger.info(f"✅ Consenso en {group[0].symbol}: {group[0].action}")
                logger.info(f"   Filósofos: {consensus['philosophers']}")
        
        return consensus_signals
    
    def _risk_management(self, signals: List) -> List:
        """Validación de gestión de riesgo"""
        
        validated = []
        
        for signal in signals:
            # Verificar posiciones abiertas
            if len(self.daily_stats['active_positions']) >= self.trading_config['max_positions']:
                logger.warning("⚠️ Máximo de posiciones alcanzado")
                continue
            
            # Verificar exposición por símbolo
            symbol_exposure = sum(1 for p in self.daily_stats['active_positions'] 
                                if p['symbol'] == signal['symbol'])
            if symbol_exposure > 0:
                logger.warning(f"⚠️ Ya hay posición abierta en {signal['symbol']}")
                continue
            
            # Calcular riesgo
            risk_amount = self.capital * self.trading_config['risk_per_trade']
            position_size = risk_amount / abs(signal['entry_price'] - signal['stop_loss'])
            
            # Verificar tamaño mínimo
            min_order_size = 10  # $10 mínimo
            if position_size * signal['entry_price'] < min_order_size:
                logger.warning(f"⚠️ Posición muy pequeña para {signal['symbol']}")
                continue
            
            signal['position_size'] = position_size
            signal['risk_amount'] = risk_amount
            
            validated.append(signal)
        
        return validated
    
    async def _execute_trades(self, signals: List):
        """Ejecuta las órdenes de trading"""
        
        for signal in signals:
            try:
                # Crear orden
                order = Order(
                    symbol=signal['symbol'],
                    side=OrderSide.BUY if signal['action'] == 'BUY' else OrderSide.SELL,
                    type=OrderType.LIMIT,
                    amount=signal['position_size'],
                    price=signal['entry_price'],
                    project_id=signal.get('project_id'),
                    philosopher=', '.join(signal['philosophers'])
                )
                
                # Ejecutar
                result = self.binance.place_order(order)
                
                if 'error' not in result:
                    # Registrar trade
                    self.daily_stats['trades_executed'] += 1
                    self.daily_stats['active_positions'].append({
                        'symbol': signal['symbol'],
                        'entry_price': signal['entry_price'],
                        'stop_loss': signal['stop_loss'],
                        'take_profit': signal['take_profit'],
                        'position_size': signal['position_size'],
                        'philosophers': signal['philosophers'],
                        'timestamp': datetime.now()
                    })
                    
                    logger.info(f"✅ TRADE EJECUTADO: {signal['action']} {signal['symbol']}")
                    logger.info(f"   Precio: ${signal['entry_price']:,.2f}")
                    logger.info(f"   Stop: ${signal['stop_loss']:,.2f}")
                    logger.info(f"   Target: ${signal['take_profit']:,.2f}")
                    
            except Exception as e:
                logger.error(f"❌ Error ejecutando trade: {e}")
    
    def _update_positions(self):
        """Actualiza el estado de las posiciones"""
        
        positions = self.binance.update_positions()
        
        for pos in positions:
            # Verificar stops y targets
            for active in self.daily_stats['active_positions']:
                if active['symbol'] == pos.symbol:
                    # Check stop loss
                    if pos.current_price <= active['stop_loss']:
                        logger.warning(f"🛑 STOP LOSS alcanzado en {pos.symbol}")
                        self._close_position(pos, 'STOP_LOSS')
                    
                    # Check take profit
                    elif pos.current_price >= active['take_profit']:
                        logger.info(f"🎯 TAKE PROFIT alcanzado en {pos.symbol}")
                        self._close_position(pos, 'TAKE_PROFIT')
    
    def _close_position(self, position, reason: str):
        """Cierra una posición"""
        
        try:
            # Crear orden de cierre
            order = Order(
                symbol=position.symbol,
                side=OrderSide.SELL if position.side == 'long' else OrderSide.BUY,
                type=OrderType.MARKET,
                amount=position.amount
            )
            
            result = self.binance.place_order(order)
            
            if 'error' not in result:
                # Actualizar estadísticas
                if position.pnl > 0:
                    self.daily_stats['winning_trades'] += 1
                else:
                    self.daily_stats['losing_trades'] += 1
                
                self.daily_stats['daily_pnl'] += position.pnl
                
                # Remover de posiciones activas
                self.daily_stats['active_positions'] = [
                    p for p in self.daily_stats['active_positions'] 
                    if p['symbol'] != position.symbol
                ]
                
                logger.info(f"📊 Posición cerrada: {position.symbol}")
                logger.info(f"   Razón: {reason}")
                logger.info(f"   P&L: ${position.pnl:.2f}")
                
        except Exception as e:
            logger.error(f"Error cerrando posición: {e}")
    
    def _report_status(self):
        """Reporta el estado actual del sistema"""
        
        current_time = datetime.now().strftime('%H:%M')
        
        print(f"\n⏰ [{current_time}] ESTADO DEL SISTEMA:")
        print(f"   Trades hoy: {self.daily_stats['trades_executed']}")
        print(f"   Ganadores: {self.daily_stats['winning_trades']}")
        print(f"   Perdedores: {self.daily_stats['losing_trades']}")
        print(f"   P&L Diario: ${self.daily_stats['daily_pnl']:.2f}")
        print(f"   Posiciones abiertas: {len(self.daily_stats['active_positions'])}")
    
    # ===========================================
    # CIERRE DEL DÍA
    # ===========================================
    
    def end_of_day_report(self):
        """Reporte de fin de día"""
        
        print("\n" + "="*60)
        print(f"🌙 CIERRE DEL DÍA - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("="*60)
        
        # Calcular métricas
        total_trades = self.daily_stats['trades_executed']
        win_rate = (self.daily_stats['winning_trades'] / total_trades * 100) if total_trades > 0 else 0
        
        print(f"\n📊 RESUMEN DEL DÍA:")
        print(f"   Total trades: {total_trades}")
        print(f"   Ganadores: {self.daily_stats['winning_trades']}")
        print(f"   Perdedores: {self.daily_stats['losing_trades']}")
        print(f"   Win Rate: {win_rate:.1f}%")
        print(f"   P&L: ${self.daily_stats['daily_pnl']:.2f}")
        print(f"   ROI: {(self.daily_stats['daily_pnl'] / self.capital * 100):.2f}%")
        
        # Performance por proyecto
        print(f"\n🗂️ PERFORMANCE POR PROYECTO:")
        for project_id in self.project_manager.projects:
            perf = self.project_manager.get_project_performance(project_id)
            print(f"\n   {project_id}:")
            print(f"   Trades: {perf.get('total_trades', 0)}")
            print(f"   P&L: ${perf.get('total_pnl', 0):.2f}")
        
        # Filosofos más exitosos
        print(f"\n🏛️ FILÓSOFOS DEL DÍA:")
        # Aquí podrías trackear qué filósofos generaron mejores señales
        
        print(f"\n💤 Buenas noches! Hasta mañana.")

# ===========================================
# FUNCIONES DE UTILIDAD
# ===========================================

def run_daily_trading_simulation():
    """Ejecuta una simulación de trading diario"""
    
    print("\n" + "="*60)
    print("SIMULACIÓN DE TRADING DIARIO")
    print("="*60)
    
    # Crear manager
    manager = DailyTradingManager(capital=1000, testnet=True)
    
    # Setup matutino
    manager.morning_setup()
    
    # Simular algunas horas de trading
    print("\n⏰ SIMULANDO TRADING...")
    
    # Aquí simularíamos el ciclo de trading
    # En producción, esto sería:
    # asyncio.run(manager.trading_cycle())
    
    # Reporte de fin de día
    manager.end_of_day_report()

def explain_daily_workflow():
    """Explica el flujo de trabajo diario"""
    
    print("\n" + "="*60)
    print("📚 CÓMO FUNCIONA EL DAILY TRADING")
    print("="*60)
    
    workflow = """
    
    🌅 MAÑANA (Setup Inicial):
    1. Revisar balance y posiciones abiertas
    2. Crear 4 proyectos con diferentes filosofías:
       - Conservador: Sócrates + Confucio + Kant (30% capital)
       - Balanceado: Platón + Descartes + Aristóteles (40% capital)
       - Agresivo: Nietzsche + Sun Tzu + Maquiavelo (20% capital)
       - Adaptativo: Heráclito (10% capital)
    3. Análisis inicial del mercado
    
    🔄 DURANTE EL DÍA (Cada Hora):
    1. Obtener datos de Binance (BTC, ETH, SOL)
    2. Cada filósofo analiza según su filosofía
    3. Buscar consenso (mínimo 2 filósofos de acuerdo)
    4. Validar con gestión de riesgo:
       - Máximo 3 posiciones simultáneas
       - 1% riesgo por trade
       - 5% pérdida máxima diaria
    5. Ejecutar órdenes en Binance
    6. Monitorear stops y take profits
    
    🌙 NOCHE (Cierre):
    1. Cerrar posiciones si es necesario
    2. Calcular P&L del día
    3. Generar reporte de performance
    4. Identificar mejores filosofías del día
    
    🎯 VENTAJAS DEL SISTEMA:
    • Diversificación filosófica reduce sesgo
    • Consenso mejora calidad de señales
    • Gestión de riesgo automática
    • Múltiples estrategias simultáneas
    • Adaptación a diferentes condiciones de mercado
    
    💡 EJEMPLO DE CONSENSO:
    Si Platón detecta un patrón perfecto de compra en BTC
    Y Kant confirma que todas sus reglas se cumplen
    → Se genera señal de COMPRA con alta confianza
    
    ⚙️ INTEGRACIÓN COMPLETA:
    • Binance API: Datos en tiempo real y ejecución
    • 10 Filósofos: Análisis desde múltiples perspectivas
    • FastAPI: Monitoreo vía web
    • Risk Management: Protección del capital
    • Multi-Project: Diversificación de estrategias
    """
    
    print(workflow)

if __name__ == "__main__":
    # Explicar el workflow
    explain_daily_workflow()
    
    # Ejecutar simulación
    run_daily_trading_simulation()