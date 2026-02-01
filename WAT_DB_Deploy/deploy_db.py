import os
import subprocess
import sys
import time
from pathlib import Path

# ==========================================
# 1. 配置区域 (你可以修改这里)
# ==========================================
DB_CONFIG = {
    "ROOT_PASSWORD": "root_secure_password",
    "DATABASE": "wat_db",
    "USER": "wat_user",
    "PASSWORD": "wat_password",
    "PORT": "3306"
}

# ==========================================
# 2. 定义文件内容
# ==========================================

# --- A. 初始化 SQL (包含星型模型建表) ---
CONTENT_SQL = """
-- 1. 晶圆维度表 (Dimension Wafer)
CREATE TABLE IF NOT EXISTS dim_wafer (
    wafer_key BIGINT AUTO_INCREMENT PRIMARY KEY,
    lot_id VARCHAR(50),
    wafer_id VARCHAR(50),
    product_id VARCHAR(50),
    recipe_id VARCHAR(100),
    test_time DATETIME,
    equip_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_wafer (lot_id, wafer_id, test_time)
);

-- 2. 测试项维度表 (Dimension Test Item)
CREATE TABLE IF NOT EXISTS dim_test_item (
    item_key INT AUTO_INCREMENT PRIMARY KEY,
    module VARCHAR(50),
    device VARCHAR(50),
    param_name VARCHAR(100),
    unit VARCHAR(20),
    spec_low FLOAT,
    spec_high FLOAT,
    UNIQUE KEY uq_item (module, device, param_name)
);

-- 3. 坐标维度表 (Dimension Site)
CREATE TABLE IF NOT EXISTS dim_site (
    site_key INT AUTO_INCREMENT PRIMARY KEY,
    site_index INT,
    x_coord INT,
    y_coord INT,
    UNIQUE KEY uq_site_coord (site_index, x_coord, y_coord)
);

-- 4. 测量事实表 (Fact Measurement - 海量数据)
CREATE TABLE IF NOT EXISTS fact_measurement (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    wafer_key BIGINT NOT NULL,
    item_key INT NOT NULL,
    site_key INT NOT NULL,
    value FLOAT,
    
    -- 外键约束 (可选，为了性能通常在大数据场景下不强制物理外键，但保留索引)
    INDEX idx_wafer (wafer_key),
    INDEX idx_item (item_key),
    INDEX idx_site (site_key)
) ENGINE=InnoDB;
"""

# --- B. MySQL 配置文件 (针对 WAT 大数据优化) ---
# 默认 MySQL 配置内存很小，导入百万行 WAT 数据会卡死。
CONTENT_MY_CNF = """
[mysqld]
# 核心优化: 给 InnoDB 分配 1GB 缓冲池 (根据你电脑内存调整，建议 1G-4G)
innodb_buffer_pool_size = 1G
innodb_log_file_size = 256M
innodb_flush_log_at_trx_commit = 2  # 允许 1秒丢失风险换取极大写入性能提升
innodb_flush_method = O_DIRECT

# 连接设置
max_connections = 200
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci

[client]
default-character-set = utf8mb4
"""

# --- C. Docker Compose 文件 ---
CONTENT_DOCKER_COMPOSE = f"""
version: '3.8'

services:
  wat_mysql:
    image: mysql:8.0
    container_name: wat_mysql_server
    restart: always
    environment:
      MYSQL_ROOT_PASSWORD: {DB_CONFIG['ROOT_PASSWORD']}
      MYSQL_DATABASE: {DB_CONFIG['DATABASE']}
      MYSQL_USER: {DB_CONFIG['USER']}
      MYSQL_PASSWORD: {DB_CONFIG['PASSWORD']}
      TZ: Asia/Shanghai
    ports:
      - "{DB_CONFIG['PORT']}:3306"
    volumes:
      - wat_mysql_data:/var/lib/mysql
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
      - ./my.cnf:/etc/mysql/conf.d/custom.cnf
    command: --default-authentication-plugin=mysql_native_password

volumes:
  wat_mysql_data:
"""

# ==========================================
# 3. 执行逻辑
# ==========================================

def create_file(filename, content):
    path = Path(filename)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content.strip())
    print(f"✔ Created config: {filename}")

def check_docker():
    try:
        subprocess.run(["docker", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("✔ Docker is installed and reachable.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Error: Docker is not installed or not in PATH.")
        print("   Please install Docker Desktop first: https://www.docker.com/products/docker-desktop/")
        sys.exit(1)

def run_docker_compose():
    print("🚀 Starting MySQL Container...")
    try:
        subprocess.run(["docker-compose", "up", "-d"], check=True)
        print("\n✨ Database is starting up in the background!")
    except subprocess.CalledProcessError:
        print("⚠️ 'docker-compose' command not found, trying 'docker compose' (V2)...")
        try:
            subprocess.run(["docker", "compose", "up", "-d"], check=True)
            print("\n✨ Database is starting up in the background!")
        except Exception as e:
            print(f"❌ Failed to start Docker: {e}")
            sys.exit(1)

def main():
    print("--- WAT Database One-Click Setup ---")
    
    # 1. Check Docker
    check_docker()
    
    # 2. Generate Files
    create_file("init.sql", CONTENT_SQL)
    create_file("my.cnf", CONTENT_MY_CNF)
    create_file("docker-compose.yml", CONTENT_DOCKER_COMPOSE)
    
    # 3. Run
    run_docker_compose()
    
    print("-" * 50)
    print(f"✅ Setup Complete.")
    print(f"   Host:     localhost")
    print(f"   Port:     {DB_CONFIG['PORT']}")
    print(f"   User:     {DB_CONFIG['USER']}")
    print(f"   Pass:     {DB_CONFIG['PASSWORD']}")
    print(f"   DB:       {DB_CONFIG['DATABASE']}")
    print("-" * 50)
    print("⏳ Please wait 10-20 seconds for MySQL to initialize before connecting.")

if __name__ == "__main__":
    main()