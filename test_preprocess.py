import pandas as pd
import numpy as np
import os

# 导入数据预处理函数
from tasks import preprocess_data

# 创建测试数据
def create_test_data():
    """创建测试数据"""
    data = {
        '年': [2021, 2021, 2021, 2021],
        '月': [1, 1, 1, 1],
        '日': [1, 1, 2, 2],
        '核算账簿名称': ['总账', '总账', '总账', '总账'],
        '凭证号': ['1', '1', '2', '2'],
        '分录号': [1, 2, 1, 2],
        '摘要': ['支付差旅费', '银行转账', '购买办公用品', '支付工资'],
        '科目编码': ['660201', '1002', '660202', '660101'],
        '科目名称': ['管理费用\差旅费', '银行存款', '管理费用\办公费', '管理费用\工资'],
        '辅助项': ['【部门：行政部】【人员：张三】', '【银行账户：建设银行】【金额：1000】', '【部门：财务部】', '【部门：人力资源部】【人员：李四】'],
        '币种': ['人民币', '人民币', '人民币', '人民币'],
        '借方本币': [1000.00, 0.00, 500.00, 5000.00],
        '贷方本币': [0.00, 1000.00, 0.00, 0.00]
    }
    
    df = pd.DataFrame(data)
    df.to_excel('test_data.xlsx', index=False)
    return 'test_data.xlsx'

# 测试数据预处理
def test_preprocess():
    """测试数据预处理功能"""
    print("开始测试数据预处理...")
    
    # 创建测试数据
    file_path = create_test_data()
    
    # 执行预处理
    df = preprocess_data(file_path)
    
    # 验证结果
    print("\n1. 数据清洗验证:")
    print(f"日期列类型: {df['date'].dtype}")
    print(f"金额列类型: {df['amount'].dtype}")
    print(f"借贷方向列: {df['direction'].unique()}")
    
    print("\n2. 科目层级拆分验证:")
    print(f"科目末级: {df['科目末级'].unique()}")
    print(f"科目一级: {df['科目一级'].unique()}")
    print(f"科目二级: {df['科目二级'].unique()}")
    
    print("\n3. 辅助项解析验证:")
    print(f"辅助项列: {[col for col in df.columns if col not in ['年', '月', '日', '核算账簿名称', '凭证号', '分录号', '摘要', '科目编码', '科目名称', '辅助项', '币种', '借方本币', '贷方本币', 'date', 'direction', 'amount', '科目末级', '科目一级', '科目二级', '辅助项_dict', '借贷平衡', '差额', '风险标记']]}")
    
    print("\n4. 凭证借贷平衡验证:")
    print(f"借贷平衡: {df['借贷平衡'].unique()}")
    print(f"差额: {df['差额'].unique()}")
    
    print("\n5. 异常预标记验证:")
    print(f"风险标记: {df['风险标记'].tolist()}")
    
    print("\n数据预处理测试完成！")
    
    # 清理测试文件
    if os.path.exists(file_path):
        os.remove(file_path)

if __name__ == "__main__":
    test_preprocess()