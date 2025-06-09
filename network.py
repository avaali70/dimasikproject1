import asyncio
import websockets
import json
from PyQt5.QtCore import pyqtSignal, QObject

# Настройки сети
HOST = '158.255.6.80'
WS_PORT = 23345

class NetworkHandler(QObject):
    update_info = pyqtSignal(dict)
    update_status = pyqtSignal(str)
    disconnect_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.ws = None
        self.running = True
        self.loop = asyncio.get_event_loop() if asyncio.get_event_loop().is_running() else asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def start_websocket(self):
        import threading
        threading.Thread(target=self.run_websocket, daemon=True).start()

    def run_websocket(self):
        self.loop.run_until_complete(self.websocket_handler())

    async def websocket_handler(self):
        uri = f"ws://{HOST}:{WS_PORT}"
        while self.running:
            try:
                async with websockets.connect(uri, ping_interval=20, ping_timeout=60, close_timeout=10) as ws:
                    self.ws = ws
                    self.update_status.emit("Online")
                    while self.running:
                        try:
                            message = await ws.recv()
                            data = json.loads(message)
                            if data.get("type") == "info":
                                self.update_info.emit(data["payload"])
                            elif data.get("type") == "status":
                                self.update_status.emit(data["payload"])
                        except websockets.ConnectionClosed:
                            break
            except Exception as e:
                print(f"WebSocket handler error: {str(e)}")  # Для отладки
                self.update_status.emit("Offline")
                self.update_info.emit({'count': 0, 'logins': [], 'channels': {}, 'speaking': {}})
                self.ws = None
                await asyncio.sleep(3)

    async def send_action(self, action, **kwargs):
        try:
            if self.ws and hasattr(self.ws, 'open') and self.ws.open:
                await self.ws.send(json.dumps({"action": action, **kwargs}))
                return None
            return "WebSocket not connected"
        except Exception as e:
            return str(e)

    async def authenticate(self, login, password):
        for attempt in range(3):  # Пробуем 3 раза
            try:
                if not self.ws or not hasattr(self.ws, 'open') or not self.ws.open:
                    self.ws = await websockets.connect(f"ws://{HOST}:{WS_PORT}", ping_interval=20, ping_timeout=60, close_timeout=10)
                request = {"action": "login", "login": login, "password": password}
                print(f"Sending login request: {request}")  # Для отладки
                await self.ws.send(json.dumps(request))
                while True:
                    response = await asyncio.wait_for(self.ws.recv(), timeout=5)
                    data = json.loads(response)
                    print(f"Auth response candidate: {data}")  # Для отладки
                    if data.get("status") in ["success", "failed"]:
                        return data
            except asyncio.TimeoutError:
                print(f"Auth timeout (attempt {attempt + 1}/3): No valid response received")  # Для отладки
                if attempt < 2:
                    await asyncio.sleep(1)
                    continue
                return {"status": "failed", "error": "Timeout waiting for auth response"}
            except Exception as e:
                print(f"Auth error (attempt {attempt + 1}/3): {str(e)}")  # Для отладки
                if attempt < 2:
                    await asyncio.sleep(1)
                    continue
                return {"status": "failed", "error": str(e)}

    async def verify_token(self, login, session_token):
        for attempt in range(3):  # Пробуем 3 раза
            try:
                if not self.ws or not hasattr(self.ws, 'open') or not self.ws.open:
                    self.ws = await websockets.connect(f"ws://{HOST}:{WS_PORT}", ping_interval=20, ping_timeout=60, close_timeout=10)
                request = {"action": "verify_token", "login": login, "session_token": session_token}
                print(f"Sending verify_token request: {request}")  # Для отладки
                await self.ws.send(json.dumps(request))
                while True:
                    response = await asyncio.wait_for(self.ws.recv(), timeout=5)
                    data = json.loads(response)
                    #print(f"Verify token response candidate: {data}")  # Для отладки
                    if data.get("status") in ["success", "failed"]:
                        return data
            except asyncio.TimeoutError:
                print(f"Verify token timeout (attempt {attempt + 1}/3): No valid response received")  # Для отладки
                if attempt < 2:
                    await asyncio.sleep(1)
                    continue
                return {"status": "failed", "error": "Timeout waiting for verify_token response"}
            except Exception as e:
                print(f"Verify token error (attempt {attempt + 1}/3): {str(e)}")  # Для отладки
                if attempt < 2:
                    await asyncio.sleep(1)
                    continue
                return {"status": "failed", "error": str(e)}

    async def stop(self):
        self.running = False
        if self.ws and hasattr(self.ws, 'open') and self.ws.open:
            await self.ws.close()
        self.loop.stop()
        self.loop.close()