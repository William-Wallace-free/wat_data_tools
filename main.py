import sys
import os

# 适配高分屏
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

from PySide6.QtWidgets import QApplication
from src.ui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion") # 统一风格
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())
