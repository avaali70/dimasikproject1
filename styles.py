MAIN_STYLES = """
    QMainWindow { background-color: #2C2F33; }
    QWidget#community_bar { 
        background-color: #2C2F33; 
        border-radius: 10px;
        margin: 0px;
    }
    QWidget#navigation_bar { 
        background-color: #36393F; 
        border-radius: 10px;
        margin: 0px 2px 0px 0px;
    }
    QWidget#main_content { 
        background-color: #3A3D42; 
        border-radius: 10px;
        margin-left: 2px;
    }
    QWidget#user_bar { 
        background-color: #F1C40F; 
        border-radius: 10px;
        margin: 0px 2px 10px 0px;
    }
    QLabel { color: #FFFFFF; font-size: 14px; }
    QLabel#user_label { font-size: 16px; }
    QPushButton { 
        background-color: #36393F; 
        color: white; 
        padding: 10px; 
        border-radius: 5px; 
        font-size: 14px;
        border: 2px solid #36393F;
    }
    QPushButton:hover { 
        background-color: #4A5A8C; 
    }
    QPushButton:disabled { background-color: #4A5A8C; }
    QPushButton[connected="true"] { 
        border: 2px solid #43B581; 
        border-left: 4px solid #7289DA;
        min-width: 110px;
        min-height: 66px;
    }
    QPushButton.control_button { 
        background-color: #2C2F33; 
        color: white; 
        padding: 5px; 
        border-radius: 5px; 
        border: none; 
        font-size: 16px; 
    }
    QPushButton.control_button:hover { background-color: #555; }
    QLabel.community_button { 
        background-color: #2C2F33; 
        color: white; 
        padding: 5px; 
        border-radius: 25px; 
        border: none;
        overflow: hidden;
    }
    QLabel.community_button[active="true"] { 
        border-left: 4px solid #7289DA; 
        min-width: 60px;
        min-height: 60px;
    }
    QLabel.community_button:hover { background-color: #4A5A8C; }
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