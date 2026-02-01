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