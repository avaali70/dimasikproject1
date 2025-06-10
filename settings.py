from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QWidget, QComboBox, QLabel
from PyQt5.QtCore import Qt, QPropertyAnimation
from PyQt5.QtGui import QIcon

class SettingsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Настройки")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setStyleSheet("background-color: #2C2F33; border-radius: 10px;")
        self.init_ui()
        self.position_dialog()
        self.animate_appear()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Кнопка закрытия справа сверху
        close_button = QPushButton("×")
        close_button.setFixedSize(30, 30)
        close_button.setObjectName("control_button")
        close_button.setStyleSheet("background-color: transparent; border: none; color: white; font-size: 16px;")
        close_button.clicked.connect(self.close_with_animation)
        layout.addWidget(close_button, alignment=Qt.AlignRight | Qt.AlignTop)

        # Получаем список устройств
        input_devices, output_devices = self.parent().audio_handler.get_audio_devices()

        # Выбор микрофона
        mic_label = QLabel("Выберите микрофон:")
        mic_label.setStyleSheet("color: white; font-size: 14px;")
        layout.addWidget(mic_label)
        
        self.mic_combo = QComboBox()
        self.mic_combo.setStyleSheet("background-color: #36393F; color: white; padding: 5px; border-radius: 5px;")
        for device in input_devices:
            self.mic_combo.addItem(device['name'], device['index'])
        current_input = self.parent().audio_handler.input_device_index
        if current_input is not None:
            self.mic_combo.setCurrentIndex(self.mic_combo.findData(current_input))
        self.mic_combo.currentIndexChanged.connect(self.update_mic_device)
        layout.addWidget(self.mic_combo)

        # Выбор динамика
        speaker_label = QLabel("Выберите динамик:")
        speaker_label.setStyleSheet("color: white; font-size: 14px;")
        layout.addWidget(speaker_label)
        
        self.speaker_combo = QComboBox()
        self.speaker_combo.setStyleSheet("background-color: #36393F; color: white; padding: 5px; border-radius: 5px;")
        for device in output_devices:
            self.speaker_combo.addItem(device['name'], device['index'])
        current_output = self.parent().audio_handler.output_device_index
        if current_output is not None:
            self.speaker_combo.setCurrentIndex(self.speaker_combo.findData(current_output))
        self.speaker_combo.currentIndexChanged.connect(self.update_speaker_device)
        layout.addWidget(self.speaker_combo)

        layout.addStretch()

        self.setLayout(layout)

    def position_dialog(self):
        parent = self.parent()
        if parent:
            parent_rect = parent.geometry()
            dialog_width = parent_rect.width() // 2
            dialog_height = parent_rect.height() // 2
            self.setFixedSize(dialog_width, dialog_height)
            x = parent_rect.x() + parent_rect.width() // 4
            y = parent_rect.y() + parent_rect.height() // 4
            self.move(x, y)

    def animate_appear(self):
        self.setWindowOpacity(0)
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(300)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.start()

    def animate_disappear(self):
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(300)
        self.animation.setStartValue(1)
        self.animation.setEndValue(0)
        self.animation.finished.connect(self.close)
        self.animation.start()

    def close_with_animation(self):
        self.animate_disappear()

    def update_mic_device(self):
        index = self.mic_combo.currentData()
        if self.parent().audio_handler:
            self.parent().audio_handler.change_input_device(index)

    def update_speaker_device(self):
        index = self.speaker_combo.currentData()
        if self.parent().audio_handler:
            self.parent().audio_handler.change_output_device(index)