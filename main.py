from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from pydantic import BaseModel
from typing import Optional, Dict
import pandas as pd
import numpy as np
import logging

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

def process_file(file_path, rule_config):
    logger.info(f"Processing file: {file_path}")
    
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)
    
    logger.info(f"Read {len(df)} rows")
    
    df['date'] = pd.to_datetime(df[['年', '月', '日']].astype(str).agg('-'.join, axis=1))
    
    for col in ['借方本币', '贷方本币']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '').astype(float)
    
    df['amount'] = df[['借方本币', '贷方本币']].max(axis=1)
    df['科目末级'] = df['科目名称'].apply(lambda x: str(x).split('\\')[-1] if '\\' in str(x) else str(x))
    
    balance = df.groupby('凭证号').agg({'借方本币': 'sum', '贷方本币': 'sum'}).reset_index()
    balance['借贷平衡'] = (balance['借方本币'] - balance['贷方本币']).abs() < 0.01
    df = df.merge(balance[['凭证号', '借贷平衡']], on='凭证号', how='left')
    df['风险标记'] = [[] for _ in range(len(df))]
    
    # Run rules
    if rule_config.get('借贷不平', {}).get('enabled', True):
        for idx in df[~df['借贷平衡']].index:
            df.at[idx, '风险标记'].append({'规则名称': '借贷不平', '风险等级': '高'})
    
    if rule_config.get('节假日记账', {}).get('enabled', True):
        df['weekday'] = df['date'].dt.weekday
        for idx in df[df['weekday'].isin([5, 6])].index:
            df.at[idx, '风险标记'].append({'规则名称': '节假日记账', '风险等级': '低'})
    
    # Count risks
    high = len(df[df['风险标记'].apply(lambda x: any(m['风险等级'] == '高' for m in x))])
    medium = len(df[df['风险标记'].apply(lambda x: any(m['风险等级'] == '中' for m in x))])
    low = len(df[df['风险标记'].apply(lambda x: any(m['风险等级'] == '低' for m in x))])
    
    # Get anomaly records
    anomaly_df = df[df['风险标记'].apply(lambda x: len(x) > 0)]
    cols = [c for c in ['凭证号', 'date', '摘要', '科目名称', 'amount', '风险标记'] if c in anomaly_df.columns]
    records = anomaly_df[cols].head(100).to_dict('records')
    
    return {
        'total_records': len(df),
        'high_risk_count': high,
        'medium_risk_count': medium,
        'low_risk_count': low,
        'anomaly_records': clean_for_json(records)
    }

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
    uvicorn.run(app, host="0.0.0.0", port=8000)
