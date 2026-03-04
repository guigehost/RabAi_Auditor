import pandas as pd
import numpy as np
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class RiskMark:
    rule_name: str
    risk_level: str
    description: str
    details: Optional[Dict] = None

class BaseRule(ABC):
    def __init__(self, name: str, risk_level: str, enabled: bool = True):
        self.name = name
        self.risk_level = risk_level
        self.enabled = enabled
    
    @abstractmethod
    def check(self, df: pd.DataFrame) -> pd.DataFrame:
        pass
    
    def add_risk_mark(self, df: pd.DataFrame, mask: pd.Series, description: str, details: Dict = None):
        for idx in df[mask].index:
            current_marks = df.at[idx, '风险标记']
            if not isinstance(current_marks, list):
                current_marks = []
            current_marks.append({
                '规则名称': self.name,
                '风险等级': self.risk_level,
                '描述': description,
                '详情': details
            })
            df.at[idx, '风险标记'] = current_marks
        return df

class VoucherBalanceRule(BaseRule):
    def __init__(self):
        super().__init__('借贷不平', '高')
    
    def check(self, df: pd.DataFrame) -> pd.DataFrame:
        if '借贷平衡' not in df.columns:
            return df
        mask = ~df['借贷平衡']
        self.add_risk_mark(df, mask, '凭证借贷不平衡', {'差额': df.loc[mask, '差额'].tolist()})
        return df

class VoucherSequenceRule(BaseRule):
    def __init__(self):
        super().__init__('凭证断号', '中')
    
    def check(self, df: pd.DataFrame) -> pd.DataFrame:
        if '凭证号' not in df.columns:
            return df
        
        voucher_numbers = df['凭证号'].unique()
        broken_vouchers = []
        
        for i in range(1, len(voucher_numbers)):
            prev = voucher_numbers[i-1]
            curr = voucher_numbers[i]
            try:
                prev_num = int(re.search(r'\d+', str(prev)).group())
                curr_num = int(re.search(r'\d+', str(curr)).group())
                if curr_num - prev_num > 1:
                    broken_vouchers.append(curr)
            except (AttributeError, ValueError):
                continue
        
        if broken_vouchers:
            mask = df['凭证号'].isin(broken_vouchers)
            self.add_risk_mark(df, mask, '凭证号不连续', {'断号凭证': broken_vouchers})
        return df

class OneToManyVoucherRule(BaseRule):
    def __init__(self):
        super().__init__('一借多贷异常', '中')
    
    def check(self, df: pd.DataFrame) -> pd.DataFrame:
        if '凭证号' not in df.columns or 'direction' not in df.columns:
            return df
        
        for voucher in df['凭证号'].unique():
            voucher_df = df[df['凭证号'] == voucher]
            debit_count = (voucher_df['direction'] == '借').sum()
            credit_count = (voucher_df['direction'] == '贷').sum()
            
            if debit_count == 1 and credit_count > 3:
                credit_amounts = voucher_df[voucher_df['direction'] == '贷']['amount'].tolist()
                if len(set(credit_amounts)) == 1:
                    mask = df['凭证号'] == voucher
                    self.add_risk_mark(df, mask, '一借多贷且金额相等', {'贷方金额': credit_amounts})
        return df

class SummaryAccountMatchRule(BaseRule):
    def __init__(self):
        super().__init__('摘要-科目匹配', '中')
    
    def check(self, df: pd.DataFrame) -> pd.DataFrame:
        if '摘要' not in df.columns or '科目名称' not in df.columns:
            return df
        
        keyword_account_map = {
            '差旅': ['差旅费'],
            '出差': ['差旅费'],
            '办公': ['办公费'],
            '工资': ['工资', '薪酬'],
            '社保': ['社保'],
            '公积金': ['公积金'],
            '税费': ['税'],
            '利息': ['利息'],
            '手续费': ['手续费'],
            '工程': ['在建工程', '工程'],
            '设备': ['设备', '固定资产'],
            '采购': ['采购', '原材料', '库存商品'],
        }
        
        def check_match(row):
            summary = str(row['摘要'])
            account = str(row['科目名称'])
            
            for keyword, account_keywords in keyword_account_map.items():
                if keyword in summary:
                    if not any(acc_kw in account for acc_kw in account_keywords):
                        return True
            return False
        
        mask = df.apply(check_match, axis=1)
        self.add_risk_mark(df, mask, '摘要与科目不匹配')
        return df

class ProjectAccountRule(BaseRule):
    def __init__(self):
        super().__init__('在建工程科目关联', '中')
    
    def check(self, df: pd.DataFrame) -> pd.DataFrame:
        if '科目名称' not in df.columns:
            return df
        
        project_keywords = ['在建工程', '工程投资', '工程待摊']
        mask = df['科目名称'].apply(lambda x: any(kw in str(x) for kw in project_keywords))
        
        if '合同号' in df.columns:
            mask = mask & (df['合同号'] == '') & (df.get('项目', '') == '')
        elif '项目' in df.columns:
            mask = mask & (df['项目'] == '')
        
        self.add_risk_mark(df, mask, '在建工程科目缺少合同号或项目信息')
        return df

class TaxAccountRule(BaseRule):
    def __init__(self):
        super().__init__('税费科目逻辑', '高')
    
    def check(self, df: pd.DataFrame) -> pd.DataFrame:
        if '科目名称' not in df.columns:
            return df
        
        tax_keywords = ['应交税费', '增值税', '进项税', '销项税']
        mask = df['科目名称'].apply(lambda x: any(kw in str(x) for kw in tax_keywords))
        
        if '增值税税码税率' in df.columns:
            mask = mask & (df['增值税税码税率'] == '')
        
        self.add_risk_mark(df, mask, '税费科目缺少税率信息')
        return df

class BankAccountRule(BaseRule):
    def __init__(self):
        super().__init__('银行存款科目', '中')
    
    def check(self, df: pd.DataFrame) -> pd.DataFrame:
        if '科目名称' not in df.columns:
            return df
        
        mask = df['科目名称'].str.contains('银行存款', na=False)
        
        if '银行账户' in df.columns:
            mask = mask & (df['银行账户'] == '')
        
        self.add_risk_mark(df, mask, '银行存款科目缺少银行账户信息')
        return df

class LargeAmountRule(BaseRule):
    def __init__(self, threshold_multiplier: float = 3.0):
        super().__init__('大额交易', '中')
        self.threshold_multiplier = threshold_multiplier
    
    def check(self, df: pd.DataFrame) -> pd.DataFrame:
        if '科目末级' not in df.columns or 'amount' not in df.columns:
            return df
        
        for account in df['科目末级'].unique():
            account_mask = df['科目末级'] == account
            account_df = df[account_mask]
            
            if len(account_df) < 5:
                continue
            
            mean = account_df['amount'].mean()
            std = account_df['amount'].std()
            
            if std > 0:
                threshold = mean + self.threshold_multiplier * std
                large_mask = account_mask & (df['amount'] > threshold)
                self.add_risk_mark(df, large_mask, '金额超过均值+3σ', {
                    '均值': round(mean, 2),
                    '标准差': round(std, 2),
                    '阈值': round(threshold, 2)
                })
        return df

class IntegerAmountRule(BaseRule):
    def __init__(self):
        super().__init__('整数金额', '低')
    
    def check(self, df: pd.DataFrame) -> pd.DataFrame:
        if 'amount' not in df.columns:
            return df
        
        mask = (df['amount'] == df['amount'].astype(int)) & (df['amount'] >= 10000)
        self.add_risk_mark(df, mask, '金额为整数且大于等于1万')
        return df

class FrequentSmallAmountRule(BaseRule):
    def __init__(self, threshold: float = 100.0, min_count: int = 5):
        super().__init__('频繁小额', '低')
        self.threshold = threshold
        self.min_count = min_count
    
    def check(self, df: pd.DataFrame) -> pd.DataFrame:
        if '科目末级' not in df.columns or 'amount' not in df.columns:
            return df
        
        for account in df['科目末级'].unique():
            account_mask = df['科目末级'] == account
            small_mask = account_mask & (df['amount'] < self.threshold)
            
            if small_mask.sum() >= self.min_count:
                self.add_risk_mark(df, small_mask, '频繁出现小额交易', {
                    '次数': int(small_mask.sum())
                })
        return df

class SplitTransactionRule(BaseRule):
    def __init__(self):
        super().__init__('异常拆分', '高')
    
    def check(self, df: pd.DataFrame) -> pd.DataFrame:
        if '凭证号' not in df.columns or 'amount' not in df.columns:
            return df
        
        for voucher in df['凭证号'].unique():
            voucher_mask = df['凭证号'] == voucher
            voucher_df = df[voucher_mask]
            
            if len(voucher_df) < 3:
                continue
            
            amounts = voucher_df['amount'].tolist()
            if len(set(amounts)) == 1 and len(amounts) >= 3:
                self.add_risk_mark(df, voucher_mask, '同一凭证多笔相同金额', {
                    '金额': amounts[0],
                    '笔数': len(amounts)
                })
        return df

class MissingFieldRule(BaseRule):
    def __init__(self):
        super().__init__('关键字段缺失', '中')
    
    def check(self, df: pd.DataFrame) -> pd.DataFrame:
        if '科目名称' not in df.columns:
            return df
        
        field_requirements = {
            '银行存款': ['银行账户'],
            '在建工程': ['合同号', '项目'],
            '差旅费': ['部门', '人员'],
            '应付账款': ['客商'],
            '应收账款': ['客商'],
            '其他应收': ['客商', '人员'],
            '其他应付': ['客商', '人员'],
        }
        
        for account_keyword, required_fields in field_requirements.items():
            account_mask = df['科目名称'].str.contains(account_keyword, na=False)
            
            for field in required_fields:
                if field in df.columns:
                    missing_mask = account_mask & (df[field] == '')
                    self.add_risk_mark(df, missing_mask, f'{account_keyword}科目缺少{field}')
        
        return df

class ContractFormatRule(BaseRule):
    def __init__(self):
        super().__init__('合同号格式异常', '中')
        self.valid_patterns = [
            r'\d{2}-[A-Z]{2,3}\d{3}-\d+',
            r'[A-Z]{2,3}-\d{4}-\d+',
            r'\d{4}-\d{2}-\d+',
        ]
    
    def check(self, df: pd.DataFrame) -> pd.DataFrame:
        if '合同号' not in df.columns:
            return df
        
        def is_valid_contract(contract_no):
            if not contract_no or contract_no == '':
                return True
            for pattern in self.valid_patterns:
                if re.match(pattern, str(contract_no)):
                    return True
            return False
        
        mask = ~df['合同号'].apply(is_valid_contract)
        mask = mask & (df['合同号'] != '')
        self.add_risk_mark(df, mask, '合同号格式不符合规范')
        return df

class DuplicateTransactionRule(BaseRule):
    def __init__(self):
        super().__init__('完全重复', '高')
    
    def check(self, df: pd.DataFrame) -> pd.DataFrame:
        if 'amount' not in df.columns or '摘要' not in df.columns:
            return df
        
        duplicate_cols = ['amount', '摘要']
        for col in ['银行账户', '客商', '合同号']:
            if col in df.columns:
                duplicate_cols.append(col)
        
        duplicates = df.duplicated(subset=duplicate_cols, keep=False)
        self.add_risk_mark(df, duplicates, '存在完全重复的交易')
        return df

class HolidayTransactionRule(BaseRule):
    def __init__(self):
        super().__init__('节假日记账', '低')
    
    def check(self, df: pd.DataFrame) -> pd.DataFrame:
        if 'date' not in df.columns:
            return df
        
        df['weekday'] = df['date'].dt.weekday
        mask = df['weekday'].isin([5, 6])
        self.add_risk_mark(df, mask, '周六、周日有记账')
        return df

class MonthEndRule(BaseRule):
    def __init__(self):
        super().__init__('月末突击', '中')
    
    def check(self, df: pd.DataFrame) -> pd.DataFrame:
        if 'date' not in df.columns or 'amount' not in df.columns:
            return df
        
        df['day'] = df['date'].dt.day
        df['month'] = df['date'].dt.month
        
        last_days = df.groupby('month')['day'].max()
        
        for month, last_day in last_days.items():
            month_mask = df['month'] == month
            last_day_mask = month_mask & (df['day'] == last_day)
            
            if last_day_mask.sum() > 0:
                avg_amount = df[month_mask & ~last_day_mask]['amount'].mean()
                last_day_avg = df[last_day_mask]['amount'].mean()
                
                if last_day_avg > avg_amount * 2:
                    self.add_risk_mark(df, last_day_mask, '月末最后一天大额交易', {
                        '月末平均': round(last_day_avg, 2),
                        '月均': round(avg_amount, 2)
                    })
        return df

class YearEndAdjustRule(BaseRule):
    def __init__(self):
        super().__init__('跨年调整', '中')
    
    def check(self, df: pd.DataFrame) -> pd.DataFrame:
        if 'date' not in df.columns:
            return df
        
        mask = (df['date'].dt.month == 12) & (df['date'].dt.day == 31)
        
        if mask.sum() > 10:
            self.add_risk_mark(df, mask, '12月31日有大量调整分录', {
                '笔数': int(mask.sum())
            })
        return df

class RuleEngine:
    def __init__(self):
        self.rules: List[BaseRule] = []
        self._register_default_rules()
    
    def _register_default_rules(self):
        self.rules = [
            VoucherBalanceRule(),
            VoucherSequenceRule(),
            OneToManyVoucherRule(),
            SummaryAccountMatchRule(),
            ProjectAccountRule(),
            TaxAccountRule(),
            BankAccountRule(),
            LargeAmountRule(),
            IntegerAmountRule(),
            FrequentSmallAmountRule(),
            SplitTransactionRule(),
            MissingFieldRule(),
            ContractFormatRule(),
            DuplicateTransactionRule(),
            HolidayTransactionRule(),
            MonthEndRule(),
            YearEndAdjustRule(),
        ]
    
    def add_rule(self, rule: BaseRule):
        self.rules.append(rule)
    
    def enable_rule(self, rule_name: str, enabled: bool = True):
        for rule in self.rules:
            if rule.name == rule_name:
                rule.enabled = enabled
                break
    
    def run(self, df: pd.DataFrame, rule_config: Dict = None) -> pd.DataFrame:
        if '风险标记' not in df.columns:
            df['风险标记'] = [[] for _ in range(len(df))]
        
        if rule_config:
            for rule in self.rules:
                rule.enabled = rule_config.get(rule.name, {}).get('enabled', True)
        
        for rule in self.rules:
            if rule.enabled:
                try:
                    df = rule.check(df)
                except Exception as e:
                    print(f"规则 {rule.name} 执行失败: {str(e)}")
        
        return df

def run_rules(df: pd.DataFrame, rule_config: Dict = None) -> pd.DataFrame:
    engine = RuleEngine()
    return engine.run(df, rule_config)
