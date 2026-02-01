from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QLabel)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

class CompactStatsTable(QWidget):
    """
    [优化版] 紧凑型统计表，针对小尺寸网格进行了适配。
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0) # 零边距
        
        self.table = QTableWidget()
        self.layout.addWidget(self.table)
        self.setup_table()

    def setup_table(self):
        columns = ["Raw", "K-Sigma", "IQR"]
        rows = [
            "Mean", "Stdev", "Median", 
            "Std/Mean", "Std/Med",
            "Dev(Mn)>", "Dev(Md)>", # 缩写标题以节省空间
            "Count", "Outliers", "List"
        ]
        
        self.table.setColumnCount(len(columns))
        self.table.setRowCount(len(rows))
        self.table.setVerticalHeaderLabels(rows)
        self.table.setHorizontalHeaderLabels(columns)
        
        # === 核心布局优化 ===
        header = self.table.horizontalHeader()
        # 列宽策略：所有列平均分配，或者 ResizeToContents
        # 这里使用 Stretch 保证填满，但在 update_stats 时我们会 resizeColumnsToContents
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setMinimumSectionSize(30) # 允许压得很窄
        
        v_header = self.table.verticalHeader()
        v_header.setSectionResizeMode(QHeaderView.Fixed)
        v_header.setDefaultSectionSize(18) # 极度紧凑的行高
        
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(True)
        
        # 样式表：小字体，无边框，背景色
        self.table.setStyleSheet("""
            QTableWidget {
                border: none;
                font-family: "Segoe UI", Arial;
                font-size: 8pt; 
                background-color: #fafafa;
            }
            QHeaderView::section {
                background-color: #e5e5e5;
                font-weight: bold;
                border: 1px solid #d0d0d0;
                font-size: 7pt;
                padding: 0px;
                height: 18px;
            }
            QTableCornerButton::section {
                background-color: #e5e5e5;
                border: 1px solid #d0d0d0;
            }
            QTableWidget::item {
                padding-left: 0px;
                padding-right: 0px;
            }
        """)

    def update_headers(self, k_val, dev_val):
        # 缩写标题以适应窄列
        self.table.setHorizontalHeaderItem(1, QTableWidgetItem(f"K-Sig({k_val}σ)"))
        
        v_header = self.table.verticalHeader()
        self.table.setVerticalHeaderItem(5, QTableWidgetItem(f"Dev(Mn)>{dev_val:.0f}%"))
        self.table.setVerticalHeaderItem(6, QTableWidgetItem(f"Dev(Md)>{dev_val:.0f}%"))

    def update_stats(self, stats_data):
        self.table.clearContents()
        
        groups = ["Raw", "K-Sigma", "IQR"]
        
        for col_idx, group_key in enumerate(groups):
            data = stats_data.get(group_key, {})
            
            def set_cell(row, val, color=None, bg=None, tooltip=None, bold=False):
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                if color: item.setForeground(QColor(color))
                if bg: item.setBackground(QColor(bg))
                if tooltip: item.setToolTip(tooltip)
                # 字体微调
                font = item.font()
                font.setPointSize(8)
                if bold: font.setBold(True)
                item.setFont(font)
                self.table.setItem(row, col_idx, item)

            # 格式化数字：保留合理的小数位，太长就科学计数
            def fmt(v):
                if isinstance(v, (int, float)):
                    if abs(v) > 10000 or (abs(v) < 0.001 and v != 0):
                        return f"{v:.2e}"
                    return f"{v:.3f}"
                return str(v)

            set_cell(0, fmt(data.get('mean', 0)))
            set_cell(1, fmt(data.get('std', 0)))
            set_cell(2, fmt(data.get('median', 0)))
            
            set_cell(3, f"{data.get('cv_mean', 0)*100:.1f}%")
            set_cell(4, f"{data.get('cv_median', 0)*100:.1f}%")
            
            d_mean = data.get('dev_mean_cnt', 0)
            set_cell(5, d_mean, color="blue" if d_mean > 0 else None, bold=(d_mean>0))
            
            d_med = data.get('dev_med_cnt', 0)
            set_cell(6, d_med, color="blue" if d_med > 0 else None, bold=(d_med>0))
            
            set_cell(7, data.get('count', 0))
            
            out_cnt = data.get('outlier_count', 0)
            set_cell(8, out_cnt, 
                     color="red" if out_cnt > 0 and group_key!="Raw" else None,
                     bg="#fff0f0" if out_cnt > 0 and group_key!="Raw" else None,
                     bold=(out_cnt>0))
            
            out_list = data.get('outliers', "")
            # 列表只显示简略信息
            short_list = "..." if len(out_list) > 10 else out_list
            set_cell(9, short_list, tooltip=out_list)

        # [关键] 填完数据后，尝试调整列宽
        # 但为了防止跳变，保持 Stretch 并在必要时显示省略号