#!/bin/bash

# Deploy Hybrid Trading System to Fly.io
# This script deploys the backend with automatic signal generation

echo "🚀 Deploying BotPhia Hybrid Trading System to Fly.io"
echo "=================================================="

# Check if fly CLI is installed
if ! command -v flyctl &> /dev/null; then
    echo "❌ Error: flyctl CLI not found. Please install it first."
    echo "Visit: https://fly.io/docs/hands-on/install-flyctl/"
    exit 1
fi

# App name - use existing app
APP_NAME="botphia-api"

echo "📦 Building and deploying to Fly.io..."

# Deploy with the hybrid Dockerfile
flyctl deploy \
    --app $APP_NAME \
    --dockerfile Dockerfile.hybrid \
    --strategy rolling

if [ $? -eq 0 ]; then
    echo "✅ Deployment successful!"
    
    echo ""
    echo "📊 Setting environment variables..."
    
    # Set secrets (only if not already set)
    echo "Setting demo mode secrets..."
    flyctl secrets set \
        BINANCE_API_KEY="demo" \
        BINANCE_SECRET_KEY="demo" \
        JWT_SECRET_KEY="botphia_secure_jwt_key_2025_change_in_production" \
        TRADING_MODE="demo" \
        SIGNAL_SCAN_INTERVAL="30" \
        AUTO_TRADE="false" \
        DATABASE_PATH="/app/data/trading_bot.db" \
        --app $APP_NAME
    
    echo ""
    echo "🔍 Checking app status..."
    flyctl status --app $APP_NAME
    
    echo ""
    echo "📋 Checking logs..."
    flyctl logs --app $APP_NAME --limit 20
    
    echo ""
    echo "✨ Deployment complete!"
    echo ""
    echo "📌 Important URLs:"
    echo "   Backend API: https://$APP_NAME.fly.dev"
    echo "   Health Check: https://$APP_NAME.fly.dev/health"
    echo "   WebSocket: wss://$APP_NAME.fly.dev/ws"
    echo ""
    echo "🔧 To upgrade to REAL trading mode later:"
    echo "   1. Get real Binance API keys"
    echo "   2. Run: flyctl secrets set BINANCE_API_KEY='your_key' BINANCE_SECRET_KEY='your_secret' TRADING_MODE='live' --app $APP_NAME"
    echo ""
    echo "📊 Monitor logs:"
    echo "   flyctl logs --app $APP_NAME"
    echo ""
else
    echo "❌ Deployment failed. Check the error messages above."
    exit 1
fi