# src/ui/components/navigator.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, 
                               QLineEdit, QPushButton)
from PySide6.QtCore import Signal, Qt

class WatNavigator(QWidget):
    # [Fix] 信号改为发送两个字符串: (lot_id, wafer_id)
    wafer_selected = Signal(str, str) 

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

        grouped = df.groupby('lot_id')
        
        for lot_id, group in grouped:
            # 1. 创建 Lot 节点
            lot_node = QTreeWidgetItem([f"Lot: {lot_id}"])
            lot_node.setData(0, Qt.UserRole, "lot")
            lot_node.setData(0, Qt.UserRole + 1, lot_id) # [关键] 把纯 lot_id 存入 UserRole+1
            
            for _, row in group.iterrows():
                wafer_id = row['wafer_id']
                label = f"{wafer_id} ({str(row['test_time'])[:10]})"
                
                # 2. 创建 Wafer 节点
                wafer_node = QTreeWidgetItem([label])
                wafer_node.setData(0, Qt.UserRole, "wafer")
                wafer_node.setData(0, Qt.UserRole + 1, wafer_id) # 存 wafer_id
                
                lot_node.addChild(wafer_node)
            
            self.tree.addTopLevelItem(lot_node)
        
        self.tree.expandAll()

    def on_item_double_clicked(self, item, column):
        node_type = item.data(0, Qt.UserRole)
        
        if node_type == "wafer":
            # 1. 获取自身的 Wafer ID
            wafer_id = item.data(0, Qt.UserRole + 1)
            
            # 2. [Fix] 获取父节点 (Lot) 的 ID
            parent = item.parent()
            lot_id = parent.data(0, Qt.UserRole + 1)
            
            print(f"User selected: Lot={lot_id}, Wafer={wafer_id}")
            
            # 3. 发送组合信号
            self.wafer_selected.emit(lot_id, wafer_id)

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
