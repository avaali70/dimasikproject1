import os
import json
import base64
from PyQt5.QtWidgets import QMainWindow, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QGridLayout, QDesktopWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QImage
from audio import AudioHandler
from network import NetworkHandler, HOST
from ui_dialogs import LoginDialog, CreateChannelDialog
from ui_window_manager import WindowManager
from styles import MAIN_STYLES

class VoiceChatClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.login = None
        self.avatar_data = None  # Храним base64-данные аватара
        self.audio_handler = AudioHandler()
        self.network_handler = NetworkHandler()
        self.last_info = {'count': 0, 'logins': [], 'channels': {}, 'speaking': {}}
        self.last_status = "Offline"
        self.current_channel = None
        self.channel_buttons = {}
        self.window_manager = WindowManager(self)

        if not self.try_auto_login():
            self.show_login_dialog()
        if not self.login:
            self.close()
            return
        self.init_ui()
        self.init_signals()
        self.network_handler.start_websocket()

    def try_auto_login(self):
        if os.path.exists("auth.json"):
            try:
                with open("auth.json", "r") as f:
                    auth_data = json.load(f)
                session_token = auth_data.get("session_token")
                login = auth_data.get("login")
                self.avatar_data = auth_data.get("avatar_data")
                if session_token and login:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(self.network_handler.verify_token(login, session_token))
                        #print(f"Auto-login response: {result}")  # Для отладки
                        if result.get("status") == "success":
                            self.login = login
                            self.session_token = session_token
                            self.avatar_data = result.get("avatar_data")  # Получаем base64-данные
                            return True
                        else:
                            print(f"Auto-login failed: {result.get('error', 'Invalid token')}")
                    finally:
                        loop.close()
            except Exception as e:
                print(f"Auto-login error: {str(e)}")  # Для отладки
        return False

    def show_login_dialog(self):
        dialog = LoginDialog(self, self.network_handler)
        dialog.exec_()

    def init_ui(self):
        self.setWindowTitle(f"Voice Chat Client: {self.login}")
        self.setStyleSheet(MAIN_STYLES)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 10, 20, 20)
        main_layout.setSpacing(15)

        self.title_bar = QWidget()
        self.title_bar.setObjectName("title_bar")
        self.title_bar.setFixedHeight(40)
        title_bar_layout = QHBoxLayout(self.title_bar)
        title_bar_layout.setContentsMargins(10, 2, 10, 2)
        title_bar_layout.setSpacing(5)

        avatar_label = QLabel()
        if self.avatar_data:
            try:
                # Декодируем base64-данные в изображение
                image_data = base64.b64decode(self.avatar_data)
                image = QImage.fromData(image_data)
                pixmap = QPixmap.fromImage(image)
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    avatar_label.setPixmap(pixmap)
                else:
                    pass
                    #print("Failed to load avatar from base64 data")  # Для отладки
            except Exception as e:
                pass
                #print(f"Failed to decode avatar: {str(e)}")  # Для отладки
        else:
            pass
            #print("No avatar data available")  # Для отладки

        title_bar_layout.addWidget(avatar_label)

        title_bar_layout.addWidget(QLabel(f"{self.login}"))
        title_bar_layout.addStretch()

        self.minimize_button = QPushButton("−")
        self.minimize_button.setFixedSize(40, 40)
        self.minimize_button.setObjectName("control_button")
        self.minimize_button.clicked.connect(self.showMinimized)
        title_bar_layout.addWidget(self.minimize_button)

        self.maximize_button = QPushButton("□")
        self.maximize_button.setFixedSize(40, 40)
        self.maximize_button.setObjectName("control_button")
        self.maximize_button.clicked.connect(self.window_manager.toggle_maximize)
        title_bar_layout.addWidget(self.maximize_button)

        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(40, 40)
        self.close_button.setObjectName("control_button")
        self.close_button.clicked.connect(self.window_manager.hide_to_tray)
        title_bar_layout.addWidget(self.close_button)

        main_layout.addWidget(self.title_bar)

        self.create_channel_button = QPushButton("+")
        self.create_channel_button.setFixedSize(30, 30)
        self.create_channel_button.clicked.connect(self.open_create_channel_dialog)
        main_layout.addWidget(self.create_channel_button, alignment=Qt.AlignLeft)

        self.status_label = QLabel("Server status: Checking...")
        main_layout.addWidget(self.status_label)

        self.clients_count_label = QLabel("Connected clients: -")
        main_layout.addWidget(self.clients_count_label)

        main_layout.addWidget(QLabel("Voice Channels:"))
        self.channels_container = QWidget()
        self.channels_layout = QGridLayout(self.channels_container)
        self.channels_layout.setSpacing(10)
        main_layout.addWidget(self.channels_container)

        self.extended_info_label = QLabel("Server Info:\nStatus: Checking...\nApps Running: -\nVoice Connected: -\nSpeaking: -")
        self.extended_info_label.setStyleSheet("background-color: #36393F; padding: 10px; border-radius: 5px;")
        main_layout.addWidget(self.extended_info_label)

        self.disconnect_button = QPushButton("Disconnect Voice")
        self.disconnect_button.clicked.connect(self.disconnect)
        self.disconnect_button.setEnabled(False)
        main_layout.addWidget(self.disconnect_button)

        main_layout.addStretch()

    def init_signals(self):
        self.network_handler.update_info.connect(self.update_info)
        self.network_handler.update_status.connect(self.update_server_status)
        self.network_handler.disconnect_signal.connect(self.disconnect)
        self.audio_handler.disconnect_signal.connect(self.disconnect)

    def update_server_status(self, status):
        self.last_status = status
        self.status_label.setText(f"Server status: {status}")
        if status == "Offline" and self.audio_handler.connected:
            self.disconnect()

    def update_info(self, info):
        self.last_info = info
        self.clients_count_label.setText(f"Connected clients: {info.get('count', 0)}")
        channels = info.get('channels', {})
        speaking = ", ".join([f"Client {login} (Channel {chan})" for login, chan in info.get('speaking', {}).items()]) or "None"
        self.extended_info_label.setText(
            f"Server Info:\n"
            f"Status: {info.get('status', 'Offline')}\n"
            f"Apps Running: {info.get('app_count', 0)}\n"
            f"Voice Connected: {info.get('voice_count', 0)}\n"
            f"Speaking: {speaking}"
        )

        existing_ids = set(self.channel_buttons.keys())
        new_ids = set(channels.keys())
        for chan_id in existing_ids - new_ids:
            button = self.channel_buttons.pop(chan_id)
            self.channels_layout.removeWidget(button)
            button.deleteLater()
        for chan_id, name in channels.items():
            if chan_id not in self.channel_buttons:
                button = QPushButton(f"{name}\n(ID: {chan_id})")
                button.setFixedSize(100, 60)
                button.clicked.connect(lambda checked, cid=chan_id: self.connect_to_channel(cid))
                self.channel_buttons[chan_id] = button
                row = (len(self.channel_buttons) - 1) // 3
                col = (len(self.channel_buttons) - 1) % 3
                self.channels_layout.addWidget(button, row, col)
        self.update_channel_styles()

    def update_channel_styles(self):
        for chan_id, button in self.channel_buttons.items():
            button.setProperty("connected", self.audio_handler.connected and self.current_channel == chan_id)
            button.setStyleSheet("")
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()

    def open_create_channel_dialog(self):
        dialog = CreateChannelDialog(self, self.network_handler)
        dialog.exec_()

    def connect_to_channel(self, channel_id):
        try:
            channel_id = int(channel_id)
            if self.audio_handler.connected and self.current_channel == channel_id:
                return True
            if self.audio_handler.connected:
                self.disconnect()
            self.current_channel = channel_id
            self.audio_handler = AudioHandler()  # Создаём новый экземпляр
            result = self.audio_handler.start_audio(HOST, 23343, self.login, channel_id)
            if result is not True:
                self.status_label.setText(f"Server status: {self.last_status} (Failed to connect: {result})")
                self.current_channel = None
                self.audio_handler.connected = False
                return False
            self.audio_handler.connected = True
            self.disconnect_button.setEnabled(True)
            self.status_label.setText(f"Server status: {self.last_status} (Connected to Channel: {channel_id})")
            self.update_channel_styles()
            return True
        except Exception as e:
            print(f"Failed to connect: {str(e)}")
            self.status_label.setText(f"Server status: {self.last_status} (Failed to connect: {e})")
            self.current_channel = None
            self.audio_handler.connected = False
            self.audio_handler.disconnect()
            self.audio_handler = AudioHandler()  # Пересоздаём экземпляр
            self.update_channel_styles()
            return False

    def disconnect(self):
        try:
            if self.audio_handler.connected:
                self.audio_handler.disconnect()
                self.audio_handler = AudioHandler()  # Создаём новый экземпляр
                self.current_channel = None
                self.audio_handler.connected = False
                self.disconnect_button.setEnabled(False)
                self.status_label.setText(f"Server status: {self.last_status} (Disconnected)")
                self.update_channel_styles()
        except Exception as e:
            print(f"Failed to disconnect: {str(e)}")

    def full_exit(self):
        self.network_handler.stop()
        if self.audio_handler:
            self.audio_handler.close()
            self.audio_handler = None
        self.window_manager.tray_icon.hide()
        self.close()

    def closeEvent(self, event):
        event.ignore()
        self.window_manager.hide_to_tray()

    def mousePressEvent(self, event):
        self.window_manager.mouse_press(event)

    def mouseMoveEvent(self, event):
        self.window_manager.mouse_move(event)

    def mouseReleaseEvent(self, event):
        self.window_manager.mouse_release(event)