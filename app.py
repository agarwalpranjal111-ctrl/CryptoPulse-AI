import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from routes import setup_routes, crypto_service

logging.basicConfig(level=logging.INFO)


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logging.info("Client connected to WebSocket")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logging.info("Client disconnected from WebSocket")

    async def send(self, message: dict, websocket: WebSocket):
        await websocket.send_text(json.dumps(message))

    async def broadcast(self, message: dict):
        text = json.dumps(message)
        for connection in list(self.active_connections):
            try:
                await connection.send_text(text)
            except Exception:
                self.disconnect(connection)


manager = ConnectionManager()


async def background_price_updates():
    """Push market + trending data to all clients every 30 seconds."""
    while True:
        try:
            if manager.active_connections:
                # crypto_service is blocking, so run it in a worker thread
                market = await run_in_threadpool(crypto_service.get_market_overview)
                await manager.broadcast({"type": "price_update", "data": market})
                trending = await run_in_threadpool(crypto_service.get_trending_coins)
                await manager.broadcast({"type": "trending_update", "data": trending})
        except Exception as e:
            logging.error(f"Error in background price updates: {e}")
        await asyncio.sleep(30)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(background_price_updates())
    yield
    task.cancel()


app = FastAPI(title="Blockchain Analytics Dashboard", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,   # "*" origins + credentials is not allowed by browsers
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_routes(app)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    await manager.send({"type": "status", "data": {"msg": "Connected to live price feed"}}, websocket)
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue
            message_type = message.get("type")
            data = message.get("data") or {}

            if message_type == "subscribe_to_coin":
                coin_id = data.get("coin_id")
                if coin_id:
                    await manager.send({"type": "subscription_confirmed",
                                        "data": {"coin_id": coin_id}}, websocket)

            elif message_type == "get_live_price":
                coin_id = data.get("coin_id", "bitcoin")
                try:
                    market = await run_in_threadpool(crypto_service.get_market_overview)
                    coin = next((c for c in market.get("coins", []) if c["id"] == coin_id), None)
                    if coin:
                        await manager.send({"type": "live_price_response", "data": {
                            "coin_id": coin_id,
                            "price": coin["current_price"],
                            "change_24h": coin["price_change_percentage_24h"],
                            "timestamp": int(time.time() * 1000)}}, websocket)
                    else:
                        await manager.send({"type": "live_price_error",
                                            "data": {"error": f"Coin {coin_id} not found"}}, websocket)
                except Exception as e:
                    logging.error(f"Error getting live price: {e}")
                    await manager.send({"type": "live_price_error",
                                        "data": {"error": "Failed to fetch live price data"}}, websocket)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)
