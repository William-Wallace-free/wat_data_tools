import pyqtgraph as pg
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
