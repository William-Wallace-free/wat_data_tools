import sys
import os
from sqlalchemy import (create_engine, MetaData, Table, Column, Integer, String, 
                        Float, DateTime, Text, ForeignKey, UniqueConstraint, Index, text)

# [修改] 这是一个纯函数，不再依赖全局配置，由调用者传入 db_url 和 db_type
def init_db(db_url, db_type):
    print(f"🚀 Initializing Database ({db_type.upper()})...")
    print(f"   Target: {db_url}")
    
    engine = create_engine(db_url)
    metadata = MetaData()

    # --- Dim Wafer ---
    dim_wafer = Table('dim_wafer', metadata,
        Column('wafer_key', Integer, primary_key=True, autoincrement=True),
        Column('lot_id', String(50), nullable=False),
        Column('wafer_id', String(50), nullable=False),
        Column('product_id', String(50)),
        Column('test_time', DateTime),
        UniqueConstraint('lot_id', 'wafer_id', name='uq_wafer')
    )

    # --- Dim Site ---
    dim_site = Table('dim_site', metadata,
        Column('site_key', Integer, primary_key=True, autoincrement=True),
        Column('site_index', Integer),
        Column('x_coord', Integer),
        Column('y_coord', Integer),
        UniqueConstraint('site_index', 'x_coord', 'y_coord', name='uq_site')
    )

    # --- Dim Test Item ---
    dim_test_item = Table('dim_test_item', metadata,
        Column('item_key', Integer, primary_key=True, autoincrement=True),
        Column('module', String(50)),
        Column('device', String(50)),
        Column('param_name', String(100)),
        Column('algo_name', String(100)),
        Column('device_name', String(100)),
        Column('input_params', Text),
        Column('terminals', String(100)),
        Column('spec_low', Float),
        Column('spec_high', Float),
        Column('unit', String(20)),
        UniqueConstraint('module', 'device', 'param_name', name='uq_item')
    )

    # --- Fact Measurement ---
    fact_measurement = Table('fact_measurement', metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('wafer_key', Integer, ForeignKey('dim_wafer.wafer_key')),
        Column('site_key', Integer, ForeignKey('dim_site.site_key')),
        Column('item_key', Integer, ForeignKey('dim_test_item.item_key')),
        Column('value', Float),
    )
    Index('idx_fact_w_i', fact_measurement.c.wafer_key, fact_measurement.c.item_key)

    # 1. 建表
    metadata.create_all(engine)
    print("✅ Tables Created.")

    # 2. 建视图
    view_sql_drop = "DROP VIEW IF EXISTS v_wat_detail"
    view_sql_create = """
    CREATE VIEW v_wat_detail AS
    SELECT 
        f.id AS meas_id,
        w.lot_id, w.wafer_id, w.test_time,
        t.module, t.device, t.device_name, t.param_name, 
        t.algo_name, t.input_params, t.terminals, 
        s.site_index, s.x_coord, s.y_coord,
        f.value
    FROM fact_measurement f
    JOIN dim_wafer w ON f.wafer_key = w.wafer_key
    JOIN dim_test_item t ON f.item_key = t.item_key
    JOIN dim_site s ON f.site_key = s.site_key;
    """

    try:
        with engine.connect() as conn:
            conn.execute(text(view_sql_drop))
            conn.execute(text(view_sql_create))
            print("✅ View (v_wat_detail) Created.")
    except Exception as e:
        print(f"❌ View Creation Failed: {e}")

# 兼容命令行独立运行 (测试用)
if __name__ == "__main__":
    # 为了测试，这里临时引用 settings，实际使用由 main 传入
    try:
        # 路径 hack
        current = os.path.dirname(os.path.abspath(__file__))
        root = os.path.dirname(os.path.dirname(current))
        sys.path.insert(0, root)
        
        from src.core.settings import settings
        init_db(settings.get_db_url(), settings.get_db_type())
    except ImportError:
        print("Please run from project root via 'python main_v2.py'")