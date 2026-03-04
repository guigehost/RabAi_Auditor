from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from pydantic import BaseModel
from typing import Optional, Dict, List
import pandas as pd
import numpy as np
import logging
from datetime import datetime
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="智能审计工具 API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class AuditTask(BaseModel):
    task_id: str
    status: str
    progress: float
    result: Optional[Dict] = None

class LLMRequest(BaseModel):
    prompt: str
    context: Optional[Dict] = None

class RuleItem(BaseModel):
    rule_type: str
    enabled: bool
    parameters: Optional[Dict] = None

DEFAULT_RULES = {
    "凭证级": {
        "借贷不平": {"enabled": True, "description": "检测借贷金额不平衡的凭证", "risk": "高"},
        "凭证断号": {"enabled": True, "description": "检测凭证号不连续的情况", "risk": "中"},
        "一借多贷异常": {"enabled": True, "description": "检测一借多贷且金额相等的异常", "risk": "中"},
        "摘要为空": {"enabled": True, "description": "检测摘要为空的记录", "risk": "低"},
    },
    "科目合规": {
        "摘要科目匹配": {"enabled": True, "description": "检测摘要与科目是否匹配", "risk": "中"},
        "在建工程关联": {"enabled": True, "description": "检测在建工程是否缺少合同号/项目", "risk": "中"},
        "税费科目逻辑": {"enabled": True, "description": "检测税费科目是否缺少税率信息", "risk": "高"},
        "往来科目清理": {"enabled": True, "description": "检测长期挂账的往来款项", "risk": "中"},
    },
    "金额合理": {
        "大额交易": {"enabled": True, "description": "检测超过均值+3σ的大额交易", "risk": "中", "threshold": 3.0},
        "整数金额": {"enabled": True, "description": "检测金额为整数且>=1万的记录", "risk": "低", "min_amount": 10000},
        "频繁小额": {"enabled": True, "description": "检测同一科目频繁小额交易", "risk": "低", "count_threshold": 5},
        "异常拆分": {"enabled": True, "description": "检测同一凭证多笔相同金额", "risk": "高"},
        "金额尾数异常": {"enabled": True, "description": "检测金额尾数为特定数字", "risk": "低"},
    },
    "时间异常": {
        "节假日记账": {"enabled": True, "description": "检测周末/节假日记账", "risk": "低"},
        "月末突击": {"enabled": True, "description": "检测月末大额交易", "risk": "中"},
        "跨年调整": {"enabled": True, "description": "检测12月31日大量调整分录", "risk": "中"},
        "间隔异常": {"enabled": True, "description": "检测记账日期间隔异常", "risk": "低"},
    }
}

def clean_for_json(obj):
    if obj is None:
        return None
    if isinstance(obj, dict):
        return {k: clean_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [clean_for_json(item) for item in obj]
    if isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return round(obj, 2)
    if pd.isna(obj):
        return None
    if hasattr(obj, 'strftime'):
        return obj.strftime('%Y-%m-%d')
    return obj

class RuleEngine:
    def __init__(self, df, rule_config):
        self.df = df.copy()
        self.rule_config = rule_config
        self.df['风险标记'] = [[] for _ in range(len(self.df))]
    
    def run_all_rules(self):
        self._check_balance()
        self._check_voucher_sequence()
        self._check_one_debit_multi_credit()
        self._check_empty_summary()
        self._check_large_amount()
        self._check_round_amount()
        self._check_frequent_small()
        self._check_split_amount()
        self._check_weekend_booking()
        self._check_month_end()
        self._check_year_end()
        return self.df
    
    def _add_risk(self, indices, rule_name, risk_level, description=""):
        for idx in indices:
            self.df.at[idx, '风险标记'].append({
                '规则名称': rule_name,
                '风险等级': risk_level,
                '描述': description
            })
    
    def _check_balance(self):
        if not self.rule_config.get('凭证级', {}).get('借贷不平', {}).get('enabled', True):
            return
        balance = self.df.groupby('凭证号').agg({'借方本币': 'sum', '贷方本币': 'sum'}).reset_index()
        balance['差额'] = (balance['借方本币'] - balance['贷方本币']).abs()
        unbalanced = balance[balance['差额'] > 0.01]['凭证号'].tolist()
        mask = self.df['凭证号'].isin(unbalanced)
        self._add_risk(self.df[mask].index, '借贷不平', '高', f'借贷差额超过0.01')
        logger.info(f"借贷不平: {mask.sum()} 条")
    
    def _check_voucher_sequence(self):
        if not self.rule_config.get('凭证级', {}).get('凭证断号', {}).get('enabled', True):
            return
        voucher_nums = self.df['凭证号'].unique()
        if len(voucher_nums) > 1:
            try:
                nums = pd.to_numeric(voucher_nums, errors='coerce')
                nums = nums[~np.isnan(nums)].astype(int).sort_values()
                if len(nums) > 1:
                    gaps = []
                    for i in range(1, len(nums)):
                        if nums.iloc[i] - nums.iloc[i-1] > 1:
                            gaps.extend(range(nums.iloc[i-1]+1, nums.iloc[i]))
                    if gaps:
                        self._add_risk(self.df.index[:1], '凭证断号', '中', f'发现{len(gaps)}处断号')
                        logger.info(f"凭证断号: {len(gaps)} 处")
            except:
                pass
    
    def _check_one_debit_multi_credit(self):
        if not self.rule_config.get('凭证级', {}).get('一借多贷异常', {}).get('enabled', True):
            return
        for voucher in self.df['凭证号'].unique():
            v_df = self.df[self.df['凭证号'] == voucher]
            debit_count = (v_df['借方本币'] > 0).sum()
            credit_count = (v_df['贷方本币'] > 0).sum()
            if debit_count == 1 and credit_count > 1:
                credit_amounts = v_df[v_df['贷方本币'] > 0]['贷方本币'].values
                if len(set(credit_amounts)) == 1:
                    self._add_risk(v_df.index, '一借多贷异常', '中', '一借多贷且金额相等')
        logger.info("一借多贷异常检查完成")
    
    def _check_empty_summary(self):
        if not self.rule_config.get('凭证级', {}).get('摘要为空', {}).get('enabled', True):
            return
        mask = self.df['摘要'].isna() | (self.df['摘要'].astype(str).str.strip() == '')
        self._add_risk(self.df[mask].index, '摘要为空', '低', '摘要字段为空')
        logger.info(f"摘要为空: {mask.sum()} 条")
    
    def _check_large_amount(self):
        config = self.rule_config.get('金额合理', {}).get('大额交易', {})
        if not config.get('enabled', True):
            return
        threshold = config.get('threshold', 3.0)
        for subject in self.df['科目末级'].unique():
            s_df = self.df[self.df['科目末级'] == subject]
            if len(s_df) > 3:
                mean, std = s_df['amount'].mean(), s_df['amount'].std()
                if std > 0:
                    limit = mean + threshold * std
                    mask = (self.df['科目末级'] == subject) & (self.df['amount'] > limit)
                    count = mask.sum()
                    if count > 0:
                        self._add_risk(self.df[mask].index, '大额交易', '中', f'金额{limit:.2f}超过阈值')
                        logger.info(f"大额交易({subject}): {count} 条")
    
    def _check_round_amount(self):
        config = self.rule_config.get('金额合理', {}).get('整数金额', {})
        if not config.get('enabled', True):
            return
        min_amount = config.get('min_amount', 10000)
        mask = (self.df['amount'] == self.df['amount'].astype(int)) & (self.df['amount'] >= min_amount)
        self._add_risk(self.df[mask].index, '整数金额', '低', f'金额为整数且>={min_amount}')
        logger.info(f"整数金额: {mask.sum()} 条")
    
    def _check_frequent_small(self):
        config = self.rule_config.get('金额合理', {}).get('频繁小额', {})
        if not config.get('enabled', True):
            return
        threshold = config.get('count_threshold', 5)
        for subject in self.df['科目末级'].unique():
            s_df = self.df[self.df['科目末级'] == subject]
            small = s_df[s_df['amount'] < 1000]
            if len(small) >= threshold:
                self._add_risk(small.index, '频繁小额', '低', f'小额交易{len(small)}笔')
        logger.info("频繁小额检查完成")
    
    def _check_split_amount(self):
        if not self.rule_config.get('金额合理', {}).get('异常拆分', {}).get('enabled', True):
            return
        for voucher in self.df['凭证号'].unique():
            v_df = self.df[self.df['凭证号'] == voucher]
            amounts = v_df['amount'].values
            if len(amounts) > 2:
                unique_amounts, counts = np.unique(amounts, return_counts=True)
                for amt, cnt in zip(unique_amounts, counts):
                    if cnt > 2:
                        self._add_risk(v_df.index, '异常拆分', '高', f'同凭证{cnt}笔相同金额{amt:.2f}')
        logger.info("异常拆分检查完成")
    
    def _check_weekend_booking(self):
        if not self.rule_config.get('时间异常', {}).get('节假日记账', {}).get('enabled', True):
            return
        self.df['weekday'] = self.df['date'].dt.weekday
        mask = self.df['weekday'].isin([5, 6])
        self._add_risk(self.df[mask].index, '节假日记账', '低', '周末记账')
        logger.info(f"节假日记账: {mask.sum()} 条")
    
    def _check_month_end(self):
        if not self.rule_config.get('时间异常', {}).get('月末突击', {}).get('enabled', True):
            return
        mask = (self.df['date'].dt.day >= 25) & (self.df['amount'] > self.df['amount'].quantile(0.9))
        self._add_risk(self.df[mask].index, '月末突击', '中', '月末大额交易')
        logger.info(f"月末突击: {mask.sum()} 条")
    
    def _check_year_end(self):
        if not self.rule_config.get('时间异常', {}).get('跨年调整', {}).get('enabled', True):
            return
        mask = (self.df['date'].dt.month == 12) & (self.df['date'].dt.day == 31)
        if mask.sum() > 10:
            self._add_risk(self.df[mask].index, '跨年调整', '中', f'年末调整{mask.sum()}笔')
        logger.info(f"跨年调整: {mask.sum()} 条")

def process_file(file_path, rule_config):
    logger.info(f"Processing file: {file_path}")
    
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)
    
    logger.info(f"Read {len(df)} rows, columns: {list(df.columns)}")
    
    df['date'] = pd.to_datetime(df[['年', '月', '日']].astype(str).agg('-'.join, axis=1))
    
    for col in ['借方本币', '贷方本币']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '').astype(float)
    
    df['amount'] = df[['借方本币', '贷方本币']].max(axis=1)
    df['科目末级'] = df['科目名称'].apply(lambda x: str(x).split('\\')[-1] if '\\' in str(x) else str(x))
    df['科目一级'] = df['科目名称'].apply(lambda x: str(x).split('\\')[0] if '\\' in str(x) else str(x))
    
    engine = RuleEngine(df, rule_config)
    df = engine.run_all_rules()
    
    high = len(df[df['风险标记'].apply(lambda x: any(m['风险等级'] == '高' for m in x))])
    medium = len(df[df['风险标记'].apply(lambda x: any(m['风险等级'] == '中' for m in x))])
    low = len(df[df['风险标记'].apply(lambda x: any(m['风险等级'] == '低' for m in x))])
    
    anomaly_df = df[df['风险标记'].apply(lambda x: len(x) > 0)]
    cols = [c for c in ['凭证号', 'date', '摘要', '科目名称', '科目一级', 'amount', '风险标记', '借方本币', '贷方本币'] if c in anomaly_df.columns]
    records = anomaly_df[cols].head(200).to_dict('records')
    
    rule_stats = {}
    for _, row in df.iterrows():
        for mark in row['风险标记']:
            rule_name = mark['规则名称']
            if rule_name not in rule_stats:
                rule_stats[rule_name] = {'count': 0, 'risk': mark['风险等级']}
            rule_stats[rule_name]['count'] += 1
    
    return {
        'total_records': len(df),
        'high_risk_count': high,
        'medium_risk_count': medium,
        'low_risk_count': low,
        'anomaly_records': clean_for_json(records),
        'rule_stats': rule_stats
    }

@app.get("/api/rules")
async def get_rules():
    return DEFAULT_RULES

@app.post("/api/rules")
async def save_rules(rules: Dict):
    with open("rules_config.json", "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)
    return {"message": "规则配置已保存"}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), rules: str = Form(...)):
    logger.info(f"Upload: {file.filename}")
    try:
        os.makedirs("uploads", exist_ok=True)
        path = f"uploads/{file.filename}"
        with open(path, "wb") as f:
            f.write(await file.read())
        result = process_file(path, json.loads(rules))
        return {"task_id": "sync", "status": "SUCCESS", "result": result}
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return {"task_id": "error", "status": "FAILURE", "error": str(e)}

@app.get("/api/task/{task_id}")
async def get_task(task_id: str):
    return AuditTask(task_id=task_id, status="SUCCESS", progress=100.0)

@app.post("/api/llm/analyze")
async def llm_analyze(request: LLMRequest):
    try:
        import requests as req
        r = req.get("http://localhost:11434/api/tags", timeout=5)
        if r.status_code == 200:
            models = [m['name'] for m in r.json().get('models', [])]
            if models:
                resp = req.post("http://localhost:11434/api/generate", 
                              json={"model": models[0], "prompt": request.prompt, "stream": False}, timeout=60)
                if resp.status_code == 200:
                    return {"result": resp.json()}
        return {"error": "LLM unavailable"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/llm/health")
async def llm_health():
    try:
        import requests as req
        r = req.get("http://localhost:11434/api/tags", timeout=5)
        if r.status_code == 200:
            models = [m['name'] for m in r.json().get('models', [])]
            return {"status": "healthy" if models else "unavailable", "available_models": models}
        return {"status": "unavailable"}
    except:
        return {"status": "unavailable"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
