# run_test_etl.py
import os
from src.etl.pipeline import WatEtlPipeline

# 1. 配置数据库连接
# 格式: mysql+pymysql://用户名:密码@IP:端口/数据库名
DB_URL = "mysql+pymysql://wat_user:wat_password@localhost:3306/wat_db"

def main(csv_file:str):
    # 2. 检查测试文件是否存在
    
    if not os.path.exists(csv_file):
        print(f"❌ 找不到文件: {csv_file}")
        return

    # 3. 初始化 ETL 管道
    print("正在初始化 ETL 系统...")
    pipeline = WatEtlPipeline(DB_URL)

    # 4. 运行导入
    try:
        pipeline.run(csv_file)
        print("🎉 测试结束！请去数据库检查数据。")
    except Exception as e:
        print(f"❌ 发生错误: {e}")

if __name__ == "__main__":
    csv_file = "MES-000_PXW_BEOL_HALFMAP_refabs_24_20260115141343.csv" # 替换为你真实的文件名
    main(csv_file)