from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, 
                               QGroupBox, QSizePolicy, QToolButton, QMenu, QInputDialog)
from PySide6.QtCore import Signal
from PySide6.QtGui import QAction
import pandas as pd

from src.ui.components.check_combo import CheckableComboBox

class AdvancedFilterBar(QWidget):
    params_changed = Signal(list) 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.full_df = pd.DataFrame() 
        self.selection_state = {} 
        
        self.all_filters = [
            ("Module:", "module"),
            ("Device:", "device_name"), 
            ("Algo:", "algo_name"),
            ("Terminal:", "terminals"),
            ("Input:", "input_params")
        ]
        self.target_col = "param_name"
        
        self.combos = {} 
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        group = QGroupBox("Smart Multi-Filter")
        group_layout = QHBoxLayout(group)
        group_layout.setContentsMargins(10, 10, 10, 10)

        for label_text, col_name in self.all_filters:
            container = QVBoxLayout()
            container.setSpacing(1)
            
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-weight: bold; color: #555;")
            
            combo = CheckableComboBox()
            if col_name == "input_params": combo.setMinimumWidth(120)
            else: combo.setMinimumWidth(100)
            
            # 绑定信号
            combo.itemsChanged.connect(lambda items, c=col_name: self.on_filter_changed(c, items))
            
            container.addWidget(lbl)
            container.addWidget(combo)
            group_layout.addLayout(container)
            
            self.combos[col_name] = combo
            self.selection_state[col_name] = [] 

        # Parameter 区域
        container = QVBoxLayout()
        container.setSpacing(1)
        
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0,0,0,0)
        lbl = QLabel("Parameters:")
        lbl.setStyleSheet("font-weight: bold; color: #0055aa;")
        header_row.addWidget(lbl)
        
        self.btn_smart = QToolButton()
        self.btn_smart.setText("⚡")
        self.btn_smart.setToolTip("Smart Selection")
        self.btn_smart.setPopupMode(QToolButton.InstantPopup)
        self.btn_smart.clicked.connect(self.show_smart_menu)
        header_row.addWidget(self.btn_smart)
        header_row.addStretch()
        
        container.addLayout(header_row)
        
        self.multi_combo = CheckableComboBox()
        self.multi_combo.setMinimumWidth(160)
        self.multi_combo.itemsChanged.connect(self.on_param_selection_changed)
        container.addWidget(self.multi_combo)
        
        group_layout.addLayout(container)

        self.btn_reset = QPushButton("Reset")
        self.btn_reset.clicked.connect(self.reset_filters)
        self.btn_reset.setStyleSheet("color: darkred; font-weight: bold;")
        group_layout.addWidget(self.btn_reset)

        layout.addWidget(group)

    def load_data(self, df: pd.DataFrame):
        if df.empty:
            self.full_df = pd.DataFrame()
            self._clear_ui()
            return
        self.full_df = df.fillna("-").astype(str)
        self.reset_filters()

    def _clear_ui(self):
        self.block_signals_all(True)
        for c in self.combos.values(): c.clear()
        self.multi_combo.clear()
        self.block_signals_all(False)

    def reset_filters(self):
        self.block_signals_all(True)
        
        for label, col_name in self.all_filters:
            combo = self.combos[col_name]
            self.selection_state[col_name] = [] 
            
            if col_name in self.full_df.columns:
                unique_vals = sorted(self.full_df[col_name].unique())
                combo.safe_update_items(unique_vals)
            else:
                combo.clear()

        if self.target_col in self.full_df.columns:
            all_params = sorted(self.full_df[self.target_col].unique())
            self.multi_combo.safe_update_items(all_params)
        
        self.block_signals_all(False)

    def on_filter_changed(self, changed_col_name, selected_items):
        """核心级联逻辑"""
        self.selection_state[changed_col_name] = selected_items
        self.block_signals_all(True)
        
        # 遍历所有筛选器
        for label, target_col in self.all_filters:
            
            # [关键修复] 如果是当前正在操作的列，跳过更新！
            # 防止用户在输入/勾选时，列表被重置导致输入中断
            if target_col == changed_col_name:
                continue
            
            combo = self.combos[target_col]
            
            # 计算 Mask
            mask = pd.Series(True, index=self.full_df.index)
            is_constrained = False 
            
            for col_key, sel_items in self.selection_state.items():
                if col_key == target_col: continue 
                if sel_items: 
                    mask &= (self.full_df[col_key].isin(sel_items))
                    is_constrained = True
            
            if is_constrained:
                valid_options = sorted(self.full_df[mask][target_col].unique())
            else:
                valid_options = sorted(self.full_df[target_col].unique())

            # 更新 UI，保留有效勾选
            current_checked = self.selection_state[target_col]
            new_checked = [x for x in current_checked if x in valid_options]
            
            combo.safe_update_items(valid_options)
            combo.set_checked_items(new_checked, append=False)
            
            self.selection_state[target_col] = new_checked

        # 最后更新 Parameter 列表
        self._update_param_list()
        self.block_signals_all(False)

    def _update_param_list(self):
        mask = pd.Series(True, index=self.full_df.index)
        for col_name, sel_items in self.selection_state.items():
            if sel_items:
                mask &= (self.full_df[col_name].isin(sel_items))
        
        valid_df = self.full_df[mask]
        
        if self.target_col in valid_df.columns:
            valid_params = sorted(valid_df[self.target_col].unique())
            
            current_checked = self.multi_combo.get_checked_items()
            new_checked = [x for x in current_checked if x in valid_params]
            
            self.multi_combo.safe_update_items(valid_params)
            self.multi_combo.set_checked_items(new_checked, append=False)

    def on_param_selection_changed(self, checked_items):
        self.params_changed.emit(checked_items)

    def show_smart_menu(self):
        menu = QMenu(self)
        act_all = QAction("✅ Select All Visible", self)
        act_all.triggered.connect(lambda: self.batch_select_param("all"))
        menu.addAction(act_all)

        act_none = QAction("❌ Clear Selection", self)
        act_none.triggered.connect(lambda: self.batch_select_param("none"))
        menu.addAction(act_none)
        
        self.btn_smart.setMenu(menu)
        self.btn_smart.showMenu()

    def batch_select_param(self, mode):
        self.multi_combo.check_all_visible(state=(mode == "all"))

    def block_signals_all(self, block: bool):
        for c in self.combos.values(): c.blockSignals(block)
        self.multi_combo.blockSignals(block)