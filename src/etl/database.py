from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class DatabaseManager:
    def __init__(self, connection_str: str):
        # pool_size=10: 保持10个连接，防止频繁握手
        # max_overflow=20: 临时突发可增加到30个
        self.engine = create_engine(connection_str, pool_size=10, max_overflow=20)
        self.Session = sessionmaker(bind=self.engine)

    def get_session(self):
        return self.Session()
