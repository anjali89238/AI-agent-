"""Entry point: `python run.py`

Set RELOAD=1 to auto-restart on file changes (dev mode).
"""
import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=os.getenv("RELOAD", "").lower() in {"1", "true", "yes"},
    )