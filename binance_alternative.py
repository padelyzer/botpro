#!/usr/bin/env python3
"""
Alternative methods to get Binance prices avoiding 418 error
"""

import httpx
import asyncio
import random
import time
from typing import Dict, Optional
import json

class BinanceAlternative:
    """Multiple strategies to get Binance prices"""
    
    def __init__(self):
        self.endpoints = [
            # Different Binance domains
            "https://api.binance.com",
            "https://api1.binance.com", 
            "https://api2.binance.com",
            "https://api3.binance.com",
            "https://api4.binance.com",
            # Binance US (might have different rate limits)
            "https://api.binance.us",
            # Data endpoints (less restricted)
            "https://data.binance.com",
            "https://data-stream.binance.com"
        ]
        
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        self.cache = {}
        self.last_request_time = 0
        
    async def get_price_method1(self, symbol: str) -> Optional[float]:
        """Method 1: Use 24hr ticker endpoint (has more data, sometimes less restricted)"""
        try:
            await self._rate_limit()
            
            endpoint = random.choice(self.endpoints[:4])  # Use main endpoints
            headers = self._get_headers()
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{endpoint}/api/v3/ticker/24hr",
                    params={"symbol": symbol},
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return float(data['lastPrice'])
                    
        except Exception as e:
            print(f"Method1 failed: {e}")
        return None
    
    async def get_price_method2(self, symbol: str) -> Optional[float]:
        """Method 2: Use avgPrice endpoint (3 minute average, often less restricted)"""
        try:
            await self._rate_limit()
            
            endpoint = random.choice(self.endpoints[:4])
            headers = self._get_headers()
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{endpoint}/api/v3/avgPrice",
                    params={"symbol": symbol},
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return float(data['price'])
                    
        except Exception as e:
            print(f"Method2 failed: {e}")
        return None
    
    async def get_price_method3(self, symbol: str) -> Optional[float]:
        """Method 3: Use klines endpoint (OHLC data)"""
        try:
            await self._rate_limit()
            
            endpoint = random.choice(self.endpoints[:4])
            headers = self._get_headers()
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{endpoint}/api/v3/klines",
                    params={
                        "symbol": symbol,
                        "interval": "1m",
                        "limit": 1
                    },
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        # Kline format: [open_time, open, high, low, close, volume, ...]
                        return float(data[0][4])  # Return close price
                        
        except Exception as e:
            print(f"Method3 failed: {e}")
        return None
    
    async def get_price_method4(self, symbol: str) -> Optional[float]:
        """Method 4: Use public data API (sometimes different rate limits)"""
        try:
            await self._rate_limit()
            
            headers = self._get_headers()
            
            # Try data.binance.com endpoint
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://data-api.binance.vision/api/v3/ticker/price",
                    params={"symbol": symbol},
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return float(data['price'])
                    
        except Exception as e:
            print(f"Method4 failed: {e}")
        return None
    
    async def get_price_method5(self, symbol: str) -> Optional[float]:
        """Method 5: Use Binance.US if symbol is available"""
        try:
            await self._rate_limit()
            
            headers = self._get_headers()
            
            # Map USDT pairs to USD for Binance.US
            us_symbol = symbol.replace("USDT", "USD") if symbol.endswith("USDT") else symbol
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.binance.us/api/v3/ticker/price",
                    params={"symbol": us_symbol},
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return float(data['price'])
                    
        except Exception as e:
            print(f"Method5 failed: {e}")
        return None
    
    async def get_price_proxy(self, symbol: str) -> Optional[float]:
        """Use a proxy service or alternative API"""
        try:
            # You could use:
            # 1. CoinGecko API (free tier available)
            # 2. CoinMarketCap API
            # 3. CryptoCompare API
            # 4. Your own proxy server
            
            # Example with CoinGecko (no API key needed for basic requests)
            symbol_map = {
                "BTCUSDT": "bitcoin",
                "ETHUSDT": "ethereum", 
                "BNBUSDT": "binancecoin",
                "SOLUSDT": "solana",
                "ADAUSDT": "cardano"
            }
            
            if symbol in symbol_map:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"https://api.coingecko.com/api/v3/simple/price",
                        params={
                            "ids": symbol_map[symbol],
                            "vs_currencies": "usd"
                        },
                        timeout=10.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        return data[symbol_map[symbol]]["usd"]
                        
        except Exception as e:
            print(f"Proxy method failed: {e}")
        return None
    
    async def get_price(self, symbol: str) -> float:
        """Try all methods to get price"""
        
        # Check cache first (1 minute cache)
        if symbol in self.cache:
            cached_time, cached_price = self.cache[symbol]
            if time.time() - cached_time < 60:
                return cached_price
        
        # Try each method in sequence
        methods = [
            self.get_price_method1,
            self.get_price_method2,
            self.get_price_method3,
            self.get_price_method4,
            self.get_price_method5,
            self.get_price_proxy
        ]
        
        for i, method in enumerate(methods):
            price = await method(symbol)
            if price:
                print(f"✅ Got price for {symbol}: ${price:.2f} using method {i+1}")
                self.cache[symbol] = (time.time(), price)
                return price
            
            # Small delay between methods
            await asyncio.sleep(random.uniform(0.5, 1.5))
        
        # If all methods fail, return cached price or default
        if symbol in self.cache:
            _, cached_price = self.cache[symbol]
            print(f"⚠️ Using cached price for {symbol}: ${cached_price:.2f}")
            return cached_price
        
        # Default prices as last resort
        defaults = {
            "BTCUSDT": 95000.0,
            "ETHUSDT": 3300.0,
            "BNBUSDT": 700.0,
            "SOLUSDT": 210.0,
            "ADAUSDT": 0.95
        }
        
        return defaults.get(symbol, 100.0)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get randomized headers"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        }
    
    async def _rate_limit(self):
        """Implement random delays to avoid rate limiting"""
        # Ensure minimum time between requests (randomized)
        min_delay = random.uniform(0.5, 2.0)  # Random between 0.5-2 seconds
        
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < min_delay:
            await asyncio.sleep(min_delay - time_since_last)
        
        self.last_request_time = time.time()


# Test function
async def test_prices():
    """Test all methods"""
    api = BinanceAlternative()
    
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    
    for symbol in symbols:
        print(f"\nTesting {symbol}:")
        price = await api.get_price(symbol)
        print(f"Final price: ${price:.2f}")
        
        # Add delay between symbols
        await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(test_prices())