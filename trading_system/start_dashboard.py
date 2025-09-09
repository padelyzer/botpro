#!/usr/bin/env python3
"""
Crypto Operations Center Launcher
Starts the professional web dashboard
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    print("🚀 Starting Crypto Operations Center...")
    
    # Change to dashboard directory
    dashboard_dir = Path(__file__).parent / "dashboard" / "api"
    os.chdir(dashboard_dir)
    
    print(f"📁 Working directory: {dashboard_dir}")
    print("🌐 Dashboard will be available at: http://localhost:8081")
    print("📊 Features available:")
    print("   • Real-time BTC/SOL monitoring")
    print("   • Entry signal alerts")
    print("   • Wait strategy analysis") 
    print("   • BTC/SOL correlation tracking")
    print("   • Virtual terminals")
    print("   • Live charts and data")
    print("\n⚡ Press Ctrl+C to stop the server\n")
    
    try:
        # Start the FastAPI server
        subprocess.run([
            sys.executable, "main.py"
        ])
    except KeyboardInterrupt:
        print("\n\n⏹️ Crypto Operations Center stopped")
    except Exception as e:
        print(f"\n❌ Error starting dashboard: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())