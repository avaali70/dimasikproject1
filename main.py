from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from ui_main import VoiceChatClient

if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication([])
    client = VoiceChatClient()
    client.show()
    app.exec_()