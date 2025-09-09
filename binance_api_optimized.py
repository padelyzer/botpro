#!/usr/bin/env python3
"""
Optimización de Binance API según documentación oficial 2024
https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints
"""

import requests
import pandas as pd
import time
from typing import Dict, List, Optional, Union
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

# Import error handling system
try:
    from error_handler import handle_api_error, ApiError, NetworkError
except ImportError:
    # Fallback if error_handler not available
    def handle_api_error(error, context=None):
        print(f"API Error: {error}")
    class ApiError(Exception): pass
    class NetworkError(Exception): pass

logger = logging.getLogger(__name__)

@dataclass
class BinanceConfig:
    """Configuración optimizada para Binance API"""
    # Endpoints oficiales recomendados
    spot_api_base = "https://api.binance.com"
    data_api_base = "https://data-api.binance.vision"  # Para datos de mercado puros
    
    # Rate limits según documentación
    default_weight_limit = 1200  # Por minuto
    request_timeout = 10  # Segundos (recomendado por Binance)
    
    # Parámetros optimizados
    max_klines_limit = 1000
    default_depth_limit = 100
    max_depth_limit = 5000

class OptimizedBinanceAPI:
    """
    Cliente optimizado para Binance API según mejores prácticas oficiales
    """
    
    def __init__(self, use_data_endpoint: bool = True):
        self.config = BinanceConfig()
        self.session = requests.Session()
        self.session.timeout = self.config.request_timeout
        
        # Usar endpoint especializado para datos de mercado
        self.base_url = (self.config.data_api_base if use_data_endpoint 
                        else self.config.spot_api_base)
        
        # Rate limiting tracking
        self.weight_used = 0
        self.last_weight_reset = time.time()
        
        logger.info(f"🚀 Binance API optimizado inicializado: {self.base_url}")
    
    def _check_rate_limit(self, weight: int):
        """Verifica límites de rate según documentación"""
        current_time = time.time()
        
        # Reset weight counter cada minuto
        if current_time - self.last_weight_reset >= 60:
            self.weight_used = 0
            self.last_weight_reset = current_time
        
        if self.weight_used + weight > self.config.default_weight_limit:
            sleep_time = 60 - (current_time - self.last_weight_reset)
            logger.warning(f"Rate limit alcanzado. Esperando {sleep_time:.1f}s")
            time.sleep(sleep_time)
            self.weight_used = 0
            self.last_weight_reset = time.time()
        
        self.weight_used += weight
    
    def get_klines(self, symbol: str, interval: str, limit: int = 500,
                   start_time: Optional[int] = None, end_time: Optional[int] = None) -> pd.DataFrame:
        """
        Obtiene datos de klines usando endpoint oficial optimizado
        
        Endpoint: GET /api/v3/klines
        Weight: 2 por request
        
        Args:
            symbol: Símbolo (ej: 'BTCUSDT')
            interval: Intervalo ('1m', '5m', '15m', '1h', '4h', '1d', etc.)
            limit: Número de klines (máx 1000)
            start_time: Timestamp de inicio en ms (opcional)
            end_time: Timestamp de fin en ms (opcional)
        """
        self._check_rate_limit(2)  # Weight = 2 según documentación
        
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': min(limit, self.config.max_klines_limit)
        }
        
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
        
        try:
            url = f"{self.base_url}/api/v3/klines"
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Convertir a DataFrame según formato oficial
            df = pd.DataFrame(data, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
            ])
            
            # Optimizar tipos de datos
            numeric_columns = ['open', 'high', 'low', 'close', 'volume', 
                             'quote_asset_volume', 'taker_buy_base_asset_volume', 
                             'taker_buy_quote_asset_volume']
            
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Convertir timestamps a datetime
            df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Retornar solo columnas OHLCV principales para compatibilidad
            return df[['open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            logger.error(f"Error obteniendo klines: {e}")
            return pd.DataFrame()
    
    def get_current_price(self, symbol: str) -> float:
        """
        Obtiene precio actual usando endpoint optimizado
        
        Endpoint: GET /api/v3/ticker/price
        Weight: 2 para símbolo único
        """
        self._check_rate_limit(2)
        
        try:
            url = f"{self.base_url}/api/v3/ticker/price"
            params = {'symbol': symbol}
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            return float(data['price'])
            
        except Exception as e:
            logger.error(f"Error obteniendo precio: {e}")
            return 0.0
    
    def get_24hr_ticker(self, symbol: str) -> Dict:
        """
        Obtiene estadísticas de 24h
        
        Endpoint: GET /api/v3/ticker/24hr
        Weight: 2 para símbolo único
        """
        self._check_rate_limit(2)
        
        try:
            url = f"{self.base_url}/api/v3/ticker/24hr"
            params = {'symbol': symbol}
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error obteniendo ticker 24h: {e}")
            return {}
    
    def get_order_book(self, symbol: str, limit: int = 100) -> Dict:
        """
        Obtiene order book optimizado
        
        Endpoint: GET /api/v3/depth
        Weight: Varía según limit (5-250)
        """
        limit = min(limit, self.config.max_depth_limit)
        
        # Weight según documentación
        if limit <= 100:
            weight = 5
        elif limit <= 500:
            weight = 25
        elif limit <= 1000:
            weight = 50
        else:
            weight = 250
            
        self._check_rate_limit(weight)
        
        try:
            url = f"{self.base_url}/api/v3/depth"
            params = {'symbol': symbol, 'limit': limit}
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error obteniendo order book: {e}")
            return {}
    
    def get_average_price(self, symbol: str) -> float:
        """
        Obtiene precio promedio actual
        
        Endpoint: GET /api/v3/avgPrice
        Weight: 2
        """
        self._check_rate_limit(2)
        
        try:
            url = f"{self.base_url}/api/v3/avgPrice"
            params = {'symbol': symbol}
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            return float(data['price'])
            
        except Exception as e:
            logger.error(f"Error obteniendo precio promedio: {e}")
            return 0.0
    
    def health_check(self) -> bool:
        """Verifica conectividad con API"""
        try:
            url = f"{self.base_url}/api/v3/ping"
            response = self.session.get(url, timeout=5)
            return response.status_code == 200
        except (requests.RequestException, requests.Timeout) as e:
            handle_api_error(NetworkError(
                message=f"Binance API ping failed: {str(e)}",
                context={'url': url}
            ))
            return False
        except Exception as e:
            handle_api_error(e, {'operation': 'test_connectivity', 'url': url})
            return False
    
    def get_server_time(self) -> int:
        """Obtiene tiempo del servidor Binance"""
        try:
            url = f"{self.base_url}/api/v3/time"
            response = self.session.get(url, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            return data['serverTime']
        except (requests.RequestException, requests.Timeout, KeyError) as e:
            handle_api_error(ApiError(
                message=f"Failed to get Binance server time: {str(e)}",
                context={'url': url}
            ))
            return int(time.time() * 1000)
        except Exception as e:
            handle_api_error(e, {'operation': 'get_server_time', 'url': url})
            return int(time.time() * 1000)

# Función de conveniencia para reemplazar la implementación actual
def create_optimized_binance_connector():
    """Crea connector optimizado para reemplazar BinanceConnector actual"""
    return OptimizedBinanceAPI()

if __name__ == "__main__":
    # Test de la implementación optimizada
    api = OptimizedBinanceAPI()
    
    print("🧪 Testing optimized Binance API...")
    
    # Test conectividad
    if api.health_check():
        print("✅ Conexión OK")
    else:
        print("❌ Conexión fallida")
    
    # Test precio actual
    price = api.get_current_price('BTCUSDT')
    print(f"💰 Precio BTC: ${price:,.2f}")
    
    # Test datos históricos
    df = api.get_klines('BTCUSDT', '15m', limit=10)
    print(f"📊 Klines obtenidos: {len(df)} velas")
    if not df.empty:
        print(f"   Último close: ${df['close'].iloc[-1]:,.2f}")
    
    # Test ticker 24h
    ticker = api.get_24hr_ticker('BTCUSDT')
    if ticker:
        print(f"📈 Cambio 24h: {ticker.get('priceChangePercent', 'N/A')}%")
    
    print(f"⚖️ Weight usado: {api.weight_used}/{api.config.default_weight_limit}")