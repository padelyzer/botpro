#!/usr/bin/env python3
"""
Live Market Analysis - Real-time market direction detector
"""

import asyncio
import httpx
from datetime import datetime
import numpy as np
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text

console = Console()

class MarketAnalyzer:
    def __init__(self):
        self.binance_url = "https://api.binance.com/api/v3"
        self.symbols = ['BTCUSDT', 'SOLUSDT', 'ETHUSDT', 'AVAXUSDT', 'NEARUSDT']
        self.data_history = {symbol: [] for symbol in self.symbols}
        
    async def get_ticker_data(self, symbol):
        """Get current price and 24h stats"""
        async with httpx.AsyncClient() as client:
            try:
                # Get current price
                ticker = await client.get(
                    f"{self.binance_url}/ticker/24hr",
                    params={"symbol": symbol}
                )
                
                # Get recent klines for technical analysis
                klines = await client.get(
                    f"{self.binance_url}/klines",
                    params={"symbol": symbol, "interval": "1h", "limit": 50}
                )
                
                if ticker.status_code == 200 and klines.status_code == 200:
                    ticker_data = ticker.json()
                    klines_data = klines.json()
                    
                    closes = [float(k[4]) for k in klines_data]
                    
                    return {
                        'symbol': symbol.replace('USDT', ''),
                        'price': float(ticker_data['lastPrice']),
                        'change_24h': float(ticker_data['priceChangePercent']),
                        'volume': float(ticker_data['volume']),
                        'high_24h': float(ticker_data['highPrice']),
                        'low_24h': float(ticker_data['lowPrice']),
                        'rsi': self.calculate_rsi(closes),
                        'trend': self.calculate_trend(closes),
                        'volatility': self.calculate_volatility(closes),
                        'support': self.find_support(closes),
                        'resistance': self.find_resistance(closes)
                    }
            except Exception as e:
                console.print(f"[red]Error fetching {symbol}: {e}[/red]")
                return None
    
    def calculate_rsi(self, prices, period=14):
        """Calculate RSI"""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices)
        seed = deltas[:period]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        
        if down == 0:
            return 100.0
        
        rs = up / down
        return 100 - (100 / (1 + rs))
    
    def calculate_trend(self, prices):
        """Calculate trend direction"""
        if len(prices) < 10:
            return "NEUTRAL"
        
        # Simple moving averages
        sma_5 = np.mean(prices[-5:])
        sma_10 = np.mean(prices[-10:])
        sma_20 = np.mean(prices[-20:]) if len(prices) >= 20 else sma_10
        
        current = prices[-1]
        
        if current > sma_5 > sma_10 > sma_20:
            return "STRONG_UP"
        elif current > sma_5 and sma_5 > sma_10:
            return "UP"
        elif current < sma_5 < sma_10 < sma_20:
            return "STRONG_DOWN"
        elif current < sma_5 and sma_5 < sma_10:
            return "DOWN"
        else:
            return "NEUTRAL"
    
    def calculate_volatility(self, prices):
        """Calculate price volatility"""
        if len(prices) < 2:
            return 0
        returns = np.diff(prices) / prices[:-1]
        return np.std(returns) * 100
    
    def find_support(self, prices):
        """Find nearest support level"""
        if len(prices) < 10:
            return min(prices)
        recent_lows = []
        for i in range(1, len(prices)-1):
            if prices[i] < prices[i-1] and prices[i] < prices[i+1]:
                recent_lows.append(prices[i])
        return np.mean(recent_lows[-3:]) if recent_lows else min(prices[-10:])
    
    def find_resistance(self, prices):
        """Find nearest resistance level"""
        if len(prices) < 10:
            return max(prices)
        recent_highs = []
        for i in range(1, len(prices)-1):
            if prices[i] > prices[i-1] and prices[i] > prices[i+1]:
                recent_highs.append(prices[i])
        return np.mean(recent_highs[-3:]) if recent_highs else max(prices[-10:])
    
    def analyze_market_sentiment(self, data_points):
        """Analyze overall market sentiment"""
        if not data_points:
            return "UNKNOWN"
        
        bullish = sum(1 for d in data_points if d and d['change_24h'] > 0)
        bearish = len([d for d in data_points if d]) - bullish
        
        avg_change = np.mean([d['change_24h'] for d in data_points if d])
        avg_rsi = np.mean([d['rsi'] for d in data_points if d])
        
        if avg_change > 3 and avg_rsi > 60:
            return "BULLISH", "🟢"
        elif avg_change > 0 and avg_rsi > 50:
            return "SLIGHTLY_BULLISH", "🟡"
        elif avg_change < -3 and avg_rsi < 40:
            return "BEARISH", "🔴"
        elif avg_change < 0 and avg_rsi < 50:
            return "SLIGHTLY_BEARISH", "🟠"
        else:
            return "NEUTRAL", "⚪"
    
    def create_analysis_table(self, data_points):
        """Create analysis table"""
        table = Table(title="🎯 Live Market Analysis", show_header=True, header_style="bold cyan")
        table.add_column("Asset", style="cyan", width=8)
        table.add_column("Price", style="white", width=12)
        table.add_column("24h %", width=10)
        table.add_column("RSI", width=8)
        table.add_column("Trend", width=12)
        table.add_column("Signal", width=15)
        table.add_column("S/R Levels", width=20)
        
        for data in data_points:
            if data:
                # Color coding for change
                change_color = "green" if data['change_24h'] > 0 else "red"
                change_text = f"[{change_color}]{data['change_24h']:+.2f}%[/{change_color}]"
                
                # RSI color
                rsi_color = "red" if data['rsi'] > 70 else "green" if data['rsi'] < 30 else "yellow"
                rsi_text = f"[{rsi_color}]{data['rsi']:.0f}[/{rsi_color}]"
                
                # Trend color
                trend_colors = {
                    "STRONG_UP": "bright_green",
                    "UP": "green",
                    "NEUTRAL": "yellow",
                    "DOWN": "red",
                    "STRONG_DOWN": "bright_red"
                }
                trend_color = trend_colors.get(data['trend'], "white")
                trend_text = f"[{trend_color}]{data['trend']}[/{trend_color}]"
                
                # Trading signal
                signal = self.get_trading_signal(data)
                
                # Support/Resistance
                sr_text = f"S: ${data['support']:.2f}\nR: ${data['resistance']:.2f}"
                
                table.add_row(
                    data['symbol'],
                    f"${data['price']:,.2f}",
                    change_text,
                    rsi_text,
                    trend_text,
                    signal,
                    sr_text
                )
        
        return table
    
    def get_trading_signal(self, data):
        """Generate trading signal"""
        if data['rsi'] < 30 and data['trend'] in ['DOWN', 'STRONG_DOWN']:
            return "[bright_green]🟢 BUY SIGNAL[/bright_green]"
        elif data['rsi'] < 35 and data['change_24h'] < -5:
            return "[green]👀 BUY ZONE[/green]"
        elif data['rsi'] > 70 and data['trend'] in ['UP', 'STRONG_UP']:
            return "[bright_red]🔴 SELL SIGNAL[/bright_red]"
        elif data['rsi'] > 65 and data['change_24h'] > 5:
            return "[red]⚠️ SELL ZONE[/red]"
        elif data['trend'] == 'STRONG_UP':
            return "[cyan]📈 MOMENTUM[/cyan]"
        elif data['trend'] == 'STRONG_DOWN':
            return "[magenta]📉 CORRECTION[/magenta]"
        else:
            return "[yellow]⏳ WAIT[/yellow]"
    
    def create_summary_panel(self, data_points):
        """Create market summary panel"""
        sentiment, emoji = self.analyze_market_sentiment(data_points)
        
        # Calculate averages
        avg_change = np.mean([d['change_24h'] for d in data_points if d])
        avg_rsi = np.mean([d['rsi'] for d in data_points if d])
        
        # Count signals
        buy_signals = sum(1 for d in data_points if d and d['rsi'] < 35)
        sell_signals = sum(1 for d in data_points if d and d['rsi'] > 65)
        
        summary_text = Text()
        summary_text.append(f"{emoji} Market Sentiment: ", style="bold")
        summary_text.append(f"{sentiment}\n\n", style="bold cyan")
        summary_text.append(f"📊 Average Change: {avg_change:+.2f}%\n")
        summary_text.append(f"📈 Average RSI: {avg_rsi:.1f}\n")
        summary_text.append(f"🟢 Buy Opportunities: {buy_signals}\n")
        summary_text.append(f"🔴 Sell Opportunities: {sell_signals}\n")
        
        return Panel(summary_text, title="Market Overview", border_style="cyan")
    
    def create_sol_analysis(self, sol_data):
        """Special analysis for SOL position"""
        if not sol_data:
            return Panel("No SOL data available", title="SOL Position Analysis")
        
        entry_price = 198.20
        current = sol_data['price']
        pnl = (current - entry_price) / entry_price * 100
        
        analysis = Text()
        analysis.append("📍 Your Position\n", style="bold")
        analysis.append(f"Entry: $198.20\n")
        analysis.append(f"Current: ${current:.2f}\n")
        
        pnl_color = "green" if pnl > 0 else "red"
        analysis.append(f"P&L: [{pnl_color}]{pnl:+.2f}%[/{pnl_color}]\n\n")
        
        analysis.append("📊 Technical Analysis\n", style="bold")
        analysis.append(f"RSI: {sol_data['rsi']:.1f}\n")
        analysis.append(f"Trend: {sol_data['trend']}\n")
        analysis.append(f"Support: ${sol_data['support']:.2f}\n")
        analysis.append(f"Resistance: ${sol_data['resistance']:.2f}\n\n")
        
        # Recommendation
        analysis.append("💡 Recommendation: ", style="bold")
        if current < 185:
            analysis.append("Consider adding to position\n", style="green")
        elif current > 210:
            analysis.append("Consider taking partial profits\n", style="yellow")
        else:
            analysis.append("Hold position, monitor levels\n", style="cyan")
        
        return Panel(analysis, title="SOL Position Analysis", border_style="green")
    
    async def run_analysis(self):
        """Run continuous analysis"""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main", size=20),
            Layout(name="bottom", ratio=1)
        )
        
        with Live(layout, refresh_per_second=1, console=console):
            while True:
                try:
                    # Fetch data for all symbols
                    tasks = [self.get_ticker_data(symbol) for symbol in self.symbols]
                    data_points = await asyncio.gather(*tasks)
                    
                    # Update header
                    header_text = Text()
                    header_text.append("🚀 CRYPTO MARKET ANALYZER", style="bold cyan")
                    header_text.append(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", style="dim")
                    layout["header"].update(Panel(header_text, border_style="cyan"))
                    
                    # Update main table
                    table = self.create_analysis_table(data_points)
                    layout["main"].update(table)
                    
                    # Update bottom panels
                    bottom_layout = Layout()
                    bottom_layout.split_row(
                        Layout(self.create_summary_panel(data_points)),
                        Layout(self.create_sol_analysis(next((d for d in data_points if d and d['symbol'] == 'SOL'), None)))
                    )
                    layout["bottom"].update(bottom_layout)
                    
                    await asyncio.sleep(10)  # Update every 10 seconds
                    
                except Exception as e:
                    console.print(f"[red]Analysis error: {e}[/red]")
                    await asyncio.sleep(5)

async def main():
    analyzer = MarketAnalyzer()
    await analyzer.run_analysis()

if __name__ == "__main__":
    console.print("[bold cyan]🚀 Starting Live Market Analysis...[/bold cyan]")
    console.print("[dim]Press Ctrl+C to stop[/dim]\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Analysis stopped[/yellow]")