import pandas as pd
import re
import io

class WatCsvParser:
    def parse(self, file_path: str):
        """
        解析 WAT CSV 文件 (工业级容错版)
        1. 支持 Metadata 行列数不匹配 (自动截断)
        2. 支持 Data 表头跨多行 (自动合并)
        3. 支持 Site 坐标正则多种格式
        """
        metadata = {
            'lot_id': 'UNKNOWN', 
            'wafer_id': 'UNKNOWN', 
            'product_id': 'UNKNOWN', 
            'test_time': None
        }
        
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            lines = [line.strip() for line in f.readlines()]
            
        # ==========================================
        # 1. 智能提取 Metadata
        # ==========================================
        meta_key_idx = -1
        for i, line in enumerate(lines[:20]):
            if "LOT_ID" in line and "WAFER_ID" in line:
                meta_key_idx = i
                break
        
        if meta_key_idx != -1 and meta_key_idx + 1 < len(lines):
            # 过滤空字符串，处理末尾逗号造成的空列
            keys = [k.strip() for k in lines[meta_key_idx].split(',') if k.strip()]
            # Value 行可能有空值(,,)，所以不能简单 filter，只能 strip
            vals = [v.strip() for v in lines[meta_key_idx+1].split(',')]
            
            # 【关键修复】使用 min 取交集，防止列数不一致报错
            limit = min(len(keys), len(vals))
            meta_dict = dict(zip(keys[:limit], vals[:limit]))
            
            metadata['lot_id'] = meta_dict.get('LOT_ID', 'UNKNOWN')
            metadata['wafer_id'] = meta_dict.get('WAFER_ID', 'UNKNOWN')
            metadata['product_id'] = meta_dict.get('PRODUCT_ID', 'UNKNOWN')
            # 尝试拼接日期和时间 (如果有断行风险，这里只取第一部分)
            metadata['test_time'] = meta_dict.get('TEST_START_TIME', None)

        # ==========================================
        # 2. 智能重组 Data Header (修复换行问题)
        # ==========================================
        header_start_idx = -1
        data_start_idx = -1
        
        # 寻找 Header 开始 (MODULE, DEVICE...)
        for i, line in enumerate(lines):
            if line.startswith("MODULE") and "DEVICE" in line:
                header_start_idx = i
                break
        
        # 寻找 Data 开始 (通常以 PCM 或 BLR 开头，或者全是数字csv)
        # 我们假设 Data 行不包含 "Site_" 且有逗号
        if header_start_idx != -1:
            for i in range(header_start_idx + 1, len(lines)):
                # 如果这一行看起来像数据 (比如以 PCM, BLR 开头，或者包含大量数字)
                # 且不像表头 (不含 Site_Value)
                if (lines[i].startswith("PCM") or lines[i].startswith("BLR") or 
                    lines[i].startswith("TJV") or lines[i].count(',') > 5):
                    if "Site_" not in lines[i]: # 再次确认不是断裂的表头
                        data_start_idx = i
                        break
        
        if header_start_idx == -1 or data_start_idx == -1:
            print(f"[Warn] Could not locate data block in {file_path}")
            return metadata, [], pd.DataFrame()

        # 【关键修复】合并 header_start 到 data_start 之间的所有行为一行
        # 你的文件中，Site 列名被换行符切断了，这里把它们拼回来
        full_header_str = "".join(lines[header_start_idx:data_start_idx])
        
        # 构造新的 CSV 内容：合并后的表头 + 数据体
        data_lines = [full_header_str] + lines[data_start_idx:]
        body_str = "\n".join(data_lines)
        
        # 使用 pandas 读取
        try:
            df_body = pd.read_csv(io.StringIO(body_str))
        except Exception as e:
            print(f"[Error] Pandas read failed: {e}")
            return metadata, [], pd.DataFrame()

        # ==========================================
        # 3. 提取 Site 坐标
        # ==========================================
        # 正则兼容: "Site_1_Value(-1 2)" 或 "Site_1_Value(-1, 2)" 甚至跨行拼接后的空格
        site_pattern = re.compile(r"Site_(\d+)_Value\s*\(\s*([-\d]+)[\s,]+([-\d]+)\s*\)")
        
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
        
        # ==========================================
        # 4. 数据重塑 (Unpivot)
        # ==========================================
        id_vars = ['MODULE', 'DEVICE', 'ITEM']
        # 确保这些列存在，不存在则只取存在的
        valid_id_vars = [c for c in id_vars if c in df_body.columns]
        
        if not site_cols:
            print(f"[Warn] No Site columns found. Header might be parsed wrongly.")
            # 调试用：打印前几个列名看看
            # print(f"Columns: {df_body.columns[:5]}")
            return metadata, [], pd.DataFrame()

        df_melted = df_body.melt(
            id_vars=valid_id_vars,
            value_vars=site_cols,
            var_name='site_col_name',
            value_name='value'
        )
        
        # 数据清洗
        df_melted['value'] = pd.to_numeric(df_melted['value'], errors='coerce')
        df_melted = df_melted.dropna(subset=['value'])

        return metadata, site_mappings, df_melted