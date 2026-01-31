from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
                               QDialogButtonBox, QMessageBox)

class DatabaseConnectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connect to MySQL (Docker)")
        self.resize(400, 250)
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.host = QLineEdit("localhost")
        self.port = QLineEdit("3306")
        self.user = QLineEdit("wat_user")
        self.pwd = QLineEdit("wat_password")
        self.pwd.setEchoMode(QLineEdit.Password)
        self.db = QLineEdit("wat_db")
        self.query = QLineEdit("SELECT * FROM wat_data LIMIT 5000")
        
        form.addRow("Host:", self.host)
        form.addRow("Port:", self.port)
        form.addRow("User:", self.user)
        form.addRow("Password:", self.pwd)
        form.addRow("Database:", self.db)
        form.addRow("Initial Query:", self.query)
        
        layout.addLayout(form)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_info(self):
        h = self.host.text()
        p = self.port.text()
        u = self.user.text()
        pw = self.pwd.text()
        d = self.db.text()
        q = self.query.text()
        
        # SQLAlchemy Connection String
        conn_str = f"mysql+pymysql://{u}:{pw}@{h}:{p}/{d}"
        return conn_str, q
