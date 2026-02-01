from sqlalchemy import create_engine, text

# 数据库连接
DB_URL = "mysql+pymysql://wat_user:wat_password@localhost:3306/wat_db"

SQL_CREATE_TABLES = """
-- 1. 晶圆维度表
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

-- 2. 测试项维度表
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

-- 3. 坐标维度表
CREATE TABLE IF NOT EXISTS dim_site (
    site_key INT AUTO_INCREMENT PRIMARY KEY,
    site_index INT,
    x_coord INT,
    y_coord INT,
    UNIQUE KEY uq_site_coord (site_index, x_coord, y_coord)
);

-- 4. 测量事实表
CREATE TABLE IF NOT EXISTS fact_measurement (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    wafer_key BIGINT NOT NULL,
    item_key INT NOT NULL,
    site_key INT NOT NULL,
    value FLOAT,
    INDEX idx_wafer (wafer_key),
    INDEX idx_item (item_key),
    INDEX idx_site (site_key)
) ENGINE=InnoDB;
"""

def main():
    try:
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            # 逐条执行（因为 SQLAlchemy execute 不支持一次执行多条 DDL）
            statements = SQL_CREATE_TABLES.split(';')
            for stmt in statements:
                if stmt.strip():
                    conn.execute(text(stmt))
            conn.commit()
        print("✅ 成功！表结构已手动创建。")
    except Exception as e:
        print(f"❌ 建表失败: {e}")

if __name__ == "__main__":
    main()