from llm_service import LLMService, create_llm_service, PromptTemplates

def test_llm_service():
    print("Starting LLM service test...")
    
    llm = create_llm_service()
    
    print("\n1. Checking LLM service health...")
    health = llm.check_service()
    print(f"Status: {health['status']}")
    print(f"Configured model: {health['model']}")
    print(f"Available model: {health.get('available_model', 'None')}")
    print(f"Available models: {health.get('available_models', [])}")
    print(f"Message: {health.get('message', '')}")
    
    if health['status'] != 'healthy' or not health.get('available_model'):
        print("\n" + "="*60)
        print("LLM service is not fully configured.")
        print("To use LLM features, please:")
        print("1. Ensure Ollama is running: ollama serve")
        print("2. Pull a model: ollama pull mistral")
        print("="*60)
        print("\nTesting prompt templates instead...")
        
        print("\n2. Testing prompt template generation...")
        summaries = [
            "杨荣康报销上海锅炉厂汽包水压试验见证出差补贴",
            "内部银行账户转款（东方农商-建设银行）",
            "支付石化产业基地公用工程岛项目一期工程总承包EPC"
        ]
        
        prompt = PromptTemplates.classify_summary(summaries)
        print("Classification prompt generated successfully")
        print(f"Prompt length: {len(prompt)} characters")
        
        voucher_data = {
            "凭证号": "记-0024",
            "日期": "2021-01-14",
            "分录": [
                {"分录号": 1, "摘要": "付银行转账手续费", "科目": "660304", "科目名称": "财务费用\\手续费", "借方": 61.80, "贷方": 0},
            ]
        }
        
        prompt = PromptTemplates.analyze_voucher(voucher_data)
        print("\nVoucher analysis prompt generated successfully")
        print(f"Prompt length: {len(prompt)} characters")
        
        question = "在建工程转固定资产的条件是什么？"
        prompt = PromptTemplates.audit_qa(question)
        print("\nAudit QA prompt generated successfully")
        print(f"Prompt length: {len(prompt)} characters")
        
        print("\nLLM service test completed (template mode)!")
        return
    
    print("\n2. Testing summary classification...")
    summaries = [
        "杨荣康报销上海锅炉厂汽包水压试验见证出差补贴",
        "内部银行账户转款（东方农商-建设银行）",
        "支付石化产业基地公用工程岛项目一期工程总承包EPC"
    ]
    
    categories = llm.classify_summaries(summaries)
    print(f"Summaries: {summaries}")
    print(f"Categories: {categories}")
    
    print("\n3. Testing voucher analysis...")
    voucher_data = {
        "凭证号": "记-0024",
        "日期": "2021-01-14",
        "分录": [
            {"分录号": 1, "摘要": "付银行转账手续费", "科目": "660304", "科目名称": "财务费用\\手续费", "借方": 61.80, "贷方": 0},
            {"分录号": 2, "摘要": "付银行转账手续费", "科目": "1002", "科目名称": "银行存款", "借方": 0, "贷方": 30.00},
            {"分录号": 3, "摘要": "付银行转账手续费", "科目": "1002", "科目名称": "银行存款", "借方": 0, "贷方": 27.00},
            {"分录号": 4, "摘要": "付银行转账手续费", "科目": "1002", "科目名称": "银行存款", "借方": 0, "贷方": 4.80}
        ],
        "异常标记": ["大额拆分支付"]
    }
    
    analysis = llm.analyze_voucher(voucher_data)
    if analysis['status'] == 'success':
        print("Analysis result:")
        print(analysis['analysis'][:500] + "..." if len(analysis['analysis']) > 500 else analysis['analysis'])
    else:
        print(f"Error: {analysis['error']}")
    
    print("\n4. Testing question answering...")
    question = "在建工程转固定资产的条件是什么？"
    answer = llm.answer_question(question)
    if answer['status'] == 'success':
        print(f"Question: {question}")
        print(f"Answer: {answer['answer'][:500]}..." if len(answer['answer']) > 500 else answer['answer'])
    else:
        print(f"Error: {answer['error']}")
    
    print("\nLLM service test completed!")

if __name__ == "__main__":
    test_llm_service()
