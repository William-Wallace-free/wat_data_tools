import sys
import os
from PySide6.QtWidgets import QApplication
from src.views.main_window import MainWindow
from src.controllers.main_ctrl import MainController

# 适配高分屏
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion") # 使用 Fusion 风格，跨平台一致

    # 1. 实例化 View
    window = MainWindow()
    
    # 2. 实例化 Controller (注入 View)
    controller = MainController(window)
    
    # 3. 启动
    window.show()
    sys.exit(app.exec())
