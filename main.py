from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from celery import Celery
import duckdb
import os
import json
from pydantic import BaseModel
from typing import List, Dict, Optional

app = FastAPI(title="智能审计工具 API")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应设置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置Celery
celery_app = Celery(
    "audit",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

# 数据库连接
db = duckdb.connect('audit.db')

# 数据模型
class AuditTask(BaseModel):
    task_id: str
    status: str
    progress: float
    result: Optional[Dict] = None

class RuleConfig(BaseModel):
    rule_type: str
    enabled: bool
    parameters: Optional[Dict] = None

class LLMRequest(BaseModel):
    prompt: str
    context: Optional[Dict] = None

# 上传文件接口
@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), rules: str = Form(...)):
    """上传审计数据文件"""
    # 保存文件
    file_path = f"uploads/{file.filename}"
    os.makedirs("uploads", exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    # 解析规则配置
    rule_config = json.loads(rules)
    
    # 启动异步任务
    task = celery_app.send_task(
        "tasks.process_audit_data",
        args=[file_path, rule_config]
    )
    
    return {"task_id": task.id, "status": "pending"}

# 获取任务状态
@app.get("/api/task/{task_id}")
async def get_task_status(task_id: str):
    """获取审计任务状态"""
    task = celery_app.AsyncResult(task_id)
    status = task.status
    progress = 0.0
    result = None
    
    if task.ready():
        result = task.get()
        progress = 100.0
    elif status == "PROGRESS":
        # 从任务元数据获取进度
        progress = task.info.get("progress", 0.0)
    
    return AuditTask(
        task_id=task_id,
        status=status,
        progress=progress,
        result=result
    )

# LLM分析接口
@app.post("/api/llm/analyze")
async def llm_analyze(request: LLMRequest):
    """使用LLM进行深度分析"""
    import requests as req
    
    try:
        tags_response = req.get("http://localhost:11434/api/tags", timeout=5)
        if tags_response.status_code == 200:
            models = tags_response.json().get('models', [])
            available_models = [m['name'] for m in models]
            
            model_name = None
            for m in ['mistral:latest', 'llama2:latest', 'qwen:latest']:
                if m in available_models:
                    model_name = m
                    break
            
            if not model_name and available_models:
                model_name = available_models[0]
            
            if not model_name:
                return {"error": "No LLM models available. Please pull a model using: ollama pull mistral"}
        else:
            return {"error": "LLM service unavailable"}
        
        payload = {
            "model": model_name,
            "prompt": request.prompt,
            "stream": False
        }
        
        response = req.post(
            "http://localhost:11434/api/generate",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            return {"result": response.json()}
        else:
            return {"error": f"LLM服务调用失败: {response.text}"}
    except Exception as e:
        return {"error": f"LLM服务异常: {str(e)}"}

# LLM健康检查接口
@app.get("/api/llm/health")
async def llm_health():
    """检查LLM服务健康状态"""
    import requests as req
    
    try:
        response = req.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            available_models = [m['name'] for m in models]
            
            available_model = None
            for m in ['mistral:latest', 'llama2:latest', 'qwen:latest']:
                if m in available_models:
                    available_model = m
                    break
            
            if not available_model and available_models:
                available_model = available_models[0]
            
            return {
                "status": "healthy" if available_model else "unavailable",
                "model": "mistral:latest",
                "available_model": available_model,
                "available_models": available_models,
                "base_url": "http://localhost:11434",
                "message": "LLM service is ready" if available_model else "No models available. Please pull a model using: ollama pull mistral"
            }
        else:
            return {
                "status": "unavailable",
                "message": "Ollama service is not responding"
            }
    except Exception as e:
        return {
            "status": "unavailable",
            "message": f"Failed to connect to Ollama: {str(e)}"
        }

# 规则配置接口
@app.post("/api/rules")
async def configure_rules(rules: List[RuleConfig]):
    """配置审计规则"""
    # 保存规则配置
    with open("rules.json", "w") as f:
        json.dump([rule.model_dump() for rule in rules], f)
    
    return {"message": "规则配置已保存"}

# 健康检查
@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)