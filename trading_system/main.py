#!/usr/bin/env python3
"""
Professional Trading System v2.0
Main Controller - Unified entry point for all trading tools

Usage: python3 main.py
"""

import os
import sys
import asyncio
import subprocess
from typing import Dict, List, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import config
from core.alerts import trading_alerts, AlertType
from core.market_data import market_fetcher, market_analyzer
from monitors import entry_alert_monitor, wait_strategy_monitor, correlation_monitor

class TradingSystemController:
    """Main controller for the trading system"""
    
    def __init__(self):
        self.running_processes: Dict[str, subprocess.Popen] = {}
        self.running_monitors: Dict[str, asyncio.Task] = {}
        self.system_started = False
        
    def show_header(self):
        """Display system header"""
        print('\033[2J\033[H')  # Clear screen
        print('='*70)
        print('🚀 PROFESSIONAL TRADING SYSTEM v2.0')
        print('   Advanced Crypto Trading Tools & Analysis')
        print('='*70)
        print(f'📅 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        print(f'⚙️ Configuration: {config.config_path}')
        print('='*70)
    
    def show_main_menu(self):
        """Display main menu"""
        print('\n📋 MAIN MENU:')
        print('='*40)
        print('1. 🔍 Monitoring System')
        print('2. 📊 Analysis Tools')
        print('3. ⚙️ Configuration')
        print('4. 📱 Dashboard & API')
        print('5. 📈 Current Status')
        print('6. 🔧 System Utilities')
        print('7. 📖 Help & Documentation')
        print('8. 🚪 Exit')
        print('='*40)
    
    def show_monitoring_menu(self):
        """Display monitoring submenu"""
        print('\n🔍 MONITORING SYSTEM:')
        print('='*40)
        print('🎯 INTEGRATED MONITORS (New):')
        print('1. 🚨 Entry Alert Monitor (Integrated)')
        print('2. ⏳ Wait Strategy Monitor (Integrated)')
        print('3. 🔗 Correlation Monitor (Integrated)')
        print('')
        print('📊 LEGACY MONITORS:')
        print('4. 📈 Price Monitor (Legacy)')
        print('5. 💧 Liquidity Monitor (Legacy)')
        print('')
        print('⚙️ CONTROL:')
        print('6. 🎯 All Integrated Monitors')
        print('7. ⏹️ Stop All Monitors')
        print('8. 📊 Monitor Status')
        print('9. ← Back to Main Menu')
    
    def show_analysis_menu(self):
        """Display analysis submenu"""
        print('\n📊 ANALYSIS TOOLS:')
        print('='*25)
        print('1. 📈 Current Market Check')
        print('2. 🔗 BTC/SOL Correlation')
        print('3. 📊 Technical Analysis')
        print('4. 🏛️ Historical Analysis')
        print('5. ⚖️ Risk Assessment')
        print('6. 💰 Position Review')
        print('7. 🎯 Entry Score Calculator')
        print('8. ← Back to Main Menu')
    
    async def run_market_check(self):
        """Run quick market analysis"""
        print('\n🔍 Running Market Analysis...')
        
        try:
            # Get market data
            btc_data, sol_data = await market_fetcher.get_btc_sol_data()
            market_overview = await market_fetcher.get_market_overview()
            
            if not btc_data or not sol_data:
                print('❌ Failed to fetch market data')
                return
            
            # Parse data
            btc_price = float(btc_data['lastPrice'])
            btc_change = float(btc_data['priceChangePercent'])
            sol_price = float(sol_data['lastPrice'])
            sol_change = float(sol_data['priceChangePercent'])
            
            # Analysis
            btc_analysis = market_analyzer.check_btc_strength(btc_data)
            market_sentiment = market_analyzer.get_market_sentiment(market_overview)
            
            # Display results
            print(f'\n📊 MARKET SNAPSHOT:')
            print(f'BTC: ${btc_price:,.2f} ({btc_change:+.2f}%) - {btc_analysis["status"].upper()}')
            print(f'SOL: ${sol_price:.2f} ({sol_change:+.2f}%)')
            print(f'Market: {market_sentiment["status"].upper()} ({market_sentiment["bearish_count"]}/{market_sentiment["total_coins"]} bearish)')
            
            # Position analysis
            current_liq = config.get('position.current_liquidation', 152.05)
            distance_to_liq = ((sol_price - current_liq) / sol_price) * 100
            print(f'Position: {distance_to_liq:.1f}% from liquidation')
            
        except Exception as e:
            print(f'❌ Error in market analysis: {e}')
        
        input('\nPress Enter to continue...')
    
    def start_monitor(self, monitor_name: str, script_path: str) -> bool:
        """Start a monitoring process"""
        try:
            if monitor_name in self.running_processes:
                print(f'⚠️ {monitor_name} is already running')
                return False
            
            # Build full path
            full_path = os.path.join('..', script_path)
            
            if not os.path.exists(full_path):
                print(f'❌ Script not found: {full_path}')
                return False
            
            # Start process
            process = subprocess.Popen([
                sys.executable, full_path
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.running_processes[monitor_name] = process
            print(f'✅ Started {monitor_name} (PID: {process.pid})')
            return True
            
        except Exception as e:
            print(f'❌ Failed to start {monitor_name}: {e}')
            return False
    
    def stop_monitor(self, monitor_name: str) -> bool:
        """Stop a monitoring process"""
        if monitor_name not in self.running_processes:
            print(f'⚠️ {monitor_name} is not running')
            return False
        
        try:
            process = self.running_processes[monitor_name]
            process.terminate()
            process.wait(timeout=5)
            del self.running_processes[monitor_name]
            print(f'✅ Stopped {monitor_name}')
            return True
        except Exception as e:
            print(f'❌ Failed to stop {monitor_name}: {e}')
            return False
    
    async def start_integrated_monitor(self, monitor_name: str, monitor_obj) -> bool:
        """Start an integrated monitoring module"""
        try:
            if monitor_name in self.running_monitors:
                print(f'⚠️ {monitor_name} is already running')
                return False
            
            # Start the monitor as an async task
            task = asyncio.create_task(monitor_obj.monitor_continuous())
            self.running_monitors[monitor_name] = task
            print(f'✅ Started {monitor_name} (Integrated)')
            return True
            
        except Exception as e:
            print(f'❌ Failed to start {monitor_name}: {e}')
            return False
    
    def stop_integrated_monitor(self, monitor_name: str) -> bool:
        """Stop an integrated monitoring module"""
        if monitor_name not in self.running_monitors:
            print(f'⚠️ {monitor_name} is not running')
            return False
        
        try:
            task = self.running_monitors[monitor_name]
            task.cancel()
            del self.running_monitors[monitor_name]
            print(f'✅ Stopped {monitor_name}')
            return True
        except Exception as e:
            print(f'❌ Failed to stop {monitor_name}: {e}')
            return False
    
    def stop_all_monitors(self):
        """Stop all running monitors (both legacy and integrated)"""
        total_stopped = 0
        
        # Stop legacy monitors
        if self.running_processes:
            stopped_count = 0
            for monitor_name in list(self.running_processes.keys()):
                if self.stop_monitor(monitor_name):
                    stopped_count += 1
            total_stopped += stopped_count
            
        # Stop integrated monitors
        if self.running_monitors:
            stopped_count = 0
            for monitor_name in list(self.running_monitors.keys()):
                if self.stop_integrated_monitor(monitor_name):
                    stopped_count += 1
            total_stopped += stopped_count
        
        if total_stopped == 0:
            print('ℹ️ No monitors are currently running')
        else:
            print(f'✅ Stopped {total_stopped} monitors')
    
    def show_monitor_status(self):
        """Show status of all monitors"""
        total_monitors = len(self.running_processes) + len(self.running_monitors)
        print(f'\n📊 MONITOR STATUS ({total_monitors} running):')
        print('='*50)
        
        # Show integrated monitors
        if self.running_monitors:
            print('\n🎯 INTEGRATED MONITORS:')
            for name, task in self.running_monitors.items():
                status = "🟢 Running" if not task.done() else "🔴 Stopped"
                print(f'  {name}: {status}')
        
        # Show legacy monitors
        if self.running_processes:
            print('\n📊 LEGACY MONITORS:')
            for name, process in self.running_processes.items():
                status = "🟢 Running" if process.poll() is None else "🔴 Stopped"
                pid = process.pid if process.poll() is None else "N/A"
                print(f'  {name}: {status} (PID: {pid})')
        
        if total_monitors == 0:
            print('No monitors currently running')
    
    def show_current_status(self):
        """Show comprehensive system status"""
        print('\n📈 CURRENT SYSTEM STATUS:')
        print('='*30)
        
        # System info
        print(f'System: Trading System v2.0')
        print(f'Time: {datetime.now().strftime("%H:%M:%S")}')
        print(f'Config: Loaded from {os.path.basename(config.config_path)}')
        
        # Monitor status
        print(f'\nMonitors: {len(self.running_processes)} active')
        if self.running_processes:
            for name in self.running_processes.keys():
                print(f'  • {name}')
        
        # Configuration summary
        sol_targets = config.get('targets.sol.buy_zones', [])
        print(f'\nSOL Targets: {len(sol_targets)} configured')
        for zone in sol_targets:
            print(f"  • ${zone['price']}: ${zone['position_size']} ({zone['priority']})")
        
        # Position info
        current_liq = config.get('position.current_liquidation')
        breakeven = config.get('position.breakeven_price')
        if current_liq and breakeven:
            print(f'\nPosition:')
            print(f'  • Liquidation: ${current_liq}')
            print(f'  • Breakeven: ${breakeven}')
    
    async def handle_monitoring_menu(self):
        """Handle monitoring submenu"""
        while True:
            self.show_monitoring_menu()
            choice = input('\nSelect option (1-9): ').strip()
            
            if choice == '1':
                print('\n🔄 Starting Entry Alert Monitor (Integrated)...')
                await self.start_integrated_monitor('Entry Alert Monitor', entry_alert_monitor)
                input('Press Enter to continue...')
                
            elif choice == '2':
                print('\n🔄 Starting Wait Strategy Monitor (Integrated)...')
                await self.start_integrated_monitor('Wait Strategy Monitor', wait_strategy_monitor)
                input('Press Enter to continue...')
                
            elif choice == '3':
                print('\n🔄 Starting Correlation Monitor (Integrated)...')
                await self.start_integrated_monitor('Correlation Monitor', correlation_monitor)
                input('Press Enter to continue...')
                
            elif choice == '4':
                print('\n🔄 Starting Price Monitor (Legacy)...')
                self.start_monitor('Price Monitor', 'current_market_check.py')
                input('Press Enter to continue...')
                
            elif choice == '5':
                print('\n🔄 Starting Liquidity Monitor (Legacy)...')
                self.start_monitor('Liquidity Monitor', 'liquidity_enhanced_system.py')
                input('Press Enter to continue...')
                
            elif choice == '6':
                print('\n🔄 Starting All Integrated Monitors...')
                monitors = [
                    ('Entry Alert Monitor', entry_alert_monitor),
                    ('Wait Strategy Monitor', wait_strategy_monitor),
                    ('Correlation Monitor', correlation_monitor)
                ]
                
                for name, monitor_obj in monitors:
                    await self.start_integrated_monitor(name, monitor_obj)
                
                input('Press Enter to continue...')
                
            elif choice == '7':
                print('\n⏹️ Stopping All Monitors...')
                self.stop_all_monitors()
                input('Press Enter to continue...')
                
            elif choice == '8':
                self.show_monitor_status()
                input('Press Enter to continue...')
                
            elif choice == '9':
                break
                
            else:
                print('❌ Invalid option')
                input('Press Enter to continue...')
    
    async def handle_analysis_menu(self):
        """Handle analysis submenu"""
        while True:
            self.show_analysis_menu()
            choice = input('\nSelect option (1-8): ').strip()
            
            if choice == '1':
                await self.run_market_check()
                
            elif choice == '2':
                print('\n🔗 Running Correlation Analysis...')
                # Run correlation analysis
                input('Press Enter to continue...')
                
            elif choice == '8':
                break
                
            else:
                print('❌ Feature coming soon...')
                input('Press Enter to continue...')
    
    def handle_configuration_menu(self):
        """Handle configuration menu"""
        print('\n⚙️ Configuration Menu:')
        print('1. View Current Config')
        print('2. Edit Alert Settings')
        print('3. Edit Position Targets')
        print('4. Reload Configuration')
        print('5. ← Back')
        
        choice = input('\nSelect option: ').strip()
        
        if choice == '1':
            print('\n📄 Current Configuration:')
            print('='*30)
            print(f"Alert threshold: {config.get('alerts.min_score_threshold', 60)}")
            print(f"Refresh interval: {config.get('monitoring.refresh_interval', 30)}s")
            print(f"Sound enabled: {config.get('alerts.sound_enabled', True)}")
            
            sol_zones = config.get('targets.sol.buy_zones', [])
            print(f"\nSOL Buy Zones:")
            for zone in sol_zones:
                print(f"  ${zone['price']}: ${zone['position_size']} ({zone['priority']})")
                
        elif choice == '4':
            print('\n🔄 Reloading configuration...')
            config.reload()
            print('✅ Configuration reloaded')
        
        input('\nPress Enter to continue...')
    
    async def run(self):
        """Main application loop"""
        trading_alerts.system_status("Trading System v2.0 started")
        
        while True:
            self.show_header()
            self.show_main_menu()
            
            choice = input('\nSelect option (1-8): ').strip()
            
            if choice == '1':
                await self.handle_monitoring_menu()
                
            elif choice == '2':
                await self.handle_analysis_menu()
                
            elif choice == '3':
                self.handle_configuration_menu()
                
            elif choice == '4':
                print('\n📱 Dashboard & API coming soon...')
                input('Press Enter to continue...')
                
            elif choice == '5':
                self.show_current_status()
                input('\nPress Enter to continue...')
                
            elif choice == '6':
                print('\n🔧 System Utilities coming soon...')
                input('Press Enter to continue...')
                
            elif choice == '7':
                print('\n📖 Help & Documentation coming soon...')
                input('Press Enter to continue...')
                
            elif choice == '8':
                print('\n👋 Shutting down...')
                self.stop_all_monitors()
                trading_alerts.system_status("Trading System stopped")
                break
                
            else:
                print('❌ Invalid option')
                input('Press Enter to continue...')

async def main():
    """Main entry point"""
    try:
        controller = TradingSystemController()
        await controller.run()
    except KeyboardInterrupt:
        print('\n\n⏹️ System interrupted by user')
    except Exception as e:
        print(f'\n❌ System error: {e}')
    finally:
        print('👋 Goodbye!')

if __name__ == "__main__":
    asyncio.run(main())