import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from statistical_detection import StatisticalAnomalyDetector, run_statistical_detection

def create_test_data():
    """Create test data with various patterns"""
    np.random.seed(42)
    
    n = 1000
    dates = [datetime(2021, 1, 1) + timedelta(days=i % 365) for i in range(n)]
    
    normal_amounts = np.random.lognormal(mean=8, sigma=1.5, size=n)
    anomaly_amounts = np.random.uniform(1000000, 5000000, size=20)
    
    amounts = np.concatenate([normal_amounts[:n-20], anomaly_amounts])
    np.random.shuffle(amounts)
    
    data = {
        '年': [d.year for d in dates],
        '月': [d.month for d in dates],
        '日': [d.day for d in dates],
        '核算账簿名称': ['总账'] * n,
        '凭证号': [f'{i+1:04d}' for i in range(n)],
        '分录号': [1] * n,
        '摘要': ['交易'] * n,
        '科目编码': ['6602'] * n,
        '科目名称': ['管理费用\\办公费'] * n,
        '辅助项': ['【部门：行政部】【客商：供应商A】'] * n,
        '币种': ['人民币'] * n,
        '借方本币': amounts,
        '贷方本币': [0] * n,
    }
    
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df[['年', '月', '日']].astype(str).agg('-'.join, axis=1))
    df['direction'] = '借'
    df['amount'] = df['借方本币']
    df['科目末级'] = '办公费'
    df['科目一级'] = '管理费用'
    df['部门'] = '行政部'
    df['客商'] = '供应商A'
    df['风险标记'] = [[] for _ in range(len(df))]
    
    return df

def test_statistical_detection():
    print("Starting statistical anomaly detection test...")
    
    df = create_test_data()
    print(f"Test data created: {len(df)} records")
    
    print("\nRunning statistical anomaly detection...")
    df, results = run_statistical_detection(df)
    
    print("\n=== Benford's Law Analysis ===")
    benford_result = results.get('benford', {}).get('overall', {})
    if benford_result.get('status') == 'completed':
        print(f"Chi-square statistic: {benford_result['chi2_statistic']}")
        print(f"P-value: {benford_result['p_value']}")
        print(f"Is anomalous: {benford_result['is_anomalous']}")
        print(f"Sample count: {benford_result['sample_count']}")
    else:
        print(f"Status: {benford_result.get('status', 'unknown')}")
        print(f"Message: {benford_result.get('message', 'N/A')}")
    
    print("\n=== Trend Analysis ===")
    trend_result = results.get('trend', {})
    if trend_result.get('status') == 'completed':
        print(f"Monthly statistics: {trend_result['statistics']}")
        print(f"Anomaly months: {len(trend_result.get('anomaly_months', []))}")
    else:
        print(f"Status: {trend_result.get('status', 'unknown')}")
    
    print("\n=== Isolation Forest Analysis ===")
    if_result = results.get('isolation_forest', {})
    if if_result.get('status') == 'completed':
        print(f"Anomaly count: {if_result['anomaly_count']}")
        print(f"Anomaly ratio: {if_result['anomaly_ratio']}%")
        print(f"Score statistics: {if_result['score_statistics']}")
    else:
        print(f"Status: {if_result.get('status', 'unknown')}")
    
    print("\n=== Graph Analysis ===")
    graph_result = results.get('graph', {})
    if graph_result.get('status') == 'completed':
        print(f"Node count: {graph_result['node_count']}")
        print(f"Edge count: {graph_result['edge_count']}")
        print(f"Anomalies detected: {len(graph_result.get('anomalies', []))}")
    else:
        print(f"Status: {graph_result.get('status', 'unknown')}")
    
    print("\n=== Risk Mark Summary ===")
    risk_counts = {'高': 0, '中': 0, '低': 0}
    for marks in df['风险标记']:
        for mark in marks:
            level = mark['风险等级']
            risk_counts[level] = risk_counts.get(level, 0) + 1
    
    for level, count in risk_counts.items():
        print(f"{level}: {count}")
    
    print("\nStatistical anomaly detection test completed!")

if __name__ == "__main__":
    test_statistical_detection()
