#!/usr/bin/env python3
"""
TRADING API V1.0
API REST para sistema de trading inteligente con estrategias adaptativas
Optimizado para deployment en Render (cuenta gratuita)
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import yfinance as yf
import pandas as pd
import numpy as np
import jwt
import os
from enum import Enum

# Import de estrategias
from strategies_v1 import (
    StrategyManager,
    Signal,
    RangingStrategyV1,
    BullishStrategyV1,
    BearishStrategyV1
)

# ============================================
# CONFIGURACIÓN
# ============================================

app = FastAPI(
    title="Trading System API",
    description="Sistema inteligente de trading con estrategias adaptativas v1.0",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS para permitir acceso desde frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración de seguridad
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 horas

security = HTTPBearer()

# ============================================
# MODELOS PYDANTIC
# ============================================

class MarketRegime(str, Enum):
    RANGING = "RANGING"
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    UNKNOWN = "UNKNOWN"

class SignalType(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"

class TimeFrame(str, Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"

class AnalysisRequest(BaseModel):
    symbol: str = Field(..., example="BTC-USD")
    timeframe: TimeFrame = Field(default=TimeFrame.H1)
    period: str = Field(default="7d", example="7d")
    capital: float = Field(default=1000, ge=100)

class SignalResponse(BaseModel):
    timestamp: datetime
    symbol: str
    type: SignalType
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    strategy_name: str
    strategy_version: str
    market_regime: MarketRegime
    risk_reward_ratio: float
    position_size: float
    metadata: Dict[str, Any]

class MarketAnalysis(BaseModel):
    symbol: str
    timestamp: datetime
    market_regime: MarketRegime
    regime_confidence: float
    current_price: float
    indicators: Dict[str, float]
    strategy_recommendation: str
    risk_level: str

class StrategyInfo(BaseModel):
    name: str
    version: str
    market_regime: MarketRegime
    strengths: List[str]
    weaknesses: List[str]
    optimal_conditions: List[str]
    risk_parameters: Dict[str, Any]

class BacktestRequest(BaseModel):
    symbol: str
    strategy: MarketRegime
    start_date: str = Field(example="2024-01-01")
    end_date: str = Field(example="2024-12-31")
    initial_capital: float = Field(default=1000)

class BacktestResult(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    total_return: float
    max_drawdown: float
    sharpe_ratio: float
    trades: List[Dict[str, Any]]

# ============================================
# AUTENTICACIÓN
# ============================================

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )

# ============================================
# SERVICIOS
# ============================================

class TradingService:
    def __init__(self):
        self.strategy_manager = StrategyManager()
    
    def get_market_data(self, symbol: str, period: str = "7d", interval: str = "1h") -> pd.DataFrame:
        """Obtiene datos de mercado de Yahoo Finance"""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            df.attrs['symbol'] = symbol
            return df
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error fetching data: {str(e)}")
    
    def analyze_market(self, symbol: str, timeframe: str = "1h", period: str = "7d") -> MarketAnalysis:
        """Analiza el mercado y detecta el régimen"""
        
        df = self.get_market_data(symbol, period, timeframe)
        
        if len(df) < 50:
            raise HTTPException(status_code=400, detail="Insufficient data for analysis")
        
        # Detectar régimen
        regime = self.strategy_manager.detect_market_regime(df)
        
        # Calcular indicadores
        df = self.strategy_manager.strategies['RANGING'].calculate_indicators(df)
        current = df.iloc[-1]
        
        # Determinar nivel de riesgo
        risk_level = self._calculate_risk_level(df, regime)
        
        return MarketAnalysis(
            symbol=symbol,
            timestamp=datetime.now(),
            market_regime=MarketRegime(regime),
            regime_confidence=0.75,  # TODO: Implementar cálculo real
            current_price=float(current['Close']),
            indicators={
                'RSI': float(current['RSI']) if not pd.isna(current['RSI']) else 50,
                'MACD': float(current['MACD']) if not pd.isna(current['MACD']) else 0,
                'BB_Position': float(current['BB_Position']) if 'BB_Position' in current and not pd.isna(current['BB_Position']) else 0.5,
                'Volume_Ratio': float(current['Volume_Ratio']) if not pd.isna(current['Volume_Ratio']) else 1,
                'ATR': float(current['ATR']) if not pd.isna(current['ATR']) else 0
            },
            strategy_recommendation=f"Use {regime} strategy",
            risk_level=risk_level
        )
    
    def _calculate_risk_level(self, df: pd.DataFrame, regime: str) -> str:
        """Calcula el nivel de riesgo actual"""
        
        current = df.iloc[-1]
        
        # Factores de riesgo
        risk_score = 0
        
        # Volatilidad
        if current['ATR'] > df['ATR'].rolling(50).mean().iloc[-1] * 1.5:
            risk_score += 2
        
        # RSI extremos
        if current['RSI'] > 70 or current['RSI'] < 30:
            risk_score += 1
        
        # Volumen anormal
        if current['Volume_Ratio'] > 2:
            risk_score += 1
        
        # Régimen
        if regime == "BEARISH":
            risk_score += 1
        
        if risk_score >= 3:
            return "HIGH"
        elif risk_score >= 2:
            return "MEDIUM"
        else:
            return "LOW"
    
    def generate_signal(self, symbol: str, timeframe: str = "1h", 
                       period: str = "7d", capital: float = 1000) -> Optional[SignalResponse]:
        """Genera señal de trading usando la estrategia óptima"""
        
        df = self.get_market_data(symbol, period, timeframe)
        
        if len(df) < 200:
            raise HTTPException(status_code=400, detail="Insufficient data for signal generation")
        
        signal = self.strategy_manager.generate_signal(df, capital)
        
        if signal:
            return SignalResponse(
                timestamp=signal.timestamp,
                symbol=signal.symbol,
                type=SignalType(signal.type),
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                take_profit=signal.take_profit,
                confidence=signal.confidence,
                strategy_name=signal.strategy_name,
                strategy_version=signal.strategy_version,
                market_regime=MarketRegime(signal.market_regime),
                risk_reward_ratio=signal.risk_reward_ratio,
                position_size=signal.position_size,
                metadata=signal.metadata
            )
        
        return None
    
    def run_backtest(self, symbol: str, strategy: str, start_date: str, 
                    end_date: str, initial_capital: float) -> BacktestResult:
        """Ejecuta backtest de una estrategia"""
        
        # TODO: Implementar backtest completo
        # Por ahora retornamos datos de ejemplo
        
        return BacktestResult(
            total_trades=100,
            winning_trades=45,
            losing_trades=55,
            win_rate=0.45,
            profit_factor=1.35,
            total_return=0.25,
            max_drawdown=-0.15,
            sharpe_ratio=1.2,
            trades=[]
        )

# Instancia global del servicio
trading_service = TradingService()

# ============================================
# ENDPOINTS
# ============================================

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Trading System API v1.0",
        "status": "online",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "strategies": "/api/v1/strategies",
            "analysis": "/api/v1/analysis",
            "signals": "/api/v1/signals"
        }
    }

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "version": "1.0.0"
    }

# ============================================
# ENDPOINTS DE ESTRATEGIAS
# ============================================

@app.get("/api/v1/strategies", response_model=List[StrategyInfo], tags=["Strategies"])
async def get_all_strategies():
    """Obtiene información de todas las estrategias disponibles"""
    
    strategies = []
    docs = trading_service.strategy_manager.get_all_documentation()
    
    for regime, strategy_doc in docs['strategies'].items():
        strategies.append(StrategyInfo(
            name=strategy_doc['name'],
            version=strategy_doc['version'],
            market_regime=MarketRegime(regime),
            strengths=strategy_doc['strengths'],
            weaknesses=strategy_doc['weaknesses'],
            optimal_conditions=strategy_doc['optimal_conditions'],
            risk_parameters=strategy_doc['risk_parameters']
        ))
    
    return strategies

@app.get("/api/v1/strategies/{regime}", response_model=StrategyInfo, tags=["Strategies"])
async def get_strategy(regime: MarketRegime):
    """Obtiene información de una estrategia específica"""
    
    if regime.value not in trading_service.strategy_manager.strategies:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    strategy = trading_service.strategy_manager.strategies[regime.value]
    doc = strategy.get_documentation()
    
    return StrategyInfo(
        name=doc['name'],
        version=doc['version'],
        market_regime=regime,
        strengths=doc['strengths'],
        weaknesses=doc['weaknesses'],
        optimal_conditions=doc['optimal_conditions'],
        risk_parameters=doc['risk_parameters']
    )

# ============================================
# ENDPOINTS DE ANÁLISIS
# ============================================

@app.post("/api/v1/analysis", response_model=MarketAnalysis, tags=["Analysis"])
async def analyze_market(request: AnalysisRequest):
    """Analiza el mercado actual y detecta el régimen"""
    
    return trading_service.analyze_market(
        symbol=request.symbol,
        timeframe=request.timeframe.value,
        period=request.period
    )

@app.post("/api/v1/signals", response_model=Optional[SignalResponse], tags=["Signals"])
async def generate_signal(request: AnalysisRequest):
    """Genera señal de trading basada en el análisis actual"""
    
    signal = trading_service.generate_signal(
        symbol=request.symbol,
        timeframe=request.timeframe.value,
        period=request.period,
        capital=request.capital
    )
    
    if not signal:
        raise HTTPException(
            status_code=204,
            detail="No signal available at this moment"
        )
    
    return signal

@app.get("/api/v1/signals/active", response_model=List[SignalResponse], tags=["Signals"])
async def get_active_signals():
    """Obtiene señales activas (placeholder para base de datos futura)"""
    
    # TODO: Implementar con base de datos
    return []

# ============================================
# ENDPOINTS DE BACKTEST
# ============================================

@app.post("/api/v1/backtest", response_model=BacktestResult, tags=["Backtest"])
async def run_backtest(request: BacktestRequest):
    """Ejecuta backtest de una estrategia"""
    
    return trading_service.run_backtest(
        symbol=request.symbol,
        strategy=request.strategy.value,
        start_date=request.start_date,
        end_date=request.end_date,
        initial_capital=request.initial_capital
    )

# ============================================
# ENDPOINTS DE AUTENTICACIÓN
# ============================================

@app.post("/api/v1/auth/token", tags=["Auth"])
async def login(api_key: str = "demo-key"):
    """Genera token de acceso (simplificado para demo)"""
    
    # En producción, validar api_key contra base de datos
    if api_key != "demo-key":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    access_token = create_access_token(data={"sub": "demo-user"})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

# ============================================
# ENDPOINTS PROTEGIDOS (EJEMPLO)
# ============================================

@app.get("/api/v1/protected", tags=["Protected"])
async def protected_route(current_user: dict = Depends(verify_token)):
    """Ejemplo de endpoint protegido"""
    return {"message": "This is a protected route", "user": current_user}

# ============================================
# MANEJO DE ERRORES
# ============================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return {
        "error": exc.detail,
        "status_code": exc.status_code,
        "timestamp": datetime.now()
    }

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return {
        "error": "Internal server error",
        "detail": str(exc),
        "status_code": 500,
        "timestamp": datetime.now()
    }

# ============================================
# STARTUP EVENTS
# ============================================

@app.on_event("startup")
async def startup_event():
    print("="*60)
    print("TRADING SYSTEM API V1.0")
    print("="*60)
    print("✅ Estrategias cargadas")
    print("✅ API lista en http://localhost:8000")
    print("📊 Documentación en http://localhost:8000/docs")
    print("="*60)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)