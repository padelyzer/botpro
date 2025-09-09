#!/usr/bin/env python3
"""
Sistema con Análisis de Liquidez y Block Orders
Integra análisis de pools de liquidez, órdenes grandes y market depth
"""

import asyncio
import httpx
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Importar configuraciones ganadoras
WINNING_CONFIGS = {
    'BTCUSDT': {'4h': {'min_change_pct': 2.5, 'rsi_oversold': 32, 'rsi_overbought': 68, 'min_volume_ratio': 1.1, 'max_volatility': 10, 'atr_multiplier': 2.2, 'min_confidence': 55, 'trend_filter_strength': 1.2, 'use_trend_following': True}},
    'ETHUSDT': {'4h': {'min_change_pct': 3.0, 'rsi_oversold': 25, 'rsi_overbought': 75, 'min_volume_ratio': 1.3, 'max_volatility': 13, 'atr_multiplier': 3.5, 'min_confidence': 65, 'trend_filter_strength': 0.8, 'use_mean_reversion': True, 'bb_extreme_threshold': 0.15, 'rsi_confirmation': True}},
    'SOLUSDT': {'1h': {'min_change_pct': 3.0, 'rsi_oversold': 30, 'rsi_overbought': 70, 'min_volume_ratio': 1.05, 'max_volatility': 16, 'atr_multiplier': 2.5, 'min_confidence': 55, 'trend_filter_strength': 0.5, 'use_momentum': True}},
    'BNBUSDT': {'1h': {'min_change_pct': 2.2, 'rsi_oversold': 34, 'rsi_overbought': 66, 'min_volume_ratio': 1.2, 'max_volatility': 10, 'atr_multiplier': 2.1, 'min_confidence': 60, 'trend_filter_strength': 0.9, 'use_range_trading': True}, '4h': {'min_change_pct': 2.8, 'rsi_oversold': 31, 'rsi_overbought': 69, 'min_volume_ratio': 1.25, 'max_volatility': 11, 'atr_multiplier': 2.3, 'min_confidence': 62, 'trend_filter_strength': 1.1, 'use_range_trading': True}},
    'ADAUSDT': {'4h': {'min_change_pct': 3.0, 'rsi_oversold': 28, 'rsi_overbought': 72, 'min_volume_ratio': 1.15, 'max_volatility': 15, 'atr_multiplier': 2.6, 'min_confidence': 57, 'trend_filter_strength': 0.8, 'use_mean_reversion': True}},
    'DOGEUSDT': {'1h': {'min_change_pct': 3.5, 'rsi_oversold': 28, 'rsi_overbought': 72, 'min_volume_ratio': 0.95, 'max_volatility': 22, 'atr_multiplier': 3.2, 'min_confidence': 52, 'trend_filter_strength': 0.4, 'use_momentum': True, 'extra_caution': True}, '4h': {'min_change_pct': 4.0, 'rsi_oversold': 25, 'rsi_overbought': 75, 'min_volume_ratio': 1.0, 'max_volatility': 25, 'atr_multiplier': 3.5, 'min_confidence': 55, 'trend_filter_strength': 0.5, 'use_momentum': True, 'extra_caution': True}}
}

INITIAL_CAPITAL = 220.0
MAX_RISK_PER_TRADE = 0.02
DEFAULT_LEVERAGE = 3

class LiquidityAnalyzer:
    """Analiza liquidez y órdenes grandes"""
    
    def __init__(self):
        self.binance_api = "https://fapi.binance.com/fapi/v1"
        self.spot_api = "https://api.binance.com/api/v3"
        
    async def get_order_book_depth(self, symbol: str) -> Dict:
        """Analiza profundidad del order book para detectar órdenes grandes"""
        
        try:
            async with httpx.AsyncClient() as client:
                # Obtener order book profundo (500 niveles)
                depth_response = await client.get(
                    f"{self.spot_api}/depth",
                    params={"symbol": symbol, "limit": 500}
                )
                
                if depth_response.status_code != 200:
                    return {"error": "No depth data"}
                
                depth_data = depth_response.json()
                
                # Analizar bids y asks
                bids = [[float(price), float(qty)] for price, qty in depth_data["bids"][:100]]
                asks = [[float(price), float(qty)] for price, qty in depth_data["asks"][:100]]
                
                # Detectar órdenes grandes (block orders)
                current_price = (bids[0][0] + asks[0][0]) / 2
                large_orders = self._detect_large_orders(bids, asks, current_price)
                
                # Calcular imbalance
                total_bid_volume = sum([bid[1] for bid in bids[:20]])
                total_ask_volume = sum([ask[1] for ask in asks[:20]])
                imbalance = (total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume) * 100
                
                # Calcular spreads en diferentes niveles
                spread_1 = ((asks[0][0] - bids[0][0]) / current_price) * 100
                spread_10 = ((asks[9][0] - bids[9][0]) / current_price) * 100 if len(bids) > 9 and len(asks) > 9 else spread_1
                
                return {
                    "current_price": current_price,
                    "imbalance": imbalance,
                    "spread_bps": spread_1 * 100,  # basis points
                    "spread_10_level": spread_10 * 100,
                    "large_orders": large_orders,
                    "liquidity_score": self._calculate_liquidity_score(bids, asks, current_price),
                    "support_levels": self._find_support_resistance(bids, current_price, "support"),
                    "resistance_levels": self._find_support_resistance(asks, current_price, "resistance"),
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting order book depth for {symbol}: {e}")
            return {"error": str(e)}
    
    def _detect_large_orders(self, bids: List, asks: List, current_price: float) -> Dict:
        """Detecta órdenes grandes (block orders) que pueden mover el precio"""
        
        large_orders = {
            "large_bids": [],
            "large_asks": [],
            "total_large_bid_volume": 0,
            "total_large_ask_volume": 0,
            "whale_activity": False
        }
        
        # Calcular volumen promedio para detectar órdenes anómalas
        all_bid_volumes = [bid[1] for bid in bids[:50]]
        all_ask_volumes = [ask[1] for ask in asks[:50]]
        
        avg_bid_volume = np.mean(all_bid_volumes)
        avg_ask_volume = np.mean(all_ask_volumes)
        
        # Umbral para considerar una orden como "grande" (3x el promedio)
        large_bid_threshold = avg_bid_volume * 3
        large_ask_threshold = avg_ask_volume * 3
        
        # Detectar órdenes grandes en bids
        for bid in bids[:50]:
            price, volume = bid
            if volume > large_bid_threshold:
                distance_pct = ((current_price - price) / current_price) * 100
                large_orders["large_bids"].append({
                    "price": price,
                    "volume": volume,
                    "distance_pct": distance_pct,
                    "usd_value": price * volume
                })
                large_orders["total_large_bid_volume"] += volume
        
        # Detectar órdenes grandes en asks
        for ask in asks[:50]:
            price, volume = ask
            if volume > large_ask_threshold:
                distance_pct = ((price - current_price) / current_price) * 100
                large_orders["large_asks"].append({
                    "price": price,
                    "volume": volume,
                    "distance_pct": distance_pct,
                    "usd_value": price * volume
                })
                large_orders["total_large_ask_volume"] += volume
        
        # Determinar actividad whale
        total_large_volume = large_orders["total_large_bid_volume"] + large_orders["total_large_ask_volume"]
        large_orders["whale_activity"] = bool(total_large_volume > (avg_bid_volume + avg_ask_volume) * 10)
        
        return large_orders
    
    def _calculate_liquidity_score(self, bids: List, asks: List, current_price: float) -> Dict:
        """Calcula score de liquidez en diferentes niveles de precio"""
        
        # Calcular liquidez en diferentes porcentajes del precio actual
        levels = [0.5, 1.0, 2.0, 5.0]  # 0.5%, 1%, 2%, 5% del precio
        
        liquidity_at_levels = {}
        
        for level_pct in levels:
            level_range = current_price * (level_pct / 100)
            
            # Liquidez por debajo del precio actual (bids)
            bid_liquidity = sum([
                bid[1] for bid in bids 
                if bid[0] >= (current_price - level_range)
            ])
            
            # Liquidez por encima del precio actual (asks)
            ask_liquidity = sum([
                ask[1] for ask in asks 
                if ask[0] <= (current_price + level_range)
            ])
            
            liquidity_at_levels[f"{level_pct}%"] = {
                "bid_liquidity": bid_liquidity,
                "ask_liquidity": ask_liquidity,
                "total_liquidity": bid_liquidity + ask_liquidity,
                "imbalance": (bid_liquidity - ask_liquidity) / (bid_liquidity + ask_liquidity + 0.00001) * 100
            }
        
        return liquidity_at_levels
    
    def _find_support_resistance(self, orders: List, current_price: float, order_type: str) -> List:
        """Encuentra niveles de soporte/resistencia basados en concentración de órdenes"""
        
        # Agrupar órdenes por niveles de precio similares
        price_levels = {}
        
        for order in orders[:30]:
            price, volume = order
            # Redondear precio a niveles significativos
            if current_price > 1000:
                level = round(price, -1)  # Redondear a decenas
            elif current_price > 100:
                level = round(price, 0)   # Redondear a unidades
            else:
                level = round(price, 2)   # Redondear a centavos
            
            if level not in price_levels:
                price_levels[level] = 0
            price_levels[level] += volume
        
        # Encontrar los niveles con más volumen
        sorted_levels = sorted(price_levels.items(), key=lambda x: x[1], reverse=True)
        
        # Devolver top 5 niveles con su distancia del precio actual
        levels = []
        for level, volume in sorted_levels[:5]:
            distance_pct = abs(level - current_price) / current_price * 100
            
            levels.append({
                "price": level,
                "volume": volume,
                "distance_pct": distance_pct,
                "strength": "HIGH" if volume > np.mean(list(price_levels.values())) * 2 else "MEDIUM"
            })
        
        return levels
    
    async def get_liquidation_data(self, symbol: str) -> Dict:
        """Obtiene datos de liquidaciones de futuros"""
        
        try:
            async with httpx.AsyncClient() as client:
                # Open Interest
                oi_response = await client.get(
                    f"{self.binance_api}/openInterest",
                    params={"symbol": symbol}
                )
                
                # Funding Rate
                funding_response = await client.get(
                    f"{self.binance_api}/fundingRate",
                    params={"symbol": symbol, "limit": 1}
                )
                
                # Long/Short Ratio
                ratio_response = await client.get(
                    f"{self.binance_api}/globalLongShortAccountRatio",
                    params={"symbol": symbol, "period": "1h", "limit": 1}
                )
                
                liquidation_data = {}
                
                if oi_response.status_code == 200:
                    oi_data = oi_response.json()
                    liquidation_data["open_interest"] = {
                        "value": float(oi_data["openInterest"]),
                        "sum_value": float(oi_data["sumOpenInterest"])
                    }
                
                if funding_response.status_code == 200:
                    funding_data = funding_response.json()
                    if funding_data:
                        current_funding = float(funding_data[0]["fundingRate"]) * 100
                        liquidation_data["funding_rate"] = {
                            "current": current_funding,
                            "interpretation": "BULLISH_PRESSURE" if current_funding > 0.01 else "BEARISH_PRESSURE" if current_funding < -0.01 else "NEUTRAL"
                        }
                
                if ratio_response.status_code == 200:
                    ratio_data = ratio_response.json()
                    if ratio_data:
                        long_short_ratio = float(ratio_data[0]["longShortRatio"])
                        liquidation_data["long_short_ratio"] = {
                            "ratio": long_short_ratio,
                            "interpretation": "LONG_HEAVY" if long_short_ratio > 1.2 else "SHORT_HEAVY" if long_short_ratio < 0.8 else "BALANCED"
                        }
                
                # Calcular zonas de liquidación estimadas
                current_price = await self._get_current_price(symbol)
                if current_price:
                    liquidation_data["liquidation_zones"] = self._calculate_liquidation_zones(current_price, liquidation_data)
                
                return liquidation_data
                
        except Exception as e:
            logger.error(f"Error getting liquidation data for {symbol}: {e}")
            return {"error": str(e)}
    
    async def _get_current_price(self, symbol: str) -> float:
        """Obtiene precio actual"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.binance_api}/ticker/price",
                    params={"symbol": symbol}
                )
                if response.status_code == 200:
                    return float(response.json()["price"])
        except:
            pass
        return 0
    
    def _calculate_liquidation_zones(self, current_price: float, liquidation_data: Dict) -> Dict:
        """Calcula zonas de liquidación probables"""
        
        zones = {
            "long_liquidation_levels": [],
            "short_liquidation_levels": [],
            "high_risk_zones": []
        }
        
        # Niveles comunes de apalancamiento
        leverages = [5, 10, 20, 50, 100]
        
        for leverage in leverages:
            # Liquidación de longs (precio baja)
            long_liq = current_price * (1 - 0.8/leverage)
            zones["long_liquidation_levels"].append({
                "leverage": f"{leverage}x",
                "price": long_liq,
                "distance_pct": ((current_price - long_liq) / current_price) * 100
            })
            
            # Liquidación de shorts (precio sube)
            short_liq = current_price * (1 + 0.8/leverage)
            zones["short_liquidation_levels"].append({
                "leverage": f"{leverage}x", 
                "price": short_liq,
                "distance_pct": ((short_liq - current_price) / current_price) * 100
            })
        
        # Identificar zonas de alto riesgo basadas en long/short ratio
        if "long_short_ratio" in liquidation_data:
            ratio_data = liquidation_data["long_short_ratio"]
            if ratio_data["interpretation"] == "LONG_HEAVY":
                # Muchos longs = riesgo de cascade down
                zones["high_risk_zones"].append({
                    "direction": "DOWN",
                    "reason": "High long concentration",
                    "risk_level": "HIGH"
                })
            elif ratio_data["interpretation"] == "SHORT_HEAVY":
                # Muchos shorts = riesgo de short squeeze
                zones["high_risk_zones"].append({
                    "direction": "UP", 
                    "reason": "High short concentration",
                    "risk_level": "HIGH"
                })
        
        return zones

class LiquidityEnhancedSignalGenerator:
    """Generador de señales con análisis de liquidez"""
    
    def __init__(self):
        self.liquidity_analyzer = LiquidityAnalyzer()
        
    async def fetch_market_data(self, symbol: str, interval: str) -> Optional[pd.DataFrame]:
        """Obtiene datos de mercado"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    'https://fapi.binance.com/fapi/v1/klines',
                    params={'symbol': symbol, 'interval': interval, 'limit': 100}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    df = pd.DataFrame(data, columns=[
                        'timestamp', 'open', 'high', 'low', 'close',
                        'volume', 'close_time', 'quote_volume', 'trades',
                        'taker_buy_volume', 'taker_buy_quote', 'ignore'
                    ])
                    
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        df[col] = df[col].astype(float)
                    
                    return df
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
        
        return None
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores técnicos básicos"""
        
        df['change_pct'] = df['close'].pct_change() * 100
        df['range_position'] = (df['close'] - df['low']) / (df['high'] - df['low'] + 0.00001)
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        df['atr'] = ranges.max(axis=1).rolling(14).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / (loss + 0.00001)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # EMAs
        df['ema_20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        # MACD
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(20).mean()
        df['bb_std'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * 2)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * 2)
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'] + 0.00001)
        
        # Volatilidad y volumen
        df['volatility'] = ((df['high'] - df['low']) / df['close']) * 100
        df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        df['is_uptrend'] = df['ema_20'] > df['ema_50']
        
        return df
    
    async def generate_enhanced_signal(self, symbol: str, interval: str) -> Optional[Dict]:
        """Genera señales mejoradas con análisis de liquidez"""
        
        # Solo usar configuraciones ganadoras
        if symbol not in WINNING_CONFIGS or interval not in WINNING_CONFIGS[symbol]:
            return None
        
        config = WINNING_CONFIGS[symbol][interval]
        
        # Obtener datos de mercado
        df = await self.fetch_market_data(symbol, interval)
        if df is None or len(df) < 50:
            return None
        
        df = self.calculate_indicators(df)
        last = df.iloc[-1]
        
        if pd.isna(last['atr']) or pd.isna(last['rsi']):
            return None
        
        # Obtener análisis de liquidez EN PARALELO
        liquidity_tasks = [
            self.liquidity_analyzer.get_order_book_depth(symbol),
            self.liquidity_analyzer.get_liquidation_data(symbol)
        ]
        
        try:
            liquidity_results = await asyncio.gather(*liquidity_tasks, return_exceptions=True)
            order_book_data = liquidity_results[0] if not isinstance(liquidity_results[0], Exception) else {}
            liquidation_data = liquidity_results[1] if not isinstance(liquidity_results[1], Exception) else {}
        except:
            order_book_data = {}
            liquidation_data = {}
        
        # Generar señal base usando la estrategia ganadora
        base_signal = self._generate_base_signal(last, df.iloc[-2], config)
        
        if not base_signal:
            return None
        
        # ENHANCES CON LIQUIDEZ
        enhanced_signal = await self._enhance_with_liquidity(
            base_signal, order_book_data, liquidation_data, last, config
        )
        
        if enhanced_signal and enhanced_signal['confidence'] >= config['min_confidence']:
            # Agregar información completa
            enhanced_signal.update({
                'symbol': symbol,
                'price': last['close'],
                'timeframe': interval,
                'liquidity_analysis': {
                    'order_book': order_book_data,
                    'liquidations': liquidation_data
                },
                'indicators': {
                    'rsi': last['rsi'],
                    'change_pct': last['change_pct'],
                    'volume_ratio': last['volume_ratio'],
                    'volatility': last['volatility']
                },
                'timestamp': datetime.now().isoformat()
            })
            
            # Calcular stops mejorados
            enhanced_signal = self._calculate_enhanced_stops(enhanced_signal, last, config, order_book_data)
            
            return enhanced_signal
        
        return None
    
    def _generate_base_signal(self, row, prev_row, config):
        """Genera señal base usando estrategia ganadora"""
        
        if row['volatility'] > config['max_volatility']:
            return None
        
        signal = None
        confidence = config['min_confidence']
        
        # TREND FOLLOWING
        if config.get('use_trend_following'):
            if (row['is_uptrend'] and row['macd_histogram'] > 0 and
                row['change_pct'] > config['min_change_pct'] * 0.5 and
                row['rsi'] < config['rsi_overbought'] and row['rsi'] > 45):
                
                signal = {'type': 'LONG', 'strategy': 'TREND_FOLLOWING', 'confidence': confidence + 10}
        
        # MEAN REVERSION
        elif config.get('use_mean_reversion'):
            bb_threshold = config.get('bb_extreme_threshold', 0.2)
            
            if (row['change_pct'] < -config['min_change_pct'] and
                row['rsi'] < config['rsi_oversold'] and
                row['bb_position'] < bb_threshold):
                
                signal = {'type': 'LONG', 'strategy': 'MEAN_REVERSION', 'confidence': confidence}
            
            elif (row['change_pct'] > config['min_change_pct'] and
                  row['rsi'] > config['rsi_overbought'] and
                  row['bb_position'] > (1 - bb_threshold)):
                
                signal = {'type': 'SHORT', 'strategy': 'MEAN_REVERSION', 'confidence': confidence}
        
        # MOMENTUM
        elif config.get('use_momentum'):
            if (row['change_pct'] > config['min_change_pct'] and
                row['macd_histogram'] > prev_row['macd_histogram'] and
                row['rsi'] > 50 and row['rsi'] < config['rsi_overbought']):
                
                signal = {'type': 'LONG', 'strategy': 'MOMENTUM', 'confidence': confidence}
        
        # RANGE TRADING
        elif config.get('use_range_trading'):
            if (row['bb_position'] < 0.2 and row['rsi'] < config['rsi_oversold'] + 5):
                signal = {'type': 'LONG', 'strategy': 'RANGE_TRADING', 'confidence': confidence}
            elif (row['bb_position'] > 0.8 and row['rsi'] > config['rsi_overbought'] - 5):
                signal = {'type': 'SHORT', 'strategy': 'RANGE_TRADING', 'confidence': confidence}
        
        return signal
    
    async def _enhance_with_liquidity(self, base_signal, order_book_data, liquidation_data, row, config):
        """Mejora la señal con análisis de liquidez"""
        
        if not base_signal:
            return None
        
        enhanced_confidence = base_signal['confidence']
        liquidity_reasons = []
        
        # 1. ANÁLISIS DE ORDER BOOK
        if 'large_orders' in order_book_data:
            large_orders = order_book_data['large_orders']
            
            if base_signal['type'] == 'LONG':
                # Buscar support de órdenes grandes
                large_bids_nearby = [
                    bid for bid in large_orders['large_bids'] 
                    if bid['distance_pct'] < 2.0  # Dentro del 2%
                ]
                if large_bids_nearby:
                    enhanced_confidence += 8
                    liquidity_reasons.append("Large bid support detected")
                
                # Verificar si hay resistance de asks cercana
                large_asks_nearby = [
                    ask for ask in large_orders['large_asks']
                    if ask['distance_pct'] < 1.0  # Dentro del 1% arriba
                ]
                if large_asks_nearby:
                    enhanced_confidence -= 5
                    liquidity_reasons.append("Large ask resistance nearby")
            
            else:  # SHORT
                # Buscar resistance de órdenes grandes
                large_asks_nearby = [
                    ask for ask in large_orders['large_asks']
                    if ask['distance_pct'] < 2.0
                ]
                if large_asks_nearby:
                    enhanced_confidence += 8
                    liquidity_reasons.append("Large ask resistance detected")
                
                large_bids_nearby = [
                    bid for bid in large_orders['large_bids']
                    if bid['distance_pct'] < 1.0
                ]
                if large_bids_nearby:
                    enhanced_confidence -= 5
                    liquidity_reasons.append("Large bid support nearby")
        
        # 2. ANÁLISIS DE IMBALANCE
        if 'imbalance' in order_book_data:
            imbalance = order_book_data['imbalance']
            
            if base_signal['type'] == 'LONG' and imbalance > 10:
                enhanced_confidence += 5
                liquidity_reasons.append(f"Positive order book imbalance ({imbalance:.1f}%)")
            elif base_signal['type'] == 'SHORT' and imbalance < -10:
                enhanced_confidence += 5
                liquidity_reasons.append(f"Negative order book imbalance ({imbalance:.1f}%)")
        
        # 3. ANÁLISIS DE LIQUIDACIONES
        if 'long_short_ratio' in liquidation_data:
            ratio_data = liquidation_data['long_short_ratio']
            
            if base_signal['type'] == 'LONG':
                if ratio_data['interpretation'] == 'SHORT_HEAVY':
                    enhanced_confidence += 12  # Short squeeze potential
                    liquidity_reasons.append("Short squeeze setup detected")
                elif ratio_data['interpretation'] == 'LONG_HEAVY':
                    enhanced_confidence -= 8   # Long liquidation risk
                    liquidity_reasons.append("High long liquidation risk")
            
            else:  # SHORT
                if ratio_data['interpretation'] == 'LONG_HEAVY':
                    enhanced_confidence += 12  # Long cascade potential
                    liquidity_reasons.append("Long liquidation cascade setup")
                elif ratio_data['interpretation'] == 'SHORT_HEAVY':
                    enhanced_confidence -= 8   # Short cover risk
                    liquidity_reasons.append("High short covering risk")
        
        # 4. FUNDING RATE
        if 'funding_rate' in liquidation_data:
            funding_data = liquidation_data['funding_rate']
            
            if base_signal['type'] == 'LONG':
                if funding_data['interpretation'] == 'BEARISH_PRESSURE':
                    enhanced_confidence += 6  # Contrarian opportunity
                    liquidity_reasons.append("Negative funding supports long")
            else:  # SHORT
                if funding_data['interpretation'] == 'BULLISH_PRESSURE':
                    enhanced_confidence += 6  # Contrarian opportunity
                    liquidity_reasons.append("Positive funding supports short")
        
        # 5. LIQUIDITY SCORE
        if 'liquidity_score' in order_book_data:
            liquidity_score = order_book_data['liquidity_score']
            if '1.0%' in liquidity_score:
                total_liquidity = liquidity_score['1.0%']['total_liquidity']
                if total_liquidity > 1000:  # Good liquidity
                    enhanced_confidence += 3
                    liquidity_reasons.append("Good market liquidity")
        
        # Aplicar límites
        enhanced_confidence = max(0, min(95, enhanced_confidence))
        
        # Actualizar señal
        base_signal['confidence'] = enhanced_confidence
        base_signal['liquidity_enhancement'] = {
            'reasons': liquidity_reasons,
            'original_confidence': base_signal['confidence'],
            'enhanced_confidence': enhanced_confidence
        }
        
        return base_signal
    
    def _calculate_enhanced_stops(self, signal, row, config, order_book_data):
        """Calcula stops mejorados considerando niveles de liquidez"""
        
        atr_mult = config['atr_multiplier']
        base_stop_distance = row['atr'] * atr_mult
        
        # Ajustar stops basándose en soporte/resistencia de liquidez
        if 'support_levels' in order_book_data and signal['type'] == 'LONG':
            # Buscar soporte cercano para ajustar stop
            nearby_support = [
                level for level in order_book_data['support_levels']
                if level['distance_pct'] < 3.0 and level['price'] < signal['price']
            ]
            
            if nearby_support:
                # Usar el soporte más fuerte como referencia
                strongest_support = max(nearby_support, key=lambda x: x['volume'])
                support_stop = strongest_support['price'] * 0.995  # 0.5% por debajo del soporte
                
                # Usar el stop más conservador
                signal['stop_loss'] = max(signal['price'] - base_stop_distance, support_stop)
                signal['liquidity_stop'] = True
            else:
                signal['stop_loss'] = signal['price'] - base_stop_distance
                signal['liquidity_stop'] = False
        
        elif 'resistance_levels' in order_book_data and signal['type'] == 'SHORT':
            # Buscar resistencia cercana para ajustar stop
            nearby_resistance = [
                level for level in order_book_data['resistance_levels']
                if level['distance_pct'] < 3.0 and level['price'] > signal['price']
            ]
            
            if nearby_resistance:
                strongest_resistance = max(nearby_resistance, key=lambda x: x['volume'])
                resistance_stop = strongest_resistance['price'] * 1.005  # 0.5% por encima
                
                signal['stop_loss'] = min(signal['price'] + base_stop_distance, resistance_stop)
                signal['liquidity_stop'] = True
            else:
                signal['stop_loss'] = signal['price'] + base_stop_distance
                signal['liquidity_stop'] = False
        
        else:
            # Stops estándar
            if signal['type'] == 'LONG':
                signal['stop_loss'] = signal['price'] - base_stop_distance
            else:
                signal['stop_loss'] = signal['price'] + base_stop_distance
            signal['liquidity_stop'] = False
        
        # Take profit estándar
        if signal['type'] == 'LONG':
            signal['take_profit'] = signal['price'] + (base_stop_distance * 1.5)
        else:
            signal['take_profit'] = signal['price'] - (base_stop_distance * 1.5)
        
        # Position size
        risk_amount = INITIAL_CAPITAL * MAX_RISK_PER_TRADE
        signal['position_size'] = (risk_amount * DEFAULT_LEVERAGE) / signal['price']
        signal['leverage'] = DEFAULT_LEVERAGE
        
        return signal

# API
app = FastAPI(title="Liquidity Enhanced Trading System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

signal_generator = LiquidityEnhancedSignalGenerator()

@app.get("/api/signals")
async def get_enhanced_signals():
    """Obtiene señales mejoradas con análisis de liquidez"""
    
    all_signals = []
    
    # Solo usar configuraciones ganadoras
    for symbol, intervals in WINNING_CONFIGS.items():
        for interval in intervals:
            signal = await signal_generator.generate_enhanced_signal(symbol, interval)
            if signal:
                all_signals.append(signal)
    
    # Ordenar por confianza
    all_signals.sort(key=lambda x: x['confidence'], reverse=True)
    return all_signals

@app.get("/api/liquidity/{symbol}")
async def get_liquidity_analysis(symbol: str):
    """Análisis detallado de liquidez para un símbolo"""
    
    liquidity_analyzer = LiquidityAnalyzer()
    
    try:
        order_book_data = await liquidity_analyzer.get_order_book_depth(symbol)
        liquidation_data = await liquidity_analyzer.get_liquidation_data(symbol)
        
        return {
            "symbol": symbol,
            "order_book_analysis": order_book_data,
            "liquidation_analysis": liquidation_data,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/block-orders/{symbol}")
async def get_block_orders(symbol: str):
    """Detecta block orders y whale activity"""
    
    liquidity_analyzer = LiquidityAnalyzer()
    
    try:
        order_book_data = await liquidity_analyzer.get_order_book_depth(symbol)
        
        return {
            "symbol": symbol,
            "large_orders": order_book_data.get("large_orders", {}),
            "whale_activity": order_book_data.get("large_orders", {}).get("whale_activity", False),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/stats")
async def get_stats():
    """Estadísticas del sistema con liquidez"""
    return {
        "capital": INITIAL_CAPITAL,
        "risk_per_trade": MAX_RISK_PER_TRADE,
        "default_leverage": DEFAULT_LEVERAGE,
        "winning_configs_only": len([
            (symbol, interval) 
            for symbol, intervals in WINNING_CONFIGS.items() 
            for interval in intervals
        ]),
        "features": [
            "Order book depth analysis",
            "Block order detection", 
            "Liquidation zone mapping",
            "Funding rate analysis",
            "Support/resistance from liquidity"
        ],
        "active": True
    }

if __name__ == "__main__":
    print("="*60)
    print("SISTEMA CON ANÁLISIS DE LIQUIDEZ Y BLOCK ORDERS")
    print("="*60)
    print(f"Capital: ${INITIAL_CAPITAL}")
    print(f"Configuraciones ganadoras: {len([(s,i) for s,ints in WINNING_CONFIGS.items() for i in ints])}")
    
    features = [
        "✓ Order book depth analysis (500 levels)",
        "✓ Block order detection (whale activity)",
        "✓ Liquidation zone mapping",
        "✓ Support/resistance from liquidity",
        "✓ Funding rate integration",
        "✓ Long/short ratio analysis",
        "✓ Enhanced stop placement"
    ]
    
    for feature in features:
        print(f"  {feature}")
    
    print("\n" + "="*60)
    print("Servidor con liquidez en http://localhost:8002")
    print("="*60)
    
    uvicorn.run(app, host="0.0.0.0", port=8002)