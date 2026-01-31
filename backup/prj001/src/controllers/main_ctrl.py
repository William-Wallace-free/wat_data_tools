from PySide6.QtCore import QObject
from src.services.data_service import DataService

class MainController(QObject):
    def __init__(self, view):
        super().__init__()
        self.view = view
        self.service = DataService()
        
        # 修正：QAction 使用 .triggered 信号
        self.view.btn_load.triggered.connect(self.on_load_project)
        
        # QListWidget 的 itemClicked 是正确的
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