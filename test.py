import sys
import os

# 1. 屏蔽干扰日志
os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.gui.imageio*=false"

from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                               QLineEdit, QPushButton, QListView, QFrame, QLabel,
                               QStyle, QAbstractItemView)
from PySide6.QtCore import Qt, Signal, QEvent, QSortFilterProxyModel, QPoint, QObject, QRect
from PySide6.QtGui import QStandardItemModel, QStandardItem, QAction

# ==========================================
# 1. 全局点击事件过滤器 (修复版)
# ==========================================
class GlobalMouseFilter(QObject):
    def __init__(self, popup_widget):
        super().__init__()
        self.popup = popup_widget

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.MouseButtonPress, QEvent.MouseButtonDblClick):
            if self.popup.isVisible():
                if isinstance(obj, QWidget):
                    # [修复] 解决 Qt6 DeprecationWarning
                    pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
                    global_pos = obj.mapToGlobal(pos)
                    
                    popup_rect = self.popup.geometry()
                    
                    if hasattr(self.popup, 'parent_combo'):
                        combo = self.popup.parent_combo
                        combo_rect = QRect(combo.mapToGlobal(QPoint(0,0)), combo.size())

                        # 点击既不在弹窗里 也不在输入框里 -> 关闭
                        if not popup_rect.contains(global_pos) and not combo_rect.contains(global_pos):
                            self.popup.hide()
        return False

# ==========================================
# 2. 独立的列表窗口 (Tool 类型)
# ==========================================
class PopupListWidget(QFrame):
    def __init__(self, parent_combo):
        super().__init__(None, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.parent_combo = parent_combo
        
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        
        self.view = QListView()
        self.layout().addWidget(self.view)
        
        self.view.setUniformItemSizes(True)
        self.view.setFocusPolicy(Qt.NoFocus)
        self.view.setSelectionMode(QAbstractItemView.NoSelection)
        # [关键] 禁用 View 自带的编辑触发，完全靠 EventFilter 接管
        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        self.setStyleSheet("""
            QFrame { border: 1px solid #aaa; background: white; }
            QListView { border: none; outline: none; background: transparent; }
            QListView::item { padding: 4px; color: black; }
            QListView::item:hover { background: #e6f7ff; }
        """)

# ==========================================
# 3. 主控件 CheckableComboBox (V3.7)
# ==========================================
class CheckableComboBox(QWidget):
    itemsChanged = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.lineEdit = QLineEdit()
        self.lineEdit.setPlaceholderText("Search to Select All...")
        self.lineEdit.setStyleSheet("border: 1px solid #aaa; border-right: none; padding: 4px;")
        
        self.arrowBtn = QPushButton()
        self.arrowBtn.setFixedWidth(20)
        self.arrowBtn.setStyleSheet("border: 1px solid #aaa; border-left: none; background: #eee;")
        self.arrowBtn.setIcon(self.style().standardIcon(QStyle.SP_TitleBarUnshadeButton))
        self.arrowBtn.setFlat(True)
        self.arrowBtn.setFocusPolicy(Qt.NoFocus)
        
        layout.addWidget(self.lineEdit)
        layout.addWidget(self.arrowBtn)
        
        self.model_ = QStandardItemModel(self)
        self.proxy_ = QSortFilterProxyModel(self)
        self.proxy_.setSourceModel(self.model_)
        self.proxy_.setFilterCaseSensitivity(Qt.CaseInsensitive)
        
        self.popup = PopupListWidget(self)
        self.popup.view.setModel(self.proxy_)
        
        self.global_filter = GlobalMouseFilter(self.popup)
        QApplication.instance().installEventFilter(self.global_filter)
        
        self.lineEdit.textEdited.connect(self.on_text_edited)
        self.arrowBtn.clicked.connect(self.toggle_popup)
        
        # [关键] 霸道拦截列表点击
        self.popup.view.viewport().installEventFilter(self)
        self.lineEdit.installEventFilter(self)

    def on_text_edited(self, text):
        """输入文字时：过滤 + 展开 + 自动全选可见项"""
        self.proxy_.setFilterFixedString(text)
        
        if not self.popup.isVisible():
            self.show_popup()
            
        # [核心需求 V3.7] 只要在搜索，就把筛选出来的全勾上
        if text:
            self.check_all_visible(True)

    def show_popup(self):
        pos = self.mapToGlobal(QPoint(0, self.height()))
        width = self.width()
        
        fm = self.fontMetrics()
        max_w = 0
        limit = min(self.proxy_.rowCount(), 50)
        for i in range(limit):
             idx = self.proxy_.index(i, 0)
             txt = self.proxy_.data(idx)
             if txt: max_w = max(max_w, fm.horizontalAdvance(str(txt)) + 60)
        
        final_w = max(width, min(max_w, 800))
        self.popup.setGeometry(pos.x(), pos.y(), final_w, 200)
        self.popup.show()

    def hide_popup(self):
        self.popup.hide()
        self.lineEdit.clear()
        self.proxy_.setFilterFixedString("")

    def toggle_popup(self):
        if self.popup.isVisible():
            self.hide_popup()
        else:
            self.show_popup()
            self.lineEdit.setFocus()

    def eventFilter(self, obj, event):
        # 拦截列表点击 -> 手动翻转状态
        if obj == self.popup.view.viewport():
            if event.type() == QEvent.MouseButtonRelease:
                # 兼容 Qt6
                pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
                index = self.popup.view.indexAt(pos)
                if index.isValid():
                    source_idx = self.proxy_.mapToSource(index)
                    item = self.model_.itemFromIndex(source_idx)
                    if item.flags() & Qt.ItemIsUserCheckable:
                        # 翻转状态
                        new_state = Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked
                        item.setCheckState(new_state)
                        self.itemsChanged.emit(self.get_checked_items())
                        self.lineEdit.setFocus()
                        return True
            return False

        # 拦截输入框按键
        if obj == self.lineEdit and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                text = self.lineEdit.text().strip()
                if text:
                    # 回车确认全选并关闭
                    self.check_all_visible(True)
                    self.hide_popup()
                return True
            if event.key() in (Qt.Key_Up, Qt.Key_Down):
                QApplication.sendEvent(self.popup.view, event)
                return True

        return super().eventFilter(obj, event)

    def check_all_visible(self, state=True):
        """将当前列表中可见的所有项设为指定状态"""
        count = self.proxy_.rowCount()
        target_state = Qt.Checked if state else Qt.Unchecked
        changed = False
        
        self.blockSignals(True) # 暂时屏蔽信号
        for i in range(count):
            proxy_idx = self.proxy_.index(i, 0)
            source_idx = self.proxy_.mapToSource(proxy_idx)
            item = self.model_.itemFromIndex(source_idx)
            if item.checkState() != target_state:
                item.setCheckState(target_state)
                changed = True
        self.blockSignals(False)
        
        if changed:
            self.itemsChanged.emit(self.get_checked_items())

    def safe_update_items(self, items):
        self.proxy_.setSourceModel(None)
        self.proxy_.setFilterFixedString("")
        self.lineEdit.clear()
        self.model_.clear()
        
        for text in items:
            item = QStandardItem(str(text))
            item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            # [修改] 初始加载默认全部选中
            item.setCheckState(Qt.Checked) 
            item.setToolTip(str(text))
            self.model_.appendRow(item)
            
        self.proxy_.setSourceModel(self.model_)
        # [修改] 加载完立即通知
        if items:
            self.itemsChanged.emit(items)

    def get_checked_items(self):
        checked = []
        for i in range(self.model_.rowCount()):
            item = self.model_.item(i)
            if item.checkState() == Qt.Checked:
                checked.append(item.text())
        return checked
    
    def clear(self): self.safe_update_items([])
    def addItems(self, t): self.safe_update_items(t)
    def set_checked_items(self, texts, append=False):
        target = set(texts)
        changed = False
        self.blockSignals(True)
        for i in range(self.model_.rowCount()):
            item = self.model_.item(i)
            txt = item.text()
            should_check = (item.checkState() == Qt.Checked) or (txt in target) if append else (txt in target)
            new_state = Qt.Checked if should_check else Qt.Unchecked
            if item.checkState() != new_state:
                item.setCheckState(new_state)
                changed = True
        self.blockSignals(False)
        if changed: self.itemsChanged.emit(self.get_checked_items())
            
    def contextMenuEvent(self, event):
        menu = self.lineEdit.createStandardContextMenu()
        menu.addSeparator()
        act = QAction("✅ Select All Visible", self)
        act.triggered.connect(lambda: self.check_all_visible(True))
        menu.addAction(act)
        menu.exec(event.globalPos())

# ==========================================
# 4. 测试入口
# ==========================================
class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.resize(500, 300)
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        lbl = QLabel("<h3>Search Auto-Select Test</h3>"
                     "<ul>"
                     "<li><b>On Load:</b> All items are checked by default.</li>"
                     "<li><b>Type 'M':</b> Only 'Module_...' items are shown AND auto-checked.</li>"
                     "<li><b>Uncheck:</b> You can manually uncheck items in the filtered list.</li>"
                     "</ul>")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)
        
        self.combo = CheckableComboBox()
        # 模拟数据
        data = ["Special_NMOS", "Special_PMOS"] + [f"Module_{i}" for i in range(20)]
        self.combo.safe_update_items(data)
        
        self.result_lbl = QLabel("Selection: []")
        self.result_lbl.setWordWrap(True)
        self.combo.itemsChanged.connect(lambda items: self.result_lbl.setText(f"Selection ({len(items)}): {items}"))
        
        layout.addWidget(self.combo)
        layout.addWidget(self.result_lbl)
        layout.addStretch()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = TestWindow()
    win.show()
    sys.exit(app.exec())