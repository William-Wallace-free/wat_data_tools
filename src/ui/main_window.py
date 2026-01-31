from PySide6.QtWidgets import (QMainWindow, QDockWidget, QWidget, QVBoxLayout, 
                               QPushButton, QGroupBox, QFileDialog, QTreeWidget, QTreeWidgetItem, QMessageBox)
from PySide6.QtCore import Qt
from src.data.engine import DataEngine
from src.ui.viz_engine import VisualizationEngine
from src.ui.plots import WaferMapWidget
from src.ui.dialogs import DatabaseConnectDialog
from src.core.interfaces import WatAutomationAPI

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WAT Analytics Enterprise")
        self.resize(1200, 800)
        
        # 1. Core Components
        self.data_engine = DataEngine()
        self.api = WatAutomationAPI(self)
        
        # 2. Central Widget (Viz Engine)
        self.viz_engine = VisualizationEngine()
        self.setCentralWidget(self.viz_engine)
        
        # 3. UI Setup
        self.setup_docks()
        self.setup_menu()

    def setup_docks(self):
        # Left Dock: Controls
        dock = QDockWidget("Control Panel", self)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # -- Import --
        grp_imp = QGroupBox("Data Source")
        l_imp = QVBoxLayout(grp_imp)
        
        btn_file = QPushButton("Load File (CSV/Excel)")
        btn_file.clicked.connect(self.on_load_file)
        
        btn_db = QPushButton("Connect MySQL (Docker)")
        btn_db.setStyleSheet("background-color: #e3f2fd; color: #1565c0; font-weight: bold;")
        btn_db.clicked.connect(self.on_connect_db)
        
        l_imp.addWidget(btn_file)
        l_imp.addWidget(btn_db)
        layout.addWidget(grp_imp)
        
        # -- Filter --
        grp_flt = QGroupBox("Data Filter")
        l_flt = QVBoxLayout(grp_flt)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Column", "Value"])
        l_flt.addWidget(self.tree)
        layout.addWidget(grp_flt)
        
        # -- Plot --
        grp_plt = QGroupBox("Visualization")
        l_plt = QVBoxLayout(grp_plt)
        btn_map = QPushButton("Add Wafer Map")
        btn_map.clicked.connect(self.on_add_map)
        l_plt.addWidget(btn_map)
        layout.addWidget(grp_plt)
        
        layout.addStretch()
        dock.setWidget(container)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)

    def setup_menu(self):
        bar = self.menuBar()
        m_file = bar.addMenu("File")
        m_file.addAction("Run Script...").triggered.connect(self.on_run_script)

    # --- Slots ---
    def on_load_file(self):
        f, _ = QFileDialog.getOpenFileName(self, "Open Data", "", "Data (*.csv *.xlsx *.db)")
        if f:
            try:
                self.data_engine.load_source(f, "auto")
                self.refresh_filter_tree()
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def on_connect_db(self):
        dlg = DatabaseConnectDialog(self)
        if dlg.exec():
            conn_str, query = dlg.get_info()
            try:
                self.data_engine.load_source(conn_str, "mysql", query=query)
                self.refresh_filter_tree()
                self.statusBar().showMessage("Connected to MySQL")
            except Exception as e:
                QMessageBox.critical(self, "DB Error", str(e))

    def refresh_filter_tree(self):
        self.tree.clear()
        df = self.data_engine.get_data()
        if df.empty: return
        
        # 简单展示前5个列的 Unique 值
        for col in df.columns[:5]:
            root = QTreeWidgetItem([col])
            try:
                uniques = df[col].unique()[:20] # Limit
                for u in uniques:
                    root.addChild(QTreeWidgetItem(["", str(u)]))
            except: pass
            self.tree.addTopLevelItem(root)

    def on_add_map(self):
        df = self.data_engine.get_data()
        if df.empty:
            QMessageBox.warning(self, "No Data", "Please load data first.")
            return
        
        widget = WaferMapWidget(df)
        self.viz_engine.add_widget(f"Wafer Map ({len(df)} rows)", widget)

    def on_run_script(self):
        f, _ = QFileDialog.getOpenFileName(self, "Run Script", "", "Python (*.py)")
        if f:
            with open(f, 'r', encoding='utf-8') as file:
                code = file.read()
                # 注入 API 和 pandas
                exec(code, {'api': self.api, 'pd': pd})
