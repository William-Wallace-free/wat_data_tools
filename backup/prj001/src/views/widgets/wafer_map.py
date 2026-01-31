import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout

class WaferMapWidget(QWidget):
    """
    封装 PyQtGraph，对外只暴露 plot_data 接口，
    让上层 View 不用关心具体的绘图库实现。
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # 初始化 PlotWidget
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w') # 白色背景
        self.plot_widget.setAspectLocked(True)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.layout.addWidget(self.plot_widget)
        
        self.scatter = None

    def plot_data(self, data):
        self.plot_widget.clear()
        
        x = data['x']
        y = data['y']
        values = data['values']
        
        # 简单的颜色映射 (归一化到 0-255)
        # 实际项目中建议使用 pg.ColorMap
        norm_vals = (values - values.min()) / (values.max() - values.min())
        brushes = [pg.intColor(int(v * 255), alpha=200) for v in norm_vals]
        
        self.scatter = pg.ScatterPlotItem(
            x=x, y=y, size=8, brush=brushes, pen=None, hoverable=True
        )
        self.plot_widget.addItem(self.scatter)
        self.plot_widget.setTitle(f"Total Points: {len(x)}")
