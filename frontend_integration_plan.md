# 🎨 PLAN DE INTEGRACIÓN FRONTEND - TRADING SYSTEM

## 📋 Información Necesaria

Para proceder con la instrumentación, necesito saber:

### 1. **Sobre tus diseños en Lovable:**
- ¿Qué componentes ya tienes diseñados?
- ¿Tienes un dashboard principal?
- ¿Visualización de señales de los filósofos?
- ¿Gráficos de trading?
- ¿Panel de control de proyectos?

### 2. **Stack Frontend Actual:**
- Next.js (confirmado)
- ¿Qué librerías de UI usas? (Material-UI, Tailwind, Chakra?)
- ¿Librería de gráficos? (Chart.js, Recharts, TradingView?)
- ¿Estado global? (Redux, Zustand, Context?)

### 3. **Funcionalidades a Visualizar:**
- [ ] Dashboard principal con métricas
- [ ] Vista de filósofos y sus señales
- [ ] Gráficos de precios en tiempo real
- [ ] Historial de trades
- [ ] Panel de proyectos activos
- [ ] Configuración de parámetros
- [ ] Alertas y notificaciones

## 🚀 PLAN DE IMPLEMENTACIÓN

### FASE 1: Backend API (Django)
```python
# urls.py
urlpatterns = [
    path('api/dashboard/', DashboardView.as_view()),
    path('api/philosophers/', PhilosophersView.as_view()),
    path('api/signals/', SignalsView.as_view()),
    path('api/trades/', TradesView.as_view()),
    path('api/projects/', ProjectsView.as_view()),
    path('ws/trading/', TradingWebSocket.as_asgi()),
]
```

### FASE 2: Frontend Components (Next.js)
```typescript
// Componentes principales
/components
  /Dashboard
    - MetricsCard.tsx
    - PnLChart.tsx
    - ActivePositions.tsx
  /Philosophers
    - PhilosopherCard.tsx
    - SignalsList.tsx
    - ConsensusView.tsx
  /Trading
    - PriceChart.tsx
    - OrderBook.tsx
    - TradeExecutor.tsx
  /Projects
    - ProjectManager.tsx
    - PerformanceMetrics.tsx
```

### FASE 3: WebSocket para Tiempo Real
```javascript
// WebSocket connection
const ws = new WebSocket('ws://localhost:8000/ws/trading/');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // Actualizar UI con datos en tiempo real
  updatePrices(data.prices);
  updateSignals(data.signals);
  updatePositions(data.positions);
};
```

## 🎨 ESTRUCTURA RECOMENDADA

```
/frontend (Next.js)
├── /pages
│   ├── index.tsx          // Dashboard principal
│   ├── philosophers.tsx   // Vista de filósofos
│   ├── trading.tsx       // Panel de trading
│   └── projects.tsx      // Gestión de proyectos
├── /components
│   ├── /common
│   ├── /dashboard
│   ├── /philosophers
│   └── /trading
├── /hooks
│   ├── useWebSocket.ts
│   ├── useTradingData.ts
│   └── usePhilosophers.ts
├── /services
│   ├── api.ts
│   ├── websocket.ts
│   └── trading.ts
└── /styles
    └── globals.css
```

## 📊 COMPONENTES CLAVE A CREAR

### 1. Dashboard Principal
```tsx
// Dashboard con métricas en tiempo real
<Dashboard>
  <MetricsRow>
    <MetricCard title="P&L Diario" value={dailyPnl} />
    <MetricCard title="Win Rate" value={winRate} />
    <MetricCard title="Trades Hoy" value={tradesCount} />
    <MetricCard title="Capital" value={capital} />
  </MetricsRow>
  
  <ChartsRow>
    <PnLChart data={pnlHistory} />
    <PositionsChart data={positions} />
  </ChartsRow>
  
  <ActiveSignals signals={currentSignals} />
</Dashboard>
```

### 2. Panel de Filósofos
```tsx
// Vista de filósofos y consenso
<PhilosophersPanel>
  {philosophers.map(philosopher => (
    <PhilosopherCard
      key={philosopher.id}
      name={philosopher.name}
      signal={philosopher.currentSignal}
      confidence={philosopher.confidence}
      philosophy={philosopher.philosophy}
    />
  ))}
  
  <ConsensusView 
    agreements={consensusData}
    pendingSignals={pendingSignals}
  />
</PhilosophersPanel>
```

### 3. Trading View
```tsx
// Panel de trading con gráficos
<TradingView>
  <TradingChart 
    symbol={selectedSymbol}
    indicators={indicators}
    signals={signals}
  />
  
  <OrderPanel>
    <OrderForm />
    <ActiveOrders orders={orders} />
  </OrderPanel>
  
  <MarketDepth symbol={selectedSymbol} />
</TradingView>
```

## 🔧 PREGUNTAS PARA CONTINUAR

1. **¿Qué componentes ya tienes en Lovable?**
   - Compárteme screenshots o descripciones

2. **¿Prefieres empezar por?**
   - a) Backend API (Django)
   - b) Frontend components (Next.js)
   - c) WebSocket integration

3. **¿Qué librería de gráficos prefieres?**
   - a) Recharts (simple y React-friendly)
   - b) Chart.js (más opciones)
   - c) TradingView (profesional)
   - d) Otra

4. **¿Tienes algún diseño específico en mente?**
   - Dark mode / Light mode
   - Colores corporativos
   - Estilo (minimalista, dashboard trading pro, etc)

## 📝 SIGUIENTE PASO

Una vez que me compartas:
1. Los diseños de Lovable
2. Tus preferencias de las preguntas anteriores

Puedo crear:
- El código exacto del backend (Django views + serializers)
- Los componentes frontend (Next.js + TypeScript)
- La integración WebSocket
- Los hooks y servicios necesarios

¿Cómo quieres proceder? 🚀