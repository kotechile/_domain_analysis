#!/usr/bin/env python3
"""
Startup script for the Domain Analysis System backend
"""

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the app
from main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        timeout_keep_alive=1800,  # 30 minutes for very large file uploads (800K+ records)
        timeout_graceful_shutdown=30,  # 30 seconds for graceful shutdown
    )
