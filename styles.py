MAIN_STYLES = """
    QMainWindow { background-color: #2C2F33; }
    QWidget#title_bar { background-color: #2C2F33; }
    QLabel { color: #FFFFFF; font-size: 14px; }
    QPushButton { 
        background-color: #36393F; 
        color: white; 
        padding: 10px; 
        border-radius: 5px; 
        font-size: 14px;
        border: 2px solid #36393F;
    }
    QPushButton:hover { background-color: #4A5A8C; }
    QPushButton:disabled { background-color: #4A5A8C; }
    QPushButton[connected="true"] { border: 2px solid #43B581 !important; }
    QPushButton.control_button { 
        background-color: #2C2F33; 
        color: white; 
        padding: 5px; 
        border-radius: 5px; 
        border: none; 
        font-size: 16px; 
    }
    QPushButton.control_button:hover { background-color: #555; }
"""

DIALOG_STYLES = """
    QDialog { background-color: #2C2F33; }
    QLabel { color: #FFFFFF; font-size: 14px; }
    QLineEdit {
        background-color: #36393F;
        color: white;
        padding: 8px;
        border-radius: 5px;
        font-size: 14px;
    }
    QPushButton { 
        background-color: #7289DA; 
        color: white; 
        padding: 10px; 
        border-radius: 5px; 
        font-size: 14px;
    }
    QPushButton:hover { background-color: #677BC4; }
"""