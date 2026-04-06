import { useState, useEffect } from 'react';
import { Card, Tag, List, Typography, Spin, Alert, Button, Empty, Space } from 'antd';
import { ReloadOutlined, RiseOutlined, FallOutlined } from '@ant-design/icons';
import { useOutletContext } from 'react-router-dom';
import { runMacroAgent } from '../services/api';
import type { FocusStock, AgentResult } from '../types';
import { COLORS } from '../theme';

const { Text, Title, Paragraph } = Typography;

export default function MacroPage() {
  const { focus } = useOutletContext<{ focus: FocusStock | null }>();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AgentResult | null>(null);
  const [error, setError] = useState('');

  const fetchData = async () => {
    if (!focus) return;
    setLoading(true);
    setError('');
    try {
      const data = await runMacroAgent(focus.stock_code, focus.stock_name);
      setResult(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '获取宏观分析失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [focus?.stock_code]);

  if (!focus) {
    return <Empty description="请先关注一支股票" />;
  }

  const d = result?.data || {};
  const marketPhase = (d.market_phase as string) || '震荡市';
  const marketSentiment = (d.market_sentiment as number) || 0;
  const riskLevel = (d.risk_level as string) || '中';
  const keyIndicators = (d.key_indicators as Record<string, unknown>[]) || [];
  const impactOnStock = (d.impact_on_stock as string) || '';
  const analysis = (d.analysis as string) || '';

  const riskColor =
    riskLevel === '高' ? COLORS.stockUp :
    riskLevel === '低' ? COLORS.stockDown :
    COLORS.warning;

  return (
    <Spin spinning={loading}>
      <Space direction="vertical" style={{ width: '100%' }} size={16}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={4} style={{ margin: 0 }}>宏观环境分析</Title>
          <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>
            刷新
          </Button>
        </div>

        {error && <Alert type="error" message={error} showIcon />}

        {result && (
          <>
            {result.status === 'degraded' && (
              <Alert type="warning" message="AI 分析不可用，展示原始宏观数据" showIcon />
            )}

            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
              <Card style={{ flex: 1, minWidth: 180 }}>
                <Text type="secondary">市场阶段</Text>
                <Title level={3} style={{ margin: '4px 0' }}>{marketPhase}</Title>
              </Card>
              <Card style={{ flex: 1, minWidth: 180 }}>
                <Text type="secondary">市场情绪</Text>
                <Title level={3} style={{
                  margin: '4px 0',
                  color: marketSentiment > 0 ? COLORS.stockUp : marketSentiment < 0 ? COLORS.stockDown : COLORS.stockFlat,
                }}>
                  {marketSentiment > 0 ? (
                    <><RiseOutlined /> 偏多</>
                  ) : marketSentiment < 0 ? (
                    <><FallOutlined /> 偏空</>
                  ) : '中性'}
                </Title>
              </Card>
              <Card style={{ flex: 1, minWidth: 180 }}>
                <Text type="secondary">风险等级</Text>
                <Title level={3} style={{ margin: '4px 0', color: riskColor }}>
                  {riskLevel}
                </Title>
              </Card>
            </div>

            {keyIndicators.length > 0 && (
              <Card title="关键指标">
                <List
                  dataSource={keyIndicators}
                  renderItem={(item) => (
                    <List.Item>
                      <List.Item.Meta
                        title={
                          <Space>
                            <Tag color="blue">{item.name as string}</Tag>
                            <Text strong>{item.value as string}</Text>
                          </Space>
                        }
                        description={item.interpretation as string}
                      />
                    </List.Item>
                  )}
                />
              </Card>
            )}

            {impactOnStock && (
              <Card title={`对 ${focus.stock_name} 的影响`}>
                <Paragraph>{impactOnStock}</Paragraph>
              </Card>
            )}

            {analysis && (
              <Card title="分析摘要">
                <Paragraph>{analysis}</Paragraph>
              </Card>
            )}
          </>
        )}
      </Space>
    </Spin>
  );
}
