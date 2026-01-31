import numpy as np

class DataService:
    """
    负责所有非 UI 的逻辑：数据库查询、数据计算、文件解析
    """
    def get_wafer_list(self):
        return [f"Wafer_{i:02d}" for i in range(1, 26)]

    def get_wafer_map_data(self, wafer_id):
        # 模拟生成 Wafer Map 数据 (X, Y, Value)
        # 实际开发中，这里会调用 Repository 从 SQLite 读取
        n = 2000
        theta = np.random.uniform(0, 2*np.pi, n)
        r = np.sqrt(np.random.uniform(0, 1, n)) * 150
        x = r * np.cos(theta)
        y = r * np.sin(theta)
        values = np.random.normal(0.75, 0.05, n) # Vth mean=0.75
        return {"x": x, "y": y, "values": values}

    def calculate_stats(self, map_data):
        vals = map_data["values"]
        return {
            "mean": np.mean(vals),
            "std": np.std(vals),
            "max": np.max(vals),
            "min": np.min(vals),
            "yield": np.mean(vals < 0.85) * 100 # 假定 Spec
        }
