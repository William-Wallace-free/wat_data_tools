from sqlalchemy import create_engine, text

DB_URL = "mysql+pymysql://wat_user:wat_password@localhost:3306/wat_db"

def fix_view():
    print(f"🔧 正在升级视图 v_wat_detail (增加 site_index)...")
    
    engine = create_engine(DB_URL)
    
    # 增加 t.site_index
    sql = text("""
        CREATE OR REPLACE VIEW v_wat_detail AS
        SELECT 
            f.id AS meas_id,
            w.lot_id, w.wafer_id, w.test_time,
            t.module, t.device, t.device_name, t.param_name, 
            t.algo_name, t.terminals, t.input_params,
            s.site_index,    -- [新增] Site Index
            s.x_coord, s.y_coord,
            f.value
        FROM fact_measurement f
        JOIN dim_wafer w ON f.wafer_key = w.wafer_key
        JOIN dim_test_item t ON f.item_key = t.item_key
        JOIN dim_site s ON f.site_key = s.site_key;
    """)
    
    try:
        with engine.connect() as conn:
            conn.execute(sql)
            print("✅ 视图升级成功！")
    except Exception as e:
        print(f"❌ 修复失败: {e}")

if __name__ == "__main__":
    fix_view()