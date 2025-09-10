#!/usr/bin/env python3
"""
REDIRECT TO APP.PY - This file exists only for backward compatibility
"""

# Import the FastAPI app explicitly
from app import app

# This ensures uvicorn can find the app
__all__ = ['app']

print("🔄 REDIRECTING: web_api.py -> app.py")
print("✅ Using app.py v4.0.0 with real signals")

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)