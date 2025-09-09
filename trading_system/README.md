# 🚀 Professional Trading System v2.0

Advanced crypto trading tools with AI-powered analysis, real-time monitoring, and intelligent alert systems.

## ✨ Features

### 🔍 Real-Time Monitoring
- **Price Tracking**: BTC/SOL price monitoring with correlation analysis
- **Alert System**: Audio/visual alerts for entry/exit signals  
- **Liquidation Monitoring**: Track liquidation levels and risk
- **Market Sentiment**: Real-time sentiment analysis across major cryptos

### 📊 Advanced Analysis
- **Technical Analysis**: RSI, MACD, Moving Averages
- **Historical Patterns**: Compare current market to past crashes (2018, 2022)
- **Correlation Analysis**: BTC/SOL relationship tracking
- **Entry Scoring**: AI-powered entry signal scoring (0-100)

### 🎯 Strategic Tools
- **Wait Strategy**: Monitor for optimal entry conditions
- **DCA Planning**: Dollar-cost averaging strategies
- **Risk Management**: Position sizing with Kelly Criterion
- **Recovery Analysis**: Options for managing losing positions

### 🚨 Intelligent Alerts
- **Entry Signals**: Alerts when score ≥60 and price targets hit
- **Liquidation Warnings**: Early warnings before liquidation risk
- **Market Changes**: Notifications for significant market movements
- **Multi-Channel**: Terminal, sound, macOS notifications

## 🚀 Quick Start

### Installation
```bash
cd trading_system
pip3 install -r requirements.txt
```

### Usage
```bash
# Start the main controller
python3 main.py
```

### Menu System
```
🚀 PROFESSIONAL TRADING SYSTEM v2.0
========================================

1. 🔍 Monitoring System
   ├── Price Monitor (BTC/SOL)
   ├── Correlation Monitor  
   ├── Alert System
   └── All Monitors

2. 📊 Analysis Tools
   ├── Current Market Check
   ├── BTC/SOL Correlation
   ├── Technical Analysis
   └── Historical Patterns

3. ⚙️ Configuration
   ├── Alert Settings
   ├── Position Targets
   └── System Preferences

4. 📱 Dashboard & API
5. 📈 Current Status
6. 🔧 System Utilities
```

## 📁 Project Structure

```
trading_system/
├── core/                   # Core system modules
│   ├── config.py          # Configuration management
│   ├── market_data.py     # Market data fetching
│   └── alerts.py          # Alert system
├── monitors/              # Monitoring modules
├── strategies/            # Trading strategies  
├── analysis/              # Analysis tools
├── api/                   # API servers
├── dashboard/             # Web interface
├── utils/                 # Utilities
├── main.py               # 🎯 Main entry point
├── config.yaml           # Configuration file
└── requirements.txt      # Dependencies
```

## ⚙️ Configuration

Edit `config.yaml` to customize:

```yaml
# Trading targets
targets:
  sol:
    buy_zones:
      - price: 180
        position_size: 60
        priority: "primary"
      - price: 175  
        position_size: 80
        priority: "panic"

# Alert settings
alerts:
  sound_enabled: true
  min_score_threshold: 60
  
# Monitoring
monitoring:
  refresh_interval: 30
```

## 🎯 Key Features

### Entry Signal Scoring
The system calculates entry scores (0-100) based on:
- **Price Levels** (30 pts): SOL at target zones
- **BTC Strength** (25 pts): BTC recovery signals
- **Technical** (20 pts): RSI oversold conditions
- **Volume** (15 pts): High volume confirmation
- **Correlation** (10 pts): BTC/SOL relationship

### Alert Levels
- **Score 70+**: 🚨 CRITICAL - Strong buy signal
- **Score 60-69**: ⚠️ WARNING - Moderate signal  
- **Score 50-59**: ℹ️ INFO - Weak signal
- **Score <50**: 💤 Wait for better conditions

### Risk Management
- **Liquidation Monitoring**: Real-time distance tracking
- **Position Sizing**: Kelly Criterion calculations
- **Stop Loss**: Intelligent stop placement
- **Recovery Options**: Multiple exit strategies

## 🔧 Advanced Usage

### Start Specific Monitors
```bash
# Individual components (legacy)
python3 ../sol_entry_alert_monitor.py      # Entry alerts
python3 ../wait_strategy_monitor.py        # Wait strategy
python3 ../btc_sol_correlation_monitor.py  # Correlation
```

### API Access
The system includes REST API endpoints for external integration:
- Market data endpoints
- Alert configuration
- Real-time WebSocket feeds

## 📊 Supported Markets

- **Primary**: BTC/USDT, SOL/USDT
- **Secondary**: ETH, BNB, ADA, XRP
- **Data Source**: Binance API
- **Update Frequency**: Real-time (30s intervals)

## 🚨 Safety Features

- **Liquidation Warnings**: Early alerts before danger
- **Cooldown Periods**: Prevent alert spam
- **Error Handling**: Graceful failure recovery  
- **Data Validation**: Input sanitization
- **Process Management**: Clean startup/shutdown

## 🤝 Contributing

This is a personal trading system. Feel free to adapt for your own use.

## ⚠️ Disclaimer

This software is for educational purposes. Trading cryptocurrencies involves risk. Always do your own research and never invest more than you can afford to lose.

## 📝 License

MIT License - Use at your own risk

---

**🎯 Ready to start trading smarter? Run `python3 main.py` to begin!**