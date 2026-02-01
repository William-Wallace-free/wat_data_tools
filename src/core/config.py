import os

# === 数据库配置开关 ===
# 选项: "sqlite" 或 "mysql"
DB_TYPE = "mysql" 

# === SQLite 配置 ===
# 文件会生成在项目根目录
SQLITE_PATH = "wat_analytics.db"

# === MySQL 配置 ===
MYSQL_CONFIG = {
    "user": "wat_user",
    "password": "wat_password",
    "host": "localhost",
    "port": "3306",
    "db": "wat_db"
}

def get_db_url():
    if DB_TYPE == "sqlite":
        # SQLite 连接字符串 (使用绝对路径更安全)
        db_path = os.path.abspath(SQLITE_PATH)
        return f"sqlite:///{db_path}"
    
    elif DB_TYPE == "mysql":
        return (f"mysql+pymysql://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}"
                f"@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['db']}")
    
    else:
        raise ValueError("Unknown DB_TYPE. Please use 'sqlite' or 'mysql'.")

# 全局获取 URL
DB_URL = get_db_url()
print(f"🔧 Current Database: [{DB_TYPE.upper()}] -> {DB_URL}")