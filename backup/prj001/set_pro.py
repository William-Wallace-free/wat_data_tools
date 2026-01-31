import os
import sys
from pathlib import Path

# ==========================================
# 1. 代码模板 (Pro 版)
# ==========================================

# --- 核心入口 ---
CODE_MAIN = """import sys
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
"""

# --- Controller (中枢神经) ---
CODE_CONTROLLER = """from PySide6.QtCore import QObject
from src.services.data_service import DataService

class MainController(QObject):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.service = DataService()
        
        # 连接信号 (View -> Controller)
        self.view.btn_load.clicked.connect(self.on_load_project)
        self.view.list_nav.itemClicked.connect(self.on_wafer_selected)

    def on_load_project(self):
        # 1. 调用 Service 获取数据 (模拟)
        project_name = "Demo_Project_A"
        wafers = self.service.get_wafer_list()
        
        # 2. 更新 View
        self.view.status_bar.showMessage(f"Project Loaded: {project_name}")
        self.view.update_wafer_list(wafers)
        
    def on_wafer_selected(self, item):
        wafer_id = item.text()
        self.view.status_bar.showMessage(f"Analyzing Wafer: {wafer_id}...")
        
        # 1. 获取该 Wafer 的 Map 数据
        map_data = self.service.get_wafer_map_data(wafer_id)
        
        # 2. 让 View 里的 Map 组件绘图
        self.view.wafer_map_widget.plot_data(map_data)
        
        # 3. 更新统计面板
        stats = self.service.calculate_stats(map_data)
        self.view.update_stats(stats)
"""

# --- Service (模拟数据层) ---
CODE_SERVICE = """import numpy as np

class DataService:
    \"\"\"
    负责所有非 UI 的逻辑：数据库查询、数据计算、文件解析
    \"\"\"
    def get_wafer_list(self):
        return [f"Wafer_{i:02d}" for i in range(1, 26)]

    def get_wafer_map_data(self, wafer_id):
        # 模拟生成 Wafer Map 数据 (X, Y, Value)
        # 实际开发中，这里会调用 Repository 从 SQLite 读取
        n = 2000
        theta = np.random.uniform(0, 2*np.pi, n)
        r = np.sqrt(np.random.uniform(0, 1, n)) * 150
        x = r * np.cos(theta)
        y = r * np.sin(theta)
        values = np.random.normal(0.75, 0.05, n) # Vth mean=0.75
        return {"x": x, "y": y, "values": values}

    def calculate_stats(self, map_data):
        vals = map_data["values"]
        return {
            "mean": np.mean(vals),
            "std": np.std(vals),
            "max": np.max(vals),
            "min": np.min(vals),
            "yield": np.mean(vals < 0.85) * 100 # 假定 Spec
        }
"""

# --- View: 主窗口 (Docking 布局) ---
CODE_MAIN_WINDOW = """from PySide6.QtWidgets import (QMainWindow, QDockWidget, QListWidget, 
                               QWidget, QVBoxLayout, QLabel, QToolBar, QStatusBar)
from PySide6.QtCore import Qt
from src.views.widgets.wafer_map import WaferMapWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WAT Analysis Pro")
        self.resize(1200, 800)
        
        self.setup_ui()
        self.setup_docks()

    def setup_ui(self):
        # 顶部工具栏
        self.toolbar = QToolBar("Main Toolbar")
        self.addToolBar(self.toolbar)
        self.btn_load = self.toolbar.addAction("Open Project")
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # 中央区域 (用于放图表)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        
        # 嵌入自定义绘图组件
        self.wafer_map_widget = WaferMapWidget()
        self.main_layout.addWidget(self.wafer_map_widget)

    def setup_docks(self):
        # 左侧 Dock: 导航栏
        self.dock_nav = QDockWidget("Wafer Navigator", self)
        self.dock_nav.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.list_nav = QListWidget()
        self.dock_nav.setWidget(self.list_nav)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.dock_nav)

        # 右侧 Dock: 统计面板
        self.dock_stats = QDockWidget("Statistics", self)
        self.lbl_stats = QLabel("Select a wafer to see stats.")
        self.lbl_stats.setAlignment(Qt.AlignTop)
        self.lbl_stats.setStyleSheet("font-family: Consolas; font-size: 14px; padding: 10px;")
        self.dock_stats.setWidget(self.lbl_stats)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dock_stats)

    # --- View 更新接口 (供 Controller 调用) ---
    def update_wafer_list(self, wafers):
        self.list_nav.clear()
        self.list_nav.addItems(wafers)

    def update_stats(self, stats):
        text = (f"Mean : {stats['mean']:.4f} V\\n"
                f"Std  : {stats['std']:.4f} V\\n"
                f"Max  : {stats['max']:.4f} V\\n"
                f"Min  : {stats['min']:.4f} V\\n"
                f"-----------------\\n"
                f"Yield: {stats['yield']:.2f} %")
        self.lbl_stats.setText(text)
"""

# --- View: 绘图组件 (PyQtGraph 封装) ---
CODE_WAFER_MAP = """import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout

class WaferMapWidget(QWidget):
    \"\"\"
    封装 PyQtGraph，对外只暴露 plot_data 接口，
    让上层 View 不用关心具体的绘图库实现。
    \"\"\"
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # 初始化 PlotWidget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w') # 白色背景
        self.plot_widget.setAspectLocked(True)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.layout.addWidget(self.plot_widget)
        
        self.scatter = None

    def plot_data(self, data):
        self.plot_widget.clear()
        
        x = data['x']
        y = data['y']
        values = data['values']
        
        # 简单的颜色映射 (归一化到 0-255)
        # 实际项目中建议使用 pg.ColorMap
        norm_vals = (values - values.min()) / (values.max() - values.min())
        brushes = [pg.intColor(int(v * 255), alpha=200) for v in norm_vals]
        
        self.scatter = pg.ScatterPlotItem(
            x=x, y=y, size=8, brush=brushes, pen=None, hoverable=True
        )
        self.plot_widget.addItem(self.scatter)
        self.plot_widget.setTitle(f"Total Points: {len(x)}")
"""

CODE_REQ = """PySide6>=6.5.0
pyqtgraph>=0.13.0
numpy>=1.20.0"""

# ==========================================
# 2. 生成器逻辑
# ==========================================
def create_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✔  {path.name}")

def setup_pro_framework():
    root = Path(os.getcwd()).absolute()
    print(f"🚀 Building PRO Framework in: {root}")

    dirs = [
        "src/controllers",
        "src/models",
        "src/services",
        "src/views/widgets",
        "resources"
    ]
    
    # 创建目录
    for d in dirs:
        (root / d).mkdir(parents=True, exist_ok=True)

    # 创建文件
    files = {
        root / "main.py": CODE_MAIN,
        root / "requirements.txt": CODE_REQ,
        root / "src/controllers/main_ctrl.py": CODE_CONTROLLER,
        root / "src/services/data_service.py": CODE_SERVICE,
        root / "src/views/main_window.py": CODE_MAIN_WINDOW,
        root / "src/views/widgets/wafer_map.py": CODE_WAFER_MAP,
        root / "src/__init__.py": "",
    }

    for path, content in files.items():
        create_file(path, content)

    print("\n✨ Framework Ready!")
    print("1. pip install -r requirements.txt")
    print("2. python main.py")

if __name__ == "__main__":
    if input("Create files here? (y/n): ").lower() == 'y':
        setup_pro_framework()