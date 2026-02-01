from sqlalchemy import create_engine, text

# 数据库连接
DB_URL = "mysql+pymysql://wat_user:wat_password@localhost:3306/wat_db"

def check_tables():
    print(f"🕵️‍♂️ 正在检查数据库: wat_db ...")
    try:
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            # 运行 SQL 命令查询所有表
            result = conn.execute(text("SHOW TABLES;"))
            tables = [row[0] for row in result.fetchall()]
            
            if not tables:
                print("❌ 结果确认：数据库是空的！没有发现任何表。")
                print("   -> 请重新运行 init_db.py 建表脚本。")
            else:
                print(f"✅ 成功发现 {len(tables)} 张表：")
                for t in tables:
                    print(f"   - {t}")
                print("\n结论：数据库没问题，是 DataGrip 的显示问题。")
                
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        print("   -> 请检查 Docker 是否正在运行。")

if __name__ == "__main__":
    check_tables()