import os
from pathlib import Path

# ==========================================
# 1. 代码定义
# ==========================================

# --- src/etl/database.py ---
CODE_DATABASE = """from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class DatabaseManager:
    def __init__(self, connection_str: str):
        # pool_size=10: 保持10个连接，防止频繁握手
        # max_overflow=20: 临时突发可增加到30个
        self.engine = create_engine(connection_str, pool_size=10, max_overflow=20)
        self.Session = sessionmaker(bind=self.engine)

    def get_session(self):
        return self.Session()
"""

# --- src/etl/parser.py ---
CODE_PARSER = """import pandas as pd
import re
import io

class WatCsvParser:
    def parse(self, file_path: str):
        \"\"\"
        解析 WAT CSV 文件
        Returns:
            meta (dict): 晶圆元数据
            site_mappings (list): Site 坐标映射
            df_melted (DataFrame): 转换后的长表数据
        \"\"\"
        metadata = {}
        
        # 1. 分离 Header 和 Body
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
            
        # 假设前 5 行是 Header，第 6 行 (Index 5) 开始是数据
        header_section = lines[:5]
        body_section = lines[5:] 
        
        # 2. 提取 Metadata
        # 根据你的文件示例，Key在第3行(idx 2)，Value在第4行(idx 3)
        if len(header_section) > 3:
            keys = header_section[2].strip().split(',')
            vals = header_section[3].strip().split(',')
            # 简单的 zip 转 dict
            if len(keys) == len(vals):
                meta_dict = dict(zip(keys, vals))
                metadata = {
                    'lot_id': meta_dict.get('LOT_ID', 'UNKNOWN'),
                    'wafer_id': meta_dict.get('WAFER_ID', 'UNKNOWN'),
                    'product_id': meta_dict.get('PRODUCT_ID', 'UNKNOWN'),
                    'test_time': meta_dict.get('TEST_START_TIME', None)
                }

        # 3. 解析 Body
        df_body = pd.read_csv(io.StringIO("".join(body_section)))
        
        # 4. 提取 Site 坐标
        # 正则匹配: "Site_1_Value(-1 2)"
        site_pattern = re.compile(r"Site_(\d+)_Value\(([-\d]+)\s+([-\d]+)\)")
        
        site_cols = []
        site_mappings = [] 
        
        for col in df_body.columns:
            match = site_pattern.search(col)
            if match:
                site_cols.append(col)
                site_mappings.append({
                    'col_name': col,
                    'site_index': int(match.group(1)),
                    'x': int(match.group(2)),
                    'y': int(match.group(3))
                })
        
        # 5. Melt (宽表转长表)
        # 假设前几列是固定的标识列
        id_vars = ['MODULE', 'DEVICE', 'ITEM']
        valid_id_vars = [c for c in id_vars if c in df_body.columns]
        
        df_melted = df_body.melt(
            id_vars=valid_id_vars,
            value_vars=site_cols,
            var_name='site_col_name',
            value_name='value'
        )
        
        # 清洗数据：转数字，去空
        df_melted['value'] = pd.to_numeric(df_melted['value'], errors='coerce')
        df_melted = df_melted.dropna(subset=['value'])

        return metadata, site_mappings, df_melted
"""

# --- src/etl/repository.py ---
CODE_REPOSITORY = """from sqlalchemy import text
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
"""

# --- src/etl/pipeline.py ---
CODE_PIPELINE = """import pandas as pd
from src.etl.database import DatabaseManager
from src.etl.parser import WatCsvParser
from src.etl.repository import EtlRepository

class WatEtlPipeline:
    def __init__(self, db_url: str):
        self.db_manager = DatabaseManager(db_url)
        self.repo = EtlRepository(self.db_manager)
        self.parser = WatCsvParser()

    def run(self, file_path: str):
        print(f"🚀 [ETL] Processing: {file_path}")
        
        # 1. Parse
        try:
            meta, site_maps, df = self.parser.parse(file_path)
            print(f"   -> Parsed Wafer: {meta.get('wafer_id')}, Rows: {len(df)}")
        except Exception as e:
            print(f"❌ [ETL] Parser Failed: {e}")
            return

        # 2. Sync Dimensions
        try:
            wk = self.repo.get_or_create_wafer(meta)
            self.repo.sync_test_items(df)
            self.repo.sync_sites(site_maps)
        except Exception as e:
            print(f"❌ [ETL] Sync Failed: {e}")
            return
            
        # 3. Load Facts
        site_col_map = { m['col_name']: (m['site_index'], m['x'], m['y']) for m in site_maps }
        
        batch = []
        count = 0
        for _, row in df.iterrows():
            ik = self.repo.get_item_key(row['MODULE'], row['DEVICE'], row['ITEM'])
            
            s_info = site_col_map.get(row['site_col_name'])
            sk = self.repo.get_site_key(*s_info) if s_info else None
            
            if ik and sk:
                batch.append({'wk': wk, 'ik': ik, 'sk': sk, 'val': row['value']})
                
            if len(batch) >= 10000:
                self.repo.bulk_insert_facts(batch)
                count += len(batch)
                batch = []
                print(f"      -> Inserted {count}...", end='\\r')
                
        if batch:
            self.repo.bulk_insert_facts(batch)
            count += len(batch)
            
        print(f"\\n✅ [ETL] Done. Total records: {count}")

if __name__ == "__main__":
    # Test Run
    DB_URL = "mysql+pymysql://wat_user:wat_password@localhost:3306/wat_db"
    # pipeline = WatEtlPipeline(DB_URL)
    # pipeline.run("your_file.csv")
    print("ETL Pipeline is ready. Import this class to use.")
"""

# ==========================================
# 2. 生成逻辑
# ==========================================
def create_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✔ Created: {path}")

def main():
    root = Path(os.getcwd())
    etl_dir = root / "src" / "etl"
    
    print(f"Creating ETL module in: {etl_dir}")
    if not etl_dir.exists():
        etl_dir.mkdir(parents=True)
        
    create_file(etl_dir / "__init__.py", "")
    create_file(etl_dir / "database.py", CODE_DATABASE)
    create_file(etl_dir / "parser.py", CODE_PARSER)
    create_file(etl_dir / "repository.py", CODE_REPOSITORY)
    create_file(etl_dir / "pipeline.py", CODE_PIPELINE)
    
    print("\n✨ ETL Module Created Successfully!")

if __name__ == "__main__":
    main()