import pandas as pd
import sqlite3
from sqlalchemy import create_engine, text
from src.core.interfaces import IDataLoader

class CsvLoader:
    def load(self, path, **kwargs): return pd.read_csv(path)

class ExcelLoader:
    def load(self, path, **kwargs): return pd.read_excel(path)

class SqliteLoader:
    def load(self, path, **kwargs):
        conn = sqlite3.connect(path)
        return pd.read_sql("SELECT * FROM wat_data", conn)

class MySqlLoader:
    """MySQL 加载器 (SQLAlchemy)"""
    def load(self, connection_str: str, **kwargs):
        query = kwargs.get("query")
        if not query:
            query = "SELECT * FROM wat_data LIMIT 10000"
            print("[Warn] No query provided, limiting to 10k rows.")
            
        try:
            engine = create_engine(connection_str)
            with engine.connect() as conn:
                return pd.read_sql(text(query), conn)
        except Exception as e:
            print(f"[Error] MySQL Load Failed: {e}")
            raise e

class DataEngine:
    def __init__(self):
        self._raw_data = pd.DataFrame()
        self._loaders = {
            "csv": CsvLoader(),
            "xlsx": ExcelLoader(),
            "db": SqliteLoader(),
            "mysql": MySqlLoader()
        }

    def load_source(self, source: str, source_type: str = "auto", **kwargs):
        if source_type == "auto":
            source_type = source.split('.')[-1]
            
        loader = self._loaders.get(source_type)
        if not loader:
            raise ValueError(f"Unknown source type: {source_type}")
            
        print(f"Loading data via {source_type}...")
        self._raw_data = loader.load(source, **kwargs)
        print(f"Data Loaded: {self._raw_data.shape}")

    def get_data(self):
        return self._raw_data
