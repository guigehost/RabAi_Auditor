from celery import Celery
import pandas as pd
import numpy as np
import duckdb
import json
import os
import re
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from dateutil import parser
import requests

app = Celery(
    "audit",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

# 数据预处理函数
def preprocess_data(file_path):
    """数据预处理"""
    # 读取文件
    if file_path.endswith('.xlsx'):
        df = pd.read_excel(file_path)
    elif file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    else:
        raise ValueError("不支持的文件格式")
    
    # 1. 数据清洗
    # 日期合并
    df['date'] = pd.to_datetime(df[['年', '月', '日']].astype(str).agg('-'.join, axis=1))
    
    # 金额清洗
    for col in ['借方本币', '贷方本币']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '').astype(float)
    
    # 借贷方向
    df['direction'] = np.where(df['借方本币'] > 0, '借', '贷')
    df['amount'] = df[['借方本币', '贷方本币']].max(axis=1)
    
    # 2. 科目层级拆分
    df['科目末级'] = df['科目名称'].apply(lambda x: x.split('\\')[-1] if '\\' in x else x)
    df['科目一级'] = df['科目名称'].apply(lambda x: x.split('\\')[0] if '\\' in x else x)
    df['科目二级'] = df['科目名称'].apply(lambda x: x.split('\\')[1] if len(x.split('\\')) > 1 else '')
    
    # 3. 辅助项解析
    def parse_auxiliary(aux_text):
        if pd.isna(aux_text):
            return {}
        # 正则提取【键：值】对
        matches = re.findall(r'【(.*?)：(.*?)】', str(aux_text))
        return {k.strip(): v.strip() for k, v in matches}
    
    # 提取所有辅助项键
    all_keys = set()
    df['辅助项_dict'] = df['辅助项'].apply(parse_auxiliary)
    for d in df['辅助项_dict']:
        all_keys.update(d.keys())
    
    # 展开为独立列
    for key in all_keys:
        df[key] = df['辅助项_dict'].apply(lambda x: x.get(key, ''))
    
    # 4. 凭证借贷平衡计算
    balance_df = df.groupby('凭证号').agg({
        '借方本币': 'sum',
        '贷方本币': 'sum'
    }).reset_index()
    balance_df['借贷平衡'] = (balance_df['借方本币'] - balance_df['贷方本币']).abs() < 0.01
    balance_df['差额'] = balance_df['借方本币'] - balance_df['贷方本币']
    
    df = df.merge(balance_df[['凭证号', '借贷平衡', '差额']], on='凭证号', how='left')
    
    # 5. 异常预标记
    df['风险标记'] = df.apply(lambda x: [], axis=1)
    
    return df

# 规则引擎
def run_rules(df, rule_config):
    """执行规则引擎"""
    # 1. 凭证级规则
    if rule_config.get('凭证级规则', {}).get('enabled', True):
        # 借贷不平
        df.loc[~df['借贷平衡'], '风险标记'] = df.loc[~df['借贷平衡'], '风险标记'].apply(lambda x: x + [{'规则名称': '借贷不平', '风险等级': '高'}])
        
        # 凭证断号
        voucher_numbers = sorted(df['凭证号'].unique())
        for i in range(1, len(voucher_numbers)):
            # 简单判断：如果凭证号是数字且不连续
            if voucher_numbers[i-1].isdigit() and voucher_numbers[i].isdigit():
                if int(voucher_numbers[i]) - int(voucher_numbers[i-1]) > 1:
                    df.loc[df['凭证号'] == voucher_numbers[i], '风险标记'] = df.loc[df['凭证号'] == voucher_numbers[i], '风险标记'].apply(lambda x: x + [{'规则名称': '凭证断号', '风险等级': '中'}])
    
    # 2. 科目合规性规则
    if rule_config.get('科目合规性规则', {}).get('enabled', True):
        # 摘要-科目匹配
        travel_keywords = ['差旅', '差旅费', '出差']
        travel_accounts = ['管理费用\\差旅费', '销售费用\\差旅费']
        
        def check_summary_account(row):
            for keyword in travel_keywords:
                if keyword in str(row['摘要']):
                    if not any(acc in str(row['科目名称']) for acc in travel_accounts):
                        return True
            return False
        
        df.loc[df.apply(check_summary_account, axis=1), '风险标记'] = df.loc[df.apply(check_summary_account, axis=1), '风险标记'].apply(lambda x: x + [{'规则名称': '摘要-科目匹配', '风险等级': '中'}])
    
    # 3. 金额合理性规则
    if rule_config.get('金额合理性规则', {}).get('enabled', True):
        # 大额交易
        for col in df['科目末级'].unique():
            col_df = df[df['科目末级'] == col]
            if len(col_df) > 3:
                mean = col_df['amount'].mean()
                std = col_df['amount'].std()
                threshold = mean + 3 * std
                df.loc[(df['科目末级'] == col) & (df['amount'] > threshold), '风险标记'] = df.loc[(df['科目末级'] == col) & (df['amount'] > threshold), '风险标记'].apply(lambda x: x + [{'规则名称': '大额交易', '风险等级': '中'}])
        
        # 整数金额
        df.loc[df['amount'] == df['amount'].astype(int), '风险标记'] = df.loc[df['amount'] == df['amount'].astype(int), '风险标记'].apply(lambda x: x + [{'规则名称': '整数金额', '风险等级': '低'}])
    
    # 4. 辅助项完整性规则
    if rule_config.get('辅助项完整性规则', {}).get('enabled', True):
        # 银行存款科目必须带有银行账户
        bank_accounts = ['银行存款']
        df.loc[(df['科目一级'].isin(bank_accounts)) & (df.get('银行账户', '') == ''), '风险标记'] = df.loc[(df['科目一级'].isin(bank_accounts)) & (df.get('银行账户', '') == ''), '风险标记'].apply(lambda x: x + [{'规则名称': '关键字段缺失', '风险等级': '中'}])
    
    # 5. 时间异常规则
    if rule_config.get('时间异常规则', {}).get('enabled', True):
        # 节假日记账
        df['weekday'] = df['date'].dt.weekday
        df.loc[df['weekday'].isin([5, 6]), '风险标记'] = df.loc[df['weekday'].isin([5, 6]), '风险标记'].apply(lambda x: x + [{'规则名称': '节假日记账', '风险等级': '低'}])
    
    return df

# 统计异常检测
def run_statistical_detection(df):
    """执行统计异常检测"""
    # 1. Benford定律检验
    def benford_test(series):
        # 简化版Benford检验
        first_digits = series.astype(str).str.lstrip('0').str[0].astype(float)
        first_digits = first_digits[first_digits > 0]
        if len(first_digits) < 100:
            return False
        
        observed = first_digits.value_counts().sort_index()
        expected = pd.Series([np.log10(1 + 1/d) for d in range(1, 10)], index=range(1, 10))
        expected = expected * len(first_digits)
        
        # 简单卡方检验
        chi2 = ((observed - expected) ** 2 / expected).sum()
        return chi2 > 20  # 阈值
    
    # 对每个科目应用Benford检验
    for col in df['科目末级'].unique():
        col_df = df[df['科目末级'] == col]
        if benford_test(col_df['amount']):
            df.loc[df['科目末级'] == col, '风险标记'] = df.loc[df['科目末级'] == col, '风险标记'].apply(lambda x: x + [{'规则名称': 'Benford定律异常', '风险等级': '中'}])
    
    # 2. 孤立森林
    if len(df) > 100:
        # 准备特征
        features = df[['amount', 'weekday']].copy()
        features['month'] = df['date'].dt.month
        features['is_weekend'] = df['weekday'].isin([5, 6]).astype(int)
        
        # 标准化
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        
        # 训练孤立森林
        clf = IsolationForest(contamination=0.01, random_state=42)
        outliers = clf.fit_predict(features_scaled) == -1
        
        df.loc[outliers, '风险标记'] = df.loc[outliers, '风险标记'].apply(lambda x: x + [{'规则名称': '孤立森林异常', '风险等级': '高'}])
    
    return df

# LLM分析
def llm_analyze(voucher_data):
    """使用LLM进行深度分析"""
    prompt = f"你是一名经验丰富的审计专家。请分析以下财务凭证，解释可能存在的异常问题，并提供审计建议。\n\n【公司业务背景】中星能源主要从事公用工程岛项目建设及运营，涉及动力岛、气化岛等。\n【凭证详情】{json.dumps(voucher_data, ensure_ascii=False)}\n\n请按以下格式输出：\n1. 异常描述：用通俗语言解释该凭证可能存在的问题\n2. 风险等级：高/中/低\n3. 审计建议：建议进一步检查哪些方面\n4. 相关法规：可能涉及的法规条款（参考知识库）"
    
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "mistral:7b-instruct-v0.3-q4_0",
                "prompt": prompt
            },
            timeout=30
        )
        return response.json().get('response', '')
    except Exception as e:
        return f"LLM分析失败: {str(e)}"

# 主处理任务
@app.task(bind=True)
def process_audit_data(self, file_path, rule_config):
    """处理审计数据"""
    try:
        # 1. 数据预处理
        self.update_state(state='PROGRESS', meta={'progress': 20})
        df = preprocess_data(file_path)
        
        # 2. 规则引擎
        self.update_state(state='PROGRESS', meta={'progress': 40})
        df = run_rules(df, rule_config)
        
        # 3. 统计异常检测
        self.update_state(state='PROGRESS', meta={'progress': 60})
        df = run_statistical_detection(df)
        
        # 4. LLM深度分析（对高风险凭证）
        self.update_state(state='PROGRESS', meta={'progress': 80})
        high_risk_vouchers = df[df['风险标记'].apply(lambda x: any(item['风险等级'] == '高' for item in x))]['凭证号'].unique()
        
        llm_results = {}
        for voucher in high_risk_vouchers[:10]:  # 限制处理数量
            voucher_data = df[df['凭证号'] == voucher].to_dict('records')
            llm_results[voucher] = llm_analyze(voucher_data)
        
        # 5. 保存结果到数据库
        self.update_state(state='PROGRESS', meta={'progress': 90})
        db = duckdb.connect('audit.db')
        db.execute('CREATE TABLE IF NOT EXISTS audit_results AS SELECT * FROM df')
        db.execute('INSERT INTO audit_results SELECT * FROM df')
        
        # 6. 生成结果
        result = {
            'total_records': len(df),
            'high_risk_count': len(df[df['风险标记'].apply(lambda x: any(item['风险等级'] == '高' for item in x))]),
            'medium_risk_count': len(df[df['风险标记'].apply(lambda x: any(item['风险等级'] == '中' for item in x))]),
            'low_risk_count': len(df[df['风险标记'].apply(lambda x: any(item['风险等级'] == '低' for item in x))]),
            'llm_analysis': llm_results
        }
        
        self.update_state(state='PROGRESS', meta={'progress': 100})
        return result
        
    except Exception as e:
        return {'error': str(e)}
