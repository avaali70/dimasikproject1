import os
import json
import base64
from PyQt5.QtWidgets import QMainWindow, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QGridLayout, QDesktopWidget
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QPixmap, QImage
from audio import AudioHandler
from network import NetworkHandler, HOST
from ui_dialogs import LoginDialog, CreateChannelDialog, CreateCommunityDialog
from ui_window_manager import WindowManager
from styles import MAIN_STYLES
from PyQt5.QtGui import QRegion, QPainter, QPainterPath
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QRect, QEvent
from PyQt5.QtGui import QPainter, QPainterPath, QPixmap, QFont
import asyncio
from PyQt5.QtCore import Qt, QEvent, QSize
from PyQt5.QtGui import QPainter, QPainterPath, QPixmap, QFont, QIcon
from PyQt5.QtWidgets import QLabel, QWidget, QHBoxLayout, QApplication

class VoiceChatClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.login = None
        self.avatar_data = None
        self.audio_handler = AudioHandler()
        self.network_handler = NetworkHandler()
        self.last_info = {'count': 0, 'logins': [], 'communities': {}, 'channels': {}, 'speaking': {}}
        self.last_status = "Offline"
        self.current_channel = None
        self.current_community = None
        self.channel_buttons = {}
        self.community_buttons = {}
        self.original_pixmaps = {}
        self.window_manager = WindowManager(self)
        self.MICROPHONE_ENABLED = 1

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
                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    try:
                        result = loop.run_until_complete(self.network_handler.verify_token(login, session_token))
                        if result.get("status") == "success":
                            self.login = login
                            self.session_token = session_token
                            self.avatar_data = result.get("avatar_data", self.avatar_data)
                            return True
                    finally:
                        if not loop.is_running():
                            loop.close()
            except Exception as e:
                print(f"Auto-login error: {str(e)}")
        return False

    def show_login_dialog(self):
        dialog = LoginDialog(self, self.network_handler)
        dialog.exec_()

    def create_round_pixmap(self, pixmap, size):
        target = QPixmap(size, size)
        target.fill(Qt.transparent)
        painter = QPainter(target)
        painter.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)
        scaled_pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        painter.drawPixmap(0, 0, scaled_pixmap)
        painter.end()
        return target

    def init_ui(self):
        self.setWindowTitle(f"Voice Client: {self.login}")
        self.setStyleSheet(MAIN_STYLES)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        left_container = QWidget()
        left_container.setFixedWidth(272)
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        top_left_container = QWidget()
        top_left_layout = QHBoxLayout(top_left_container)
        top_left_layout.setContentsMargins(0, 0, 0, 0)
        top_left_layout.setSpacing(0)

        self.community_bar = QWidget()
        self.community_bar.setObjectName("community_bar")
        self.community_bar.setFixedWidth(70)
        community_layout = QVBoxLayout(self.community_bar)
        community_layout.setContentsMargins(5, 5, 5, 5)
        community_layout.setSpacing(10)

        self.home_button = QLabel()
        self.home_button.setObjectName("community_button")
        self.home_button.setFixedSize(50, 50)
        self.home_button.setAlignment(Qt.AlignCenter)
        home_pixmap = QPixmap("home.png")
        if not home_pixmap.isNull():
            home_pixmap = home_pixmap.scaled(50, 50, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self.home_button.setPixmap(self.create_round_pixmap(home_pixmap, 50))
        else:
            print("Failed to load home.png")
        self.home_button.mousePressEvent = lambda event: self.go_home()
        self.home_button.installEventFilter(self)
        community_layout.addWidget(self.home_button)

        community_layout.addStretch()
        top_left_layout.addWidget(self.community_bar)

        self.navigation_bar = QWidget()
        self.navigation_bar.setObjectName("navigation_bar")
        self.navigation_bar.setFixedWidth(200)
        self.nav_layout = QVBoxLayout(self.navigation_bar)
        self.nav_layout.setContentsMargins(10, 10, 10, 10)
        self.nav_layout.setSpacing(10)
        
        self.channels_container = QWidget()
        self.channels_layout = QVBoxLayout(self.channels_container)
        self.channels_layout.setContentsMargins(0, 0, 0, 0)
        self.channels_layout.setSpacing(10)
        
        self.update_nav_bar()
        top_left_layout.addWidget(self.navigation_bar)

        left_layout.addWidget(top_left_container)

        self.user_bar = QWidget()
        self.user_bar.setObjectName("user_bar")
        self.user_bar.setFixedHeight(70)
        self.user_bar.setFixedWidth(272)
        user_layout = QHBoxLayout(self.user_bar)
        user_layout.setContentsMargins(15, 10, 15, 10)
        user_layout.setSpacing(10)
        user_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Кнопка настроек слева от аватарки
        self.settings_button = QPushButton()
        self.settings_button.setFixedSize(40, 40)
        self.settings_button.setObjectName("settings_button")
        self.settings_button.setStyleSheet("""
            QPushButton#settings_button {
                background-color: transparent;
                border: none;
            }
            QPushButton#settings_button:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        self.settings_button.setIcon(QIcon("settings.png"))
        self.settings_button.setIconSize(QSize(30, 30))
        self.settings_button.clicked.connect(self.open_settings_dialog)
        user_layout.addWidget(self.settings_button)

        avatar_label = QLabel()
        if self.avatar_data:
            try:
                image_data = base64.b64decode(self.avatar_data)
                image = QImage.fromData(image_data)
                pixmap = QPixmap.fromImage(image)
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(40, 40, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    round_pixmap = self.create_round_pixmap(pixmap, 40)
                    avatar_label.setPixmap(round_pixmap)
                avatar_label.installEventFilter(self)
            except Exception as e:
                pass
        user_layout.addWidget(avatar_label)

        nick_label = QLabel(f"{self.login}")
        nick_label.setObjectName("user_label")
        user_layout.addWidget(nick_label)

        self.mic_button = QPushButton()
        self.mic_button.setFixedSize(40, 40)
        self.mic_button.setObjectName("control_button")
        self.mic_button.setStyleSheet("background-color: transparent; border: none;")
        self.update_mic_button_icon()
        self.mic_button.clicked.connect(self.toggle_microphone)
        user_layout.addWidget(self.mic_button)
        user_layout.addStretch()

        left_layout.addWidget(self.user_bar)
        main_layout.addWidget(left_container)

        self.main_content = QWidget()
        self.main_content.setObjectName("main_content")
        content_layout = QVBoxLayout(self.main_content)
        content_layout.setContentsMargins(20, 10, 20, 20)
        content_layout.setSpacing(15)

        control_layout = QHBoxLayout()
        control_layout.addStretch()
        self.minimize_button = QPushButton("−")
        self.minimize_button.setFixedSize(40, 40)
        self.minimize_button.setObjectName("control_button")
        self.minimize_button.clicked.connect(self.showMinimized)
        control_layout.addWidget(self.minimize_button)

        self.maximize_button = QPushButton("□")
        self.maximize_button.setFixedSize(40, 40)
        self.maximize_button.setObjectName("control_button")
        self.maximize_button.clicked.connect(self.window_manager.toggle_maximize)
        control_layout.addWidget(self.maximize_button)

        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(40, 40)
        self.close_button.setObjectName("control_button")
        self.close_button.clicked.connect(self.window_manager.hide_to_tray)
        control_layout.addWidget(self.close_button)

        content_layout.addLayout(control_layout)
        self.content_layout = QVBoxLayout()
        self.update_content()
        content_layout.addLayout(self.content_layout)
        content_layout.addStretch()

        self.overlay_widget = QWidget(self.main_content)
        self.overlay_widget.setObjectName("overlay_widget")
        self.overlay_widget.setStyleSheet("background-color: rgba(0, 0, 0, 0.7); border-radius: 10px;")
        self.overlay_widget.hide()
        overlay_layout = QVBoxLayout(self.overlay_widget)
        overlay_layout.setContentsMargins(20, 20, 20, 20)
        self.server_down_label = QLabel("Сервер упал! Ожидаем восстановления...")
        self.server_down_label.setStyleSheet("color: red; font-size: 18px; font-weight: bold; background-color: transparent;")
        self.server_down_label.setAlignment(Qt.AlignCenter)
        overlay_layout.addWidget(self.server_down_label)
        self.overlay_widget.setFixedSize(300, 100)

        main_layout.addWidget(self.main_content, 1)

        self.position_overlay()

    def open_settings_dialog(self):
        from settings import SettingsDialog
        dialog = SettingsDialog(self)
        dialog.exec_()

    def update_mic_button_icon(self):
        # Обновляем иконку кнопки в зависимости от состояния микрофона
        if self.MICROPHONE_ENABLED == 1:
            icon = QIcon("microphone.png")
        else:
            icon = QIcon("mute_microphone.png")
        self.mic_button.setIcon(icon)
        self.mic_button.setIconSize(QSize(30, 30))  # Увеличиваем размер иконки

    def toggle_microphone(self):
        # Переключаем состояние микрофона
        self.MICROPHONE_ENABLED = 1 if self.MICROPHONE_ENABLED == 0 else 0
        self.update_mic_button_icon()

    def position_overlay(self):
        # Позиционируем overlay_widget в центре main_content
        if hasattr(self, 'overlay_widget') and hasattr(self, 'main_content'):
            content_rect = self.main_content.rect()
            overlay_rect = self.overlay_widget.rect()
            x = (content_rect.width() - overlay_rect.width()) // 2
            y = (content_rect.height() - overlay_rect.height()) // 2
            self.overlay_widget.move(x, y)

    def eventFilter(self, obj, event):
        if obj in (self.home_button, *self.community_buttons.values()) or obj in [w for w in self.user_bar.children() if isinstance(w, QLabel)]:
            comm_id = next((cid for cid, btn in self.community_buttons.items() if btn == obj), None)
            if event.type() == QEvent.Enter:
                obj.setFixedSize(60, 60)
                if comm_id and comm_id in self.original_pixmaps:
                    pixmap = self.original_pixmaps[comm_id]  # Используем оригинальный пиксмап
                    scaled_pixmap = pixmap.scaled(60, 60, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    obj.setPixmap(self.create_round_pixmap(scaled_pixmap, 60))
            elif event.type() == QEvent.Leave:
                obj.setFixedSize(50, 50)
                if comm_id and comm_id in self.original_pixmaps:
                    pixmap = self.original_pixmaps[comm_id]  # Используем оригинальный пиксмап
                    scaled_pixmap = pixmap.scaled(50, 50, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    obj.setPixmap(self.create_round_pixmap(scaled_pixmap, 50))
        return super().eventFilter(obj, event)

    def update_nav_bar(self):
        for i in reversed(range(self.nav_layout.count())):
            item = self.nav_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
            self.nav_layout.removeItem(item)

        if not self.current_community:
            friends_button = QPushButton("Друзья")
            self.nav_layout.addWidget(friends_button)
            messages_button = QPushButton("Личные сообщения")
            self.nav_layout.addWidget(messages_button)
            self.nav_layout.addStretch()
        else:
            create_channel_button = QPushButton("+")
            create_channel_button.setFixedSize(30, 30)
            create_channel_button.clicked.connect(self.open_create_channel_dialog)
            self.nav_layout.addWidget(create_channel_button, alignment=Qt.AlignLeft)
            
            self.nav_layout.addWidget(QLabel("Голосовые каналы:"))
            self.channels_container = QWidget()
            self.channels_layout = QGridLayout(self.channels_container)
            self.channels_layout.setSpacing(10)
            self.update_channels()
            self.nav_layout.addWidget(self.channels_container)
            self.nav_layout.addStretch()

    def update_content(self):
        for i in reversed(range(self.content_layout.count())):
            item = self.content_layout.itemAt(i)
            if item.widget():
                item.widget().deleteLater()
            self.content_layout.removeItem(item)

        self.status_label = None
        self.clients_count_label = None
        self.extended_info_label = None
        self.disconnect_button = None

        if not self.current_community:
            self.content_layout.addStretch()
        else:
            self.status_label = QLabel("Server status: Checking...")
            self.content_layout.addWidget(self.status_label)

            self.clients_count_label = QLabel("Connected clients: -")
            self.content_layout.addWidget(self.clients_count_label)

            self.extended_info_label = QLabel("Server Info:\nStatus: Checking...\nApps Running: -\nVoice Connected: -\nSpeaking: -")
            self.extended_info_label.setStyleSheet("background-color: #36393F; padding: 10px; border-radius: 5px;")
            self.content_layout.addWidget(self.extended_info_label)

            self.disconnect_button = QPushButton("Disconnect Voice")
            self.disconnect_button.clicked.connect(self.disconnect)
            self.disconnect_button.setEnabled(False)
            self.content_layout.addWidget(self.disconnect_button)

            self.content_layout.addStretch()

    def init_signals(self):
        self.network_handler.update_info.connect(self.update_info)
        self.network_handler.update_status.connect(self.update_server_status)
        self.network_handler.disconnect_signal.connect(self.disconnect)

    def update_server_status(self, status):
        self.last_status = status
        if self.status_label:
            self.status_label.setText(f"Server status: {status}")
        # Проверяем, существует ли audio_handler перед обращением к connected
        if status == "Offline" and self.audio_handler and getattr(self.audio_handler, 'connected', False):
            self.disconnect()
        # Показываем или скрываем табличку в зависимости от статуса
        if status == "Offline":
            self.overlay_widget.show()
        else:
            self.overlay_widget.hide()
        self.position_overlay()  # Обновляем позицию таблички

    def update_info(self, info):
        self.last_info = info or {}
        if self.clients_count_label:
            self.clients_count_label.setText(f"Connected clients: {self.last_info.get('count', 0)}")
        speaking = ", ".join([f"{login} ({chan})" for login, chan in self.last_info.get('speaking', {}).items()]) or "None"
        if self.extended_info_label:
            self.extended_info_label.setText(
                f"Server Info:\n"
                f"Status: {self.last_info.get('status', 'Offline')}\n"
                f"Apps: {self.last_info.get('app_count', 0)}\n"
                f"Voice: {self.last_info.get('voice_count', 0)}\n"
                f"Speaking: {speaking}"
            )

        existing_communities = set(self.community_buttons.keys())
        new_communities = set(self.last_info.get('communities', {}).keys())
        for comm_id in existing_communities - new_communities:
            button = self.community_buttons.pop(comm_id)
            if button:
                self.community_bar.layout().removeWidget(button)
                button.deleteLater()
        for comm_id, data in self.last_info.get('communities', {}).items():
            if comm_id not in self.community_buttons:
                community_label = QLabel()
                community_label.setObjectName("community_button")
                community_label.setFixedSize(50, 50)
                community_label.setAlignment(Qt.AlignCenter)
                avatar_data = data.get('avatar_data')
                if avatar_data:
                    try:
                        image_data = base64.b64decode(avatar_data)
                        image = QImage.fromData(image_data)
                        if image.isNull():
                            print(f"Invalid image data for community {comm_id}")
                            return
                        pixmap = QPixmap.fromImage(image)
                        if not pixmap.isNull():
                            self.original_pixmaps[comm_id] = pixmap  # Сохраняем оригинальный пиксмап
                            pixmap = pixmap.scaled(50, 50, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                            round_pixmap = self.create_round_pixmap(pixmap, 50)
                            community_label.setPixmap(round_pixmap)
                        else:
                            print(f"Invalid pixmap for community {comm_id}")
                    except Exception as e:
                        print(f"Failed to load community avatar: {e}")
                community_label.mousePressEvent = lambda event, cid=comm_id: self.select_community(cid)
                community_label.installEventFilter(self)
                self.community_buttons[comm_id] = community_label
                self.community_bar.layout().insertWidget(1, community_label)
        self.update_community_styles()
        self.update_channels()

    def update_channels(self):
        if not self.current_community or not hasattr(self, 'channels_layout'):
            return
        # Очищаем существующий layout
        while self.channels_layout.count():
            item = self.channels_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.channel_buttons.clear()
        # Добавляем кнопки каналов в вертикальный layout
        for chan_id, name in self.last_info.get('channels', {}).get(self.current_community, {}).items():
            button = QPushButton(f"{name}\n(ID: {chan_id})")
            button.setFixedSize(100, 60)
            button.clicked.connect(lambda checked, cid=chan_id: self.connect_to_channel(cid))
            self.channel_buttons[chan_id] = button
            self.channels_layout.addWidget(button)
        self.update_channel_styles()

    def update_community_styles(self):
        for comm_id, button in self.community_buttons.items():
            if comm_id == self.current_community:  # Предполагается, что current_community хранит ID выбранного сообщества
                button.setStyleSheet("""
                    QLabel#community_button {
                        border-left: 3px solid #00BFFF;  /* Голубая полоска слева */
                        padding-left: 5px;
                    }
                """)
            else:
                button.setStyleSheet("""
                    QLabel#community_button {
                        border-left: none;
                        padding-left: 5px;
                    }
                """)

    def update_channel_styles(self):
        for chan_id, button in list(self.channel_buttons.items()):
            if button.isWidgetType():
                is_connected = self.audio_handler and self.audio_handler.connected and self.current_channel == chan_id
                button.setProperty("connected", is_connected)
                button.setStyleSheet("")
                button.style().unpolish(button)
                button.style().polish(button)
                button.update()

    def go_home(self):
        self.current_community = None
        self.update_community_styles()
        self.update_nav_bar()
        self.update_content()

    def select_community(self, community_id):
        self.current_community = community_id
        self.update_community_styles()
        self.update_nav_bar()
        self.update_content()

    def open_create_channel_dialog(self):
        if not self.current_community:
            return
        dialog = CreateChannelDialog(self, self.network_handler, self.current_community)
        dialog.exec_()

    def connect_to_channel(self, channel_id):
        try:
            channel_id = int(channel_id)
            if self.audio_handler and self.audio_handler.connected and self.current_channel == channel_id:
                return True
            if self.audio_handler and self.audio_handler.connected:
                self.disconnect()
            self.current_channel = channel_id
            self.audio_handler = AudioHandler()
            result = self.audio_handler.start_audio(
                HOST, 23343, self.login, channel_id,
                input_device_index=self.audio_handler.input_device_index,
                output_device_index=self.audio_handler.output_device_index
            )
            if result is not True:
                if self.status_label:
                    self.status_label.setText(f"Server status: {self.last_status} (Failed to connect: {result})")
                self.current_channel = None
                if self.audio_handler:
                    self.audio_handler.connected = False
                return False
            self.audio_handler.connected = True
            if self.disconnect_button:
                self.disconnect_button.setEnabled(True)
            if self.status_label:
                self.status_label.setText(f"Server status: {self.last_status} (Connected to Channel: {channel_id})")
            self.update_channel_styles()
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            if self.status_label:
                self.status_label.setText(f"Server status: {self.last_status} (Failed to connect: {e})")
            self.current_channel = None
            if self.audio_handler:
                self.audio_handler.connected = False
                self.audio_handler.disconnect()
                self.audio_handler = AudioHandler()
            self.update_channel_styles()
            return False

    def disconnect(self):
        try:
            if self.audio_handler and self.audio_handler.connected:
                self.audio_handler.disconnect()
                self.audio_handler.connected = False
                self.current_channel = None
                if self.disconnect_button:
                    self.disconnect_button.setEnabled(False)
                if self.status_label:
                    self.status_label.setText(f"Server status: {self.last_status} (Disconnected)")
                self.update_channel_styles()
        except Exception as e:
            print(f"Failed to disconnect: {e}")
        finally:
            if self.audio_handler:
                self.audio_handler.close()
                self.audio_handler = None

    def full_exit(self):
        import asyncio
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.network_handler.stop())  # Остановка WebSocket
        if self.audio_handler:
            self.audio_handler.close()
            self.audio_handler = None
        self.window_manager.tray_icon.hide()
        self.close()

    def closeEvent(self, event):
        if self.window_manager.tray_icon.isVisible():
            self.hide()  # Скрываем окно вместо закрытия
            event.ignore()  # Игнорируем событие закрытия
        else:
            event.accept()  # Закрываем приложение, если трей не активен

    def mousePressEvent(self, event):
        self.window_manager.mouse_press(event)

    def mouseMoveEvent(self, event):
        self.window_manager.mouse_move(event)

    def mouseReleaseEvent(self, event):
        self.window_manager.mouse_release(event)