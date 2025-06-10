from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter
import sys

# Инициализация приложения (необходима для QPixmap и других графических объектов)
app = QApplication(sys.argv)

# Открываем файл для записи
with open("qt_constants.txt", "w", encoding="utf-8") as f:
    # Записываем константы Qt
    f.write("Константы в Qt:\n")
    qt_constants = dir(Qt)
    for attr in sorted(qt_constants):  # Сортируем для удобства чтения
        f.write(f"{attr}\n")
    
    # Пустая строка для разделения
    f.write("\n" + "="*50 + "\n\n")
    
    # Записываем константы QPainter
    f.write("Константы в QPainter:\n")
    qpainter_constants = dir(QPainter)
    for attr in sorted(qpainter_constants):  # Сортируем для удобства чтения
        f.write(f"{attr}\n")

# Выход из приложения
sys.exit(app.exec_())