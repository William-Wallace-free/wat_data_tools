from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from pyqtgraph.dockarea import DockArea, Dock

class VisualizationEngine(QWidget):
    """
    管理多页 Dock 布局
    """
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.layout.addWidget(self.tabs)
        
        self.add_page("Dashboard")

    def add_page(self, name: str):
        area = DockArea()
        self.tabs.addTab(area, name)
        return area

    def get_current_area(self) -> DockArea:
        return self.tabs.currentWidget()

    def add_widget(self, title: str, widget, position='right'):
        area = self.get_current_area()
        if not area:
            area = self.add_page("New Page")
        
        d = Dock(title, size=(500, 400))
        d.addWidget(widget)
        area.addDock(d, position)
