import sys
import cv2
import numpy as np
from PyQt5.QtWidgets import QDialog, QLabel, QApplication, QPushButton, QVBoxLayout
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import QThread, pyqtSignal, Qt
import pyautogui
import base64
import asyncio
import websockets
import json

class ScreenShareThread(QThread):
    change_pixmap = pyqtSignal(QImage)

    def __init__(self, handler):
        super().__init__()
        self.handler = handler
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            screenshot = pyautogui.screenshot()
            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            # Сжимаем изображение для экономии трафика
            _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
            if self.handler.running:
                asyncio.run_coroutine_threadsafe(
                    self.handler.send_screenshot(jpg_as_text),
                    self.handler.loop
                )
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.change_pixmap.emit(image)
            self.msleep(100)  # 10 FPS для экономии ресурсов

    def stop(self):
        self.running = False
        self.wait()

class ScreenShareDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Screen Share")
        self.setModal(True)
        self.resize(800, 600)
        self.label = QLabel(self)
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

    def update_image(self, image):
        pixmap = QPixmap.fromImage(image)
        scaled_pixmap = pixmap.scaled(self.label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.label.setPixmap(scaled_pixmap)

    def closeEvent(self, event):
        event.accept()

class ScreenShareHandler:
    def __init__(self, network_handler, loop):
        self.network_handler = network_handler
        self.loop = loop
        self.thread = None
        self.dialog = None
        self.running = False
        self.current_sharer = None

    async def send_screenshot(self, jpg_data):
        if self.network_handler.ws and self.network_handler.ws.open:
            message = {
                "type": "screen_share",
                "data": jpg_data,
                "community_id": self.network_handler.current_community,
                "channel_id": self.network_handler.current_channel
            }
            await self.network_handler.ws.send(json.dumps(message))

    async def receive_screenshot(self, message):
        if message["type"] == "screen_share" and message["data"]:
            if not self.dialog or not self.dialog.isVisible():
                self.dialog = ScreenShareDialog()
                self.dialog.show()
            image_data = base64.b64decode(message["data"])
            image = QImage.fromData(image_data)
            if not image.isNull():
                self.dialog.update_image(image)
            self.current_sharer = message.get("user_id")

    async def stop_sharing(self):
        if self.running:
            self.running = False
            if self.thread:
                self.thread.stop()
                self.thread = None
            if self.network_handler.ws and self.network_handler.ws.open:
                message = {
                    "type": "screen_share_stop",
                    "community_id": self.network_handler.current_community,
                    "channel_id": self.network_handler.current_channel
                }
                await self.network_handler.ws.send(json.dumps(message))

    async def handle_stop_sharing(self, message):
        if message["type"] == "screen_share_stop" and self.dialog and self.dialog.isVisible():
            self.dialog.close()
            self.dialog = None
            self.current_sharer = None

    def start_sharing(self):
        if not self.running:
            self.running = True
            self.thread = ScreenShareThread(self)
            self.thread.change_pixmap.connect(self.update_own_screenshot)
            self.thread.start()

    def update_own_screenshot(self, image):
        if not self.dialog or not self.dialog.isVisible():
            self.dialog = ScreenShareDialog()
            self.dialog.show()
        self.dialog.update_image(image)