import pandas as pd
import numpy as np

class WatStatsEngine:
    @staticmethod
    def calculate_metrics(series: pd.Series, dev_threshold=0.1):
        """
        计算基础指标 + 偏差统计
        dev_threshold: 偏差阈值 (例如 0.1 代表 10%)
        """
        if series.empty:
            return {
                'mean': 0.0, 'std': 0.0, 'median': 0.0, 
                'cv_mean': 0.0, 'cv_median': 0.0,
                'dev_mean_cnt': 0, 'dev_med_cnt': 0
            }
        
        mean = series.mean()
        std = series.std()
        median = series.median()
        
        metrics = {
            'mean': mean,
            'std': std,
            'median': median,
            'cv_mean': (std / mean) if mean and mean != 0 else 0.0,
            'cv_median': (std / median) if median and median != 0 else 0.0
        }

        # 统计偏差超过 threshold 的点数量
        # |(x - Mean) / Mean| > threshold
        if mean and mean != 0:
            dev_mean = (series - mean).abs() / abs(mean)
            metrics['dev_mean_cnt'] = (dev_mean > dev_threshold).sum()
        else:
            metrics['dev_mean_cnt'] = 0

        # |(x - Median) / Median| > threshold
        if median and median != 0:
            dev_med = (series - median).abs() / abs(median)
            metrics['dev_med_cnt'] = (dev_med > dev_threshold).sum()
        else:
            metrics['dev_med_cnt'] = 0

        return metrics

    @staticmethod
    def run_analysis(df: pd.DataFrame, k=3.0, dev_threshold=0.1):
        """
        全套分析
        dev_threshold: 0.1 means 10%
        """
        result = {}
        values = df['value'].dropna()
        
        # 1. Raw
        result['Raw'] = WatStatsEngine.calculate_metrics(values, dev_threshold)
        result['Raw']['count'] = len(values)
        result['Raw']['outliers'] = []
        result['Raw']['outlier_count'] = 0

        # 2. K-Sigma
        clean_k = df.copy()
        max_iter = 10
        for _ in range(max_iter):
            v = clean_k['value']
            if len(v) < 2: break
            
            mean = v.mean()
            std = v.std()
            if pd.isna(std) or std == 0: break
            
            mask = (v >= mean - k * std) & (v <= mean + k * std)
            if mask.all(): break
            clean_k = clean_k[mask]

        outlier_indices_k = set(df.index) - set(clean_k.index)
        outliers_k = df.loc[list(outlier_indices_k)]
        
        result['K-Sigma'] = WatStatsEngine.calculate_metrics(clean_k['value'], dev_threshold)
        result['K-Sigma']['count'] = len(clean_k)
        result['K-Sigma']['outlier_count'] = len(outliers_k)
        result['K-Sigma']['outliers'] = WatStatsEngine._format_outliers(outliers_k)

        # 3. IQR
        if len(values) > 0:
            Q1 = values.quantile(0.25)
            Q3 = values.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            mask_iqr = (df['value'] >= lower_bound) & (df['value'] <= upper_bound)
            clean_iqr = df[mask_iqr]
            outliers_iqr = df[~mask_iqr]

            result['IQR'] = WatStatsEngine.calculate_metrics(clean_iqr['value'], dev_threshold)
            result['IQR']['count'] = len(clean_iqr)
            result['IQR']['outlier_count'] = len(outliers_iqr)
            result['IQR']['outliers'] = WatStatsEngine._format_outliers(outliers_iqr)
        else:
            result['IQR'] = WatStatsEngine.calculate_metrics(pd.Series(), dev_threshold)
            result['IQR']['count'] = 0
            result['IQR']['outlier_count'] = 0
            result['IQR']['outliers'] = "None"

        return result

    @staticmethod
    def _format_outliers(outlier_df):
        if outlier_df.empty:
            return "None"
        outlier_df = outlier_df.sort_values('site_index')
        items = []
        for _, row in outlier_df.iterrows():
            site = int(row.get('site_index', 0))
            val = row['value']
            items.append(f"S{site}:{val:.2f}")
        
        if len(items) > 10:
            return ", ".join(items[:10]) + f" ... (+{len(items)-10})"
        return ", ".join(items)