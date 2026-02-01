from sqlalchemy import text
import pandas as pd

class EtlRepository:
    def __init__(self, db_manager):
        self.db = db_manager
        # 内存缓存，加速 ID 查找
        self._item_cache = {} 
        self._site_cache = {} 

    def get_or_create_wafer(self, meta: dict) -> int:
        session = self.db.get_session()
        try:
            # 1. 查重
            sql_sel = text("SELECT wafer_key FROM dim_wafer WHERE lot_id=:l AND wafer_id=:w AND test_time=:t")
            res = session.execute(sql_sel, {'l': meta['lot_id'], 'w': meta['wafer_id'], 't': meta['test_time']}).fetchone()
            if res: return res[0]

            # 2. 插入
            sql_ins = text("INSERT INTO dim_wafer (lot_id, wafer_id, product_id, test_time) VALUES (:l, :w, :p, :t)")
            session.execute(sql_ins, {'l': meta['lot_id'], 'w': meta['wafer_id'], 'p': meta['product_id'], 't': meta['test_time']})
            session.commit()
            
            # 3. 返回新 ID (简单起见再查一次)
            return self.get_or_create_wafer(meta)
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def sync_test_items(self, df_data):
        session = self.db.get_session()
        try:
            items = df_data[['MODULE', 'DEVICE', 'ITEM']].drop_duplicates()
            for _, row in items.iterrows():
                # 使用 INSERT IGNORE 忽略重复
                sql = text("INSERT IGNORE INTO dim_test_item (module, device, param_name) VALUES (:m, :d, :p)")
                session.execute(sql, {'m': row['MODULE'], 'd': row['DEVICE'], 'p': row['ITEM']})
            session.commit()
            
            # 刷新缓存
            res = session.execute(text("SELECT module, device, param_name, item_key FROM dim_test_item"))
            self._item_cache = { (r[0], r[1], r[2]): r[3] for r in res.fetchall() }
        finally:
            session.close()

    def sync_sites(self, site_mappings: list):
        session = self.db.get_session()
        try:
            for sm in site_mappings:
                sql = text("INSERT IGNORE INTO dim_site (site_index, x_coord, y_coord) VALUES (:i, :x, :y)")
                session.execute(sql, {'i': sm['site_index'], 'x': sm['x'], 'y': sm['y']})
            session.commit()

            # 刷新缓存
            res = session.execute(text("SELECT site_index, x_coord, y_coord, site_key FROM dim_site"))
            self._site_cache = { (r[0], r[1], r[2]): r[3] for r in res.fetchall() }
        finally:
            session.close()
    
    def get_site_key(self, idx, x, y):
        return self._site_cache.get((idx, x, y))
        
    def get_item_key(self, m, d, i):
        return self._item_cache.get((m, d, i))
        
    def bulk_insert_facts(self, data_list: list):
        if not data_list: return
        session = self.db.get_session()
        try:
            # 批量插入事实数据
            session.execute(
                text("INSERT INTO fact_measurement (wafer_key, item_key, site_key, value) VALUES (:wk, :ik, :sk, :val)"),
                data_list
            )
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
