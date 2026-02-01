from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QLineEdit, QComboBox, QPushButton, QMessageBox, 
                               QGroupBox, QFormLayout)
from sqlalchemy import create_engine, text
from src.core.settings import settings

class DbSetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Database Connection Settings")
        self.resize(400, 350)
        self.init_ui()
        self.load_current_settings()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 1. 数据库类型选择
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Database Type:"))
        self.combo_type = QComboBox()
        self.combo_type.addItems(["SQLite (Local File)", "MySQL (Server)"])
        self.combo_type.currentIndexChanged.connect(self.toggle_inputs)
        type_layout.addWidget(self.combo_type)
        layout.addLayout(type_layout)

        # 2. SQLite 设置区
        self.group_sqlite = QGroupBox("SQLite Settings")
        form_sqlite = QFormLayout(self.group_sqlite)
        self.txt_sqlite_path = QLineEdit("wat_analytics.db")
        form_sqlite.addRow("DB Filename:", self.txt_sqlite_path)
        layout.addWidget(self.group_sqlite)

        # 3. MySQL 设置区
        self.group_mysql = QGroupBox("MySQL Settings")
        form_mysql = QFormLayout(self.group_mysql)
        self.txt_host = QLineEdit("localhost")
        self.txt_port = QLineEdit("3306")
        self.txt_user = QLineEdit("root")
        self.txt_pass = QLineEdit()
        self.txt_pass.setEchoMode(QLineEdit.Password)
        self.txt_db = QLineEdit("wat_db")
        
        form_mysql.addRow("Host:", self.txt_host)
        form_mysql.addRow("Port:", self.txt_port)
        form_mysql.addRow("User:", self.txt_user)
        form_mysql.addRow("Password:", self.txt_pass)
        form_mysql.addRow("Database:", self.txt_db)
        layout.addWidget(self.group_mysql)

        # 4. 按钮区
        btn_layout = QHBoxLayout()
        self.btn_test = QPushButton("Test Connection")
        self.btn_test.clicked.connect(self.test_connection)
        
        self.btn_save = QPushButton("Save & Apply")
        self.btn_save.clicked.connect(self.save_settings)
        self.btn_save.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white;")
        
        btn_layout.addWidget(self.btn_test)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def toggle_inputs(self):
        is_mysql = self.combo_type.currentText().startswith("MySQL")
        self.group_mysql.setVisible(is_mysql)
        self.group_sqlite.setVisible(not is_mysql)

    def load_current_settings(self):
        """从 settings 加载并填入 UI"""
        c = settings.config_data
        if c["db_type"] == "mysql":
            self.combo_type.setCurrentIndex(1)
        else:
            self.combo_type.setCurrentIndex(0)
            
        self.txt_sqlite_path.setText(c.get("sqlite_path", "wat_analytics.db"))
        self.txt_host.setText(c.get("mysql_host", "localhost"))
        self.txt_port.setText(c.get("mysql_port", "3306"))
        self.txt_user.setText(c.get("mysql_user", ""))
        self.txt_pass.setText(c.get("mysql_password", ""))
        self.txt_db.setText(c.get("mysql_db", "wat_db"))
        
        self.toggle_inputs()

    def get_ui_data(self):
        is_mysql = self.combo_type.currentText().startswith("MySQL")
        return {
            "db_type": "mysql" if is_mysql else "sqlite",
            "sqlite_path": self.txt_sqlite_path.text(),
            "mysql_host": self.txt_host.text(),
            "mysql_port": self.txt_port.text(),
            "mysql_user": self.txt_user.text(),
            "mysql_password": self.txt_pass.text(),
            "mysql_db": self.txt_db.text()
        }

    def test_connection(self):
        data = self.get_ui_data()
        url = ""
        try:
            if data["db_type"] == "sqlite":
                url = f"sqlite:///{data['sqlite_path']}"
            else:
                url = (f"mysql+pymysql://{data['mysql_user']}:{data['mysql_password']}"
                       f"@{data['mysql_host']}:{data['mysql_port']}/{data['mysql_db']}")
            
            engine = create_engine(url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            QMessageBox.information(self, "Success", "Connection Successful!")
        except Exception as e:
            QMessageBox.critical(self, "Connection Failed", str(e))

    def save_settings(self):
        # 保存并关闭
        new_config = self.get_ui_data()
        settings.save_config(new_config)
        self.accept()