from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from ui_main import VoiceChatClient

if __name__ == "__main__":
    app = QApplication([])
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    client = VoiceChatClient()
    client.show()
    app.exec_()