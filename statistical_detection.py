import pandas as pd
import numpy as np
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

class BenfordAnalyzer:
    def __init__(self, significance_level: float = 0.05):
        self.significance_level = significance_level
        self.expected_distribution = {
            1: 0.301, 2: 0.176, 3: 0.125, 4: 0.097,
            5: 0.079, 6: 0.067, 7: 0.058, 8: 0.051, 9: 0.046
        }
    
    def get_first_digit(self, number: float) -> Optional[int]:
        if number == 0 or pd.isna(number):
            return None
        abs_num = abs(number)
        while abs_num >= 10:
            abs_num /= 10
        while abs_num < 1 and abs_num > 0:
            abs_num *= 10
        return int(abs_num)
    
    def analyze(self, amounts: pd.Series, min_samples: int = 100) -> Dict:
        first_digits = amounts.apply(self.get_first_digit).dropna()
        
        if len(first_digits) < min_samples:
            return {
                'status': 'insufficient_data',
                'message': f'样本量不足，需要至少{min_samples}条记录',
                'sample_count': len(first_digits)
            }
        
        observed = first_digits.value_counts().sort_index()
        expected = pd.Series(self.expected_distribution) * len(first_digits)
        
        chi2_stat, p_value = stats.chisquare(observed, expected)
        
        observed_pct = observed / len(first_digits)
        expected_pct = pd.Series(self.expected_distribution)
        
        deviations = {}
        for digit in range(1, 10):
            obs_pct = observed_pct.get(digit, 0)
            exp_pct = expected_pct[digit]
            deviations[digit] = {
                'observed_pct': round(obs_pct * 100, 2),
                'expected_pct': round(exp_pct * 100, 2),
                'deviation': round((obs_pct - exp_pct) * 100, 2)
            }
        
        is_anomalous = p_value < self.significance_level
        
        return {
            'status': 'completed',
            'chi2_statistic': round(chi2_stat, 4),
            'p_value': round(p_value, 4),
            'is_anomalous': is_anomalous,
            'sample_count': len(first_digits),
            'deviations': deviations
        }
    
    def analyze_by_account(self, df: pd.DataFrame, account_col: str = '科目末级', amount_col: str = 'amount') -> Dict:
        results = {}
        
        for account in df[account_col].unique():
            account_df = df[df[account_col] == account]
            result = self.analyze(account_df[amount_col])
            results[account] = result
        
        return results

class TrendAnalyzer:
    def __init__(self, threshold_sigma: float = 3.0):
        self.threshold_sigma = threshold_sigma
    
    def analyze_monthly_trend(self, df: pd.DataFrame, date_col: str = 'date', amount_col: str = 'amount', account_col: str = None) -> Dict:
        df = df.copy()
        df['year_month'] = df[date_col].dt.to_period('M')
        
        if account_col:
            results = {}
            for account in df[account_col].unique():
                account_df = df[df[account_col] == account]
                results[account] = self._analyze_single_series(account_df, date_col, amount_col)
            return results
        else:
            return self._analyze_single_series(df, date_col, amount_col)
    
    def _analyze_single_series(self, df: pd.DataFrame, date_col: str, amount_col: str) -> Dict:
        monthly = df.groupby('year_month').agg({
            amount_col: ['sum', 'count', 'mean']
        }).reset_index()
        
        monthly.columns = ['year_month', 'total', 'count', 'average']
        monthly['year_month'] = monthly['year_month'].astype(str)
        
        if len(monthly) < 3:
            return {
                'status': 'insufficient_data',
                'message': '月度数据不足，需要至少3个月的数据'
            }
        
        values = monthly['total'].values
        mean = np.mean(values)
        std = np.std(values)
        
        if std > 0:
            z_scores = (values - mean) / std
            anomalies = np.abs(z_scores) > self.threshold_sigma
        else:
            anomalies = np.zeros(len(values), dtype=bool)
        
        monthly['z_score'] = z_scores
        monthly['is_anomaly'] = anomalies
        
        anomaly_months = monthly[monthly['is_anomaly']].to_dict('records')
        
        return {
            'status': 'completed',
            'monthly_summary': monthly.to_dict('records'),
            'anomaly_months': anomaly_months,
            'statistics': {
                'mean': round(mean, 2),
                'std': round(std, 2),
                'threshold': round(mean + self.threshold_sigma * std, 2)
            }
        }

class IsolationForestDetector:
    def __init__(self, contamination: float = 0.01, n_estimators: int = 100, random_state: int = 42):
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.model = None
        self.scaler = None
    
    def prepare_features(self, df: pd.DataFrame, date_col: str = 'date', amount_col: str = 'amount') -> pd.DataFrame:
        features = pd.DataFrame()
        
        features['amount'] = df[amount_col]
        features['amount_log'] = np.log1p(df[amount_col])
        
        if date_col in df.columns:
            features['month'] = df[date_col].dt.month
            features['day'] = df[date_col].dt.day
            features['weekday'] = df[date_col].dt.weekday
            features['is_weekend'] = (df[date_col].dt.weekday >= 5).astype(int)
            features['is_month_end'] = (df[date_col].dt.day >= 25).astype(int)
            features['is_year_end'] = (df[date_col].dt.month == 12).astype(int)
        
        if '科目编码' in df.columns:
            features['account_code'] = df['科目编码'].astype('category').cat.codes
        
        if '凭证号' in df.columns:
            voucher_counts = df.groupby('凭证号').size()
            features['voucher_entries'] = df['凭证号'].map(voucher_counts)
        
        features = features.fillna(0)
        
        return features
    
    def fit_predict(self, df: pd.DataFrame, date_col: str = 'date', amount_col: str = 'amount') -> Tuple[np.ndarray, np.ndarray]:
        features = self.prepare_features(df, date_col, amount_col)
        
        self.scaler = StandardScaler()
        features_scaled = self.scaler.fit_transform(features)
        
        self.model = IsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            random_state=self.random_state
        )
        
        predictions = self.model.fit_predict(features_scaled)
        scores = self.model.decision_function(features_scaled)
        
        return predictions, scores
    
    def analyze(self, df: pd.DataFrame, date_col: str = 'date', amount_col: str = 'amount') -> Dict:
        if len(df) < 100:
            return {
                'status': 'insufficient_data',
                'message': '样本量不足，需要至少100条记录'
            }
        
        predictions, scores = self.fit_predict(df, date_col, amount_col)
        
        anomaly_mask = predictions == -1
        anomaly_indices = df[anomaly_mask].index.tolist()
        
        df_result = df.copy()
        df_result['anomaly_score'] = scores
        df_result['is_anomaly'] = anomaly_mask
        
        return {
            'status': 'completed',
            'anomaly_count': int(anomaly_mask.sum()),
            'anomaly_ratio': round(anomaly_mask.mean() * 100, 2),
            'anomaly_indices': anomaly_indices,
            'score_statistics': {
                'mean': round(float(np.mean(scores)), 4),
                'std': round(float(np.std(scores)), 4),
                'min': round(float(np.min(scores)), 4),
                'max': round(float(np.max(scores)), 4)
            }
        }

class TransactionGraphAnalyzer:
    def __init__(self):
        self.nodes = {}
        self.edges = {}
    
    def build_graph(self, df: pd.DataFrame) -> Dict:
        self.nodes = {}
        self.edges = {}
        
        entity_cols = ['银行账户', '客商', '部门', '人员', '合同号']
        
        for col in entity_cols:
            if col in df.columns:
                for entity in df[col].unique():
                    if entity and entity != '':
                        node_key = f"{col}_{entity}"
                        if node_key not in self.nodes:
                            self.nodes[node_key] = {
                                'type': col,
                                'name': entity,
                                'transaction_count': 0,
                                'total_amount': 0
                            }
        
        for idx, row in df.iterrows():
            voucher_entities = []
            for col in entity_cols:
                if col in df.columns and row[col] and row[col] != '':
                    node_key = f"{col}_{row[col]}"
                    voucher_entities.append(node_key)
                    self.nodes[node_key]['transaction_count'] += 1
                    self.nodes[node_key]['total_amount'] += row.get('amount', 0)
            
            for i, source in enumerate(voucher_entities):
                for target in voucher_entities[i+1:]:
                    edge_key = tuple(sorted([source, target]))
                    if edge_key not in self.edges:
                        self.edges[edge_key] = {
                            'source': edge_key[0],
                            'target': edge_key[1],
                            'transaction_count': 0,
                            'total_amount': 0
                        }
                    self.edges[edge_key]['transaction_count'] += 1
                    self.edges[edge_key]['total_amount'] += row.get('amount', 0)
        
        return {
            'nodes': self.nodes,
            'edges': self.edges
        }
    
    def detect_anomalies(self, df: pd.DataFrame) -> Dict:
        graph = self.build_graph(df)
        
        anomalies = []
        
        node_amounts = [n['total_amount'] for n in self.nodes.values()]
        if node_amounts:
            mean_amount = np.mean(node_amounts)
            std_amount = np.std(node_amounts)
            
            for node_key, node_data in self.nodes.items():
                if std_amount > 0:
                    z_score = (node_data['total_amount'] - mean_amount) / std_amount
                    if abs(z_score) > 3:
                        anomalies.append({
                            'type': 'high_value_entity',
                            'entity': node_data['name'],
                            'entity_type': node_data['type'],
                            'total_amount': node_data['total_amount'],
                            'transaction_count': node_data['transaction_count'],
                            'z_score': round(z_score, 2)
                        })
        
        for edge_key, edge_data in self.edges.items():
            if edge_data['transaction_count'] > 10:
                anomalies.append({
                    'type': 'frequent_transaction_pair',
                    'source': self.nodes[edge_data['source']]['name'],
                    'target': self.nodes[edge_data['target']]['name'],
                    'transaction_count': edge_data['transaction_count'],
                    'total_amount': edge_data['total_amount']
                })
        
        return {
            'status': 'completed',
            'node_count': len(self.nodes),
            'edge_count': len(self.edges),
            'anomalies': anomalies
        }

class StatisticalAnomalyDetector:
    def __init__(self):
        self.benford = BenfordAnalyzer()
        self.trend = TrendAnalyzer()
        self.isolation_forest = IsolationForestDetector()
        self.graph = TransactionGraphAnalyzer()
    
    def run_all(self, df: pd.DataFrame) -> Dict:
        results = {
            'benford': {},
            'trend': {},
            'isolation_forest': {},
            'graph': {}
        }
        
        if 'amount' in df.columns:
            results['benford']['overall'] = self.benford.analyze(df['amount'])
            
            if '科目末级' in df.columns:
                results['benford']['by_account'] = self.benford.analyze_by_account(df)
        
        if 'date' in df.columns and 'amount' in df.columns:
            results['trend'] = self.trend.analyze_monthly_trend(df)
            
            if '科目末级' in df.columns:
                results['trend_by_account'] = self.trend.analyze_monthly_trend(
                    df, account_col='科目末级'
                )
        
        if len(df) >= 100:
            results['isolation_forest'] = self.isolation_forest.analyze(df)
        
        entity_cols = ['银行账户', '客商', '部门', '人员', '合同号']
        has_entities = any(col in df.columns for col in entity_cols)
        
        if has_entities:
            results['graph'] = self.graph.detect_anomalies(df)
        
        return results
    
    def mark_anomalies(self, df: pd.DataFrame, results: Dict) -> pd.DataFrame:
        if '风险标记' not in df.columns:
            df['风险标记'] = [[] for _ in range(len(df))]
        
        if results.get('isolation_forest', {}).get('status') == 'completed':
            anomaly_indices = results['isolation_forest']['anomaly_indices']
            for idx in anomaly_indices:
                df.at[idx, '风险标记'].append({
                    '规则名称': '孤立森林异常',
                    '风险等级': '高',
                    '描述': '统计模型检测到异常交易模式'
                })
        
        if results.get('benford', {}).get('overall', {}).get('is_anomalous'):
            benford_result = results['benford']['overall']
            df['风险标记'] = df['风险标记'].apply(
                lambda x: x + [{
                    '规则名称': 'Benford定律异常',
                    '风险等级': '中',
                    '描述': f"金额首位数字分布异常(p={benford_result['p_value']})"
                }]
            )
        
        return df

def run_statistical_detection(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    detector = StatisticalAnomalyDetector()
    results = detector.run_all(df)
    df = detector.mark_anomalies(df, results)
    return df, results
