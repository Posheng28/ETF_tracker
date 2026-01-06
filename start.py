import uvicorn
import os
import sys

# Ensure backend directory is in path
sys.path.append(os.path.join(os.getcwd(), "backend"))

if __name__ == "__main__":
    print("Starting ETF server on port 8000...")
    # direct import to force load
    from backend.main import app
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
