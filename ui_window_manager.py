from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QDesktopWidget
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QIcon

class WindowManager:
    def __init__(self, window):
        self.window = window
        self.is_dragging = False
        self.drag_position = QPoint()
        self.normal_geometry = None
        self.setup_tray()
        self.setup_window()

    def setup_window(self):
        desktop = QDesktopWidget().screenGeometry()
        self.window.setGeometry(desktop)
        self.normal_geometry = desktop.adjusted(100, 100, -100, -100)
        self.window.setWindowFlags(Qt.FramelessWindowHint)

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(QIcon("icon.png"), self.window)
        tray_menu = QMenu()
        exit_action = tray_menu.addAction("Закрыть")
        exit_action.triggered.connect(self.window.full_exit)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_activated)
        self.tray_icon.show()

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.window.show()
            if self.window.isMaximized():
                self.window.showMaximized()
            else:
                self.window.setGeometry(self.normal_geometry)
                self.window.showNormal()

    def toggle_maximize(self):
        if self.window.isMaximized():
            self.window.showNormal()
            self.window.setGeometry(self.normal_geometry)
            self.window.maximize_button.setText("□")
            self.window.setMinimumSize(800, 600)
        else:
            self.normal_geometry = self.window.geometry()
            self.window.showMaximized()
            self.window.maximize_button.setText("❐")
            self.window.setMinimumSize(0, 0)

    def hide_to_tray(self):
        self.window.hide()
        self.tray_icon.show()

    def mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            title_bar_rect = self.window.title_bar.rect()
            title_bar_pos = self.window.title_bar.mapToParent(QPoint(0, 0))
            title_bar_rect.moveTo(title_bar_pos)
            if title_bar_rect.contains(pos):
                self.is_dragging = True
                if self.window.isMaximized():
                    desktop = QDesktopWidget().screenGeometry()
                    self.normal_geometry = desktop.adjusted(100, 100, -100, -100)
                    click_x_ratio = pos.x() / self.window.width()
                    click_y_ratio = pos.y() / self.window.height()
                    self.window.showNormal()
                    self.window.setGeometry(self.normal_geometry)
                    self.window.maximize_button.setText("□")
                    self.window.setMinimumSize(800, 600)
                    new_width = self.normal_geometry.width()
                    new_height = self.normal_geometry.height()
                    new_x = event.globalPos().x() - int(click_x_ratio * new_width)
                    new_y = event.globalPos().y() - int(click_y_ratio * new_height)
                    self.window.move(new_x, new_y)
                    self.drag_position = event.globalPos() - self.window.pos()
                else:
                    self.drag_position = event.globalPos() - self.window.pos()
                event.accept()

    def mouse_move(self, event):
        if self.is_dragging and not self.window.isMaximized():
            new_pos = event.globalPos() - self.drag_position
            if new_pos.y() <= 0:
                self.normal_geometry = self.window.geometry()
                self.window.showMaximized()
                self.window.maximize_button.setText("❐")
                self.window.setMinimumSize(0, 0)
                self.is_dragging = False
            else:
                self.window.move(new_pos)
            event.accept()

    def mouse_release(self, event):
        if event.button() == Qt.LeftButton:
            self.is_dragging = False
            event.accept()