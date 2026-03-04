import requests
import json

url = "http://localhost:8000/api/upload"

test_data = """年,月,日,核算账簿名称,凭证号,分录号,摘要,科目编码,科目名称,辅助项,币种,借方本币,贷方本币
2021,1,1,总账,1,1,支付差旅费,660201,管理费用\\差旅费,【部门：行政部】,人民币,1000.00,0
2021,1,1,总账,1,2,支付差旅费,1002,银行存款,【银行账户：建设银行】,人民币,0,1000.00
2021,1,2,总账,2,1,购买办公用品,660202,管理费用\\办公费,【部门：财务部】,人民币,500.00,0
2021,1,2,总账,2,2,购买办公用品,1002,银行存款,,人民币,0,500.00
"""

with open("test_upload.csv", "w", encoding="utf-8") as f:
    f.write(test_data)

files = {"file": ("test_upload.csv", open("test_upload.csv", "rb"), "text/csv")}
data = {"rules": json.dumps({"借贷不平": {"enabled": True}, "大额交易": {"enabled": True}})}

print("Sending upload request...")
try:
    response = requests.post(url, files=files, data=data, timeout=30)
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
