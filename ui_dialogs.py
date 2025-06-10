from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel
import asyncio
import json
import os
import base64
from PyQt5.QtGui import QPixmap, QImage

class LoginDialog(QDialog):
    def __init__(self, parent, network_handler):
        super().__init__(parent)
        self.network_handler = network_handler
        self.setWindowTitle("Login")
        self.setFixedSize(300, 200)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText("Login")
        layout.addWidget(self.login_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red;")
        layout.addWidget(self.error_label)

        login_button = QPushButton("Login")
        login_button.clicked.connect(self.try_login)
        layout.addWidget(login_button)

        self.setLayout(layout)

    def try_login(self):
        login = self.login_input.text().strip()
        password = self.password_input.text().strip()
        if not login or not password:
            self.error_label.setText("Enter both login and password!")
            return
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self.network_handler.authenticate(login, password))
            if result.get("status") == "success":
                session_token = result.get("session_token")
                if not session_token:
                    import secrets
                    session_token = secrets.token_hex(32)
                with open("auth.json", "w") as f:
                    json.dump({"session_token": session_token, "login": login, "avatar_data": result.get("avatar_data")}, f)
                self.parent().login = login
                self.parent().avatar_data = result.get("avatar_data")
                self.parent().session_token = session_token
                self.accept()
            else:
                self.error_label.setText(f"Login failed: {result.get('error', 'Invalid credentials')}")
        except Exception as e:
            self.error_label.setText(f"Login failed: {str(e)}")
        finally:
            loop.close()

class CreateChannelDialog(QDialog):
    def __init__(self, parent, network_handler, community_id):
        super().__init__(parent)
        self.network_handler = network_handler
        self.community_id = community_id
        self.setWindowTitle("Create Channel")
        self.setFixedSize(300, 150)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Channel Name")
        layout.addWidget(self.name_input)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red;")
        layout.addWidget(self.error_label)

        create_button = QPushButton("Create")
        create_button.clicked.connect(self.create_channel)
        layout.addWidget(create_button)

        self.setLayout(layout)

    def create_channel(self):
        name = self.name_input.text().strip()
        if not name:
            self.error_label.setText("Enter channel name!")
            return
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self.network_handler.send_action("create_channel", name=name, community_id=self.community_id))
            if result:
                self.error_label.setText(f"Failed to create channel: {result}")
            else:
                self.accept()
        except Exception as e:
            self.error_label.setText(f"Failed to create channel: {str(e)}")
        finally:
            loop.close()

class CreateCommunityDialog(QDialog):
    def __init__(self, parent, network_handler):
        super().__init__(parent)
        self.network_handler = network_handler
        self.setWindowTitle("Create Community")
        self.setFixedSize(300, 150)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Community Name")
        layout.addWidget(self.name_input)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red;")
        layout.addWidget(self.error_label)

        create_button = QPushButton("Create")
        create_button.clicked.connect(self.create_community)
        layout.addWidget(create_button)

        self.setLayout(layout)

    def create_community(self):
        name = self.name_input.text().strip()
        if not name:
            self.error_label.setText("Enter community name!")
            return
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(self.network_handler.send_action("create_community", name=name))
            if result:
                self.error_label.setText(f"Failed to create community: {result}")
            else:
                self.accept()
        except Exception as e:
            self.error_label.setText(f"Failed to create community: {str(e)}")
        finally:
            loop.close()