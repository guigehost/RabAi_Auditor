import requests
import json
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import time
import hashlib

@dataclass
class LLMConfig:
    model: str = "mistral:latest"
    base_url: str = "http://localhost:11434"
    timeout: int = 60
    max_retries: int = 3
    temperature: float = 0.7
    max_tokens: int = 2048
    fallback_models: List[str] = None
    
    def __post_init__(self):
        if self.fallback_models is None:
            self.fallback_models = ["mistral:latest", "llama2:latest", "qwen:latest"]

class OllamaClient:
    def __init__(self, config: LLMConfig = None):
        self.config = config or LLMConfig()
        self.cache = {}
    
    def _get_cache_key(self, prompt: str) -> str:
        return hashlib.md5(prompt.encode()).hexdigest()
    
    def _check_cache(self, prompt: str) -> Optional[str]:
        cache_key = self._get_cache_key(prompt)
        return self.cache.get(cache_key)
    
    def _save_cache(self, prompt: str, response: str):
        cache_key = self._get_cache_key(prompt)
        self.cache[cache_key] = response
    
    def generate(self, prompt: str, use_cache: bool = True) -> Dict:
        if use_cache:
            cached = self._check_cache(prompt)
            if cached:
                return {
                    'status': 'success',
                    'response': cached,
                    'cached': True
                }
        
        url = f"{self.config.base_url}/api/generate"
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens
            }
        }
        
        for attempt in range(self.config.max_retries):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    timeout=self.config.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    text = result.get('response', '')
                    
                    if use_cache:
                        self._save_cache(prompt, text)
                    
                    return {
                        'status': 'success',
                        'response': text,
                        'cached': False,
                        'model': self.config.model
                    }
                else:
                    return {
                        'status': 'error',
                        'error': f"HTTP {response.status_code}: {response.text}"
                    }
            
            except requests.exceptions.Timeout:
                if attempt < self.config.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    return {
                        'status': 'error',
                        'error': 'Request timeout after retries'
                    }
            
            except Exception as e:
                return {
                    'status': 'error',
                    'error': str(e)
                }
        
        return {
            'status': 'error',
            'error': 'Max retries exceeded'
        }
    
    def check_health(self) -> bool:
        try:
            response = requests.get(
                f"{self.config.base_url}/api/tags",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def get_available_models(self) -> List[str]:
        try:
            response = requests.get(
                f"{self.config.base_url}/api/tags",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except:
            return []
    
    def find_available_model(self) -> Optional[str]:
        available_models = self.get_available_models()
        
        if self.config.model in available_models:
            return self.config.model
        
        for fallback in (self.config.fallback_models or []):
            if fallback in available_models:
                return fallback
        
        for model in available_models:
            if 'mistral' in model.lower() or 'llama' in model.lower() or 'qwen' in model.lower():
                return model
        
        if available_models:
            return available_models[0]
        
        return None

class PromptTemplates:
    COMPANY_BACKGROUND = """
【公司业务背景】
中星能源主要从事公用工程岛项目建设及运营，涉及动力岛、气化岛等。
主要业务包括：
- 在建工程项目：公用工程岛项目（动力岛、气化岛）
- 日常运营：差旅报销、办公费用、工资社保、税费缴纳、银行转账
- 投融资：银团贷款、流贷、保理、融资租赁等
- 供应链：煤炭采购、备品备件、药剂采购、蒸汽销售等
"""
    
    @staticmethod
    def classify_summary(summaries: List[str]) -> str:
        prompt = """你是一名财务专家。请将以下财务摘要归类为：差旅费、办公费、工程款、设备采购、税费、银行手续费、工资薪酬、内部转账、其他费用。
每条摘要只输出类别名称，用逗号分隔。

摘要列表：
"""
        for i, summary in enumerate(summaries, 1):
            prompt += f"{i}. {summary}\n"
        
        prompt += "\n输出："
        return prompt
    
    @staticmethod
    def analyze_voucher(voucher_data: Dict) -> str:
        prompt = f"""你是一名经验丰富的审计专家。请分析以下财务凭证，解释可能存在的异常问题，并提供审计建议。

{PromptTemplates.COMPANY_BACKGROUND}

【凭证详情】
{json.dumps(voucher_data, ensure_ascii=False, indent=2)}

请按以下格式输出：
1. 异常描述：用通俗语言解释该凭证可能存在的问题
2. 风险等级：高/中/低
3. 审计建议：建议进一步检查哪些方面
4. 相关法规：可能涉及的法规条款（参考会计准则、税法等）
"""
        return prompt
    
    @staticmethod
    def extract_auxiliary(auxiliary_text: str) -> str:
        prompt = f"""请从以下辅助项文本中提取结构化的键值对信息，以JSON格式输出。

辅助项文本：
{auxiliary_text}

输出格式示例：
{{"银行账户": "建设银行", "部门": "行政部", "人员": "张三"}}
"""
        return prompt
    
    @staticmethod
    def audit_qa(question: str, context: str = "") -> str:
        prompt = f"""你是一名专业的审计顾问，精通财务审计、会计准则和税法。

{PromptTemplates.COMPANY_BACKGROUND}

"""
        if context:
            prompt += f"【相关知识】\n{context}\n\n"
        
        prompt += f"【问题】\n{question}\n\n请提供专业、准确的回答："
        return prompt
    
    @staticmethod
    def generate_audit_memo(anomaly_data: Dict) -> str:
        prompt = f"""请根据以下异常信息，生成规范的审计底稿。

{PromptTemplates.COMPANY_BACKGROUND}

【异常信息】
{json.dumps(anomaly_data, ensure_ascii=False, indent=2)}

请按以下格式输出审计底稿：

一、审计事项
[描述审计发现的具体事项]

二、审计发现
[详细描述发现的问题]

三、审计依据
[引用相关的会计准则、法规条款]

四、审计建议
[提出具体的改进建议]

五、附件清单
[列出相关的凭证号、金额等]
"""
        return prompt

class LLMService:
    def __init__(self, config: LLMConfig = None):
        self.client = OllamaClient(config)
        self.templates = PromptTemplates()
    
    def classify_summaries(self, summaries: List[str], batch_size: int = 20) -> List[str]:
        results = []
        
        for i in range(0, len(summaries), batch_size):
            batch = summaries[i:i+batch_size]
            prompt = self.templates.classify_summary(batch)
            
            response = self.client.generate(prompt)
            
            if response['status'] == 'success':
                categories = response['response'].strip().split(',')
                categories = [c.strip() for c in categories]
                
                while len(categories) < len(batch):
                    categories.append('其他费用')
                
                results.extend(categories[:len(batch)])
            else:
                results.extend(['其他费用'] * len(batch))
        
        return results
    
    def analyze_voucher(self, voucher_data: Dict) -> Dict:
        prompt = self.templates.analyze_voucher(voucher_data)
        response = self.client.generate(prompt)
        
        if response['status'] == 'success':
            return {
                'status': 'success',
                'analysis': response['response'],
                'cached': response.get('cached', False)
            }
        else:
            return {
                'status': 'error',
                'error': response['error']
            }
    
    def extract_auxiliary_info(self, auxiliary_text: str) -> Dict:
        prompt = self.templates.extract_auxiliary(auxiliary_text)
        response = self.client.generate(prompt)
        
        if response['status'] == 'success':
            try:
                result = json.loads(response['response'])
                return {
                    'status': 'success',
                    'data': result
                }
            except json.JSONDecodeError:
                return {
                    'status': 'error',
                    'error': 'Failed to parse JSON response'
                }
        else:
            return {
                'status': 'error',
                'error': response['error']
            }
    
    def answer_question(self, question: str, context: str = "") -> Dict:
        prompt = self.templates.audit_qa(question, context)
        response = self.client.generate(prompt)
        
        if response['status'] == 'success':
            return {
                'status': 'success',
                'answer': response['response'],
                'cached': response.get('cached', False)
            }
        else:
            return {
                'status': 'error',
                'error': response['error']
            }
    
    def generate_audit_memo(self, anomaly_data: Dict) -> Dict:
        prompt = self.templates.generate_audit_memo(anomaly_data)
        response = self.client.generate(prompt)
        
        if response['status'] == 'success':
            return {
                'status': 'success',
                'memo': response['response'],
                'cached': response.get('cached', False)
            }
        else:
            return {
                'status': 'error',
                'error': response['error']
            }
    
    def check_service(self) -> Dict:
        is_healthy = self.client.check_health()
        available_models = self.client.get_available_models()
        available_model = self.client.find_available_model()
        
        return {
            'status': 'healthy' if is_healthy and available_model else 'unavailable',
            'model': self.client.config.model,
            'available_model': available_model,
            'available_models': available_models,
            'base_url': self.client.config.base_url,
            'message': 'LLM service is ready' if available_model else 'No models available. Please pull a model using: ollama pull mistral'
        }

class RAGKnowledgeBase:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
        self.documents = []
        self.embeddings = []
    
    def add_document(self, content: str, metadata: Dict = None):
        self.documents.append({
            'content': content,
            'metadata': metadata or {}
        })
    
    def add_documents_from_file(self, file_path: str):
        if not os.path.exists(file_path):
            return
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.add_document(content, {'source': file_path})
    
    def search(self, query: str, top_k: int = 3) -> List[Dict]:
        results = []
        
        for doc in self.documents:
            score = self._simple_similarity(query, doc['content'])
            results.append({
                'content': doc['content'],
                'metadata': doc['metadata'],
                'score': score
            })
        
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]
    
    def _simple_similarity(self, text1: str, text2: str) -> float:
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    def query_with_context(self, question: str) -> Dict:
        relevant_docs = self.search(question)
        
        if relevant_docs:
            context = "\n\n".join([doc['content'] for doc in relevant_docs])
        else:
            context = ""
        
        return self.llm_service.answer_question(question, context)

def create_llm_service(model: str = None, base_url: str = None) -> LLMService:
    config = LLMConfig()
    if model:
        config.model = model
    if base_url:
        config.base_url = base_url
    
    return LLMService(config)
