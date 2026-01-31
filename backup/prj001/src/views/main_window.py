from PySide6.QtWidgets import (QMainWindow, QDockWidget, QListWidget, 
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
        text = (f"Mean : {stats['mean']:.4f} V\n"
                f"Std  : {stats['std']:.4f} V\n"
                f"Max  : {stats['max']:.4f} V\n"
                f"Min  : {stats['min']:.4f} V\n"
                f"-----------------\n"
                f"Yield: {stats['yield']:.2f} %")
        self.lbl_stats.setText(text)
