import os
import sys
from pathlib import Path

# ==============================================================================
# 1. 代码模版定义 (整合了 Ultimate 架构 + MySQL/Docker 支持)
# ==============================================================================

# --- requirements.txt ---
CODE_REQ = """PySide6>=6.5.0
pyqtgraph>=0.13.0
pandas>=2.0.0
numpy>=1.24.0
openpyxl>=3.1.0
matplotlib>=3.7.0
sqlalchemy>=2.0.0
pymysql>=1.1.0
"""

# --- main.py ---
CODE_MAIN = """import sys
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
"""

# --- src/core/interfaces.py (API 定义) ---
CODE_INTERFACES = """from typing import Protocol, Any, Dict, List
import pandas as pd

class IDataLoader(Protocol):
    \"\"\"数据加载器接口\"\"\"
    def load(self, source: str, **kwargs) -> pd.DataFrame: ...

class WatAutomationAPI:
    \"\"\"
    自动化 API 接口层
    \"\"\"
    def __init__(self, core_ui):
        self.ui = core_ui
        self.data_engine = core_ui.data_engine

    def load_data(self, source: str, source_type: str = "auto", **kwargs):
        print(f"[API] Loading {source_type}: {source}")
        self.data_engine.load_source(source, source_type, **kwargs)
        self.ui.refresh_filter_tree()

    def create_page(self, name: str):
        print(f"[API] Creating page: {name}")
        self.ui.viz_engine.add_page(name)

    def add_plot(self, plot_type: str, page_name: str = None):
        print(f"[API] Adding {plot_type}")
        # 实际逻辑需要对接 UI 的 add_plot_dock
        pass
"""

# --- src/data/engine.py (数据引擎 + MySQL) ---
CODE_DATA_ENGINE = """import pandas as pd
import sqlite3
from sqlalchemy import create_engine, text
from src.core.interfaces import IDataLoader

class CsvLoader:
    def load(self, path, **kwargs): return pd.read_csv(path)

class ExcelLoader:
    def load(self, path, **kwargs): return pd.read_excel(path)

class SqliteLoader:
    def load(self, path, **kwargs):
        conn = sqlite3.connect(path)
        return pd.read_sql("SELECT * FROM wat_data", conn)

class MySqlLoader:
    \"\"\"MySQL 加载器 (SQLAlchemy)\"\"\"
    def load(self, connection_str: str, **kwargs):
        query = kwargs.get("query")
        if not query:
            query = "SELECT * FROM wat_data LIMIT 10000"
            print("[Warn] No query provided, limiting to 10k rows.")
            
        try:
            engine = create_engine(connection_str)
            with engine.connect() as conn:
                return pd.read_sql(text(query), conn)
        except Exception as e:
            print(f"[Error] MySQL Load Failed: {e}")
            raise e

class DataEngine:
    def __init__(self):
        self._raw_data = pd.DataFrame()
        self._loaders = {
            "csv": CsvLoader(),
            "xlsx": ExcelLoader(),
            "db": SqliteLoader(),
            "mysql": MySqlLoader()
        }

    def load_source(self, source: str, source_type: str = "auto", **kwargs):
        if source_type == "auto":
            source_type = source.split('.')[-1]
            
        loader = self._loaders.get(source_type)
        if not loader:
            raise ValueError(f"Unknown source type: {source_type}")
            
        print(f"Loading data via {source_type}...")
        self._raw_data = loader.load(source, **kwargs)
        print(f"Data Loaded: {self._raw_data.shape}")

    def get_data(self):
        return self._raw_data
"""

# --- src/ui/viz_engine.py (Docking 系统) ---
CODE_VIZ_ENGINE = """from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from pyqtgraph.dockarea import DockArea, Dock

class VisualizationEngine(QWidget):
    \"\"\"
    管理多页 Dock 布局
    \"\"\"
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.layout.addWidget(self.tabs)
        
        self.add_page("Dashboard")

    def add_page(self, name: str):
        area = DockArea()
        self.tabs.addTab(area, name)
        return area

    def get_current_area(self) -> DockArea:
        return self.tabs.currentWidget()

    def add_widget(self, title: str, widget, position='right'):
        area = self.get_current_area()
        if not area:
            area = self.add_page("New Page")
        
        d = Dock(title, size=(500, 400))
        d.addWidget(widget)
        area.addDock(d, position)
"""

# --- src/ui/plots.py (绘图组件) ---
CODE_PLOTS = """import pyqtgraph as pg
import numpy as np

class WaferMapWidget(pg.PlotWidget):
    def __init__(self, data=None):
        super().__init__()
        self.setAspectLocked(True)
        self.setTitle("Wafer Map")
        self.showGrid(x=True, y=True, alpha=0.3)
        if data is not None and not data.empty:
            self.plot_dataframe(data)

    def plot_dataframe(self, df):
        self.clear()
        # 尝试自动寻找 X, Y, VALUE 列
        cols = [c.upper() for c in df.columns]
        
        # 简单的列名映射逻辑
        x_col = next((c for c in df.columns if 'X' in c.upper()), None)
        y_col = next((c for c in df.columns if 'Y' in c.upper()), None)
        v_col = next((c for c in df.columns if 'VAL' in c.upper()), None)

        if x_col and y_col:
            x = df[x_col].values
            y = df[y_col].values
            
            brushes = None
            if v_col:
                vals = df[v_col].values
                # 简单归一化颜色
                if len(vals) > 0:
                    mx, mn = np.max(vals), np.min(vals)
                    if mx != mn:
                        norm = (vals - mn) / (mx - mn)
                        brushes = [pg.intColor(int(v*255)) for v in norm]
            
            scatter = pg.ScatterPlotItem(x=x, y=y, size=12, brush=brushes, pen='w')
            self.addItem(scatter)
"""

# --- src/ui/dialogs.py (数据库连接窗口) ---
CODE_DIALOGS = """from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
                               QDialogButtonBox, QMessageBox)

class DatabaseConnectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connect to MySQL (Docker)")
        self.resize(400, 250)
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.host = QLineEdit("localhost")
        self.port = QLineEdit("3306")
        self.user = QLineEdit("wat_user")
        self.pwd = QLineEdit("wat_password")
        self.pwd.setEchoMode(QLineEdit.Password)
        self.db = QLineEdit("wat_db")
        self.query = QLineEdit("SELECT * FROM wat_data LIMIT 5000")
        
        form.addRow("Host:", self.host)
        form.addRow("Port:", self.port)
        form.addRow("User:", self.user)
        form.addRow("Password:", self.pwd)
        form.addRow("Database:", self.db)
        form.addRow("Initial Query:", self.query)
        
        layout.addLayout(form)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_info(self):
        h = self.host.text()
        p = self.port.text()
        u = self.user.text()
        pw = self.pwd.text()
        d = self.db.text()
        q = self.query.text()
        
        # SQLAlchemy Connection String
        conn_str = f"mysql+pymysql://{u}:{pw}@{h}:{p}/{d}"
        return conn_str, q
"""

# --- src/ui/main_window.py (主界面) ---
CODE_MAIN_WINDOW = """from PySide6.QtWidgets import (QMainWindow, QDockWidget, QWidget, QVBoxLayout, 
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
"""

# --- deploy/docker-compose.yml ---
CODE_DOCKER = """version: '3.8'
services:
  wat_mysql:
    image: mysql:8.0
    container_name: wat_mysql_server
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: root
      MYSQL_DATABASE: wat_db
      MYSQL_USER: wat_user
      MYSQL_PASSWORD: wat_password
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    command: --default-authentication-plugin=mysql_native_password

volumes:
  mysql_data:
"""

# --- deploy/init.sql ---
CODE_SQL_INIT = """CREATE TABLE IF NOT EXISTS wat_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    lot_id VARCHAR(50),
    wafer_id VARCHAR(50),
    x_index INT,
    y_index INT,
    param_name VARCHAR(50),
    value FLOAT,
    test_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert dummy data
INSERT INTO wat_data (lot_id, wafer_id, x_index, y_index, param_name, value) VALUES 
('L01', 'W01', 0, 0, 'Vth', 0.75),
('L01', 'W01', 1, 0, 'Vth', 0.76),
('L01', 'W01', 0, 1, 'Vth', 0.74),
('L01', 'W01', 1, 1, 'Vth', 0.80);
"""

# --- scripts/demo_automation.py ---
CODE_SCRIPT_DEMO = """# WAT Automation Script Example
print("Start Automation...")

# 1. Create a new view page
api.create_page("Auto Report")

# 2. In a real scenario, you would load data here
# api.load_data("D:/data/test.csv")

print("Automation Done.")
"""

# ==============================================================================
# 2. 构建逻辑
# ==============================================================================

def create_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✔ Created: {path}")

def main():
    root = Path(os.getcwd())
    print(f"🚀 Generating WAT Tool in: {root}")
    
    # 1. 目录结构
    dirs = [
        "src/core",
        "src/data",
        "src/ui",
        "deploy",
        "scripts"
    ]
    
    for d in dirs:
        (root / d).mkdir(parents=True, exist_ok=True)
        # 加上 __init__.py
        if "deploy" not in d and "scripts" not in d:
            (root / d / "__init__.py").touch()

    # 2. 文件映射
    files = {
        root / "requirements.txt": CODE_REQ,
        root / "main.py": CODE_MAIN,
        
        root / "src/core/interfaces.py": CODE_INTERFACES,
        root / "src/data/engine.py": CODE_DATA_ENGINE,
        root / "src/ui/viz_engine.py": CODE_VIZ_ENGINE,
        root / "src/ui/plots.py": CODE_PLOTS,
        root / "src/ui/dialogs.py": CODE_DIALOGS,
        root / "src/ui/main_window.py": CODE_MAIN_WINDOW,
        
        root / "deploy/docker-compose.yml": CODE_DOCKER,
        root / "deploy/init.sql": CODE_SQL_INIT,
        
        root / "scripts/demo_automation.py": CODE_SCRIPT_DEMO
    }
    
    # 3. 写入文件
    for p, c in files.items():
        create_file(p, c)

    # 4. 生成测试 CSV
    with open(root / "test_data.csv", "w") as f:
        f.write("LOT,WAFER,X_INDEX,Y_INDEX,VALUE\n")
        import random
        for i in range(100):
            f.write(f"L1,W1,{random.randint(-10,10)},{random.randint(-10,10)},{random.random()}\n")
    print("✔ Created: test_data.csv (For testing)")

    print("\n✨ Construction Complete! ✨")
    print("------------------------------------------------")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Run Application:      python main.py")
    print("3. Start Database:       cd deploy && docker-compose up -d")
    print("------------------------------------------------")

if __name__ == "__main__":
    confirm = input("Generate project files in CURRENT directory? (y/n): ")
    if confirm.lower() == 'y':
        main()
    else:
        print("Aborted.")