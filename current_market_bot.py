#!/usr/bin/env python3
"""
Current Market Trading Bot - Optimizado para condiciones actuales
Diseñado para operar en los próximos días con estrategia simple y efectiva
"""

import asyncio
import httpx
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketCondition(Enum):
    """Condiciones simplificadas del mercado"""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"

@dataclass
class QuickSignal:
    """Señal rápida para trading de corto plazo"""
    symbol: str
    action: str  # BUY, SELL, HOLD
    confidence: float
    entry: float
    stop_loss: float
    take_profit: float
    timeframe: str  # "5m", "15m", "1h"
    reason: str
    expiry: datetime  # Señal expira después de X tiempo

class CurrentMarketBot:
    """
    Bot optimizado para condiciones actuales del mercado
    Enfoque: Simplicidad y velocidad de ejecución
    """
    
    def __init__(self):
        self.binance_api = "https://api.binance.com/api/v3"
        
        # Símbolos de alta liquidez para trading rápido
        self.active_symbols = [
            "BTCUSDT",   # Siempre líquido
            "ETHUSDT",   # Siempre líquido
            "SOLUSDT",   # Alta volatilidad
            "BNBUSDT",   # Estable con movimientos
            "XRPUSDT",   # Pumps ocasionales
        ]
        
        # Configuración para mercado actual (finales agosto 2024)
        self.config = {
            "quick_profit": 0.015,     # 1.5% profit rápido
            "tight_stop": 0.008,       # 0.8% stop loss
            "max_position_time": 4,    # Máximo 4 horas por posición
            "min_volume_usd": 50000000,  # $50M volumen mínimo diario
            "scalp_mode": True,        # Modo scalping activo
        }
        
        # Cache de datos recientes
        self.price_cache = {}
        self.volume_cache = {}
        self.last_update = None
        
    async def get_market_data(self, symbol: str) -> Dict:
        """Obtiene datos de mercado en tiempo real"""
        try:
            async with httpx.AsyncClient() as client:
                # Precio actual y volumen 24h
                ticker = await client.get(
                    f"{self.binance_api}/ticker/24hr",
                    params={"symbol": symbol}
                )
                
                # Últimas velas de 5 minutos
                klines = await client.get(
                    f"{self.binance_api}/klines",
                    params={
                        "symbol": symbol,
                        "interval": "5m",
                        "limit": 20
                    }
                )
                
                if ticker.status_code == 200 and klines.status_code == 200:
                    ticker_data = ticker.json()
                    klines_data = klines.json()
                    
                    # Calcular momentum de 5 minutos
                    recent_closes = [float(k[4]) for k in klines_data[-5:]]
                    momentum_5m = (recent_closes[-1] - recent_closes[0]) / recent_closes[0] * 100
                    
                    # Calcular volumen spike
                    recent_volumes = [float(k[5]) for k in klines_data[-10:]]
                    avg_volume = sum(recent_volumes[:-1]) / len(recent_volumes[:-1])
                    current_volume = recent_volumes[-1]
                    volume_spike = current_volume / avg_volume if avg_volume > 0 else 1
                    
                    return {
                        "symbol": symbol,
                        "price": float(ticker_data["lastPrice"]),
                        "volume_24h": float(ticker_data["quoteVolume"]),
                        "change_24h": float(ticker_data["priceChangePercent"]),
                        "momentum_5m": momentum_5m,
                        "volume_spike": volume_spike,
                        "high_24h": float(ticker_data["highPrice"]),
                        "low_24h": float(ticker_data["lowPrice"]),
                        "timestamp": datetime.now()
                    }
                    
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
        
        return None
    
    def detect_quick_pattern(self, data: Dict) -> Optional[str]:
        """
        Detecta patrones rápidos para scalping
        """
        if not data:
            return None
        
        price = data["price"]
        high_24h = data["high_24h"]
        low_24h = data["low_24h"]
        momentum_5m = data["momentum_5m"]
        volume_spike = data["volume_spike"]
        
        # Rango del día
        daily_range = (high_24h - low_24h) / low_24h * 100 if low_24h > 0 else 0
        
        # Posición en el rango
        position_in_range = (price - low_24h) / (high_24h - low_24h) if high_24h > low_24h else 0.5
        
        # PATRONES DE ENTRADA RÁPIDA
        
        # 1. Breakout con volumen (más efectivo)
        if momentum_5m > 0.5 and volume_spike > 1.8:
            return "VOLUME_BREAKOUT"
        
        # 2. Rebote desde soporte
        if position_in_range < 0.2 and momentum_5m > 0.2 and volume_spike > 1.3:
            return "SUPPORT_BOUNCE"
        
        # 3. Momentum fuerte
        if momentum_5m > 1.0 and position_in_range < 0.7:
            return "STRONG_MOMENTUM"
        
        # 4. Reversión desde resistencia (para shorts)
        if position_in_range > 0.85 and momentum_5m < -0.3 and volume_spike > 1.2:
            return "RESISTANCE_REJECTION"
        
        # 5. Squeeze setup
        if daily_range < 2.0 and volume_spike > 2.0:
            return "VOLATILITY_SQUEEZE"
        
        return None
    
    async def generate_quick_signal(self, symbol: str) -> Optional[QuickSignal]:
        """
        Genera señales rápidas para trading inmediato
        """
        data = await self.get_market_data(symbol)
        if not data:
            return None
        
        pattern = self.detect_quick_pattern(data)
        if not pattern:
            return None
        
        price = data["price"]
        signal = None
        
        # Configurar señal según patrón
        if pattern in ["VOLUME_BREAKOUT", "STRONG_MOMENTUM", "SUPPORT_BOUNCE"]:
            # Señal LONG
            signal = QuickSignal(
                symbol=symbol,
                action="BUY",
                confidence=80 if pattern == "VOLUME_BREAKOUT" else 70,
                entry=price,
                stop_loss=price * (1 - self.config["tight_stop"]),
                take_profit=price * (1 + self.config["quick_profit"]),
                timeframe="5m",
                reason=f"{pattern}: Momentum={data['momentum_5m']:.2f}%, Vol={data['volume_spike']:.1f}x",
                expiry=datetime.now() + timedelta(minutes=15)
            )
            
        elif pattern == "RESISTANCE_REJECTION":
            # Señal SHORT (más conservadora)
            signal = QuickSignal(
                symbol=symbol,
                action="SELL",
                confidence=65,
                entry=price,
                stop_loss=price * (1 + self.config["tight_stop"] * 0.7),  # Stop más tight
                take_profit=price * (1 - self.config["quick_profit"] * 0.8),  # Target más conservador
                timeframe="5m",
                reason=f"{pattern}: Near resistance, momentum turning",
                expiry=datetime.now() + timedelta(minutes=10)
            )
            
        elif pattern == "VOLATILITY_SQUEEZE":
            # Preparación para movimiento grande
            signal = QuickSignal(
                symbol=symbol,
                action="WAIT_BREAKOUT",
                confidence=60,
                entry=price,
                stop_loss=price * 0.99,
                take_profit=price * 1.02,
                timeframe="15m",
                reason=f"{pattern}: Volatility building, wait for direction",
                expiry=datetime.now() + timedelta(minutes=30)
            )
        
        return signal
    
    async def scan_market_continuously(self):
        """
        Escaneo continuo del mercado para oportunidades
        """
        print("="*60)
        print("🚀 CURRENT MARKET BOT - MODO SCALPING")
        print("="*60)
        print(f"Configuración:")
        print(f"  • Take Profit: {self.config['quick_profit']*100:.1f}%")
        print(f"  • Stop Loss: {self.config['tight_stop']*100:.1f}%")
        print(f"  • Max tiempo por trade: {self.config['max_position_time']} horas")
        print(f"  • Símbolos activos: {', '.join(self.active_symbols)}")
        print("="*60)
        
        active_positions = {}  # Track active positions
        
        while True:
            print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Escaneando mercado...")
            
            signals_found = []
            
            for symbol in self.active_symbols:
                # Check if we have an active position
                if symbol in active_positions:
                    pos = active_positions[symbol]
                    # Check if position expired
                    if datetime.now() > pos.expiry:
                        print(f"  ⏱️ {symbol}: Posición expirada, cerrando...")
                        del active_positions[symbol]
                    else:
                        # Check current price for exit
                        data = await self.get_market_data(symbol)
                        if data:
                            current_price = data["price"]
                            if pos.action == "BUY":
                                if current_price >= pos.take_profit:
                                    print(f"  ✅ {symbol}: TARGET ALCANZADO! +{self.config['quick_profit']*100:.1f}%")
                                    del active_positions[symbol]
                                elif current_price <= pos.stop_loss:
                                    print(f"  ❌ {symbol}: Stop loss tocado -{ self.config['tight_stop']*100:.1f}%")
                                    del active_positions[symbol]
                    continue
                
                # Look for new signals
                signal = await self.generate_quick_signal(symbol)
                
                if signal and signal.confidence >= 65:
                    signals_found.append(signal)
                    
                    if signal.action in ["BUY", "SELL"]:
                        print(f"\n  🎯 {symbol}: {signal.action} SIGNAL!")
                        print(f"     Confianza: {signal.confidence}%")
                        print(f"     Entrada: ${signal.entry:.4f}")
                        print(f"     Stop Loss: ${signal.stop_loss:.4f}")
                        print(f"     Take Profit: ${signal.take_profit:.4f}")
                        print(f"     Razón: {signal.reason}")
                        
                        # Add to active positions
                        active_positions[symbol] = signal
                    elif signal.action == "WAIT_BREAKOUT":
                        print(f"  ⏳ {symbol}: Preparando breakout - {signal.reason}")
            
            # Status summary
            if not signals_found and not active_positions:
                print("  No hay señales claras en este momento...")
            elif active_positions:
                print(f"\n  📊 Posiciones activas: {len(active_positions)}")
                for sym, pos in active_positions.items():
                    time_left = (pos.expiry - datetime.now()).seconds // 60
                    print(f"     • {sym}: {pos.action} - {time_left} min restantes")
            
            # Wait before next scan
            await asyncio.sleep(30)  # Scan every 30 seconds for quick opportunities
    
    def get_market_condition(self) -> MarketCondition:
        """
        Determina condición actual del mercado de forma rápida
        """
        # Simplified market condition detection
        # In production, this would analyze multiple timeframes
        return MarketCondition.RANGING  # Default for current late August conditions
    
    async def optimize_for_current_conditions(self):
        """
        Auto-ajusta parámetros según condiciones actuales
        """
        condition = self.get_market_condition()
        
        if condition == MarketCondition.TRENDING_UP:
            self.config["quick_profit"] = 0.02  # 2% en tendencia
            self.config["tight_stop"] = 0.01    # 1% stop
            
        elif condition == MarketCondition.TRENDING_DOWN:
            self.config["quick_profit"] = 0.01  # 1% más conservador
            self.config["tight_stop"] = 0.005   # 0.5% stop muy tight
            
        elif condition == MarketCondition.RANGING:
            self.config["quick_profit"] = 0.015  # 1.5% range trading
            self.config["tight_stop"] = 0.008    # 0.8% stop
            
        elif condition == MarketCondition.VOLATILE:
            self.config["quick_profit"] = 0.025  # 2.5% aprovechar volatilidad
            self.config["tight_stop"] = 0.015    # 1.5% stop más amplio
        
        print(f"📊 Mercado detectado: {condition.value}")
        print(f"   Ajustando parámetros automáticamente...")

# Quick test function
async def test_current_market_bot():
    """Test the current market bot"""
    bot = CurrentMarketBot()
    
    print("="*80)
    print("🤖 CURRENT MARKET BOT TEST")
    print("="*80)
    
    # Optimize for current conditions
    await bot.optimize_for_current_conditions()
    
    # Test single scan
    print("\n📊 Single Market Scan:")
    print("-"*40)
    
    for symbol in bot.active_symbols[:3]:  # Test first 3 symbols
        print(f"\nChecking {symbol}...")
        
        # Get market data
        data = await bot.get_market_data(symbol)
        if data:
            print(f"  Price: ${data['price']:.4f}")
            print(f"  24h Change: {data['change_24h']:.2f}%")
            print(f"  5m Momentum: {data['momentum_5m']:.3f}%")
            print(f"  Volume Spike: {data['volume_spike']:.2f}x")
            
            # Check for signal
            signal = await bot.generate_quick_signal(symbol)
            if signal:
                print(f"\n  🎯 SIGNAL DETECTED!")
                print(f"  Action: {signal.action}")
                print(f"  Confidence: {signal.confidence}%")
                print(f"  Reason: {signal.reason}")
            else:
                print("  No clear signal")
    
    print("\n" + "="*80)
    print("Para iniciar el bot en modo continuo, ejecuta:")
    print("  await bot.scan_market_continuously()")

if __name__ == "__main__":
    # Run test
    asyncio.run(test_current_market_bot())
    
    # Para ejecutar en modo continuo:
    # bot = CurrentMarketBot()
    # asyncio.run(bot.scan_market_continuously())