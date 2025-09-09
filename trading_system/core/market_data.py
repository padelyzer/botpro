"""
Market Data Module
Centralized market data fetching and processing
"""

import httpx
import asyncio
from typing import Dict, Optional, Tuple
from datetime import datetime

class MarketDataFetcher:
    """Centralized market data fetching"""
    
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
        
    async def get_ticker_24hr(self, symbol: str) -> Optional[Dict]:
        """Get 24hr ticker statistics"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/ticker/24hr?symbol={symbol}")
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            print(f"Error fetching ticker for {symbol}: {e}")
        return None
    
    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/ticker/price?symbol={symbol}")
                if response.status_code == 200:
                    data = response.json()
                    return float(data['price'])
        except Exception as e:
            print(f"Error fetching price for {symbol}: {e}")
        return None
    
    async def get_btc_sol_data(self) -> Tuple[Optional[Dict], Optional[Dict]]:
        """Get BTC and SOL data simultaneously"""
        async with httpx.AsyncClient() as client:
            try:
                btc_task = client.get(f"{self.base_url}/ticker/24hr?symbol=BTCUSDT")
                sol_task = client.get(f"{self.base_url}/ticker/24hr?symbol=SOLUSDT")
                
                btc_response, sol_response = await asyncio.gather(btc_task, sol_task)
                
                btc_data = btc_response.json() if btc_response.status_code == 200 else None
                sol_data = sol_response.json() if sol_response.status_code == 200 else None
                
                return btc_data, sol_data
            except Exception as e:
                print(f"Error fetching BTC/SOL data: {e}")
                return None, None
    
    async def get_market_overview(self, symbols: list = None) -> Dict[str, Dict]:
        """Get market overview for multiple symbols"""
        if symbols is None:
            symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT"]
        
        results = {}
        
        async with httpx.AsyncClient() as client:
            tasks = []
            for symbol in symbols:
                task = client.get(f"{self.base_url}/ticker/24hr?symbol={symbol}")
                tasks.append((symbol, task))
            
            responses = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
            
            for (symbol, _), response in zip(tasks, responses):
                if isinstance(response, Exception):
                    print(f"Error fetching {symbol}: {response}")
                    continue
                    
                if hasattr(response, 'status_code') and response.status_code == 200:
                    results[symbol] = response.json()
        
        return results

class MarketAnalyzer:
    """Market data analysis utilities"""
    
    @staticmethod
    def calculate_change_percentage(current: float, previous: float) -> float:
        """Calculate percentage change"""
        if previous == 0:
            return 0
        return ((current - previous) / previous) * 100
    
    @staticmethod
    def get_market_sentiment(market_data: Dict[str, Dict]) -> Dict:
        """Analyze overall market sentiment"""
        if not market_data:
            return {"status": "unknown", "details": "No data available"}
        
        bearish_count = 0
        bullish_count = 0
        total_change = 0
        
        for symbol, data in market_data.items():
            try:
                change_24h = float(data.get('priceChangePercent', 0))
                total_change += change_24h
                
                if change_24h < -2:
                    bearish_count += 1
                elif change_24h > 2:
                    bullish_count += 1
                else:
                    # Neutral counts as bearish if negative, bullish if positive
                    if change_24h < 0:
                        bearish_count += 1
                    else:
                        bullish_count += 1
            except (ValueError, TypeError):
                continue
        
        total_coins = len(market_data)
        avg_change = total_change / total_coins if total_coins > 0 else 0
        
        if bearish_count >= total_coins * 0.7:
            status = "bearish_dominant"
        elif bullish_count >= total_coins * 0.7:
            status = "bullish_dominant"
        else:
            status = "mixed"
        
        return {
            "status": status,
            "bearish_count": bearish_count,
            "bullish_count": bullish_count,
            "total_coins": total_coins,
            "avg_change": avg_change,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def check_btc_strength(btc_data: Dict) -> Dict:
        """Analyze BTC strength indicators"""
        if not btc_data:
            return {"status": "unknown"}
        
        try:
            price = float(btc_data['lastPrice'])
            change_24h = float(btc_data['priceChangePercent'])
            volume = float(btc_data['quoteVolume'])
            
            # Determine BTC status based on key levels
            if price >= 112000:
                status = "strong"
            elif price >= 110000:
                status = "recovery"
            elif price >= 108000:
                status = "neutral"
            else:
                status = "weak"
            
            return {
                "status": status,
                "price": price,
                "change_24h": change_24h,
                "volume": volume,
                "analysis": {
                    "above_110k": price >= 110000,
                    "positive_24h": change_24h > 0,
                    "high_volume": volume > 2000000000
                }
            }
        except (ValueError, TypeError, KeyError):
            return {"status": "error", "message": "Invalid BTC data"}

# Global instances
market_fetcher = MarketDataFetcher()
market_analyzer = MarketAnalyzer()