from typing import Protocol, Any, Dict, List
import pandas as pd

class IDataLoader(Protocol):
    """数据加载器接口"""
    def load(self, source: str, **kwargs) -> pd.DataFrame: ...

class WatAutomationAPI:
    """
    自动化 API 接口层
    """
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
