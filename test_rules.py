import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from rules_engine import RuleEngine, run_rules

def create_test_data():
    """Create test data with various anomalies"""
    np.random.seed(42)
    
    n = 100
    dates = [datetime(2021, 1, 1) + timedelta(days=i) for i in range(n)]
    
    data = {
        '年': [d.year for d in dates],
        '月': [d.month for d in dates],
        '日': [d.day for d in dates],
        '核算账簿名称': ['总账'] * n,
        '凭证号': [f'{i+1:04d}' for i in range(n)],
        '分录号': [1] * n,
        '摘要': ['支付差旅费'] * 20 + ['银行转账'] * 20 + ['购买办公用品'] * 20 + ['支付工资'] * 20 + ['工程款支付'] * 20,
        '科目编码': ['660201'] * 20 + ['1002'] * 20 + ['660202'] * 20 + ['660101'] * 20 + ['1604'] * 20,
        '科目名称': ['管理费用\\差旅费'] * 20 + ['银行存款'] * 20 + ['管理费用\\办公费'] * 20 + ['管理费用\\工资'] * 20 + ['在建工程\\工程投资支出'] * 20,
        '辅助项': ['【部门：行政部】【人员：张三】'] * 20 + ['【银行账户：建设银行】'] * 10 + [''] * 10 + ['【部门：财务部】'] * 20 + ['【部门：人力资源部】'] * 20 + ['【合同号：03-GY001-001】'] * 10 + [''] * 10,
        '币种': ['人民币'] * n,
        '借方本币': [1000.00] * 20 + [0.00] * 20 + [500.00] * 20 + [5000.00] * 20 + [100000.00] * 20,
        '贷方本币': [0.00] * 20 + [1000.00] * 20 + [0.00] * 20 + [0.00] * 20 + [0.00] * 20,
    }
    
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df[['年', '月', '日']].astype(str).agg('-'.join, axis=1))
    df['direction'] = np.where(df['借方本币'] > 0, '借', '贷')
    df['amount'] = df[['借方本币', '贷方本币']].max(axis=1)
    df['科目末级'] = df['科目名称'].apply(lambda x: x.split('\\')[-1] if '\\' in x else x)
    df['科目一级'] = df['科目名称'].apply(lambda x: x.split('\\')[0] if '\\' in x else x)
    df['科目二级'] = df['科目名称'].apply(lambda x: x.split('\\')[1] if len(x.split('\\')) > 1 else '')
    
    def parse_auxiliary(aux_text):
        if pd.isna(aux_text):
            return {}
        import re
        matches = re.findall(r'【(.*?)：(.*?)】', str(aux_text))
        return {k.strip(): v.strip() for k, v in matches}
    
    all_keys = set()
    df['辅助项_dict'] = df['辅助项'].apply(parse_auxiliary)
    for d in df['辅助项_dict']:
        all_keys.update(d.keys())
    
    for key in all_keys:
        df[key] = df['辅助项_dict'].apply(lambda x: x.get(key, ''))
    
    balance_df = df.groupby('凭证号').agg({
        '借方本币': 'sum',
        '贷方本币': 'sum'
    }).reset_index()
    balance_df['借贷平衡'] = (balance_df['借方本币'] - balance_df['贷方本币']).abs() < 0.01
    balance_df['差额'] = balance_df['借方本币'] - balance_df['贷方本币']
    
    df = df.merge(balance_df[['凭证号', '借贷平衡', '差额']], on='凭证号', how='left')
    df['风险标记'] = [[] for _ in range(len(df))]
    
    return df

def test_rules():
    print("Starting rules engine test...")
    
    df = create_test_data()
    print(f"Test data created: {len(df)} records")
    
    print("\nRunning rules engine...")
    df = run_rules(df)
    
    print("\nRule execution results:")
    
    risk_counts = {'高': 0, '中': 0, '低': 0}
    rule_results = {}
    
    for idx, row in df.iterrows():
        for mark in row['风险标记']:
            level = mark['风险等级']
            rule_name = mark['规则名称']
            risk_counts[level] = risk_counts.get(level, 0) + 1
            rule_results[rule_name] = rule_results.get(rule_name, 0) + 1
    
    print(f"\nRisk level distribution:")
    for level, count in risk_counts.items():
        print(f"  {level}: {count}")
    
    print(f"\nRule trigger statistics:")
    for rule_name, count in sorted(rule_results.items(), key=lambda x: -x[1]):
        print(f"  {rule_name}: {count}")
    
    print("\nSample risk records:")
    sample = df[df['风险标记'].apply(lambda x: len(x) > 0)].head(5)
    for idx, row in sample.iterrows():
        print(f"\n  Record {idx}:")
        print(f"    Voucher: {row['凭证号']}")
        print(f"    Date: {row['date']}")
        print(f"    Summary: {row['摘要']}")
        print(f"    Account: {row['科目名称']}")
        print(f"    Amount: {row['amount']}")
        print(f"    Risk marks: {row['风险标记']}")
    
    print("\nRules engine test completed!")

if __name__ == "__main__":
    test_rules()
