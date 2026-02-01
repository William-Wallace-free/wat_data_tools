import pandas as pd
from sqlalchemy import create_engine, text

class WatRepository:
    def __init__(self, db_url):
        self.engine = create_engine(db_url)

    def check_connection(self):
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            print(f"DB Connection Error: {e}")
            return False

    def get_navigation_tree(self):
        """
        [修复] 方法名改为 get_navigation_tree 以匹配 UI 调用
        获取所有 Wafer 列表（用于导航栏）
        """
        sql = text("""
            SELECT lot_id, wafer_id, test_time 
            FROM dim_wafer 
            ORDER BY test_time DESC
        """)
        try:
            with self.engine.connect() as conn:
                return pd.read_sql(sql, conn)
        except Exception as e:
            print(f"Repo Error (get_tree): {e}")
            return pd.DataFrame()

    def get_wafer_test_structure(self, lot_id, wafer_id):
        """
        获取某个 Wafer 的所有测试项结构（用于筛选器）
        """
        # [关键保留] 必须包含 input_params，否则 filter_bar 报错
        sql = text("""
            SELECT DISTINCT 
                module, 
                device_name, 
                algo_name, 
                input_params,    
                terminals, 
                param_name
            FROM v_wat_detail 
            WHERE lot_id = :lid AND wafer_id = :wid
            ORDER BY module, device_name, param_name
        """)
        try:
            with self.engine.connect() as conn:
                return pd.read_sql(sql, conn, params={"lid": lot_id, "wid": wafer_id})
        except Exception as e:
            print(f"Repo Error (get_structure): {e}")
            return pd.DataFrame()

    def get_wafer_map_data(self, lot_id, wafer_id, param_name):
        """
        获取热力图/折线图数据
        """
        # [关键保留] 必须包含 site_index 用于折线图排序
        sql = text("""
            SELECT site_index, x_coord, y_coord, value 
            FROM v_wat_detail 
            WHERE lot_id = :lid AND wafer_id = :wid AND param_name = :p
            ORDER BY site_index ASC
        """)
        try:
            with self.engine.connect() as conn:
                return pd.read_sql(sql, conn, params={
                    "lid": lot_id, 
                    "wid": wafer_id, 
                    "p": param_name
                })
        except Exception as e:
            print(f"Repo Error (get_map): {e}")
            return pd.DataFrame()