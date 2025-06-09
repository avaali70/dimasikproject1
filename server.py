import socket
import threading
import struct
import json
import time
import asyncio
import websockets
import base64
import os
from db import Database, init_database

# Настройки сервера
HOST = '158.255.6.80'
VOICE_PORT = 23343
WS_PORT = 23345
BUFFER_SIZE = 1024

clients = {}  # {login: (conn, addr, channel_id)}
ws_clients = set()  # WebSocket-клиенты
speaking_clients = {}  # {login: channel_id}
channels = {}  # {channel_id: name}
db = None
loop = None  # Глобальный событийный цикл

def broadcast_audio(sender_login, audio_data, channel_id):
    for login, (conn, _, client_channel) in list(clients.items()):
        if login != sender_login and client_channel == channel_id:
            try:
                conn.sendall(audio_data)
            except:
                if login in clients:
                    del clients[login]
                    if login in speaking_clients:
                        del speaking_clients[login]
                    loop.call_soon_threadsafe(lambda: asyncio.ensure_future(broadcast_info()))

async def broadcast_info():
    info = {
        "type": "info",
        "payload": {
            "status": "Online",
            "count": len(clients),
            "logins": list(clients.keys()),
            "channels": channels,
            "app_count": len(ws_clients),
            "voice_count": len(clients),
            "speaking": speaking_clients
        }
    }
    data = json.dumps(info)
    for ws in list(ws_clients):
        try:
            await ws.send(data)
        except:
            ws_clients.discard(ws)

async def periodic_broadcast():
    while True:
        await broadcast_info()
        await asyncio.sleep(0.5)

def handle_voice_client(conn, addr):
    global loop
    login = None
    channel_id = None
    try:
        data = conn.recv(1032)
        if len(data) != 1032:
            return
        login, channel_id = struct.unpack('!1024sQ', data)
        login = login.decode('utf-8').rstrip('\x00')
        if login in clients:
            conn.close()
            return
        clients[login] = (conn, addr, channel_id)
        loop.call_soon_threadsafe(lambda: asyncio.ensure_future(broadcast_info()))

        last_activity = time.time()
        while True:
            data = conn.recv(BUFFER_SIZE)
            if not data:
                break
            current_time = time.time()
            if len(data) > 100:
                speaking_clients[login] = channel_id
                last_activity = current_time
            elif current_time - last_activity > 1.0:
                speaking_clients.pop(login, None)
            broadcast_audio(login, data, channel_id)
            loop.call_soon_threadsafe(lambda: asyncio.ensure_future(broadcast_info()))
    finally:
        if login in clients:
            del clients[login]
            speaking_clients.pop(login, None)
            loop.call_soon_threadsafe(lambda: asyncio.ensure_future(broadcast_info()))
        conn.close()

async def handle_ws_client(websocket, path):
    try:
        ws_clients.add(websocket)
        await broadcast_info()
        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                #print(f"Received WebSocket message: {data}")  # Для отладки
                action = data.get("action")
                if action == "create_channel":
                    channel_name = data.get("name")
                    if channel_name:
                        await db.add_channel(channel_name)
                        channel_list = await db.get_channels()
                        channels.clear()
                        for chan_id, name in channel_list:
                            channels[chan_id] = name
                        await broadcast_info()
                elif action == "login":
                    login = data.get("login")
                    password = data.get("password")
                    user_data = await db.authenticate_user(login, password)
                    if user_data:
                        session_token = data.get("session_token")
                        if not session_token:
                            import secrets
                            session_token = secrets.token_hex(32)
                        await db.update_token(login, session_token)
                        # Читаем файл аватара и кодируем в base64
                        avatar_path = user_data["avatar_path"]
                        avatar_data = ""
                        try:
                            with open(avatar_path, "rb") as f:
                                avatar_data = base64.b64encode(f.read()).decode('utf-8')
                        except Exception as e:
                            print(f"Failed to load avatar for {login}: {str(e)}")
                        response = {
                            "status": "success",
                            "login": login,
                            "avatar_data": avatar_data,
                            "session_token": session_token
                        }
                    else:
                        response = {"status": "failed", "error": "Invalid credentials"}
                    print(f"Sending login response: {response}")  # Для отладки
                    await websocket.send(json.dumps(response))
                elif action == "verify_token":
                    login = data.get("login")
                    session_token = data.get("session_token")
                    print(f"Processing verify_token for {login}, session_token={session_token}")  # Для отладки
                    user_data = await db.verify_token(login, session_token)
                    if user_data:
                        # Читаем файл аватара и кодируем в base64
                        avatar_path = user_data["avatar_path"]  # Доступ через индекс словаря
                        avatar_data = ""
                        try:
                            with open(avatar_path, "rb") as f:
                                avatar_data = base64.b64encode(f.read()).decode('utf-8')
                        except Exception as e:
                            print(f"Failed to load avatar for {login}: {str(e)}")
                        response = {
                            "status": "success",
                            "login": login,
                            "avatar_data": avatar_data
                        }
                    else:
                        response = {"status": "failed", "error": "Invalid login or token"}
                    print(f"Sending verify_token response: {response}")  # Для отладки
                    await websocket.send(json.dumps(response))
            except json.JSONDecodeError:
                continue
            except websockets.exceptions.ConnectionClosed:
                break
    except Exception as e:
        print(f"WebSocket error: {str(e)}")
    finally:
        ws_clients.discard(websocket)
        await broadcast_info()

async def start_ws_server():
    server = await websockets.serve(
        handle_ws_client,
        HOST,
        WS_PORT,
        ping_interval=20,
        ping_timeout=60,
        close_timeout=10
    )
    await server.wait_closed()

async def init_server():
    global db, channels
    db = await init_database()
    channel_list = await db.get_channels()
    for chan_id, name in channel_list:
        channels[chan_id] = name

def start_voice_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, VOICE_PORT))
    server.listen(5)
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_voice_client, args=(conn, addr), daemon=True).start()

def main():
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_server())
    asyncio.ensure_future(start_ws_server())
    asyncio.ensure_future(periodic_broadcast())
    threading.Thread(target=start_voice_server, daemon=True).start()
    loop.run_forever()

if __name__ == "__main__":
    main()