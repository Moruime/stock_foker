import { useState, useEffect, useCallback } from 'react';
import { Card, Tag, List, Typography, Spin, Alert, Button, Empty, Space, Tooltip, Row, Col } from 'antd';
import { ReloadOutlined, RiseOutlined, FallOutlined, ClockCircleOutlined, SyncOutlined } from '@ant-design/icons';
import { useOutletContext } from 'react-router-dom';
import { runMacroAgent, clearAgentCache } from '../services/api';
import type { FocusStock, AgentResult } from '../types';
import { COLORS } from '../theme';
import { useAgentCache } from '../contexts/AgentCacheContext';
import { useDataSource, invalidateDataSourceCache } from '../hooks/useDataSource';
import SnapshotPanel from '../components/SnapshotPanel';

const { Text, Title, Paragraph } = Typography;

function formatCacheTime(isoStr: string): string {
  const d = new Date(isoStr);
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}

export default function MacroPage() {
  const { focus } = useOutletContext<{ focus: FocusStock | null }>();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AgentResult | null>(null);
  const [error, setError] = useState('');
  const [fromCache, setFromCache] = useState(false);

  const { getAgentCache, setAgentCache, invalidateStock } = useAgentCache();

  // 独立数据源
  const hithinkIndex = useDataSource(focus?.stock_code, focus?.stock_name, 'hithink_index');

  const fetchData = useCallback(async (forceRefresh = false) => {
    if (!focus) return;

    if (!forceRefresh) {
      const cached = getAgentCache(focus.stock_code, 'macro');
      if (cached) {
        setResult(cached);
        setFromCache(true);
        return;
      }
    }

    setLoading(true);
    setError('');
    setFromCache(false);
    try {
      const data = await runMacroAgent(focus.stock_code, focus.stock_name);
      setResult(data);
      setAgentCache(focus.stock_code, 'macro', data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '获取宏观分析失败');
    } finally {
      setLoading(false);
    }
  }, [focus, getAgentCache, setAgentCache]);

  const handleRefresh = useCallback(async () => {
    if (!focus) return;
    try { await clearAgentCache(focus.stock_code); } catch { /* ignore */ }
    invalidateStock(focus.stock_code);
    invalidateDataSourceCache(focus.stock_code);
    fetchData(true);
    hithinkIndex.refresh();
  }, [focus, invalidateStock, fetchData, hithinkIndex]);

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

  // 同花顺指数原始数据（独立数据源）
  const indexRows = ((hithinkIndex.data?.datas as Record<string, unknown>[]) || []);
  const findIndexVal = (row: Record<string, unknown>, keyword: string): number | null => {
    const key = Object.keys(row).find((k) => k.includes(keyword));
    return key !== undefined ? (row[key] as number) ?? null : null;
  };

  const riskColor =
    riskLevel === '高' ? COLORS.stockUp :
    riskLevel === '低' ? COLORS.stockDown :
    COLORS.warning;

  return (
    <Spin spinning={loading}>
      <Space direction="vertical" style={{ width: '100%' }} size={16}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={4} style={{ margin: 0 }}>宏观环境分析</Title>
          <Space>
            {fromCache && result?.timestamp && (
              <Tooltip title={`数据缓存于 ${formatCacheTime(result.timestamp)}`}>
                <Text type="secondary" style={{ fontSize: 12, cursor: 'default' }}>
                  <ClockCircleOutlined style={{ marginRight: 4 }} />
                  缓存于 {formatCacheTime(result.timestamp)}
                </Text>
              </Tooltip>
            )}
            <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={loading}>
              刷新
            </Button>
          </Space>
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

            {/* 主要指数行情（独立数据源） */}
            <Card
              title={
                <Space>
                  <span>主要指数行情</span>
                  {hithinkIndex.loading && <SyncOutlined spin style={{ fontSize: 12 }} />}
                  {hithinkIndex.timestamp && (
                    <Text type="secondary" style={{ fontSize: 11, fontWeight: 'normal' }}>
                      <ClockCircleOutlined style={{ marginRight: 2 }} />
                      {formatCacheTime(hithinkIndex.timestamp)}
                    </Text>
                  )}
                </Space>
              }
              size="small"
              extra={
                <Tooltip title="刷新指数行情">
                  <ReloadOutlined
                    style={{ fontSize: 12, cursor: 'pointer' }}
                    onClick={() => hithinkIndex.refresh()}
                  />
                </Tooltip>
              }
            >
              {hithinkIndex.loading ? (
                <Spin size="small" style={{ display: 'block', margin: '16px auto' }} />
              ) : indexRows.length > 0 ? (
                <Row gutter={[16, 12]}>
                  {indexRows.map((row, i) => {
                    const name = (row['指数简称'] as string) || `指数${i + 1}`;
                    const price = findIndexVal(row, '收盘价') ?? findIndexVal(row, '最新价') ?? (row['最新价'] as number);
                    const changePct = findIndexVal(row, '涨跌幅');
                    const amount = findIndexVal(row, '成交额');
                    return (
                      <Col span={8} key={i}>
                        <Card size="small" style={{ textAlign: 'center' }}>
                          <Text type="secondary" style={{ fontSize: 12 }}>{name}</Text>
                          {price !== null && (
                            <div>
                              <Text strong style={{ fontSize: 20 }}>{price.toFixed(2)}</Text>
                            </div>
                          )}
                          {changePct !== null && (
                            <div>
                              <Text style={{
                                color: changePct > 0 ? COLORS.stockUp : changePct < 0 ? COLORS.stockDown : COLORS.stockFlat,
                                fontSize: 14,
                              }}>
                                {changePct > 0 ? '+' : ''}{changePct.toFixed(2)}%
                              </Text>
                            </div>
                          )}
                          {amount !== null && (
                            <div>
                              <Text type="secondary" style={{ fontSize: 11 }}>
                                成交 {(amount / 1e8).toFixed(0)}亿
                              </Text>
                            </div>
                          )}
                        </Card>
                      </Col>
                    );
                  })}
                </Row>
              ) : (
                <Empty description="暂无指数数据" />
              )}
            </Card>

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
      {focus && <SnapshotPanel agentType="macro" stockCode={focus.stock_code} />}
    </Spin>
  );
}
