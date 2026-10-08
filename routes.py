import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from ai_predictor import AIPredictor
from crypto_service import CryptoService
from pattern_analyzer import PatternAnalyzer

BASE_DIR = Path(__file__).resolve().parent

# One shared instance, so the cache is shared with the websocket updates in app.py
crypto_service = CryptoService()
ai_predictor = AIPredictor()
pattern_analyzer = PatternAnalyzer()


def setup_routes(app: FastAPI):
    templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

    # Pages (new Starlette signature: request first)
    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        return templates.TemplateResponse(request, "dashboard.html")

    @app.get("/predictions", response_class=HTMLResponse)
    async def predictions(request: Request):
        return templates.TemplateResponse(request, "predictions.html")

    @app.get("/patterns", response_class=HTMLResponse)
    async def patterns(request: Request):
        return templates.TemplateResponse(request, "patterns.html")

    @app.get("/defi", response_class=HTMLResponse)
    async def defi(request: Request):
        return templates.TemplateResponse(request, "defi.html")

    # API endpoints are plain `def` on purpose: they call blocking code
    # (requests, scikit-learn), and FastAPI runs `def` endpoints in a thread pool
    # so they don't freeze the server.
    @app.get("/api/market-data")
    def get_market_data():
        try:
            return crypto_service.get_market_overview()
        except Exception as e:
            logging.error(f"Error fetching market data: {e}")
            raise HTTPException(status_code=502, detail="Failed to fetch market data")

    @app.get("/api/coin-price/{coin_id}")
    def get_coin_price(coin_id: str, days: int = Query(default=7, ge=1, le=365)):
        try:
            return crypto_service.get_coin_history(coin_id, days)
        except Exception as e:
            logging.error(f"Error fetching coin price data: {e}")
            raise HTTPException(status_code=502, detail="Failed to fetch coin price data")

    @app.get("/api/predictions/{coin_id}")
    def get_predictions(coin_id: str):
        try:
            history = crypto_service.get_coin_history(coin_id, 7)
            result = ai_predictor.predict_price(history)
            if isinstance(result, dict):
                result["is_mock"] = bool(history.get("is_mock"))
                if result["is_mock"]:
                    result["warning"] = "Live data unavailable; prediction based on simulated data."
            return result
        except Exception as e:
            logging.exception(f"Error generating predictions: {e}")
            raise HTTPException(status_code=500, detail="Failed to generate predictions")

    @app.get("/api/patterns/{coin_id}")
    def get_patterns(coin_id: str):
        try:
            history = crypto_service.get_coin_history(coin_id, 14)
            result = pattern_analyzer.analyze_patterns(history)
            if isinstance(result, dict):
                result["is_mock"] = bool(history.get("is_mock"))
                if result["is_mock"]:
                    result["warning"] = "Live data unavailable; analysis based on simulated data."
            return result
        except Exception as e:
            logging.exception(f"Error analyzing patterns: {e}")
            raise HTTPException(status_code=500, detail="Failed to analyze patterns")

    @app.get("/api/defi-protocols")
    def get_defi_protocols():
        try:
            return crypto_service.get_defi_protocols()
        except Exception as e:
            logging.error(f"Error fetching DeFi data: {e}")
            raise HTTPException(status_code=502, detail="Failed to fetch DeFi protocol data")

    @app.get("/api/trending")
    def get_trending():
        try:
            return crypto_service.get_trending_coins()
        except Exception as e:
            logging.error(f"Error fetching trending data: {e}")
            raise HTTPException(status_code=502, detail="Failed to fetch trending data")
