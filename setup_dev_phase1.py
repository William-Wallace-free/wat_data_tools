import os
from pathlib import Path

# ==========================================
# 1. 数据访问层 (Repository)
# 作用: 把 SQL 细节封装起来，UI 只管调用函数
# ==========================================
CODE_REPO = """import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

class WatRepository:
    def __init__(self, db_url):
        self.engine = create_engine(db_url)

    def check_connection(self):
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except:
            return False

    def get_navigation_tree(self):
        \"\"\"
        获取导航树结构: Lot -> Wafer
        返回: DataFrame [lot_id, wafer_id, test_time]
        \"\"\"
        sql = text(\"\"\"
            SELECT lot_id, wafer_id, test_time 
            FROM dim_wafer 
            ORDER BY test_time DESC
        \"\"\")
        try:
            with self.engine.connect() as conn:
                return pd.read_sql(sql, conn)
        except Exception as e:
            print(f"Repo Error: {e}")
            return pd.DataFrame()

    def get_wafer_params(self, wafer_id):
        \"\"\"获取某片晶圆测试了哪些参数\"\"\"
        sql = text(\"\"\"
            SELECT DISTINCT param_name 
            FROM v_wat_detail 
            WHERE wafer_id = :wid 
            ORDER BY param_name
        \"\"\")
        try:
            with self.engine.connect() as conn:
                df = pd.read_sql(sql, conn, params={"wid": wafer_id})
                return df['param_name'].tolist()
        except:
            return []

    def get_wafer_map_data(self, wafer_id, param_name):
        \"\"\"
        获取画 Map 所需的数据
        返回: DataFrame [x_coord, y_coord, value]
        \"\"\"
        sql = text(\"\"\"
            SELECT x_coord, y_coord, value 
            FROM v_wat_detail 
            WHERE wafer_id = :wid AND param_name = :p
        \"\"\")
        try:
            with self.engine.connect() as conn:
                return pd.read_sql(sql, conn, params={"wid": wafer_id, "p": param_name})
        except Exception as e:
            print(f"Map Data Error: {e}")
            return pd.DataFrame()
"""

# ==========================================
# 2. UI 组件: 智能导航栏
# 作用: 自动加载数据库里的 Lot 和 Wafer
# ==========================================
CODE_NAVIGATOR = """from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, 
                               QLineEdit, QLabel, QPushButton)
from PySide6.QtCore import Signal, Qt

class WatNavigator(QWidget):
    # 定义信号: 当用户双击某个晶圆时，要把 wafer_id 发送给主窗口
    wafer_selected = Signal(str) 

    def __init__(self, repository):
        super().__init__()
        self.repo = repository
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 搜索框
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search Lot or Wafer...")
        self.search_bar.textChanged.connect(self.filter_tree)
        layout.addWidget(self.search_bar)

        # 树形控件
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("WAT Database")
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.tree)
        
        # 刷新按钮
        btn_refresh = QPushButton("Refresh List")
        btn_refresh.clicked.connect(self.load_data)
        layout.addWidget(btn_refresh)

    def load_data(self):
        self.tree.clear()
        df = self.repo.get_navigation_tree()
        
        if df.empty:
            item = QTreeWidgetItem(["No Data Found"])
            self.tree.addTopLevelItem(item)
            return

        # 核心逻辑: 把 DataFrame 转成 Tree
        # Group by Lot_ID
        grouped = df.groupby('lot_id')
        
        for lot_id, group in grouped:
            lot_node = QTreeWidgetItem([f"Lot: {lot_id}"])
            # 存储元数据，方便后续使用
            lot_node.setData(0, Qt.UserRole, "lot") 
            
            for _, row in group.iterrows():
                wafer_id = row['wafer_id']
                # 显示 Wafer ID 和时间
                label = f"{wafer_id} ({str(row['test_time'])[:10]})"
                wafer_node = QTreeWidgetItem([label])
                wafer_node.setData(0, Qt.UserRole, "wafer")
                wafer_node.setData(0, Qt.UserRole + 1, wafer_id) # 存下真实的 ID
                
                lot_node.addChild(wafer_node)
            
            self.tree.addTopLevelItem(lot_node)
        
        self.tree.expandAll()

    def on_item_double_clicked(self, item, column):
        node_type = item.data(0, Qt.UserRole)
        if node_type == "wafer":
            wafer_id = item.data(0, Qt.UserRole + 1)
            print(f"User selected wafer: {wafer_id}")
            self.wafer_selected.emit(wafer_id)

    def filter_tree(self, text):
        # 简单的搜索过滤逻辑
        # 遍历所有 Lot 节点
        for i in range(self.tree.topLevelItemCount()):
            lot_item = self.tree.topLevelItem(i)
            lot_visible = False
            
            # 检查 Wafer 子节点
            for j in range(lot_item.childCount()):
                wafer_item = lot_item.child(j)
                if text.lower() in wafer_item.text(0).lower():
                    wafer_item.setHidden(False)
                    lot_visible = True
                else:
                    wafer_item.setHidden(True)
            
            # 如果 Lot 名字匹配，或者有子节点匹配，则显示 Lot
            if text.lower() in lot_item.text(0).lower():
                lot_visible = True
                # 如果是 Lot 匹配，把所有子节点显示出来
                for j in range(lot_item.childCount()):
                    lot_item.child(j).setHidden(False)
            
            lot_item.setHidden(not lot_visible)
"""

# ==========================================
# 3. 集成到主程序 (Main Window)
# ==========================================
CODE_MAIN_UPDATED = """import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QDockWidget, QMessageBox, 
                               QLabel, QWidget, QVBoxLayout, QComboBox)
from PySide6.QtCore import Qt

# 引入我们生成的模块
from src.core.repository import WatRepository
from src.ui.components.navigator import WatNavigator
from src.ui.plots import WaferMapWidget # 复用之前的绘图组件

# 数据库连接 (如果你改了端口这里要改)
DB_URL = "mysql+pymysql://wat_user:wat_password@localhost:3306/wat_db"

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WAT Analytics Enterprise (DB Integrated)")
        self.resize(1200, 800)

        # 1. 初始化核心服务
        self.repo = WatRepository(DB_URL)
        if not self.repo.check_connection():
            QMessageBox.critical(self, "Error", "Database Connection Failed!\\nPlease check Docker.")
        
        # 2. UI 布局
        self.init_ui()

    def init_ui(self):
        # --- 左侧: 导航栏 Dock ---
        self.nav_dock = QDockWidget("Data Navigator", self)
        self.nav_dock.setAllowedAreas(Qt.LeftDockWidgetArea)
        
        # 实例化导航组件，并注入 repo
        self.navigator = WatNavigator(self.repo)
        self.navigator.wafer_selected.connect(self.on_wafer_selected)
        
        self.nav_dock.setWidget(self.navigator)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.nav_dock)

        # --- 中间: 内容区域 ---
        center_widget = QWidget()
        self.setCentralWidget(center_widget)
        self.main_layout = QVBoxLayout(center_widget)
        
        # 顶部工具栏 (参数选择)
        self.param_combo = QComboBox()
        self.param_combo.setPlaceholderText("Select Parameter to Plot")
        self.param_combo.currentIndexChanged.connect(self.update_plot)
        self.main_layout.addWidget(self.param_combo)

        # 绘图区
        self.map_widget = WaferMapWidget()
        self.main_layout.addWidget(self.map_widget)
        
        # 状态栏
        self.statusBar().showMessage("Ready.")
        
        # 暂存当前选中的 WaferID
        self.current_wafer_id = None

    def on_wafer_selected(self, wafer_id):
        \"\"\"当左侧树选择了晶圆\"\"\"
        self.current_wafer_id = wafer_id
        self.statusBar().showMessage(f"Loading params for {wafer_id}...")
        
        # 1. 获取该晶圆的所有测试参数
        params = self.repo.get_wafer_params(wafer_id)
        
        # 2. 更新下拉框
        self.param_combo.blockSignals(True) # 防止触发绘图
        self.param_combo.clear()
        self.param_combo.addItems(params)
        self.param_combo.blockSignals(False)
        
        self.statusBar().showMessage(f"Loaded {wafer_id}. Please select a parameter.")
        
        # 默认选中第一个参数并绘图
        if params:
            self.param_combo.setCurrentIndex(0)
            self.update_plot()

    def update_plot(self):
        \"\"\"画图逻辑\"\"\"
        param = self.param_combo.currentText()
        if not self.current_wafer_id or not param:
            return
            
        self.statusBar().showMessage(f"Plotting {param}...")
        
        # 1. 从数据库取数 (只取 X, Y, Value)
        df = self.repo.get_wafer_map_data(self.current_wafer_id, param)
        
        # 2. 交给绘图组件
        if not df.empty:
            self.map_widget.plot_dataframe(df)
            self.statusBar().showMessage(f"Showing {param} on {self.current_wafer_id}")
        else:
            self.statusBar().showMessage("No data found for this parameter.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
"""

def create_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✔ Created: {path}")

def main():
    root = Path(os.getcwd())
    
    # 1. 确保目录存在
    (root / "src/core").mkdir(parents=True, exist_ok=True)
    (root / "src/ui/components").mkdir(parents=True, exist_ok=True)
    
    # 2. 生成文件
    create_file(root / "src/core/repository.py", CODE_REPO)
    create_file(root / "src/ui/components/navigator.py", CODE_NAVIGATOR)
    
    # 3. 更新 Main (我们创建一个新的 main_v2.py 避免覆盖你原有的，你可以自己改名)
    create_file(root / "main_v2.py", CODE_MAIN_UPDATED)
    
    print("\\n✨ Phase 1 Development Complete! ✨")
    print("Run: python main_v2.py")

if __name__ == "__main__":
    main()