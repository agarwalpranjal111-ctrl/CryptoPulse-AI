# CryptoPulse-AI

Windows: double-click `run.bat`
Mac/Linux: `./run.sh`
Manual: `pip install -r requirements.txt` then `python run.py`

Open http://localhost:5000

Needs Python 3.9+ (3.11 recommended) and internet (CoinGecko API + CDN assets).
Optional: set COINGECKO_API_KEY (free demo key) to avoid rate limits.
Deploy (Render/Railway/etc.): start command `uvicorn app:app --host 0.0.0.0 --port $PORT`
