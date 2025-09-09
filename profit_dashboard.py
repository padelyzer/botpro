#!/usr/bin/env python3
"""
Profit Dashboard - Panel de control en tiempo real para maximizar ganancias
"""

import requests
import json
import time
from datetime import datetime
import os

class ProfitDashboard:
    def __init__(self):
        self.symbols = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'DOGE', 'ADA', 'AVAX', 'DOT', 'LINK']
        self.refresh_rate = 5  # segundos
        
    def clear_screen(self):
        """Limpia la pantalla"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def get_market_data(self):
        """Obtiene datos del mercado"""
        try:
            url = 'https://api.binance.com/api/v3/ticker/24hr'
            response = requests.get(url, timeout=5)
            data = response.json()
            
            market_data = {}
            for ticker in data:
                symbol = ticker['symbol'].replace('USDT', '')
                if symbol in self.symbols:
                    market_data[symbol] = {
                        'price': float(ticker['lastPrice']),
                        'change_24h': float(ticker['priceChangePercent']),
                        'volume': float(ticker['quoteVolume']),
                        'high': float(ticker['highPrice']),
                        'low': float(ticker['lowPrice'])
                    }
            
            return market_data
        except:
            return {}
    
    def calculate_signals(self, data):
        """Calcula señales de trading para cada símbolo"""
        signals = []
        
        for symbol, info in data.items():
            # Calcular posición en rango
            range_size = info['high'] - info['low']
            if range_size > 0:
                position = (info['price'] - info['low']) / range_size
            else:
                position = 0.5
            
            # Determinar señal
            signal_type = None
            strength = 0
            action = None
            
            # Oversold
            if info['change_24h'] < -3 and position < 0.35:
                signal_type = 'OVERSOLD'
                strength = min(90, abs(info['change_24h']) * 10)
                action = 'BUY'
            
            # Momentum
            elif info['change_24h'] > 3 and position > 0.65 and info['change_24h'] < 8:
                signal_type = 'MOMENTUM'
                strength = min(85, info['change_24h'] * 8)
                action = 'BUY'
            
            # Overbought
            elif info['change_24h'] > 8 or position > 0.9:
                signal_type = 'OVERBOUGHT'
                strength = min(80, info['change_24h'] * 5)
                action = 'SHORT'
            
            # Breakout
            elif position > 0.85 and info['volume'] > 100000000:
                signal_type = 'BREAKOUT'
                strength = 75
                action = 'BUY'
            
            # Support bounce
            elif position < 0.2 and info['change_24h'] > -2:
                signal_type = 'SUPPORT'
                strength = 70
                action = 'BUY'
            
            if signal_type:
                signals.append({
                    'symbol': symbol,
                    'price': info['price'],
                    'change': info['change_24h'],
                    'volume': info['volume'],
                    'position': position,
                    'signal': signal_type,
                    'strength': strength,
                    'action': action
                })
        
        # Ordenar por fuerza de señal
        signals.sort(key=lambda x: x['strength'], reverse=True)
        
        return signals
    
    def display_dashboard(self, data, signals):
        """Muestra el dashboard"""
        self.clear_screen()
        
        print("╔" + "═"*68 + "╗")
        print("║" + " "*20 + "💰 PROFIT DASHBOARD 💰" + " "*20 + "║")
        print("╠" + "═"*68 + "╣")
        print(f"║ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}" + " "*47 + "║")
        print("╚" + "═"*68 + "╝")
        
        # Top movers
        print("\n📈 TOP MOVERS:")
        print("─" * 70)
        sorted_by_change = sorted(data.items(), key=lambda x: abs(x[1]['change_24h']), reverse=True)[:5]
        
        for symbol, info in sorted_by_change:
            change_icon = "🟢" if info['change_24h'] > 0 else "🔴"
            print(f"{change_icon} {symbol:6} ${info['price']:10,.2f} {info['change_24h']:+7.2f}% Vol: ${info['volume']/1e6:6.0f}M")
        
        # Señales activas
        print("\n⚡ SEÑALES DE PROFIT:")
        print("─" * 70)
        
        if signals:
            for i, sig in enumerate(signals[:5]):
                if sig['action'] == 'BUY':
                    icon = "🟢"
                    target = sig['price'] * 1.03
                    stop = sig['price'] * 0.98
                else:
                    icon = "🔴"
                    target = sig['price'] * 0.97
                    stop = sig['price'] * 1.02
                
                print(f"{icon} {sig['symbol']:6} {sig['signal']:10} Fuerza:{sig['strength']:3.0f}%")
                print(f"   ${sig['price']:10,.4f} → Target: ${target:10,.4f} | Stop: ${stop:10,.4f}")
        else:
            print("   ⏳ Sin señales claras en este momento")
        
        # Resumen del mercado
        print("\n📊 RESUMEN DEL MERCADO:")
        print("─" * 70)
        
        bullish = sum(1 for s, d in data.items() if d['change_24h'] > 0)
        bearish = len(data) - bullish
        total_volume = sum(d['volume'] for d in data.values())
        
        print(f"🟢 Alcistas: {bullish}  🔴 Bajistas: {bearish}  💎 Volumen Total: ${total_volume/1e9:.1f}B")
        
        # Mejor oportunidad
        if signals and signals[0]['strength'] > 70:
            best = signals[0]
            print("\n" + "="*70)
            print("🎯 MEJOR OPORTUNIDAD AHORA:")
            print(f"   {best['action']} {best['symbol']} @ ${best['price']:,.4f}")
            print(f"   Señal: {best['signal']} | Fuerza: {best['strength']:.0f}%")
            print("="*70)
    
    def run(self):
        """Loop principal del dashboard"""
        print("Iniciando Profit Dashboard...")
        print("Presiona Ctrl+C para salir")
        time.sleep(2)
        
        try:
            while True:
                # Obtener datos
                data = self.get_market_data()
                
                if data:
                    # Calcular señales
                    signals = self.calculate_signals(data)
                    
                    # Mostrar dashboard
                    self.display_dashboard(data, signals)
                    
                    # Guardar mejor oportunidad
                    if signals and signals[0]['strength'] > 70:
                        with open('best_opportunity.json', 'w') as f:
                            json.dump({
                                'timestamp': datetime.now().isoformat(),
                                'opportunity': signals[0]
                            }, f, indent=2)
                else:
                    print("⚠️ Error obteniendo datos del mercado")
                
                # Esperar antes de actualizar
                time.sleep(self.refresh_rate)
                
        except KeyboardInterrupt:
            print("\n\n✅ Dashboard cerrado")

if __name__ == "__main__":
    dashboard = ProfitDashboard()
    dashboard.run()