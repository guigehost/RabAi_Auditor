import React, { useState, useEffect } from 'react';
import { Layout, Menu, Upload, Button, Form, Checkbox, InputNumber, Card, Table, Progress, Drawer, Modal, message, Tabs, Input, Select, Tag, Space, Descriptions, Badge, Tooltip, Alert, Spin, Empty, Row, Col, Statistic } from 'antd';
import { UploadOutlined, DashboardOutlined, SettingOutlined, FileTextOutlined, MessageOutlined, LoadingOutlined, CheckCircleOutlined, WarningOutlined, InfoCircleOutlined, ReloadOutlined, DownloadOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Header, Sider, Content } = Layout;
const { Dragger } = Upload;
const { TabPane } = Tabs;
const { TextArea } = Input;
const { Option } = Select;

const API_BASE_URL = 'http://localhost:8000';

function App() {
  const [activeKey, setActiveKey] = useState('dashboard');
  const [fileList, setFileList] = useState([]);
  const [rules, setRules] = useState({
    '借贷不平': { enabled: true },
    '凭证断号': { enabled: true },
    '一借多贷异常': { enabled: true },
    '摘要-科目匹配': { enabled: true },
    '在建工程科目关联': { enabled: true },
    '税费科目逻辑': { enabled: true },
    '银行存款科目': { enabled: true },
    '大额交易': { enabled: true },
    '整数金额': { enabled: true },
    '频繁小额': { enabled: true },
    '异常拆分': { enabled: true },
    '关键字段缺失': { enabled: true },
    '合同号格式异常': { enabled: true },
    '完全重复': { enabled: true },
    '节假日记账': { enabled: true },
    '月末突击': { enabled: true },
    '跨年调整': { enabled: true }
  });
  const [taskId, setTaskId] = useState(null);
  const [taskStatus, setTaskStatus] = useState('');
  const [taskProgress, setTaskProgress] = useState(0);
  const [results, setResults] = useState(null);
  const [anomalyData, setAnomalyData] = useState([]);
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [llmHealth, setLlmHealth] = useState(null);
  const [statistics, setStatistics] = useState({
    totalRecords: 0,
    highRisk: 0,
    mediumRisk: 0,
    lowRisk: 0
  });

  useEffect(() => {
    checkLLMHealth();
  }, []);

  useEffect(() => {
    let interval;
    if (taskId) {
      interval = setInterval(async () => {
        try {
          const response = await axios.get(`${API_BASE_URL}/api/task/${taskId}`);
          setTaskStatus(response.data.status);
          setTaskProgress(response.data.progress);
          if (response.data.status === 'SUCCESS') {
            setResults(response.data.result);
            clearInterval(interval);
            message.success('审计任务完成！');
          } else if (response.data.status === 'FAILURE') {
            clearInterval(interval);
            message.error('审计任务失败');
          }
        } catch (error) {
          console.error('检查任务状态失败:', error);
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [taskId]);

  const checkLLMHealth = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/llm/health`);
      setLlmHealth(response.data);
    } catch (error) {
      setLlmHealth({ status: 'unavailable' });
    }
  };

  const handleUpload = async (file) => {
    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('rules', JSON.stringify(rules));

    try {
      const response = await axios.post(`${API_BASE_URL}/api/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setTaskId(response.data.task_id);
      message.success('文件上传成功，任务已开始');
      setActiveKey('dashboard');
    } catch (error) {
      message.error('文件上传失败');
      console.error('上传失败:', error);
    } finally {
      setLoading(false);
    }
    return false;
  };

  const handleRuleChange = (ruleName, enabled) => {
    setRules(prev => ({
      ...prev,
      [ruleName]: { ...prev[ruleName], enabled }
    }));
  };

  const handleChatSubmit = async () => {
    if (!chatInput.trim()) return;

    const newMessage = { role: 'user', content: chatInput };
    setChatMessages(prev => [...prev, newMessage]);
    setChatInput('');

    try {
      const response = await axios.post(`${API_BASE_URL}/api/llm/analyze`, {
        prompt: chatInput
      });
      const llmResponse = {
        role: 'assistant',
        content: response.data.result?.response || response.data.result?.answer || '无法获取回答'
      };
      setChatMessages(prev => [...prev, llmResponse]);
    } catch (error) {
      console.error('LLM调用失败:', error);
      const errorMessage = {
        role: 'assistant',
        content: '抱歉，LLM服务暂时不可用，请稍后再试。'
      };
      setChatMessages(prev => [...prev, errorMessage]);
    }
  };

  const viewDetail = (record) => {
    setSelectedRecord(record);
    setDrawerVisible(true);
  };

  const getRiskTag = (riskLevel) => {
    const colors = { '高': 'red', '中': 'orange', '低': 'green' };
    return <Tag color={colors[riskLevel] || 'default'}>{riskLevel}</Tag>;
  };

  const renderDashboard = () => (
    <div style={{ padding: '20px' }}>
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card>
            <Statistic title="总记录数" value={statistics.totalRecords} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic 
              title="高风险" 
              value={statistics.highRisk} 
              valueStyle={{ color: '#cf1322' }}
              prefix={<WarningOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic 
              title="中风险" 
              value={statistics.mediumRisk} 
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic 
              title="低风险" 
              value={statistics.lowRisk} 
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {taskId && (
        <Card title="任务进度" style={{ marginTop: '20px' }}>
          <Progress 
            percent={taskProgress} 
            status={taskStatus === 'SUCCESS' ? 'success' : taskStatus === 'FAILURE' ? 'exception' : 'active'} 
          />
          <p style={{ marginTop: '10px', textAlign: 'center' }}>
            {taskStatus === 'PENDING' && '任务等待中...'}
            {taskStatus === 'PROGRESS' && `处理中... ${taskProgress}%`}
            {taskStatus === 'SUCCESS' && '任务完成！'}
            {taskStatus === 'FAILURE' && '任务失败'}
          </p>
        </Card>
      )}

      {results && (
        <Card title="审计结果概览" style={{ marginTop: '20px' }}>
          <Descriptions bordered column={2}>
            <Descriptions.Item label="总记录数">{results.total_records}</Descriptions.Item>
            <Descriptions.Item label="高风险数量">
              <Badge count={results.high_risk_count} style={{ backgroundColor: '#cf1322' }} />
            </Descriptions.Item>
            <Descriptions.Item label="中风险数量">
              <Badge count={results.medium_risk_count} style={{ backgroundColor: '#fa8c16' }} />
            </Descriptions.Item>
            <Descriptions.Item label="低风险数量">
              <Badge count={results.low_risk_count} style={{ backgroundColor: '#52c41a' }} />
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      {!taskId && !results && (
        <Card style={{ marginTop: '20px', textAlign: 'center' }}>
          <Empty description="暂无审计数据，请上传数据文件开始审计" />
        </Card>
      )}
    </div>
  );

  const renderUpload = () => (
    <div style={{ padding: '20px' }}>
      <Card title="上传审计数据">
        <Dragger
          name="file"
          multiple={false}
          beforeUpload={handleUpload}
          fileList={fileList}
          onChange={info => setFileList(info.fileList)}
          accept=".xlsx,.xls,.csv"
        >
          <p className="ant-upload-drag-icon">
            <UploadOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
          <p className="ant-upload-hint">
            支持 Excel (.xlsx, .xls) 和 CSV (.csv) 文件，数据量建议不超过10万行
          </p>
        </Dragger>
        
        <Alert
          message="数据格式要求"
          description={
            <ul style={{ marginBottom: 0 }}>
              <li>必需字段：年、月、日、凭证号、摘要、科目编码、科目名称、借方本币、贷方本币</li>
              <li>可选字段：核算账簿名称、分录号、辅助项、币种</li>
              <li>辅助项格式：【键：值】，多个键值对用空格分隔</li>
            </ul>
          }
          type="info"
          style={{ marginTop: '16px' }}
        />
      </Card>
    </div>
  );

  const renderRules = () => (
    <div style={{ padding: '20px' }}>
      <Card title="规则配置">
        <Tabs defaultActiveKey="1">
          <TabPane tab="凭证级规则" key="1">
            <Form layout="vertical">
              {['借贷不平', '凭证断号', '一借多贷异常'].map(rule => (
                <Form.Item key={rule} label={rule}>
                  <Checkbox
                    checked={rules[rule]?.enabled}
                    onChange={(e) => handleRuleChange(rule, e.target.checked)}
                  >
                    启用此规则
                  </Checkbox>
                </Form.Item>
              ))}
            </Form>
          </TabPane>
          <TabPane tab="科目合规性规则" key="2">
            <Form layout="vertical">
              {['摘要-科目匹配', '在建工程科目关联', '税费科目逻辑', '银行存款科目'].map(rule => (
                <Form.Item key={rule} label={rule}>
                  <Checkbox
                    checked={rules[rule]?.enabled}
                    onChange={(e) => handleRuleChange(rule, e.target.checked)}
                  >
                    启用此规则
                  </Checkbox>
                </Form.Item>
              ))}
            </Form>
          </TabPane>
          <TabPane tab="金额合理性规则" key="3">
            <Form layout="vertical">
              {['大额交易', '整数金额', '频繁小额', '异常拆分'].map(rule => (
                <Form.Item key={rule} label={rule}>
                  <Checkbox
                    checked={rules[rule]?.enabled}
                    onChange={(e) => handleRuleChange(rule, e.target.checked)}
                  >
                    启用此规则
                  </Checkbox>
                </Form.Item>
              ))}
            </Form>
          </TabPane>
          <TabPane tab="其他规则" key="4">
            <Form layout="vertical">
              {['关键字段缺失', '合同号格式异常', '完全重复', '节假日记账', '月末突击', '跨年调整'].map(rule => (
                <Form.Item key={rule} label={rule}>
                  <Checkbox
                    checked={rules[rule]?.enabled}
                    onChange={(e) => handleRuleChange(rule, e.target.checked)}
                  >
                    启用此规则
                  </Checkbox>
                </Form.Item>
              ))}
            </Form>
          </TabPane>
        </Tabs>
        
        <Button type="primary" onClick={() => message.success('规则配置已保存')} style={{ marginTop: '16px' }}>
          保存配置
        </Button>
      </Card>
    </div>
  );

  const renderResults = () => (
    <div style={{ padding: '20px' }}>
      <Card title="审计结果">
        {results ? (
          <Table
            columns={[
              { title: '凭证号', dataIndex: '凭证号', key: '凭证号', width: 100 },
              { title: '日期', dataIndex: 'date', key: 'date', width: 120 },
              { title: '摘要', dataIndex: '摘要', key: '摘要', ellipsis: true },
              { title: '科目名称', dataIndex: '科目名称', key: '科目名称', ellipsis: true },
              { title: '金额', dataIndex: 'amount', key: 'amount', width: 120, render: (v) => v?.toLocaleString() },
              { 
                title: '风险等级', 
                key: '风险等级',
                width: 100,
                render: (_, record) => {
                  const marks = record.风险标记 || [];
                  if (marks.some(m => m.风险等级 === '高')) return getRiskTag('高');
                  if (marks.some(m => m.风险等级 === '中')) return getRiskTag('中');
                  if (marks.some(m => m.风险等级 === '低')) return getRiskTag('低');
                  return <Tag>无</Tag>;
                }
              },
              { 
                title: '规则名称', 
                key: '规则名称',
                ellipsis: true,
                render: (_, record) => (
                  <Space size="small" wrap>
                    {(record.风险标记 || []).map((m, i) => (
                      <Tag key={i}>{m.规则名称}</Tag>
                    ))}
                  </Space>
                )
              },
              { 
                title: '操作', 
                key: 'action',
                width: 80,
                render: (_, record) => (
                  <Button size="small" onClick={() => viewDetail(record)}>
                    详情
                  </Button>
                ) 
              }
            ]}
            dataSource={anomalyData}
            pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
            scroll={{ x: 1200 }}
          />
        ) : (
          <Empty description="暂无审计结果，请先上传数据" />
        )}
      </Card>
    </div>
  );

  const renderLLMAssistant = () => (
    <div style={{ padding: '20px' }}>
      <Card 
        title={
          <Space>
            智能审计助手
            {llmHealth && (
              <Tag color={llmHealth.status === 'healthy' ? 'green' : 'red'}>
                {llmHealth.status === 'healthy' ? 'LLM服务正常' : 'LLM服务不可用'}
              </Tag>
            )}
          </Space>
        }
        extra={
          <Button icon={<ReloadOutlined />} onClick={checkLLMHealth}>
            检查服务
          </Button>
        }
      >
        <div style={{ height: '500px', border: '1px solid #f0f0f0', borderRadius: '4px', padding: '10px', overflowY: 'auto', marginBottom: '10px' }}>
          {chatMessages.length === 0 ? (
            <Empty description="开始对话，询问审计相关问题" style={{ marginTop: '150px' }} />
          ) : (
            chatMessages.map((msg, index) => (
              <div key={index} style={{ marginBottom: '16px' }}>
                <div style={{ fontWeight: 'bold', marginBottom: '5px', color: msg.role === 'user' ? '#1890ff' : '#52c41a' }}>
                  {msg.role === 'user' ? '👤 您' : '🤖 助手'}
                </div>
                <div style={{ 
                  padding: '12px', 
                  backgroundColor: msg.role === 'user' ? '#e6f7ff' : '#f6ffed', 
                  borderRadius: '8px',
                  whiteSpace: 'pre-wrap'
                }}>
                  {msg.content}
                </div>
              </div>
            ))
          )}
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <TextArea
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            placeholder="请输入您的问题，例如：'在建工程转固定资产的条件是什么？'"
            style={{ flex: 1 }}
            autoSize={{ minRows: 2, maxRows: 4 }}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault();
                handleChatSubmit();
              }
            }}
          />
          <Button type="primary" onClick={handleChatSubmit} loading={loading}>
            发送
          </Button>
        </div>
        
        <Alert
          message="提示：按 Enter 发送，Shift + Enter 换行"
          type="info"
          style={{ marginTop: '10px' }}
          showIcon
        />
      </Card>
    </div>
  );

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#001529', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h1 style={{ margin: 0, fontSize: '20px' }}>智能审计工具</h1>
        <Space>
          <Tag color="blue">v1.0.0</Tag>
          {llmHealth && (
            <Tooltip title={llmHealth.message || 'LLM服务状态'}>
              <Badge status={llmHealth.status === 'healthy' ? 'success' : 'error'} />
            </Tooltip>
          )}
        </Space>
      </Header>
      <Layout>
        <Sider width={200} style={{ background: '#fff' }}>
          <Menu
            mode="inline"
            selectedKeys={[activeKey]}
            onClick={(e) => setActiveKey(e.key)}
            style={{ height: '100%' }}
          >
            <Menu.Item key="dashboard" icon={<DashboardOutlined />}>
              仪表盘
            </Menu.Item>
            <Menu.Item key="upload" icon={<UploadOutlined />}>
              数据上传
            </Menu.Item>
            <Menu.Item key="rules" icon={<SettingOutlined />}>
              规则配置
            </Menu.Item>
            <Menu.Item key="results" icon={<FileTextOutlined />}>
              结果查看
            </Menu.Item>
            <Menu.Item key="llm" icon={<MessageOutlined />}>
              智能助手
            </Menu.Item>
          </Menu>
        </Sider>
        <Content style={{ background: '#f0f2f5' }}>
          {activeKey === 'dashboard' && renderDashboard()}
          {activeKey === 'upload' && renderUpload()}
          {activeKey === 'rules' && renderRules()}
          {activeKey === 'results' && renderResults()}
          {activeKey === 'llm' && renderLLMAssistant()}
        </Content>
      </Layout>

      <Drawer
        title="异常详情"
        placement="right"
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
        width={600}
      >
        {selectedRecord && (
          <Descriptions bordered column={1}>
            <Descriptions.Item label="凭证号">{selectedRecord.凭证号}</Descriptions.Item>
            <Descriptions.Item label="日期">{selectedRecord.date}</Descriptions.Item>
            <Descriptions.Item label="摘要">{selectedRecord.摘要}</Descriptions.Item>
            <Descriptions.Item label="科目名称">{selectedRecord.科目名称}</Descriptions.Item>
            <Descriptions.Item label="金额">{selectedRecord.amount?.toLocaleString()}</Descriptions.Item>
            <Descriptions.Item label="风险标记">
              <Space direction="vertical" style={{ width: '100%' }}>
                {(selectedRecord.风险标记 || []).map((m, i) => (
                  <div key={i}>
                    {getRiskTag(m.风险等级)} {m.规则名称}
                    {m.描述 && <span style={{ marginLeft: '8px', color: '#666' }}>- {m.描述}</span>}
                  </div>
                ))}
              </Space>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </Layout>
  );
}

export default App;