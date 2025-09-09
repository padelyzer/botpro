#!/usr/bin/env python3
"""
Simple Liquidity Server with NO CORS issues
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.request
import urllib.parse
from datetime import datetime

class LiquidityHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle preflight CORS requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests"""
        # Add CORS headers
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()
        
        # Parse URL
        parsed_path = urllib.parse.urlparse(self.path)
        
        if parsed_path.path == '/api/liquidity/multi':
            # Get data for multiple symbols
            symbols = ['SOLUSDT', 'ETHUSDT', 'BTCUSDT', 'BNBUSDT']
            results = []
            
            for symbol in symbols:
                try:
                    # Get price from Binance
                    price_url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
                    with urllib.request.urlopen(price_url) as response:
                        price_data = json.loads(response.read())
                        current_price = float(price_data['price'])
                    
                    # Get 24h data
                    ticker_url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
                    with urllib.request.urlopen(ticker_url) as response:
                        ticker_data = json.loads(response.read())
                    
                    # Get order book
                    depth_url = f"https://api.binance.com/api/v3/depth?symbol={symbol}&limit=100"
                    with urllib.request.urlopen(depth_url) as response:
                        depth_data = json.loads(response.read())
                    
                    # Calculate liquidity zones
                    bids = depth_data['bids']
                    asks = depth_data['asks']
                    
                    # Support zones (simplified)
                    support_zones = []
                    if bids:
                        total_bid_value = sum(float(bid[0]) * float(bid[1]) for bid in bids[:20])
                        support_zones.append({
                            'price': current_price * 0.99,
                            'liquidity': total_bid_value * 0.3,
                            'orders': len(bids[:20]),
                            'distance': -1.0
                        })
                        support_zones.append({
                            'price': current_price * 0.98,
                            'liquidity': total_bid_value * 0.2,
                            'orders': len(bids[:10]),
                            'distance': -2.0
                        })
                    
                    # Resistance zones (simplified)
                    resistance_zones = []
                    if asks:
                        total_ask_value = sum(float(ask[0]) * float(ask[1]) for ask in asks[:20])
                        resistance_zones.append({
                            'price': current_price * 1.01,
                            'liquidity': total_ask_value * 0.3,
                            'orders': len(asks[:20]),
                            'distance': 1.0
                        })
                        resistance_zones.append({
                            'price': current_price * 1.02,
                            'liquidity': total_ask_value * 0.2,
                            'orders': len(asks[:10]),
                            'distance': 2.0
                        })
                    
                    # Calculate imbalance
                    total_bid_value = sum(float(bid[0]) * float(bid[1]) for bid in bids)
                    total_ask_value = sum(float(ask[0]) * float(ask[1]) for ask in asks)
                    if total_bid_value + total_ask_value > 0:
                        imbalance = ((total_bid_value - total_ask_value) / (total_bid_value + total_ask_value)) * 100
                    else:
                        imbalance = 0
                    
                    # Calculate liquidation zones
                    liquidations = {
                        'longs': [
                            {'leverage': '100x', 'price': current_price * 0.99, 'distance': -1.0, 'isMagnet': True},
                            {'leverage': '50x', 'price': current_price * 0.98, 'distance': -2.0, 'isMagnet': True},
                            {'leverage': '25x', 'price': current_price * 0.96, 'distance': -4.0, 'isMagnet': False}
                        ],
                        'shorts': [
                            {'leverage': '100x', 'price': current_price * 1.01, 'distance': 1.0, 'isMagnet': False},
                            {'leverage': '50x', 'price': current_price * 1.02, 'distance': 2.0, 'isMagnet': True},
                            {'leverage': '25x', 'price': current_price * 1.04, 'distance': 4.0, 'isMagnet': False}
                        ]
                    }
                    
                    # Simple signal detection
                    signal = None
                    if imbalance > 30 and support_zones:
                        signal = {
                            'type': 'LONG',
                            'confidence': min(70 + abs(imbalance) / 3, 95),
                            'entry': current_price,
                            'target': current_price * 1.03,
                            'stop': current_price * 0.98,
                            'reason': f'Strong buy pressure ({imbalance:.1f}%) near support'
                        }
                    elif imbalance < -30 and resistance_zones:
                        signal = {
                            'type': 'SHORT',
                            'confidence': min(70 + abs(imbalance) / 3, 95),
                            'entry': current_price,
                            'target': current_price * 0.97,
                            'stop': current_price * 1.02,
                            'reason': f'Strong sell pressure ({abs(imbalance):.1f}%) near resistance'
                        }
                    
                    results.append({
                        'symbol': symbol,
                        'price': current_price,
                        'change24h': float(ticker_data['priceChangePercent']),
                        'liquidityZones': {
                            'support': support_zones,
                            'resistance': resistance_zones
                        },
                        'liquidations': liquidations,
                        'signal': signal,
                        'imbalance': imbalance,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                except Exception as e:
                    print(f"Error processing {symbol}: {e}")
                    # Add basic data even if there's an error
                    results.append({
                        'symbol': symbol,
                        'price': 0,
                        'change24h': 0,
                        'liquidityZones': {
                            'support': [],
                            'resistance': []
                        },
                        'liquidations': {
                            'longs': [],
                            'shorts': []
                        },
                        'signal': None,
                        'imbalance': 0,
                        'timestamp': datetime.now().isoformat()
                    })
                    continue
            
            # Send response
            self.wfile.write(json.dumps(results).encode())
        else:
            # Default response
            self.wfile.write(json.dumps({'status': 'ok'}).encode())

def run_server(port=8003):
    server_address = ('', port)
    httpd = HTTPServer(server_address, LiquidityHandler)
    print(f'🚀 Simple Liquidity Server running on http://localhost:{port}')
    print(f'📊 Endpoint: http://localhost:{port}/api/liquidity/multi')
    print(f'✅ CORS enabled for all origins')
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()