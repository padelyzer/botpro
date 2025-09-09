#!/usr/bin/env python3
"""
Free Whale Data Collector - APIs y métodos gratuitos para rastrear whales
Sin necesidad de pagar servicios premium
"""

import asyncio
import httpx
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

class FreeWhaleDataCollector:
    """
    Recolector de datos de whales usando APIs y fuentes GRATUITAS
    """
    
    def __init__(self):
        # APIs GRATUITAS
        self.free_apis = {
            # Blockchain explorers (100% gratis)
            "blockchain_info": "https://blockchain.info",
            "blockchair": "https://api.blockchair.com",  # 1440 requests/día gratis
            "etherscan": "https://api.etherscan.io/api",  # Necesita API key gratis
            "bscscan": "https://api.bscscan.com/api",     # Necesita API key gratis
            
            # Exchange APIs (públicas, no necesitan auth)
            "binance": "https://api.binance.com/api/v3",
            "coinbase": "https://api.exchange.coinbase.com",
            "kraken": "https://api.kraken.com/0/public",
            "okx": "https://www.okx.com/api/v5/public",
            
            # On-chain data (gratis con límites)
            "bitquery": "https://graphql.bitquery.io",  # 10 requests/min gratis
            "coinmetrics": "https://community-api.coinmetrics.io/v4",  # Community tier gratis
            "messari": "https://data.messari.io/api/v1",  # Límites pero gratis
            
            # Alternative data
            "alternative_me": "https://api.alternative.me",  # Fear & Greed gratis
            "coinglass": "https://open-api.coinglass.com/public/v2",  # Algunos datos gratis
            "cryptoquant": "https://api.cryptoquant.com/v1",  # Tier gratis disponible
            
            # Scraping targets (cuidado con rate limits)
            "whalestats": "https://www.whalestats.com",
            "clankapp": "https://clankapp.com",
            "nansen": "https://pro.nansen.ai",  # Algunos datos públicos
            "arkham": "https://platform.arkhamintelligence.com"  # Dashboard público
        }
        
        # API Keys GRATIS (hay que registrarse pero son gratis)
        self.free_api_keys = {
            "etherscan": "YOUR_FREE_ETHERSCAN_KEY",  # Registrarse en etherscan.io
            "bscscan": "YOUR_FREE_BSCSCAN_KEY",      # Registrarse en bscscan.com
            "bitquery": "YOUR_FREE_BITQUERY_KEY",    # Registrarse en bitquery.io
        }
        
        # Direcciones conocidas de whales (públicas)
        self.known_whale_addresses = {
            "BTC": {
                # Top holders conocidos
                "1P5ZEDWTKTFGxQjZphgWPQUpe554WKDfHQ": "MicroStrategy",
                "34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo": "Binance Cold",
                "bc1qa5wkgaew2dkv56kfvj49j0av5nml45x9ek9hz9": "Coinbase Cold",
                "3M219KR5vEneNb47ewrPfWyb5jQ2DjxRP6": "Bitfinex Cold",
                "bc1qgdjqv0av3q56jvd82tkdjpy7gdp9ut8tlqmgrpmv24sq90ecnvqqjwvw97": "Tesla"
            },
            "ETH": {
                # Whales ETH conocidos
                "0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8": "Binance 7",
                "0xF977814e90dA44bFA03b6295A0616a897441aceC": "Binance 8",
                "0x28C6c06298d514Db089934071355E5743bf21d60": "Binance 14",
                "0x21a31Ee1afC51d94C2eFcCAa2092aD1028285549": "Binance 15",
                "0xDFd5293D8e347dFe59E90eFd55b2956a1343963d": "Binance 16",
                "0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B": "Vitalik",
                "0x1Db3439a222C519ab44bb1144fC28167b4Fa6EE6": "Vitalik 2",
                "0x220866B1A2219f40e72f5c628B65D54268cA3550": "Vitalik 3"
            }
        }
    
    async def get_blockchain_info_data(self, address: str = None) -> Dict:
        """
        Obtiene datos de blockchain.info (BTC) - GRATIS
        """
        try:
            async with httpx.AsyncClient() as client:
                # Obtener últimas transacciones grandes
                response = await client.get(
                    f"{self.free_apis['blockchain_info']}/unconfirmed-transactions?format=json",
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    large_txs = []
                    
                    for tx in data.get('txs', [])[:50]:
                        # Calcular valor en BTC
                        total_btc = sum(out.get('value', 0) for out in tx.get('out', [])) / 100000000
                        
                        if total_btc > 50:  # Transacciones > 50 BTC
                            large_txs.append({
                                'hash': tx.get('hash'),
                                'time': datetime.fromtimestamp(tx.get('time', 0)),
                                'amount_btc': total_btc,
                                'amount_usd': total_btc * 115000,  # Precio aproximado
                                'inputs': len(tx.get('inputs', [])),
                                'outputs': len(tx.get('out', []))
                            })
                    
                    return {
                        'source': 'blockchain.info',
                        'large_transactions': large_txs,
                        'count': len(large_txs)
                    }
                    
        except Exception as e:
            logger.error(f"Error getting blockchain.info data: {e}")
        
        return {}
    
    async def get_blockchair_data(self, chain: str = "bitcoin") -> Dict:
        """
        Obtiene datos de Blockchair - GRATIS (1440 req/día)
        """
        try:
            async with httpx.AsyncClient() as client:
                # Obtener estadísticas generales
                response = await client.get(
                    f"{self.free_apis['blockchair']}/{chain}/stats",
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return {
                        'source': 'blockchair',
                        'chain': chain,
                        'stats': data.get('data', {}),
                        'large_transaction_count': data.get('data', {}).get('largest_transaction_24h', {})
                    }
                    
        except Exception as e:
            logger.error(f"Error getting blockchair data: {e}")
        
        return {}
    
    async def get_exchange_volumes(self) -> Dict:
        """
        Obtiene volúmenes de exchanges (indica actividad de whales)
        """
        volumes = {}
        
        try:
            async with httpx.AsyncClient() as client:
                # Binance 24hr ticker
                response = await client.get(
                    f"{self.free_apis['binance']}/ticker/24hr",
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Filtrar high-volume pairs
                    high_volume = []
                    for ticker in data:
                        if float(ticker['quoteVolume']) > 100000000:  # >100M USDT volume
                            high_volume.append({
                                'symbol': ticker['symbol'],
                                'volume_usdt': float(ticker['quoteVolume']),
                                'price_change': float(ticker['priceChangePercent']),
                                'count': int(ticker['count'])  # Número de trades
                            })
                    
                    # Ordenar por volumen
                    high_volume.sort(key=lambda x: x['volume_usdt'], reverse=True)
                    
                    volumes['binance'] = {
                        'high_volume_pairs': high_volume[:10],
                        'total_volume': sum(h['volume_usdt'] for h in high_volume)
                    }
                    
        except Exception as e:
            logger.error(f"Error getting exchange volumes: {e}")
        
        return volumes
    
    async def get_fear_greed_index(self) -> Dict:
        """
        Obtiene Fear & Greed Index - GRATIS
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.free_apis['alternative_me']}/fng/",
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return {
                        'value': int(data['data'][0]['value']),
                        'classification': data['data'][0]['value_classification'],
                        'timestamp': data['data'][0]['timestamp']
                    }
                    
        except Exception as e:
            logger.error(f"Error getting fear greed index: {e}")
        
        return {}
    
    async def scrape_whale_stats(self) -> Dict:
        """
        Scraping de sitios públicos de whale tracking
        """
        whale_data = {}
        
        try:
            async with httpx.AsyncClient() as client:
                # Ejemplo: Scraping de whalestats (usar con moderación)
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                
                # NOTA: Muchos sitios requieren JavaScript, considera usar Selenium
                # Este es solo un ejemplo básico
                
                response = await client.get(
                    "https://api.ethplorer.io/getTopTokenHolders/0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",  # USDC holders
                    params={'apiKey': 'freekey', 'limit': 10},
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    whale_data['top_holders'] = data.get('holders', [])[:10]
                    
        except Exception as e:
            logger.error(f"Error scraping whale stats: {e}")
        
        return whale_data
    
    async def get_coinmetrics_data(self) -> Dict:
        """
        CoinMetrics Community API - GRATIS
        """
        try:
            async with httpx.AsyncClient() as client:
                # Network data
                response = await client.get(
                    f"{self.free_apis['coinmetrics']}/timeseries/asset-metrics",
                    params={
                        'assets': 'btc,eth',
                        'metrics': 'AdrActCnt,TxCnt,TxTfrValMeanUSD',
                        'start_time': (datetime.now() - timedelta(days=1)).isoformat(),
                        'end_time': datetime.now().isoformat()
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    return {
                        'source': 'coinmetrics',
                        'data': data.get('data', [])
                    }
                    
        except Exception as e:
            logger.error(f"Error getting coinmetrics data: {e}")
        
        return {}
    
    async def analyze_large_transfers(self) -> Dict:
        """
        Analiza transferencias grandes usando múltiples fuentes gratuitas
        """
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'whale_activity': 'NORMAL',
            'large_transfers': [],
            'exchange_flows': {},
            'sentiment': {}
        }
        
        # 1. Obtener transacciones de blockchain.info
        btc_data = await self.get_blockchain_info_data()
        if btc_data.get('large_transactions'):
            analysis['large_transfers'].extend(btc_data['large_transactions'])
        
        # 2. Obtener volúmenes de exchanges
        volumes = await self.get_exchange_volumes()
        if volumes:
            analysis['exchange_flows'] = volumes
            
            # Detectar actividad anormal
            if volumes.get('binance', {}).get('total_volume', 0) > 5000000000:  # >5B
                analysis['whale_activity'] = 'HIGH'
        
        # 3. Obtener Fear & Greed
        fng = await self.get_fear_greed_index()
        if fng:
            analysis['sentiment']['fear_greed'] = fng
            
            # Whales suelen comprar en miedo extremo
            if fng['value'] < 20:
                analysis['sentiment']['whale_opportunity'] = 'ACCUMULATION_ZONE'
            elif fng['value'] > 80:
                analysis['sentiment']['whale_opportunity'] = 'DISTRIBUTION_ZONE'
        
        # 4. Analizar patrones
        if len(analysis['large_transfers']) > 10:
            analysis['whale_activity'] = 'VERY_HIGH'
        elif len(analysis['large_transfers']) > 5:
            analysis['whale_activity'] = 'HIGH'
        
        return analysis
    
    async def monitor_whale_wallets(self, addresses: List[str] = None) -> Dict:
        """
        Monitorea wallets específicas de whales conocidos
        """
        if not addresses:
            # Usar algunas direcciones conocidas
            addresses = list(self.known_whale_addresses['ETH'].keys())[:5]
        
        wallet_activity = {}
        
        for address in addresses:
            try:
                # Usar Etherscan API (necesita key gratis)
                if self.free_api_keys['etherscan'] != "YOUR_FREE_ETHERSCAN_KEY":
                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            self.free_apis['etherscan'],
                            params={
                                'module': 'account',
                                'action': 'txlist',
                                'address': address,
                                'startblock': 0,
                                'endblock': 99999999,
                                'page': 1,
                                'offset': 10,
                                'sort': 'desc',
                                'apikey': self.free_api_keys['etherscan']
                            },
                            timeout=10.0
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            if data['status'] == '1':
                                wallet_activity[address] = {
                                    'recent_txs': data['result'][:5],
                                    'name': self.known_whale_addresses['ETH'].get(address, 'Unknown')
                                }
                
            except Exception as e:
                logger.error(f"Error monitoring wallet {address}: {e}")
        
        return wallet_activity

class FreeWhaleSignalGenerator:
    """
    Genera señales de trading basadas en datos gratuitos de whales
    """
    
    def __init__(self):
        self.collector = FreeWhaleDataCollector()
        
    async def generate_signal(self, symbol: str) -> Dict:
        """
        Genera señal basada en datos gratuitos
        """
        signal = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'action': 'HOLD',
            'confidence': 0,
            'reasons': []
        }
        
        # Analizar actividad de whales
        whale_analysis = await self.collector.analyze_large_transfers()
        
        # Obtener Fear & Greed
        fng = whale_analysis.get('sentiment', {}).get('fear_greed', {})
        
        # Lógica de señales
        confidence = 0
        
        # 1. Actividad de whales
        if whale_analysis['whale_activity'] == 'VERY_HIGH':
            confidence += 30
            signal['reasons'].append("Very high whale activity detected")
        elif whale_analysis['whale_activity'] == 'HIGH':
            confidence += 20
            signal['reasons'].append("High whale activity detected")
        
        # 2. Sentimiento
        if fng.get('value', 50) < 25:  # Miedo extremo
            confidence += 25
            signal['reasons'].append(f"Extreme fear ({fng.get('value')})")
            signal['action'] = 'BUY'
        elif fng.get('value', 50) > 75:  # Codicia extrema
            confidence += 15
            signal['reasons'].append(f"Extreme greed ({fng.get('value')})")
            signal['action'] = 'SELL'
        
        # 3. Volumen de exchanges
        exchange_flows = whale_analysis.get('exchange_flows', {})
        if exchange_flows.get('binance', {}).get('total_volume', 0) > 3000000000:
            confidence += 15
            signal['reasons'].append("High exchange volume")
        
        # 4. Grandes transferencias
        if len(whale_analysis.get('large_transfers', [])) > 5:
            confidence += 20
            signal['reasons'].append(f"{len(whale_analysis['large_transfers'])} large transfers detected")
        
        signal['confidence'] = min(confidence, 95)
        
        # Solo dar señal si confianza > 60
        if signal['confidence'] < 60:
            signal['action'] = 'HOLD'
        
        return signal

# Funciones de utilidad
async def test_free_apis():
    """
    Prueba todas las APIs gratuitas
    """
    print("="*80)
    print("🆓 TESTING FREE WHALE DATA APIS")
    print("="*80)
    
    collector = FreeWhaleDataCollector()
    
    # 1. Test blockchain.info
    print("\n📊 Testing Blockchain.info (BTC)...")
    btc_data = await collector.get_blockchain_info_data()
    if btc_data.get('large_transactions'):
        print(f"  ✅ Found {len(btc_data['large_transactions'])} large BTC transactions")
        if btc_data['large_transactions']:
            tx = btc_data['large_transactions'][0]
            print(f"  Example: {tx['amount_btc']:.2f} BTC (${tx['amount_usd']:,.0f})")
    
    # 2. Test Blockchair
    print("\n📊 Testing Blockchair...")
    blockchair_data = await collector.get_blockchair_data()
    if blockchair_data.get('stats'):
        print(f"  ✅ Got blockchain stats")
    
    # 3. Test Exchange Volumes
    print("\n📊 Testing Exchange Volumes...")
    volumes = await collector.get_exchange_volumes()
    if volumes.get('binance'):
        total = volumes['binance']['total_volume']
        print(f"  ✅ Binance 24h volume: ${total/1e9:.2f}B")
        print(f"  Top pair: {volumes['binance']['high_volume_pairs'][0]['symbol']}")
    
    # 4. Test Fear & Greed
    print("\n📊 Testing Fear & Greed Index...")
    fng = await collector.get_fear_greed_index()
    if fng:
        print(f"  ✅ Current: {fng['value']} ({fng['classification']})")
    
    # 5. Test CoinMetrics
    print("\n📊 Testing CoinMetrics Community API...")
    cm_data = await collector.get_coinmetrics_data()
    if cm_data.get('data'):
        print(f"  ✅ Got network metrics")
    
    # 6. Generate signal
    print("\n🎯 Generating Signal...")
    generator = FreeWhaleSignalGenerator()
    signal = await generator.generate_signal("BTCUSDT")
    
    print(f"  Action: {signal['action']}")
    print(f"  Confidence: {signal['confidence']}%")
    if signal['reasons']:
        print("  Reasons:")
        for reason in signal['reasons']:
            print(f"    • {reason}")
    
    print("\n" + "="*80)
    print("💡 FREE DATA SOURCES SUMMARY")
    print("="*80)
    print("""
✅ WORKING FREE APIS:
• blockchain.info - Real-time BTC transactions
• Blockchair - 1440 requests/day free
• Binance API - Unlimited public data
• Alternative.me - Fear & Greed Index
• CoinMetrics - Community tier
• Ethplorer - Basic tier with 'freekey'

📝 NEED FREE REGISTRATION:
• Etherscan.io - 100k requests/day free
• BscScan.com - 100k requests/day free
• BitQuery.io - 10 requests/min free
• CryptoQuant - Limited free tier

🔧 ALTERNATIVE METHODS:
• Web scraping (careful with rate limits)
• Telegram bots monitoring
• Discord webhooks
• Twitter API for whale alerts
    """)

if __name__ == "__main__":
    asyncio.run(test_free_apis())