import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QDockWidget, QMessageBox, 
                               QLabel, QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
                               QFileDialog, QDialog, QPushButton, QSizePolicy)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from sqlalchemy import create_engine, inspect

from src.core.settings import settings
from src.ui.dialogs.db_setup import DbSetupDialog
from src.core.repository import WatRepository
from src.ui.components.navigator import WatNavigator
from src.ui.plots import MultiPagePlotManager 
from src.ui.components.filter_bar import AdvancedFilterBar
from src.etl.pipeline import WatPipeline

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.db_url = settings.get_db_url()
        self.db_type = settings.get_db_type()
        
        self.setWindowTitle(f"WAT Analytics Enterprise ({self.db_type.upper()})")
        self.resize(1400, 900)

        if not self.ensure_database_ready():
            sys.exit(0)

        self.repo = WatRepository(self.db_url)
        self.init_ui()
        self.create_menus()
        
    def ensure_database_ready(self):
        while True:
            if self.check_and_init_db(): return True
            reply = QMessageBox.critical(self, "Error", f"Connect failed. Settings?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.open_db_settings()
                self.db_url = settings.get_db_url()
                self.db_type = settings.get_db_type()
            else: return False

    def check_and_init_db(self):
        try:
            engine = create_engine(self.db_url)
            inspector = inspect(engine)
            existing = inspector.get_table_names()
            if 'dim_wafer' not in existing:
                from src.data.init_db import init_db
                init_db(self.db_url, self.db_type)
            return True
        except: return False

    def init_ui(self):
        # 1. Dock
        self.nav_dock = QDockWidget("Data Navigator", self)
        self.nav_dock.setAllowedAreas(Qt.LeftDockWidgetArea)
        self.navigator = WatNavigator(self.repo)
        self.navigator.wafer_selected.connect(self.on_wafer_selected)
        self.nav_dock.setWidget(self.navigator)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.nav_dock)

        # 2. Central
        center = QWidget()
        self.setCentralWidget(center)
        self.main_layout = QVBoxLayout(center)
        
        # 3. Top Toolbar
        top_ctrl = QWidget()
        top_ctrl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        top_layout = QVBoxLayout(top_ctrl)
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        self.filter_bar = AdvancedFilterBar()
        # [修改] 连接新的多选信号
        self.filter_bar.params_changed.connect(self.on_params_selection_changed)
        top_layout.addWidget(self.filter_bar)

        ctrl_layout = QHBoxLayout()
        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(["Wafer Map", "Histogram", "Box Plot", "Line Chart"])
        self.chart_type_combo.currentIndexChanged.connect(self.refresh_batch_plot) # 类型变了也刷新
        
        self.line_style_combo = QComboBox()
        self.line_style_combo.addItems(["Lollipop", "Standard", "Step", "Area"])
        self.line_style_combo.currentIndexChanged.connect(self.refresh_batch_plot) # 样式变了也刷新

        ctrl_layout.addWidget(QLabel("Chart Type:"))
        ctrl_layout.addWidget(self.chart_type_combo)
        ctrl_layout.addWidget(QLabel("Line Style:"))
        ctrl_layout.addWidget(self.line_style_combo)
        ctrl_layout.addStretch()
        
        self.btn_db = QPushButton("⚙️ DB")
        self.btn_db.clicked.connect(self.open_db_settings)
        ctrl_layout.addWidget(self.btn_db)
        
        top_layout.addLayout(ctrl_layout)
        self.main_layout.addWidget(top_ctrl, 0)

        # 4. Plot Manager
        self.plot_manager = MultiPagePlotManager()
        self.main_layout.addWidget(self.plot_manager, 1)

    def create_menus(self):
        m = self.menuBar().addMenu("&File")
        m.addAction("DB Settings", self.open_db_settings)
        m.addAction("Import", self.on_import_data_clicked)
        m.addAction("Exit", self.close)

    def open_db_settings(self):
        if DbSetupDialog(self).exec():
            QMessageBox.information(self, "Restart", "Please restart.")
            self.close()

    def on_import_data_clicked(self):
        csv, _ = QFileDialog.getOpenFileName(self, "Select CSV", "", "CSV (*.csv)")
        if not csv: return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            WatPipeline(self.db_url).run(csv, None)
            QMessageBox.information(self, "OK", "Imported.")
            self.navigator.load_data()
        except Exception as e: QMessageBox.critical(self, "Err", str(e))
        finally: QApplication.restoreOverrideCursor()

    def on_wafer_selected(self, lot_id, wafer_id):
        self.current_lot_id = lot_id
        self.current_wafer_id = wafer_id
        df = self.repo.get_wafer_test_structure(lot_id, wafer_id)
        if not df.empty:
            self.filter_bar.load_data(df)
            # 清空之前的图，等待用户重新勾选
            self.plot_manager.reset_data()
    
    # [核心] 处理多选逻辑
    def on_params_selection_changed(self, selected_params):
        """当用户勾选了多个参数时，自动批量重绘"""
        self.current_selected_params = selected_params # 存下来备用
        self.refresh_batch_plot()

    def refresh_batch_plot(self):
        """根据当前选中的参数列表、图表类型、线型，执行批量绘图"""
        if not hasattr(self, 'current_selected_params') or not self.current_selected_params:
            self.plot_manager.reset_data()
            return
            
        if not hasattr(self, 'current_lot_id'): return

        chart_type = self.chart_type_combo.currentText()
        line_style = self.line_style_combo.currentText()
        
        # 准备批量数据
        batch_data = []
        
        # 遍历所有被勾选的参数
        for param in self.current_selected_params:
            df = self.repo.get_wafer_map_data(self.current_lot_id, self.current_wafer_id, param)
            if not df.empty:
                batch_data.append({
                    'df': df,
                    'title': f"{param}",
                    'chart_type': chart_type,
                    'line_style': line_style
                })
        
        # 发送给管理器进行布局和绘制
        if batch_data:
            self.plot_manager.plot_batch(batch_data)
            self.statusBar().showMessage(f"Plotted {len(batch_data)} charts.")
        else:
            self.plot_manager.reset_data()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())