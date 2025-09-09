/**
 * Crypto Operations Center - Dashboard JavaScript
 * Professional Trading System Web Interface
 */

class CryptoOperationsCenter {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        this.activeTerminal = 'entry';
        this.lastUpdateTime = null;
        this.selectedPair = 'SOL';
        this.tradingPairs = ['BTC', 'SOL', 'ETH', 'AVAX', 'NEAR'];
        
        this.init();
    }

    async init() {
        console.log('🚀 Initializing Crypto Operations Center...');
        
        // Initialize UI components
        this.initializeUI();
        this.updateClock();
        
        // Load initial system status
        await this.loadSystemStatus();
        
        // Connect WebSocket for real-time data
        this.connectWebSocket();
        
        // Start periodic updates
        setInterval(() => this.updateClock(), 1000);
        setInterval(() => this.checkSystemHealth(), 30000);
        
        console.log('✅ Crypto Operations Center initialized');
    }

    initializeUI() {
        // Set up terminal tabs
        this.setupTerminalTabs();
        
        // Initialize terminal outputs
        this.initializeTerminals();
        
        // Set up console input
        this.setupConsoleInput();
        
        // Add keyboard shortcuts
        this.setupKeyboardShortcuts();
        
        // Set up trading pair cards
        this.setupPairCards();
    }
    
    setupPairCards() {
        // Add click handlers to pair cards
        const pairCards = document.querySelectorAll('.pair-card');
        pairCards.forEach(card => {
            card.addEventListener('click', () => {
                const symbol = card.dataset.symbol;
                this.selectPair(symbol);
            });
        });
    }
    
    selectPair(symbol) {
        // Update active state
        document.querySelectorAll('.pair-card').forEach(card => {
            card.classList.remove('active');
        });
        document.querySelector(`[data-symbol="${symbol}"]`).classList.add('active');
        
        this.selectedPair = symbol;
        console.log(`Selected trading pair: ${symbol}`);
        
        // Load data for selected pair
        this.loadPairAnalysis(symbol);
    }
    
    async loadPairAnalysis(symbol) {
        try {
            const response = await fetch(`/api/pairs/${symbol}/analysis`);
            if (response.ok) {
                const data = await response.json();
                this.updatePairDisplay(symbol, data);
            }
        } catch (error) {
            console.error(`Error loading ${symbol} analysis:`, error);
        }
    }

    setupTerminalTabs() {
        const tabs = document.querySelectorAll('.tab-btn');
        tabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                const terminalName = e.target.getAttribute('onclick').match(/'([^']+)'/)[1];
                this.switchTerminal(terminalName);
            });
        });
    }

    initializeTerminals() {
        const terminals = ['entry', 'wait', 'correlation', 'console'];
        terminals.forEach(terminal => {
            const output = document.getElementById(`terminal-${terminal}-output`);
            if (output) {
                this.addTerminalLine(terminal, 'System', `${terminal.toUpperCase()} terminal initialized`);
            }
        });
    }

    setupConsoleInput() {
        const consoleInput = document.getElementById('consoleInput');
        if (consoleInput) {
            consoleInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    const command = e.target.value.trim();
                    if (command) {
                        this.executeConsoleCommand(command);
                        e.target.value = '';
                    }
                }
            });
        }
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch(e.key) {
                    case '1':
                        e.preventDefault();
                        this.switchTerminal('entry');
                        break;
                    case '2':
                        e.preventDefault();
                        this.switchTerminal('wait');
                        break;
                    case '3':
                        e.preventDefault();
                        this.switchTerminal('correlation');
                        break;
                    case '4':
                        e.preventDefault();
                        this.switchTerminal('console');
                        break;
                }
            }
        });
    }

    updateClock() {
        const now = new Date();
        const timeString = now.toLocaleTimeString('en-US', { 
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
        
        const clockElement = document.getElementById('currentTime');
        if (clockElement) {
            clockElement.textContent = timeString;
        }
    }

    async loadSystemStatus() {
        try {
            const response = await fetch('/api/system/status');
            const status = await response.json();
            
            if (status.error) {
                this.showError('System Status', status.error);
                return;
            }
            
            this.updateSystemStatus(status);
            console.log('📊 System status loaded:', status);
            
        } catch (error) {
            console.error('❌ Failed to load system status:', error);
            this.showError('System Status', 'Failed to load system status');
        }
    }

    updateSystemStatus(status) {
        // Update system indicator
        const systemStatus = document.getElementById('systemStatus');
        const systemStatusText = document.getElementById('systemStatusText');
        
        if (systemStatus && systemStatusText) {
            systemStatus.style.color = status.system.status === 'online' ? '#00d4aa' : '#ff4757';
            systemStatusText.textContent = `System ${status.system.status} - ${status.system.version}`;
        }

        // Update market data
        if (status.market) {
            this.updateMarketData(status.market);
        }

        // Update position info
        if (status.position) {
            this.updatePositionInfo(status.position);
        }

        // Update monitor status
        if (status.monitors) {
            this.updateMonitorStatus(status.monitors);
        }
    }

    updateMarketData(market) {
        // Update ticker
        const btcPrice = document.getElementById('btcPrice');
        const solPrice = document.getElementById('solPrice');
        
        if (btcPrice && market.btc) {
            btcPrice.textContent = `$${market.btc.price.toLocaleString('en-US', {minimumFractionDigits: 2})}`;
        }
        
        if (solPrice && market.sol) {
            solPrice.textContent = `$${market.sol.price.toFixed(2)}`;
        }

        // Update main market panel
        const btcPriceMain = document.getElementById('btcPriceMain');
        const btcChange = document.getElementById('btcChange');
        const solPriceMain = document.getElementById('solPriceMain');
        const solChange = document.getElementById('solChange');

        if (btcPriceMain && market.btc) {
            // Format BTC price with commas for thousands
            const formattedPrice = market.btc.price.toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
            btcPriceMain.textContent = `$${formattedPrice}`;
        }

        if (btcChange && market.btc) {
            const change = market.btc.change || market.btc.change_24h || 0;
            btcChange.textContent = `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
            btcChange.className = `market-change ${change >= 0 ? 'positive' : 'negative'}`;
        }

        if (solPriceMain && market.sol) {
            solPriceMain.textContent = `$${market.sol.price.toFixed(2)}`;
        }

        if (solChange && market.sol) {
            const change = market.sol.change || market.sol.change_24h || 0;
            solChange.textContent = `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
            solChange.className = `market-change ${change >= 0 ? 'positive' : 'negative'}`;
        }
    }

    updatePositionData(position) {
        // Update P&L display
        const currentPnL = document.getElementById('currentPnL');
        if (currentPnL && position.pnl_usd !== undefined) {
            const pnlText = `${position.pnl_usd >= 0 ? '+' : ''}$${position.pnl_usd} (${position.pnl_percent >= 0 ? '+' : ''}${position.pnl_percent}%)`;
            currentPnL.textContent = pnlText;
            currentPnL.style.color = position.pnl_usd >= 0 ? '#00d4aa' : '#ff4757';
        }

        // Update liquidation price
        const liquidationPrice = document.getElementById('liquidationPrice');
        if (liquidationPrice && position.liquidation_price) {
            liquidationPrice.textContent = `$${position.liquidation_price.toFixed(2)}`;
        }

        // Update distance to liquidation
        const distanceToLiq = document.getElementById('distanceToLiq');
        if (distanceToLiq && position.liq_distance_percent !== undefined) {
            distanceToLiq.textContent = `${position.liq_distance_percent.toFixed(1)}%`;
            
            // Color based on risk level
            if (position.liq_distance_percent > 30) {
                distanceToLiq.style.color = '#00d4aa';
            } else if (position.liq_distance_percent > 15) {
                distanceToLiq.style.color = '#ffa500';
            } else {
                distanceToLiq.style.color = '#ff4757';
            }
        }

        // Update risk status
        const riskStatus = document.getElementById('riskStatus');
        const riskAlert = document.getElementById('riskAlert');
        if (riskStatus && position.risk_status) {
            switch (position.risk_status) {
                case 'SAFE':
                    riskStatus.textContent = '✅ SAFE';
                    if (riskAlert) riskAlert.className = 'risk-alert';
                    break;
                case 'CAUTION':
                    riskStatus.textContent = '⚠️ CAUTION';
                    if (riskAlert) riskAlert.className = 'risk-alert warning';
                    break;
                case 'DANGER':
                    riskStatus.textContent = '🚨 DANGER!';
                    if (riskAlert) riskAlert.className = 'risk-alert danger';
                    break;
            }
        }

        // Add alert if we're in danger zone
        if (position.risk_level === 'high' && position.liq_distance_percent < 10) {
            this.addSystemAlert('critical', `⚠️ WARNING: Only ${position.liq_distance_percent.toFixed(1)}% to liquidation!`);
        }
    }

    updatePositionInfo(position) {
        // This is the old function - keeping for backward compatibility
        // The new updatePositionData handles real-time updates from WebSocket
        const liquidationPrice = document.getElementById('liquidationPrice');
        const distanceToLiq = document.getElementById('distanceToLiq');
        const currentPnL = document.getElementById('currentPnL');
        const riskStatus = document.getElementById('riskStatus');
        const riskAlert = document.getElementById('riskAlert');
        
        // Entry and position data
        const entryPrice = 198.20;
        const positionSize = 29.82; // SOL amount
        
        if (liquidationPrice) {
            liquidationPrice.textContent = `$${position.liquidation_price}`;
        }

        if (distanceToLiq && position.liquidation_price) {
            const solPrice = parseFloat(document.getElementById('solPrice')?.textContent?.replace('$', '') || '0');
            if (solPrice > 0) {
                const distance = ((solPrice - position.liquidation_price) / solPrice * 100).toFixed(1);
                distanceToLiq.textContent = `${distance}%`;
                
                // Update risk status based on distance
                if (distance > 20) {
                    distanceToLiq.style.color = '#00d4aa';
                    if (riskStatus) riskStatus.textContent = '✅ SAFE';
                    if (riskAlert) riskAlert.className = 'risk-alert';
                } else if (distance > 10) {
                    distanceToLiq.style.color = '#ffa500';
                    if (riskStatus) riskStatus.textContent = '⚠️ CAUTION';
                    if (riskAlert) riskAlert.className = 'risk-alert warning';
                } else {
                    distanceToLiq.style.color = '#ff4757';
                    if (riskStatus) riskStatus.textContent = '🚨 DANGER!';
                    if (riskAlert) riskAlert.className = 'risk-alert danger';
                }
                
                // Calculate P&L
                if (currentPnL) {
                    const pnlAmount = (solPrice - entryPrice) * positionSize;
                    const pnlPercent = ((solPrice - entryPrice) / entryPrice * 100);
                    currentPnL.textContent = `${pnlAmount >= 0 ? '+' : ''}$${pnlAmount.toFixed(2)} (${pnlPercent >= 0 ? '+' : ''}${pnlPercent.toFixed(1)}%)`;
                    currentPnL.style.color = pnlAmount >= 0 ? '#00d4aa' : '#ff4757';
                }
            }
        }
    }

    updateMonitorStatus(monitors) {
        Object.keys(monitors).forEach(monitorName => {
            const statusElement = document.getElementById(`status-${monitorName}`);
            if (statusElement) {
                const monitor = monitors[monitorName];
                statusElement.textContent = monitor.active ? 'Running' : monitor.status;
                statusElement.style.color = monitor.active ? '#00d4aa' : '#b0b0b0';
            }
        });
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        console.log('🔌 Connecting to WebSocket:', wsUrl);
        
        try {
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                console.log('✅ WebSocket connected');
                this.reconnectAttempts = 0;
                this.addSystemAlert('info', 'WebSocket connected - Real-time data active');
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.error('❌ WebSocket message parsing error:', error);
                }
            };
            
            this.ws.onclose = () => {
                console.log('❌ WebSocket disconnected');
                this.addSystemAlert('warning', 'WebSocket disconnected - Attempting reconnection...');
                this.attemptReconnection();
            };
            
            this.ws.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
                this.addSystemAlert('danger', 'WebSocket connection error');
            };
            
        } catch (error) {
            console.error('❌ WebSocket connection failed:', error);
            this.addSystemAlert('danger', 'Failed to establish WebSocket connection');
        }
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'realtime_update':
                this.handleRealtimeUpdate(data);
                break;
            case 'system_health':
                this.handleSystemHealth(data);
                break;
            case 'monitor_output':
                this.handleMonitorOutput(data);
                break;
            case 'error':
                this.handleError(data);
                break;
            default:
                console.log('📨 Unknown WebSocket message:', data);
        }
        
        this.lastUpdateTime = new Date();
    }

    handleRealtimeUpdate(data) {
        // Update market data
        if (data.market) {
            this.updateMarketData(data.market);
        }

        // Update position data (P&L, risk, etc.)
        if (data.position) {
            this.updatePositionData(data.position);
        }

        // Update monitor data
        if (data.monitors) {
            this.updateMonitorData(data.monitors);
        }
    }

    updateMonitorData(monitors) {
        // Update entry alerts data
        if (monitors.entry_alerts && !monitors.entry_alerts.error) {
            const data = monitors.entry_alerts;
            
            // Update entry score
            if (data.analysis) {
                this.updateEntryScore(data.analysis);
                
                // Add terminal output
                if (data.analysis.alert_triggered) {
                    this.addTerminalLine('entry', 'ALERT', 
                        `🚨 ${data.analysis.action} - Score: ${data.analysis.entry_score}/100`);
                }
            }
        }

        // Update wait strategy data
        if (monitors.wait_strategy && !monitors.wait_strategy.error) {
            const data = monitors.wait_strategy;
            
            if (data.analysis && data.analysis.conditions_met) {
                this.addTerminalLine('wait', 'ACTION', 
                    `🎯 Conditions met! ${data.analysis.action_description}`);
            }
        }

        // Update correlation data
        if (monitors.correlation && !monitors.correlation.error) {
            const data = monitors.correlation;
            
            if (data.analysis) {
                this.updateCorrelationData(data.analysis);
            }
        }
    }

    updateEntryScore(analysis) {
        const entryScore = document.getElementById('entryScore');
        const scoreFill = document.getElementById('scoreFill');
        const scoreFactors = document.getElementById('scoreFactors');
        const actionValue = document.getElementById('actionValue');
        const decisionStatus = document.getElementById('decisionStatus');

        if (entryScore) {
            const score = analysis.entry_score || 0;
            entryScore.textContent = score;
            
            // Apply color classes based on score
            entryScore.classList.remove('low', 'medium', 'high');
            if (score >= 70) {
                entryScore.classList.add('high');
            } else if (score >= 50) {
                entryScore.classList.add('medium');
            } else {
                entryScore.classList.add('low');
            }
            
            // Add animation when score changes
            entryScore.style.animation = 'none';
            setTimeout(() => {
                entryScore.style.animation = 'glow 2s ease-in-out infinite alternate';
            }, 10);
        }
        
        // Update ACTION recommendation
        if (actionValue) {
            const score = analysis.entry_score || 0;
            const solPrice = parseFloat(document.getElementById('solPrice')?.textContent?.replace('$', '') || '0');
            
            if (score >= 70) {
                actionValue.textContent = 'BUY $60 NOW!';
                actionValue.className = 'action-value buy';
                if (decisionStatus) decisionStatus.textContent = '🚨 STRONG SIGNAL';
            } else if (score >= 60) {
                actionValue.textContent = 'BUY $40';
                actionValue.className = 'action-value buy';
                if (decisionStatus) decisionStatus.textContent = '⚠️ MODERATE SIGNAL';
            } else if (solPrice < 180) {
                actionValue.textContent = 'WAIT FOR BTC';
                actionValue.className = 'action-value wait';
                if (decisionStatus) decisionStatus.textContent = 'SOL at target, wait BTC recovery';
            } else {
                actionValue.textContent = 'WAIT';
                actionValue.className = 'action-value wait';
                if (decisionStatus) decisionStatus.textContent = `Waiting SOL <$180 (now $${solPrice.toFixed(2)})`;
            }
        }

        if (scoreFill) {
            const scorePercent = Math.min(100, Math.max(0, analysis.entry_score || 0));
            scoreFill.style.width = `${scorePercent}%`;
            
            // Change color based on score
            if (scorePercent >= 70) {
                scoreFill.style.background = 'linear-gradient(90deg, #00d4aa, #00ff88)';
            } else if (scorePercent >= 50) {
                scoreFill.style.background = 'linear-gradient(90deg, #ffa500, #ffcc00)';
            } else {
                scoreFill.style.background = 'linear-gradient(90deg, #ff4757, #ff6b7a)';
            }
        }

        if (scoreFactors && analysis.factors) {
            scoreFactors.innerHTML = analysis.factors
                .slice(0, 5)
                .map(factor => {
                    let icon = '🔸';
                    if (factor.includes('✅')) icon = '✅';
                    else if (factor.includes('🟡')) icon = '🟡';
                    else if (factor.includes('❌')) icon = '❌';
                    else if (factor.includes('🔥')) icon = '🔥';
                    
                    return `<div class="factor-item" style="animation: fadeIn 0.5s">${factor}</div>`;
                })
                .join('');
        }
    }

    updateCorrelationData(analysis) {
        const correlationValue = document.getElementById('correlationValue');
        const correlationTrend = document.getElementById('correlationTrend');
        const btcRsi = document.getElementById('btcRsi');
        const solRsi = document.getElementById('solRsi');

        if (correlationValue && analysis.correlation !== undefined) {
            correlationValue.textContent = analysis.correlation.toFixed(3);
        }

        if (correlationTrend && analysis.correlation_trend) {
            correlationTrend.textContent = analysis.correlation_trend;
        }

        if (btcRsi && analysis.btc_rsi !== undefined) {
            btcRsi.textContent = analysis.btc_rsi.toFixed(1);
        }

        if (solRsi && analysis.sol_rsi !== undefined) {
            solRsi.textContent = analysis.sol_rsi.toFixed(1);
        }
    }

    handleSystemHealth(data) {
        console.log('❤️ System health:', data);
    }

    handleMonitorOutput(data) {
        if (data.monitor && data.output) {
            this.addTerminalLine(data.monitor, 'OUTPUT', data.output);
        }
    }

    handleError(data) {
        console.error('❌ WebSocket error:', data);
        this.addSystemAlert('danger', `Error: ${data.message}`);
    }

    attemptReconnection() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('❌ Max reconnection attempts reached');
            this.addSystemAlert('danger', 'Connection lost - Please refresh the page');
            return;
        }

        this.reconnectAttempts++;
        console.log(`🔄 Reconnection attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);

        setTimeout(() => {
            this.connectWebSocket();
        }, this.reconnectDelay * this.reconnectAttempts);
    }

    checkSystemHealth() {
        if (this.lastUpdateTime) {
            const now = new Date();
            const timeSinceUpdate = now - this.lastUpdateTime;
            
            if (timeSinceUpdate > 30000) { // 30 seconds
                this.addSystemAlert('warning', 'No recent data updates - Connection may be unstable');
            }
        }
    }

    // Terminal Management
    switchTerminal(terminalName) {
        // Update active terminal
        this.activeTerminal = terminalName;

        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelector(`[onclick="switchTerminal('${terminalName}')"]`)?.classList.add('active');

        // Update terminal panels
        document.querySelectorAll('.terminal-panel').forEach(panel => panel.classList.remove('active'));
        document.getElementById(`terminal-${terminalName}`)?.classList.add('active');

        console.log(`🖥️ Switched to ${terminalName} terminal`);
    }

    addTerminalLine(terminal, type, message) {
        const output = document.getElementById(`terminal-${terminal}-output`);
        if (!output) return;

        const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false });
        const line = document.createElement('div');
        line.className = 'terminal-line';
        line.innerHTML = `
            <span class="timestamp">[${timestamp}]</span>
            <span class="message">[${type}] ${message}</span>
        `;

        output.appendChild(line);
        output.scrollTop = output.scrollHeight;

        // Limit terminal lines to prevent memory issues
        const lines = output.children;
        if (lines.length > 1000) {
            output.removeChild(lines[0]);
        }
    }

    clearTerminal(terminal) {
        const output = document.getElementById(`terminal-${terminal}-output`);
        if (output) {
            output.innerHTML = '';
            this.addTerminalLine(terminal, 'System', 'Terminal cleared');
        }
    }

    executeConsoleCommand(command) {
        this.addTerminalLine('console', 'USER', `$ ${command}`);
        
        // Basic console commands
        switch (command.toLowerCase()) {
            case 'help':
                this.addTerminalLine('console', 'HELP', 'Available commands: help, status, clear, monitors');
                break;
            case 'status':
                this.addTerminalLine('console', 'STATUS', `System: Online | Monitors: ${Object.keys(document.querySelectorAll('[id^="status-"]')).length} | Time: ${new Date().toISOString()}`);
                break;
            case 'clear':
                this.clearTerminal('console');
                break;
            case 'monitors':
                this.addTerminalLine('console', 'MONITORS', 'Entry Alerts | Wait Strategy | Correlation Analysis');
                break;
            default:
                this.addTerminalLine('console', 'ERROR', `Unknown command: ${command}. Type 'help' for available commands.`);
        }
    }

    // Monitor Control
    async startMonitor(monitorName) {
        try {
            const response = await fetch(`/api/monitors/${monitorName}/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                this.addSystemAlert('info', `${monitorName} started successfully`);
                this.addTerminalLine(monitorName.replace('_', ''), 'SYSTEM', 'Monitor started');
                
                // Update button states
                const statusElement = document.getElementById(`status-${monitorName}`);
                if (statusElement) {
                    statusElement.textContent = 'Running';
                    statusElement.style.color = '#00d4aa';
                }
            } else {
                this.addSystemAlert('danger', `Failed to start ${monitorName}: ${result.error}`);
            }
        } catch (error) {
            console.error(`❌ Failed to start monitor ${monitorName}:`, error);
            this.addSystemAlert('danger', `Error starting ${monitorName}`);
        }
    }

    async stopMonitor(monitorName) {
        try {
            const response = await fetch(`/api/monitors/${monitorName}/stop`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                this.addSystemAlert('info', `${monitorName} stopped successfully`);
                this.addTerminalLine(monitorName.replace('_', ''), 'SYSTEM', 'Monitor stopped');
                
                // Update button states
                const statusElement = document.getElementById(`status-${monitorName}`);
                if (statusElement) {
                    statusElement.textContent = 'Ready';
                    statusElement.style.color = '#b0b0b0';
                }
            } else {
                this.addSystemAlert('danger', `Failed to stop ${monitorName}: ${result.error}`);
            }
        } catch (error) {
            console.error(`❌ Failed to stop monitor ${monitorName}:`, error);
            this.addSystemAlert('danger', `Error stopping ${monitorName}`);
        }
    }

    // Alert System
    addSystemAlert(type, message) {
        const alertsContainer = document.getElementById('alertsContainer');
        if (!alertsContainer) return;

        const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false });
        const alert = document.createElement('div');
        alert.className = `alert-item ${type}`;
        alert.innerHTML = `
            <span class="alert-time">${timestamp}</span>
            <span class="alert-message">${message}</span>
        `;

        // Add to top of alerts
        alertsContainer.insertBefore(alert, alertsContainer.firstChild);

        // Limit alerts to prevent overflow
        const alerts = alertsContainer.children;
        if (alerts.length > 50) {
            alertsContainer.removeChild(alerts[alerts.length - 1]);
        }

        console.log(`📢 [${type.toUpperCase()}] ${message}`);
    }

    showError(title, message) {
        console.error(`❌ ${title}: ${message}`);
        this.addSystemAlert('danger', `${title}: ${message}`);
    }
}

// Global functions for HTML onclick handlers
function switchTerminal(terminalName) {
    window.operationsCenter.switchTerminal(terminalName);
}

function clearTerminal(terminal) {
    window.operationsCenter.clearTerminal(terminal);
}

function handleConsoleInput(event) {
    if (event.key === 'Enter') {
        const command = event.target.value.trim();
        if (command) {
            window.operationsCenter.executeConsoleCommand(command);
            event.target.value = '';
        }
    }
}

function startMonitor(monitorName) {
    window.operationsCenter.startMonitor(monitorName);
}

function stopMonitor(monitorName) {
    window.operationsCenter.stopMonitor(monitorName);
}

// Signal Validator Functions
async function validateSignal() {
    const signalInput = document.getElementById('signalInput');
    const signal = signalInput.value;
    
    if (!signal) {
        alert('Por favor ingresa una señal para validar');
        return;
    }
    
    try {
        const response = await fetch('/api/validate-signal', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                signal: signal,
                position: { size: 0 }
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            updateValidationResult(data.validation);
        }
    } catch (error) {
        console.error('Error validating signal:', error);
    }
}

function updateValidationResult(validation) {
    const resultElement = document.getElementById('validationResult');
    if (!resultElement) return;
    
    const scoreElement = resultElement.querySelector('.validation-score');
    const recElement = resultElement.querySelector('.validation-recommendation');
    
    if (scoreElement) {
        scoreElement.textContent = `Score: ${validation.score}/100`;
        scoreElement.style.color = validation.score > 50 ? '#00d4aa' : 
                                   validation.score > 20 ? '#ffa500' : '#ff4757';
    }
    
    if (recElement) {
        recElement.textContent = validation.recommendation;
        
        if (validation.warnings && validation.warnings.length > 0) {
            recElement.innerHTML += '<br><br>⚠️ Warnings:<br>' + 
                validation.warnings.join('<br>');
        }
        
        if (validation.errors && validation.errors.length > 0) {
            recElement.innerHTML += '<br><br>❌ Errors:<br>' + 
                validation.errors.join('<br>');
        }
    }
}

// Philosopher Analysis Functions
async function loadPhilosopherAnalysis() {
    try {
        const response = await fetch('/api/philosophers/analysis');
        const data = await response.json();
        
        if (data.status === 'success') {
            updatePhilosophersPanel(data.analysis);
        }
    } catch (error) {
        console.error('Error loading philosopher analysis:', error);
    }
}

function updatePhilosophersPanel(analysis) {
    const scoreElement = document.getElementById('philosopherScore');
    if (scoreElement && analysis.consensus) {
        scoreElement.textContent = `${analysis.consensus.average_score}/100`;
        scoreElement.style.color = analysis.consensus.average_score > 70 ? '#00d4aa' : 
                                   analysis.consensus.average_score > 40 ? '#ffa500' : '#ff4757';
    }
    
    const listElement = document.getElementById('philosopherList');
    if (listElement && analysis.philosophers) {
        listElement.innerHTML = '';
        for (const [key, phil] of Object.entries(analysis.philosophers)) {
            const item = document.createElement('div');
            item.className = 'philosopher-item';
            
            const name = document.createElement('span');
            name.className = 'phil-name';
            name.textContent = phil.philosopher;
            
            const opinion = document.createElement('span');
            opinion.className = `phil-opinion ${phil.action.toLowerCase()}`;
            opinion.textContent = `${phil.action} (${phil.score})`;
            
            item.appendChild(name);
            item.appendChild(opinion);
            listElement.appendChild(item);
        }
    }
    
    const recElement = document.getElementById('philRecommendation');
    if (recElement && analysis.recommended_action) {
        recElement.textContent = `${analysis.consensus.action} - ${analysis.recommended_action.notes}`;
    }
}

// Initialize the system when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.operationsCenter = new CryptoOperationsCenter();
    
    // Load philosopher analysis
    loadPhilosopherAnalysis();
    setInterval(loadPhilosopherAnalysis, 30000); // Every 30 seconds
});