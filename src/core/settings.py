import os
import json
import sys

# 配置文件存储路径 (放在项目根目录下)
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.json")

class SettingsManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsManager, cls).__new__(cls)
            cls._instance.load_config()
        return cls._instance

    def load_config(self):
        """加载配置，如果不存在则使用默认值"""
        self.config_data = {
            "db_type": "sqlite", # 默认 sqlite
            "sqlite_path": "wat_analytics.db",
            "mysql_host": "localhost",
            "mysql_port": "3306",
            "mysql_user": "wat_user",
            "mysql_password": "wat_password",
            "mysql_db": "wat_db"
        }
        
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    saved_config = json.load(f)
                    self.config_data.update(saved_config)
            except Exception as e:
                print(f"Error loading config: {e}")

    def save_config(self, new_config):
        """保存配置到 JSON"""
        self.config_data.update(new_config)
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config_data, f, indent=4)
            print(f"Config saved to {CONFIG_FILE}")
        except Exception as e:
            print(f"Error saving config: {e}")

    def get_db_url(self):
        """根据当前配置生成 SQLAlchemy URL"""
        c = self.config_data
        if c["db_type"] == "sqlite":
            # 转换为绝对路径
            base_dir = os.path.dirname(CONFIG_FILE)
            db_path = os.path.join(base_dir, c["sqlite_path"])
            return f"sqlite:///{db_path}"
        
        elif c["db_type"] == "mysql":
            return (f"mysql+pymysql://{c['mysql_user']}:{c['mysql_password']}"
                    f"@{c['mysql_host']}:{c['mysql_port']}/{c['mysql_db']}")
        return ""

    def get_db_type(self):
        return self.config_data.get("db_type", "sqlite")

# 全局单例
settings = SettingsManager()