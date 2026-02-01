import sys
import os

from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                               QLineEdit, QPushButton, QListView, QFrame,
                               QStyle, QAbstractItemView)
from PySide6.QtCore import Qt, Signal, QEvent, QSortFilterProxyModel, QPoint, QObject, QRect
from PySide6.QtGui import QStandardItemModel, QStandardItem, QAction

# ==========================================
# 1. 全局点击事件过滤器
# ==========================================
class GlobalMouseFilter(QObject):
    def __init__(self, popup_widget):
        super().__init__()
        self.popup = popup_widget

    def eventFilter(self, obj, event):
        # 增加安全性检查：如果 popup 已经被销毁（C++对象没了），直接返回
        if not self.popup or not hasattr(self.popup, 'isVisible'):
            return False

        if event.type() in (QEvent.MouseButtonPress, QEvent.MouseButtonDblClick):
            if self.popup.isVisible():
                if isinstance(obj, QWidget):
                    pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
                    global_pos = obj.mapToGlobal(pos)
                    
                    popup_rect = self.popup.geometry()
                    
                    if hasattr(self.popup, 'parent_combo'):
                        combo = self.popup.parent_combo
                        # 增加安全性检查
                        if combo and combo.isVisible():
                            combo_rect = QRect(combo.mapToGlobal(QPoint(0,0)), combo.size())
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
        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        self.setStyleSheet("""
            QFrame { border: 1px solid #aaa; background: white; }
            QListView { border: none; outline: none; background: transparent; }
            QListView::item { padding: 4px; color: black; }
            QListView::item:hover { background: #e6f7ff; }
        """)

# ==========================================
# 3. 主控件 CheckableComboBox
# ==========================================
class CheckableComboBox(QWidget):
    itemsChanged = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.lineEdit = QLineEdit()
        self.lineEdit.setPlaceholderText("Select/Type...")
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
        
        # [核心修复 1] 缓存 Viewport 引用
        # 避免在 eventFilter 中频繁访问 self.popup.view.viewport()，防止对象销毁时崩溃
        self.view_viewport = self.popup.view.viewport()
        
        self.global_filter = GlobalMouseFilter(self.popup)
        QApplication.instance().installEventFilter(self.global_filter)
        
        self.lineEdit.textEdited.connect(self.on_text_edited)
        self.arrowBtn.clicked.connect(self.toggle_popup)
        
        # 使用缓存的引用安装过滤器
        self.view_viewport.installEventFilter(self)
        self.lineEdit.installEventFilter(self)

    # [核心修复 2] 增加 closeEvent 清理逻辑
    def closeEvent(self, event):
        # 移除全局过滤器，防止组件销毁后它还在后台运行报错
        if self.global_filter:
            QApplication.instance().removeEventFilter(self.global_filter)
        super().closeEvent(event)

    def on_text_edited(self, text):
        self.proxy_.setFilterFixedString(text)
        if not self.popup.isVisible():
            self.show_popup()
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
        # [核心修复 3] 使用缓存的 self.view_viewport 进行比较
        # 这样即使 self.popup 已经开始销毁，这里也不会因为访问 .view 而崩溃
        if obj == self.view_viewport:
            if event.type() == QEvent.MouseButtonRelease:
                pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
                index = self.popup.view.indexAt(pos)
                if index.isValid():
                    source_idx = self.proxy_.mapToSource(index)
                    item = self.model_.itemFromIndex(source_idx)
                    if item.flags() & Qt.ItemIsUserCheckable:
                        new_state = Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked
                        item.setCheckState(new_state)
                        self.itemsChanged.emit(self.get_checked_items())
                        self.lineEdit.setFocus()
                        return True
            return False

        if obj == self.lineEdit and event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                text = self.lineEdit.text().strip()
                if text:
                    self.check_all_visible(True)
                    self.hide_popup()
                return True
            if event.key() in (Qt.Key_Up, Qt.Key_Down):
                QApplication.sendEvent(self.popup.view, event)
                return True

        return super().eventFilter(obj, event)

    def check_all_visible(self, state=True):
        count = self.proxy_.rowCount()
        target_state = Qt.Checked if state else Qt.Unchecked
        changed = False
        
        self.blockSignals(True)
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

    def safe_update_items(self, items, default_state=Qt.Checked):
        self.blockSignals(True) 
        
        self.proxy_.setSourceModel(None)
        self.proxy_.setFilterFixedString("")
        self.lineEdit.clear()
        self.model_.clear()
        
        for text in items:
            item = QStandardItem(str(text))
            item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(default_state) 
            item.setToolTip(str(text))
            self.model_.appendRow(item)
            
        self.proxy_.setSourceModel(self.model_)
        
        self.blockSignals(False)

    def get_checked_items(self):
        checked = []
        for i in range(self.model_.rowCount()):
            item = self.model_.item(i)
            if item.checkState() == Qt.Checked:
                checked.append(item.text())
        return checked
    
    def clear(self): self.safe_update_items([])
    def addItems(self, t, default_state=Qt.Checked): self.safe_update_items(t, default_state)
    
    def set_checked_items(self, texts, append=False):
        target = set(texts)
        self.blockSignals(True)
        for i in range(self.model_.rowCount()):
            item = self.model_.item(i)
            txt = item.text()
            should_check = (item.checkState() == Qt.Checked) or (txt in target) if append else (txt in target)
            new_state = Qt.Checked if should_check else Qt.Unchecked
            if item.checkState() != new_state:
                item.setCheckState(new_state)
        self.blockSignals(False)
            
    def contextMenuEvent(self, event):
        menu = self.lineEdit.createStandardContextMenu()
        menu.addSeparator()
        act = QAction("✅ Select All Visible", self)
        act.triggered.connect(lambda: self.check_all_visible(True))
        menu.addAction(act)
        menu.exec(event.globalPos())