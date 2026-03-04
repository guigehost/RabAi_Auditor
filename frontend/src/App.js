import React, { useState, useEffect } from 'react';
import { Layout, Menu, Upload, Button, Card, Table, Progress, Drawer, message, Tabs, Input, Tag, Space, Descriptions, Badge, Alert, Empty, Row, Col, Statistic, Spin, Switch, Collapse, Divider } from 'antd';
import { UploadOutlined, DashboardOutlined, SettingOutlined, FileTextOutlined, MessageOutlined, ReloadOutlined, SaveOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Header, Sider, Content } = Layout;
const { Dragger } = Upload;
const { TextArea } = Input;
const { Panel } = Collapse;

const API_BASE_URL = 'http://localhost:8002';

function App() {
  const [activeKey, setActiveKey] = useState('dashboard');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [llmHealth, setLlmHealth] = useState(null);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [selectedRecord, setSelectedRecord] = useState(null);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [rules, setRules] = useState({});
  const [rulesLoading, setRulesLoading] = useState(false);

  useEffect(() => {
    fetchRules();
    checkLLMHealth();
  }, []);

  const fetchRules = async () => {
    setRulesLoading(true);
    try {
      const response = await axios.get(`${API_BASE_URL}/api/rules`);
      setRules(response.data);
    } catch (error) {
      console.error('Failed to fetch rules:', error);
    } finally {
      setRulesLoading(false);
    }
  };

  const checkLLMHealth = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/llm/health`);
      setLlmHealth(response.data);
    } catch (error) {
      setLlmHealth({ status: 'unavailable' });
    }
  };

  const handleRuleChange = (category, ruleName, enabled) => {
    setRules(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [ruleName]: {
          ...prev[category][ruleName],
          enabled
        }
      }
    }));
  };

  const saveRules = async () => {
    try {
      await axios.post(`${API_BASE_URL}/api/rules`, rules);
      message.success('规则配置已保存');
    } catch (error) {
      message.error('保存失败');
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
      
      if (response.data.status === 'SUCCESS') {
        setResults(response.data.result);
        message.success('审计任务完成！');
        setActiveKey('results');
      } else {
        message.error('审计任务失败: ' + (response.data.error || '未知错误'));
      }
    } catch (error) {
      message.error('文件上传失败: ' + error.message);
      console.error('上传失败:', error);
    } finally {
      setLoading(false);
    }
    return false;
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
        content: response.data.result?.response || response.data.error || '无法获取回答'
      };
      setChatMessages(prev => [...prev, llmResponse]);
    } catch (error) {
      const errorMessage = {
        role: 'assistant',
        content: '抱歉，LLM服务暂时不可用，请稍后再试。'
      };
      setChatMessages(prev => [...prev, errorMessage]);
    }
  };

  const getRiskTag = (riskLevel) => {
    const colors = { '高': 'red', '中': 'orange', '低': 'green' };
    return <Tag color={colors[riskLevel] || 'default'}>{riskLevel}风险</Tag>;
  };

  const viewDetail = (record) => {
    setSelectedRecord(record);
    setDrawerVisible(true);
  };

  const menuItems = [
    { key: 'dashboard', icon: <DashboardOutlined />, label: '仪表盘' },
    { key: 'upload', icon: <UploadOutlined />, label: '数据上传' },
    { key: 'rules', icon: <SettingOutlined />, label: '规则配置' },
    { key: 'results', icon: <FileTextOutlined />, label: '结果查看' },
    { key: 'llm', icon: <MessageOutlined />, label: '智能助手' },
  ];

  const renderContent = () => {
    switch (activeKey) {
      case 'dashboard':
        return (
          <div style={{ padding: 24 }}>
            <Row gutter={[16, 16]}>
              <Col span={6}>
                <Card>
                  <Statistic title="总记录数" value={results?.total_records || 0} />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic title="高风险" value={results?.high_risk_count || 0} valueStyle={{ color: '#cf1322' }} />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic title="中风险" value={results?.medium_risk_count || 0} valueStyle={{ color: '#fa8c16' }} />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic title="低风险" value={results?.low_risk_count || 0} valueStyle={{ color: '#52c41a' }} />
                </Card>
              </Col>
            </Row>

            {results?.rule_stats && Object.keys(results.rule_stats).length > 0 && (
              <Card title="规则触发统计" style={{ marginTop: 24 }}>
                <Row gutter={[16, 16]}>
                  {Object.entries(results.rule_stats).map(([name, stat]) => (
                    <Col span={6} key={name}>
                      <Card size="small">
                        <Statistic 
                          title={<span>{getRiskTag(stat.risk)} {name}</span>} 
                          value={stat.count} 
                        />
                      </Card>
                    </Col>
                  ))}
                </Row>
              </Card>
            )}

            {!results && (
              <Card style={{ marginTop: 24, textAlign: 'center' }}>
                <Empty description="暂无审计数据，请上传数据文件开始审计" />
                <Button type="primary" style={{ marginTop: 16 }} onClick={() => setActiveKey('upload')}>
                  上传数据
                </Button>
              </Card>
            )}
          </div>
        );

      case 'upload':
        return (
          <div style={{ padding: 24 }}>
            <Card title="上传审计数据">
              <Spin spinning={loading} tip="正在处理数据...">
                <Dragger
                  name="file"
                  multiple={false}
                  beforeUpload={handleUpload}
                  accept=".xlsx,.xls,.csv"
                  showUploadList={false}
                >
                  <p style={{ fontSize: 48, color: '#1890ff', marginBottom: 16 }}>
                    <UploadOutlined />
                  </p>
                  <p style={{ fontSize: 16 }}>点击或拖拽文件到此区域上传</p>
                  <p style={{ color: '#999' }}>支持 Excel (.xlsx, .xls) 和 CSV (.csv) 文件</p>
                </Dragger>
              </Spin>
              
              <Alert
                message="数据格式要求"
                description={
                  <div>
                    <p><strong>必需字段：</strong>年、月、日、凭证号、摘要、科目编码、科目名称、借方本币、贷方本币</p>
                    <p><strong>可选字段：</strong>核算账簿名称、分录号、辅助项、币种</p>
                    <p><strong>辅助项格式：</strong>【键：值】，多个用空格分隔，如：【部门：行政部】【人员：张三】</p>
                  </div>
                }
                type="info"
                style={{ marginTop: 16 }}
              />
            </Card>
          </div>
        );

      case 'rules':
        return (
          <div style={{ padding: 24 }}>
            <Card 
              title="审计规则配置" 
              extra={
                <Space>
                  <Button icon={<ReloadOutlined />} onClick={fetchRules}>重置</Button>
                  <Button type="primary" icon={<SaveOutlined />} onClick={saveRules}>保存配置</Button>
                </Space>
              }
            >
              <Spin spinning={rulesLoading}>
                <Collapse defaultActiveKey={Object.keys(rules)} bordered={false}>
                  {Object.entries(rules).map(([category, categoryRules]) => (
                    <Panel 
                      header={
                        <span>
                          <strong>{category}</strong>
                          <Tag style={{ marginLeft: 8 }} color="blue">
                            {Object.values(categoryRules).filter(r => r.enabled).length}/{Object.keys(categoryRules).length} 已启用
                          </Tag>
                        </span>
                      } 
                      key={category}
                    >
                      <Row gutter={[16, 16]}>
                        {Object.entries(categoryRules).map(([ruleName, ruleConfig]) => (
                          <Col span={12} key={ruleName}>
                            <Card 
                              size="small" 
                              hoverable
                              extra={
                                <Switch 
                                  checked={ruleConfig.enabled} 
                                  onChange={(checked) => handleRuleChange(category, ruleName, checked)}
                                  checkedChildren="启用" 
                                  unCheckedChildren="禁用"
                                />
                              }
                            >
                              <Card.Meta 
                                title={
                                  <Space>
                                    {getRiskTag(ruleConfig.risk)}
                                    <span>{ruleName}</span>
                                  </Space>
                                }
                                description={ruleConfig.description}
                              />
                              {ruleConfig.threshold && (
                                <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
                                  阈值: {ruleConfig.threshold}σ
                                </div>
                              )}
                              {ruleConfig.min_amount && (
                                <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
                                  最小金额: {ruleConfig.min_amount.toLocaleString()}
                                </div>
                              )}
                              {ruleConfig.count_threshold && (
                                <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
                                  次数阈值: {ruleConfig.count_threshold}
                                </div>
                              )}
                            </Card>
                          </Col>
                        ))}
                      </Row>
                    </Panel>
                  ))}
                </Collapse>
              </Spin>
            </Card>
          </div>
        );

      case 'results':
        return (
          <div style={{ padding: 24 }}>
            <Card title="审计结果">
              {results ? (
                <>
                  <Descriptions bordered column={2} style={{ marginBottom: 24 }}>
                    <Descriptions.Item label="总记录数">{results.total_records}</Descriptions.Item>
                    <Descriptions.Item label="高风险">
                      <Badge count={results.high_risk_count} style={{ backgroundColor: '#cf1322' }} />
                    </Descriptions.Item>
                    <Descriptions.Item label="中风险">
                      <Badge count={results.medium_risk_count} style={{ backgroundColor: '#fa8c16' }} />
                    </Descriptions.Item>
                    <Descriptions.Item label="低风险">
                      <Badge count={results.low_risk_count} style={{ backgroundColor: '#52c41a' }} />
                    </Descriptions.Item>
                  </Descriptions>

                  <Table
                    columns={[
                      { title: '凭证号', dataIndex: '凭证号', key: '凭证号', width: 100 },
                      { title: '日期', dataIndex: 'date', key: 'date', width: 120 },
                      { title: '摘要', dataIndex: '摘要', key: '摘要', ellipsis: true },
                      { title: '科目名称', dataIndex: '科目名称', key: '科目名称', ellipsis: true, width: 200 },
                      { title: '金额', dataIndex: 'amount', key: 'amount', width: 120, render: v => v?.toLocaleString?.() || v },
                      { 
                        title: '风险等级', 
                        key: '风险等级',
                        width: 100,
                        render: (_, record) => {
                          const marks = record['风险标记'] || [];
                          if (marks.some(m => m['风险等级'] === '高')) return getRiskTag('高');
                          if (marks.some(m => m['风险等级'] === '中')) return getRiskTag('中');
                          if (marks.some(m => m['风险等级'] === '低')) return getRiskTag('低');
                          return <Tag>无</Tag>;
                        }
                      },
                      { 
                        title: '操作', 
                        key: 'action',
                        width: 80,
                        render: (_, record) => (
                          <Button size="small" type="link" onClick={() => viewDetail(record)}>详情</Button>
                        ) 
                      }
                    ]}
                    dataSource={results.anomaly_records || []}
                    pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
                    scroll={{ x: 1000 }}
                    rowKey={(r, i) => i}
                    size="small"
                  />
                </>
              ) : (
                <Empty description="暂无审计结果，请先上传数据" />
              )}
            </Card>
          </div>
        );

      case 'llm':
        return (
          <div style={{ padding: 24 }}>
            <Card 
              title={
                <Space>
                  智能审计助手
                  {llmHealth && (
                    <Tag color={llmHealth.status === 'healthy' ? 'green' : 'red'}>
                      {llmHealth.status === 'healthy' ? '服务正常' : '服务不可用'}
                    </Tag>
                  )}
                </Space>
              }
              extra={<Button icon={<ReloadOutlined />} onClick={checkLLMHealth}>刷新</Button>}
            >
              <div style={{ height: 400, overflowY: 'auto', border: '1px solid #f0f0f0', borderRadius: 4, padding: 16, marginBottom: 16 }}>
                {chatMessages.length === 0 ? (
                  <Empty description="开始对话，询问审计相关问题" />
                ) : (
                  chatMessages.map((msg, i) => (
                    <div key={i} style={{ marginBottom: 16 }}>
                      <div style={{ fontWeight: 'bold', marginBottom: 4, color: msg.role === 'user' ? '#1890ff' : '#52c41a' }}>
                        {msg.role === 'user' ? '👤 您' : '🤖 助手'}
                      </div>
                      <div style={{ padding: 12, backgroundColor: msg.role === 'user' ? '#e6f7ff' : '#f6ffed', borderRadius: 8, whiteSpace: 'pre-wrap' }}>
                        {msg.content}
                      </div>
                    </div>
                  ))
                )}
              </div>
              <Space.Compact style={{ width: '100%' }}>
                <TextArea
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="输入审计相关问题，如：这笔大额交易是否合理？"
                  autoSize={{ minRows: 1, maxRows: 3 }}
                  onPressEnter={(e) => {
                    if (!e.shiftKey) {
                      e.preventDefault();
                      handleChatSubmit();
                    }
                  }}
                  style={{ flex: 1 }}
                />
                <Button type="primary" onClick={handleChatSubmit}>发送</Button>
              </Space.Compact>
            </Card>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ background: '#001529', padding: '0 24px', display: 'flex', alignItems: 'center' }}>
        <h1 style={{ color: '#fff', margin: 0, fontSize: 20 }}>智能审计工具</h1>
        <div style={{ flex: 1 }} />
        <Tag color="blue">v1.0.0</Tag>
      </Header>
      <Layout>
        <Sider width={200} style={{ background: '#fff' }}>
          <Menu
            mode="inline"
            selectedKeys={[activeKey]}
            onClick={(e) => setActiveKey(e.key)}
            items={menuItems}
            style={{ height: '100%', borderRight: 0 }}
          />
        </Sider>
        <Content style={{ background: '#f0f2f5', minHeight: 'calc(100vh - 64px)' }}>
          {renderContent()}
        </Content>
      </Layout>

      <Drawer
        title="异常详情"
        placement="right"
        onClose={() => setDrawerVisible(false)}
        open={drawerVisible}
        width={500}
      >
        {selectedRecord && (
          <Descriptions bordered column={1}>
            <Descriptions.Item label="凭证号">{selectedRecord['凭证号']}</Descriptions.Item>
            <Descriptions.Item label="日期">{selectedRecord['date']}</Descriptions.Item>
            <Descriptions.Item label="摘要">{selectedRecord['摘要']}</Descriptions.Item>
            <Descriptions.Item label="科目名称">{selectedRecord['科目名称']}</Descriptions.Item>
            <Descriptions.Item label="金额">{selectedRecord['amount']?.toLocaleString?.()}</Descriptions.Item>
            <Descriptions.Item label="借方金额">{selectedRecord['借方本币']?.toLocaleString?.()}</Descriptions.Item>
            <Descriptions.Item label="贷方金额">{selectedRecord['贷方本币']?.toLocaleString?.()}</Descriptions.Item>
            <Descriptions.Item label="风险标记">
              <Space direction="vertical" style={{ width: '100%' }}>
                {(selectedRecord['风险标记'] || []).map((m, i) => (
                  <div key={i} style={{ padding: 8, backgroundColor: '#f5f5f5', borderRadius: 4 }}>
                    <div>
                      {getRiskTag(m['风险等级'])} 
                      <strong style={{ marginLeft: 8 }}>{m['规则名称']}</strong>
                    </div>
                    {m['描述'] && <div style={{ marginTop: 4, color: '#666', fontSize: 12 }}>{m['描述']}</div>}
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
