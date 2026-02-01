import os
import pandas as pd
from datetime import datetime # [新增] 引入时间处理模块
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from src.core.settings import settings 
from src.etl.parser import WatCsvParser
from src.etl.tpl_parser import TplParser

class WatPipeline:
    def __init__(self, db_url=None):
        self.db_url = db_url if db_url else settings.get_db_url()
        self.db_type = settings.get_db_type() 
        
        self.engine = create_engine(self.db_url)
        self.csv_parser = WatCsvParser()
        self.tpl_parser = TplParser()

    def run(self, csv_path, tpl_path=None):
        if not tpl_path:
             base_path = os.path.splitext(csv_path)[0]
             for ext in ['.tple', '.tpl', '.tst']:
                 if os.path.exists(base_path + ext):
                     tpl_path = base_path + ext
                     break
        
        print(f"🔒 Pipeline Start: {os.path.basename(csv_path)}")
        print(f"   Target DB: {self.db_type.upper()}")

        metadata, site_mappings, df_meas = self.csv_parser.parse(csv_path)
        tpl_mapping = self.tpl_parser.parse(tpl_path) if tpl_path else {}
        
        self.save_to_db(metadata, site_mappings, df_meas, tpl_mapping)

    def _get_upsert_stmt(self, table_name, data_dict, unique_keys):
        """生成 Upsert 语句"""
        update_cols = {x: data_dict[x] for x in data_dict if x not in unique_keys}

        if self.db_type == "mysql":
            stmt = mysql_insert(table_name).values(data_dict)
            return stmt.on_duplicate_key_update(**update_cols)
            
        elif self.db_type == "sqlite":
            stmt = sqlite_insert(table_name).values(data_dict)
            return stmt.on_conflict_do_update(
                index_elements=unique_keys,
                set_=update_cols
            )
        return None

    def save_to_db(self, meta, site_mappings, df_meas, tpl_mapping):
        from sqlalchemy import MetaData
        
        metadata_obj = MetaData()
        metadata_obj.reflect(bind=self.engine)
        
        t_wafer = metadata_obj.tables['dim_wafer']
        t_site = metadata_obj.tables['dim_site']
        t_item = metadata_obj.tables['dim_test_item']
        
        with self.engine.begin() as conn:
            # =========================================
            # 1. Upsert Dim Wafer
            # =========================================
            
            # [关键修复] 解析时间字符串为 datetime 对象
            test_time_str = meta.get('test_time')
            test_time_obj = None
            
            if test_time_str and isinstance(test_time_str, str):
                try:
                    # 尝试解析常见格式 '2026-01-26 11:05:49'
                    test_time_obj = datetime.strptime(test_time_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        # 备用格式 '2026/01/26 11:05:49'
                        test_time_obj = datetime.strptime(test_time_str, "%Y/%m/%d %H:%M:%S")
                    except:
                        # 解析失败，设为 None 防止报错
                        test_time_obj = None
            
            wafer_data = {
                "lot_id": meta.get('lot_id'),
                "wafer_id": meta.get('wafer_id'),
                "product_id": meta.get('product_id'),
                "test_time": test_time_obj  # 这里必须传对象，不能传字符串
            }
            
            if self.db_type == "mysql":
                stmt = mysql_insert(t_wafer).values(wafer_data)
                stmt = stmt.on_duplicate_key_update(product_id=wafer_data['product_id'])
            else: # sqlite
                stmt = sqlite_insert(t_wafer).values(wafer_data)
                stmt = stmt.on_conflict_do_update(
                    index_elements=['lot_id', 'wafer_id'],
                    set_={"product_id": wafer_data['product_id']}
                )
            
            conn.execute(stmt)
            
            w_key = conn.execute(
                text("SELECT wafer_key FROM dim_wafer WHERE lot_id=:l AND wafer_id=:w"),
                {"l": meta['lot_id'], "w": meta['wafer_id']}
            ).scalar()
            
            print(f"   -> Wafer Key: {w_key}")

            # =========================================
            # 2. Upsert Dim Site
            # =========================================
            site_key_map = {}
            for s in site_mappings:
                site_data = {"site_index": s['site_index'], "x_coord": s['x'], "y_coord": s['y']}
                
                existing_key = conn.execute(text(
                    "SELECT site_key FROM dim_site WHERE site_index=:i AND x_coord=:x AND y_coord=:y"
                ), {"i": s['site_index'], "x": s['x'], "y": s['y']}).scalar()
                
                if not existing_key:
                    res = conn.execute(t_site.insert().values(site_data))
                    existing_key = conn.execute(text(
                        "SELECT site_key FROM dim_site WHERE site_index=:i AND x_coord=:x AND y_coord=:y"
                    ), {"i": s['site_index'], "x": s['x'], "y": s['y']}).scalar()

                site_key_map[s['col_name']] = existing_key

            # =========================================
            # 3. Upsert Dim Test Item
            # =========================================
            item_key_map = {}
            unique_items = df_meas[['MODULE', 'DEVICE', 'ITEM']].drop_duplicates()
            
            for _, row in unique_items.iterrows():
                mod, dev, param = row['MODULE'], row['DEVICE'], row['ITEM']
                tpl_info = tpl_mapping.get(param, {})
                
                item_data = {
                    "module": mod, "device": dev, "param_name": param,
                    "algo_name": tpl_info.get('algo_name'),
                    "device_name": tpl_info.get('device_name'),
                    "input_params": tpl_info.get('input_params'),
                    "terminals": tpl_info.get('terminals')
                }
                
                update_dict = {
                    "algo_name": item_data['algo_name'],
                    "device_name": item_data['device_name'],
                    "input_params": item_data['input_params'],
                    "terminals": item_data['terminals']
                }
                
                if self.db_type == "mysql":
                    stmt = mysql_insert(t_item).values(item_data)
                    stmt = stmt.on_duplicate_key_update(**update_dict)
                else:
                    stmt = sqlite_insert(t_item).values(item_data)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['module', 'device', 'param_name'],
                        set_=update_dict
                    )
                
                conn.execute(stmt)
                
                i_key = conn.execute(text(
                    "SELECT item_key FROM dim_test_item WHERE module=:m AND device=:d AND param_name=:p"
                ), {"m": mod, "d": dev, "p": param}).scalar()
                
                item_key_map[(mod, dev, param)] = i_key

            # =========================================
            # 4. Insert Fact Measurement
            # =========================================
            df_meas['temp_item_id'] = list(zip(df_meas.MODULE, df_meas.DEVICE, df_meas.ITEM))
            df_meas['item_key'] = df_meas['temp_item_id'].map(item_key_map)
            df_meas['site_key'] = df_meas['site_col_name'].map(site_key_map)
            df_meas['wafer_key'] = w_key
            
            df_final = df_meas[['wafer_key', 'item_key', 'site_key', 'value']].dropna()
            
            print(f"   -> Inserting {len(df_final)} measurements...")
            data_to_insert = df_final.to_dict(orient='records')
            
            batch_size = 5000
            for i in range(0, len(data_to_insert), batch_size):
                batch = data_to_insert[i:i+batch_size]
                conn.execute(text("""
                    INSERT INTO fact_measurement (wafer_key, item_key, site_key, value)
                    VALUES (:wafer_key, :item_key, :site_key, :value)
                """), batch)
                
        print("   -> Transaction Committed.")