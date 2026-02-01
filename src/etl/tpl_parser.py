import re
import os

class TplParser:
    def __init__(self):
        self.column_slices = [] 
        
    def parse(self, file_path):
        """
        [工业级解析器 V3] 完美适配 8 列布局 (含尾部占位符)
        """
        if not os.path.exists(file_path):
            print(f"❌ [TPL Parser] File not found: {file_path}")
            return {}

        mapping_dict = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            # 1. 寻找最佳标尺行 (列数最多的那一行)
            self._find_best_column_layout(lines)
            
            if not self.column_slices:
                return {}

            col_count = len(self.column_slices)
            print(f"   -> 锁定 TPL 结构：共 {col_count} 列")

            # 2. 解析数据行
            for line in lines:
                line = line.rstrip('\n')
                if not line: continue
                
                # 跳过非数据行
                if line.strip().startswith(('#', '$', 'BODY')):
                    continue
                
                # 长度校验
                if len(line) < self.column_slices[0][1]: 
                    continue

                try:
                    parsed_item = self._parse_line_fixed_width(line)
                    
                    if parsed_item:
                        meta_info = {
                            'algo_name': parsed_item['algo'],
                            'device_name': parsed_item['device_name'],
                            'input_params': parsed_item['inputs'],
                            'terminals': parsed_item['terminals'],
                            'module': parsed_item['module']
                        }
                        
                        # 3. 建立映射 (支持逗号分隔的 Output)
                        for out in parsed_item['outputs']:
                            # 去掉反引号和空格
                            clean_out = out.strip().replace('`', '')
                            if clean_out:
                                mapping_dict[clean_out] = meta_info
                                
                except Exception:
                    continue

        except Exception as e:
            print(f"❌ [TPL Parser] Error: {e}")

        print(f"✅ TPL 解析完成: 成功加载 {len(mapping_dict)} 个测试定义项。")
        return mapping_dict

    def _find_best_column_layout(self, lines):
        separator_pattern = re.compile(r'^\$[- ]+$')
        candidates = []

        for line in lines:
            line_str = line.strip()
            if separator_pattern.match(line_str):
                slices = []
                for match in re.finditer(r'[^\s]+', line): 
                    slices.append(match.span())
                
                if len(slices) > 5:
                    candidates.append(slices)

        if candidates:
            # 取列数最多的 (解决 8 列 vs 7 列的问题)
            candidates.sort(key=lambda x: len(x))
            self.column_slices = candidates[-1]
        else:
            self.column_slices = []

    def _parse_line_fixed_width(self, line):
        slices = self.column_slices
        count = len(slices)
        
        def get_col(idx):
            if idx >= count: return ""
            start, end = slices[idx]
            if start >= len(line): return ""
            return line[start:end].strip()

        # === 核心修正：绝对定位逻辑 ===
        
        # 你的文件是 8 列布局：
        # [0] Mod::Dev
        # [1] Algo
        # [2] Seq
        # [3] Task
        # [4] Inputs
        # [5] Outputs  <-- 重点
        # [6] Terminals <-- 重点
        # [7] - (Empty)
        
        # 如果是 7 列布局 (没有最后的 -)，则 Outputs 是 5, Terminals 是 6
        # 所以无论哪种，Outputs 都在 [5]，Terminals 都在 [6]
        
        # 第一列：Module::Device
        col0 = get_col(0)
        col0 = col0.rstrip(':')
        
        module = ""
        device_name = ""
        if '::' in col0:
            parts = col0.split('::', 1)
            module = parts[0].replace('`', '').strip()
            device_name = parts[1].replace('`', '').strip()
        else:
            module = col0.replace('`', '').strip()

        # 其他列
        algo = get_col(1)
        inputs = get_col(4)
        raw_outputs = get_col(5) # 绝对位置 5
        terminals = get_col(6)   # 绝对位置 6
        
        # [双重保险] 如果位置 5 没有抓到 R[...]，可能是列对齐偏了
        # 尝试在前后找一下
        if 'R[' not in raw_outputs and 'TEMP' not in raw_outputs:
             # 可能是 7 列布局里的变体？尝试倒数定位
             # 如果总列数 >= 7，倒数第二列通常是 Outputs
             idx_out = count - 2
             if idx_out != 5: # 如果跟刚才不一样，试试这个
                 raw_outputs = get_col(idx_out)
                 terminals = get_col(idx_out + 1)
                 inputs = get_col(idx_out - 1)

        if not raw_outputs: return None

        output_list = [o.strip() for o in raw_outputs.split(',')]

        return {
            "module": module,
            "device_name": device_name,
            "algo": algo,
            "inputs": inputs,
            "outputs": output_list,
            "terminals": terminals
        }

if __name__ == "__main__":
    p = TplParser()
    # p.parse("SRAM_HALFMAP.tple")