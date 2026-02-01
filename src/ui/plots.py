from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                               QTabWidget, QPushButton, QSpinBox, QLabel, 
                               QScrollArea, QSizePolicy, QMenu, QMessageBox, 
                               QSplitter, QDoubleSpinBox, QGroupBox)
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import MaxNLocator
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import pandas as pd

from src.core.stats import WatStatsEngine
from src.ui.components.stats_panel import CompactStatsTable

class SinglePlotWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.splitter = QSplitter(Qt.Horizontal)
        self.layout.addWidget(self.splitter)
        
        # === Left: Chart ===
        self.chart_container = QWidget()
        chart_layout = QVBoxLayout(self.chart_container)
        chart_layout.setContentsMargins(0,0,0,0)
        
        self.figure = Figure(figsize=(4, 3), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        chart_layout.addWidget(self.canvas)
        
        # === Right: Stats ===
        self.stats_table = CompactStatsTable()
        # [关键优化] 设置最小宽度，保证至少能显示出数字
        self.stats_table.setMinimumWidth(180) 
        
        self.splitter.addWidget(self.chart_container)
        self.splitter.addWidget(self.stats_table)
        
        # [关键优化] 调整比例 6:4，表格更宽
        self.splitter.setStretchFactor(0, 6)
        self.splitter.setStretchFactor(1, 4)
        
        self.ax = None
        self.current_df = pd.DataFrame()
        self.chart_type = "Wafer Map"
        self.title = ""
        self.line_style = "Lollipop"
        self.current_k = 3.0
        self.current_dev = 0.1

    def plot(self, df: pd.DataFrame, chart_type="Wafer Map", title="", line_style="Lollipop", k_val=3.0, dev_val=0.1):
        self.current_df = df.copy()
        if '_idx_' not in self.current_df.columns:
            self.current_df['_idx_'] = range(len(self.current_df))
            
        self.chart_type = chart_type
        self.title = title
        self.line_style = line_style
        self.current_k = k_val
        self.current_dev = dev_val
        
        self._draw_chart()
        self._recalc_stats()

    def update_global_params(self, k_val, dev_val):
        self.current_k = k_val
        self.current_dev = dev_val
        self._recalc_stats()

    def _recalc_stats(self):
        if self.current_df.empty: return
        self.stats_table.update_headers(self.current_k, self.current_dev * 100)
        results = WatStatsEngine.run_analysis(self.current_df, k=self.current_k, dev_threshold=self.current_dev)
        self.stats_table.update_stats(results)

    def _draw_chart(self):
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        
        if self.current_df.empty:
            self.ax.text(0.5, 0.5, "No Data", ha='center', va='center')
            self.canvas.draw()
            return

        values = self.current_df['value'].dropna()
        
        try:
            if self.chart_type == "Wafer Map":
                self._plot_map(self.current_df)
            elif self.chart_type == "Histogram":
                self._plot_histogram(values)
            elif self.chart_type == "Box Plot":
                self._plot_box(values)
            elif self.chart_type == "Line Chart":
                self._plot_line(self.current_df)
            
            if self.chart_type != "Wafer Map":
                self.ax.grid(True, linestyle='--', alpha=0.5)
            
            self.figure.tight_layout()
            self.canvas.draw()
        except Exception as e:
            print(f"Plot Error: {e}")

    def _plot_map(self, df):
        x = df['x_coord']
        y = df['y_coord']
        values = df['value']
        cmap = plt.get_cmap('jet')
        if values.max() == values.min():
            norm = mcolors.Normalize(vmin=values.min()-0.1, vmax=values.max()+0.1)
        else:
            norm = mcolors.Normalize(vmin=values.min(), vmax=values.max())
        patches = [Rectangle((xi-0.5, yi-0.5), 1, 1) for xi, yi in zip(x, y)]
        pc = PatchCollection(patches, cmap=cmap, norm=norm)
        pc.set_array(values.values)
        self.ax.add_collection(pc)
        self.ax.set_xlim(x.min()-1, x.max()+1)
        self.ax.set_ylim(y.min()-1, y.max()+1)
        self.ax.set_aspect('equal')
        self.ax.set_title(self.title, fontsize=9)
        self.ax.tick_params(labelsize=7)

    def _plot_line(self, df):
        x_data = df['_idx_']
        y_data = df['value']
        color = '#1f77b4'
        style = self.line_style
        
        if "Lollipop" in style:
            self.ax.vlines(x_data, 0, y_data, colors=color, alpha=0.6)
            self.ax.plot(x_data, y_data, color=color, marker='o', ls='', ms=3)
            self.ax.axhline(0, color='gray', ls='--')
        elif "Step" in style:
            self.ax.step(x_data, y_data, where='mid', color=color)
        elif "Area" in style:
            self.ax.fill_between(x_data, 0, y_data, color=color, alpha=0.3)
            self.ax.plot(x_data, y_data, color=color, lw=1)
        else:
            self.ax.plot(x_data, y_data, color=color, marker='o', ms=3, lw=1)
            
        self.ax.set_title(self.title, fontsize=9)
        self.ax.tick_params(labelsize=7)
        if len(df) > 50: self.ax.xaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
        else: self.ax.xaxis.set_major_locator(MaxNLocator(integer=True))

    def _plot_histogram(self, values):
        self.ax.hist(values, bins=30, color='skyblue', edgecolor='black')
        self.ax.set_title(self.title, fontsize=9)
        self.ax.tick_params(labelsize=7)

    def _plot_box(self, values):
        self.ax.boxplot(values, vert=True, patch_artist=True)
        self.ax.set_title(self.title, fontsize=9)
        self.ax.tick_params(labelsize=7)


class PlotGridPage(QWidget):
    def __init__(self, rows=2, cols=2, parent=None):
        super().__init__(parent)
        self.rows = rows
        self.cols = cols
        self.plots = [] 
        self.next_idx = 0 
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0,0,0,0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content_widget = QWidget()
        self.grid_layout = QGridLayout(self.content_widget)
        self.grid_layout.setSpacing(5)
        
        self.scroll.setWidget(self.content_widget)
        self.main_layout.addWidget(self.scroll)

    def add_plot(self, df, chart_type, title, line_style, k_val, dev_val):
        if self.next_idx >= self.rows * self.cols: return False 
        r = self.next_idx // self.cols
        c = self.next_idx % self.cols
        
        plot_widget = SinglePlotWidget()
        plot_widget.plot(df, chart_type, title, line_style, k_val, dev_val)
        
        self.grid_layout.addWidget(plot_widget, r, c)
        self.plots.append(plot_widget)
        self.next_idx += 1
        return True

    def update_all_stats(self, k_val, dev_val):
        for plot_widget in self.plots:
            plot_widget.update_global_params(k_val, dev_val)

    def clear_all(self):
        for i in reversed(range(self.grid_layout.count())): 
            w = self.grid_layout.itemAt(i).widget()
            if w: w.setParent(None)
        self.plots = []
        self.next_idx = 0


class MultiPagePlotManager(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # === Top Controls ===
        ctrl_bar = QHBoxLayout()
        
        grp_layout = QGroupBox("Grid")
        l_layout = QHBoxLayout(grp_layout)
        l_layout.setContentsMargins(2,2,2,2)
        
        self.spin_rows = QSpinBox()
        self.spin_rows.setRange(1, 5)
        self.spin_rows.setValue(2)
        self.spin_rows.setSuffix(" R")
        self.spin_rows.setFixedWidth(50)
        
        self.spin_cols = QSpinBox()
        self.spin_cols.setRange(1, 5)
        self.spin_cols.setValue(2)
        self.spin_cols.setSuffix(" C")
        self.spin_cols.setFixedWidth(50)
        
        l_layout.addWidget(self.spin_rows)
        l_layout.addWidget(self.spin_cols)
        ctrl_bar.addWidget(grp_layout)
        
        grp_stats = QGroupBox("Global Stats Params")
        l_stats = QHBoxLayout(grp_stats)
        l_stats.setContentsMargins(2,2,2,2)
        
        l_stats.addWidget(QLabel("K:"))
        self.spin_k = QDoubleSpinBox()
        self.spin_k.setRange(1.0, 9.0)
        self.spin_k.setValue(3.0)
        self.spin_k.setSingleStep(0.5)
        self.spin_k.setSuffix("σ")
        self.spin_k.setFixedWidth(60)
        self.spin_k.valueChanged.connect(self.on_global_params_changed)
        l_stats.addWidget(self.spin_k)
        
        l_stats.addWidget(QLabel("Dev:"))
        self.spin_dev = QDoubleSpinBox()
        self.spin_dev.setRange(1.0, 100.0)
        self.spin_dev.setValue(10.0)
        self.spin_dev.setSuffix("%")
        self.spin_dev.setFixedWidth(60)
        self.spin_dev.valueChanged.connect(self.on_global_params_changed)
        l_stats.addWidget(self.spin_dev)
        ctrl_bar.addWidget(grp_stats)

        self.btn_new_page = QPushButton("New Page")
        self.btn_new_page.clicked.connect(self.add_new_page)
        ctrl_bar.addWidget(self.btn_new_page)
        
        self.btn_clear_curr = QPushButton("Clear")
        self.btn_clear_curr.clicked.connect(self.clear_current_page)
        ctrl_bar.addWidget(self.btn_clear_curr)
        
        ctrl_bar.addStretch()
        self.layout.addLayout(ctrl_bar)
        
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.layout.addWidget(self.tabs)
        
        self.add_new_page()

    def add_new_page(self):
        rows = self.spin_rows.value()
        cols = self.spin_cols.value()
        page = PlotGridPage(rows, cols)
        idx = self.tabs.addTab(page, f"Page {self.tabs.count() + 1}")
        self.tabs.setCurrentIndex(idx)

    def close_tab(self, index):
        if self.tabs.count() > 1: self.tabs.removeTab(index)
        else: self.clear_current_page()

    def clear_current_page(self):
        curr = self.tabs.currentWidget()
        if isinstance(curr, PlotGridPage): curr.clear_all()

    def reset_data(self):
        while self.tabs.count() > 1: self.tabs.removeTab(1)
        self.tabs.setCurrentIndex(0)
        self.clear_current_page()

    def get_current_params(self):
        return self.spin_k.value(), self.spin_dev.value() / 100.0

    def on_global_params_changed(self):
        k, dev = self.get_current_params()
        for i in range(self.tabs.count()):
            page = self.tabs.widget(i)
            if isinstance(page, PlotGridPage):
                page.update_all_stats(k, dev)

    def plot_batch(self, plot_data_list):
        self.reset_data()
        current_page = self.tabs.widget(0)
        k, dev = self.get_current_params()
        
        for data in plot_data_list:
            success = current_page.add_plot(
                data['df'], data['chart_type'], data['title'], 
                data['line_style'], k, dev
            )
            if not success:
                self.add_new_page()
                self.tabs.setCurrentIndex(self.tabs.count()-1)
                current_page = self.tabs.currentWidget()
                current_page.add_plot(
                    data['df'], data['chart_type'], data['title'], 
                    data['line_style'], k, dev
                )
        self.tabs.setCurrentIndex(0)