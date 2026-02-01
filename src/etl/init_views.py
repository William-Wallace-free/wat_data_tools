import sys
from sqlalchemy import create_engine, text

# 数据库连接配置 (请确保端口 3306 和密码正确)
DB_URL = "mysql+pymysql://wat_user:wat_password@localhost:3306/wat_db"

# ==========================================
# 视图定义 SQL
# ==========================================
SQL_VIEWS = [
    # 1. 明细宽表视图 (UI 画图、查参数列表专用)
    # 作用: 将星型模型还原为宽表，让 Python 可以直接查 param_name, x, y, value
    """
    CREATE OR REPLACE VIEW v_wat_detail AS
    SELECT 
        f.id AS meas_id,
        w.lot_id,
        w.wafer_id,
        w.product_id,
        w.test_time,
        t.module,
        t.device,
        t.param_name,   -- 参数名
        t.spec_low,
        t.spec_high,
        s.site_index,
        s.x_coord,      -- Die X
        s.y_coord,      -- Die Y
        f.value         -- 测试值
    FROM fact_measurement f
    JOIN dim_wafer w ON f.wafer_key = w.wafer_key
    JOIN dim_test_item t ON f.item_key = t.item_key
    JOIN dim_site s ON f.site_key = s.site_key;
    """,

    # 2. 晶圆统计视图 (可选，用于未来做汇总看板)
    """
    CREATE OR REPLACE VIEW v_wafer_summary AS
    SELECT 
        w.lot_id, 
        w.wafer_id, 
        count(f.id) as data_count
    FROM dim_wafer w
    LEFT JOIN fact_measurement f ON w.wafer_key = f.wafer_key
    GROUP BY w.wafer_key, w.lot_id, w.wafer_id;
    """
]

def init_views():
    print(f"🔌 连接数据库: {DB_URL.split('@')[-1]} ...")
    try:
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            print("🚀 正在创建/更新视图层 (View Layer)...")
            
            for i, sql in enumerate(SQL_VIEWS, 1):
                print(f"   -> Executing View Definition {i}...")
                conn.execute(text(sql))
            
            print("✅ 视图创建成功！")
            print("   -> 现在 UI 可以通过 'v_wat_detail' 查询数据了。")
            
    except Exception as e:
        print(f"❌ 创建失败: {e}")
        print("   提示: 请检查 Docker 是否运行，或是否安装了 pymysql")

if __name__ == "__main__":
    init_views()