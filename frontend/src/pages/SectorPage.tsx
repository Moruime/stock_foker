import { useState, useEffect, useCallback } from 'react';
import { Card, Tag, Table, Typography, Spin, Alert, Button, Empty, Space, Tooltip } from 'antd';
import { ReloadOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { useOutletContext } from 'react-router-dom';
import { runSectorAgent, clearAgentCache } from '../services/api';
import type { FocusStock, AgentResult } from '../types';
import { COLORS } from '../theme';
import { useAgentCache } from '../contexts/AgentCacheContext';
import SnapshotPanel from '../components/SnapshotPanel';

const { Text, Title, Paragraph } = Typography;

function formatCacheTime(isoStr: string): string {
  const d = new Date(isoStr);
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}

export default function SectorPage() {
  const { focus } = useOutletContext<{ focus: FocusStock | null }>();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AgentResult | null>(null);
  const [error, setError] = useState('');
  const [fromCache, setFromCache] = useState(false);

  const { getAgentCache, setAgentCache, invalidateStock } = useAgentCache();

  const fetchData = useCallback(async (forceRefresh = false) => {
    if (!focus) return;

    if (!forceRefresh) {
      const cached = getAgentCache(focus.stock_code, 'sector');
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
      const data = await runSectorAgent(focus.stock_code, focus.stock_name);
      setResult(data);
      setAgentCache(focus.stock_code, 'sector', data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '获取板块分析失败');
    } finally {
      setLoading(false);
    }
  }, [focus, getAgentCache, setAgentCache]);

  const handleRefresh = useCallback(async () => {
    if (!focus) return;
    try { await clearAgentCache(focus.stock_code); } catch { /* ignore */ }
    invalidateStock(focus.stock_code);
    fetchData(true);
  }, [focus, invalidateStock, fetchData]);

  useEffect(() => {
    fetchData();
  }, [focus?.stock_code]);

  if (!focus) {
    return <Empty description="请先关注一支股票" />;
  }

  const d = result?.data || {};
  const sectorName = (d.sector_name as string) || '未知';
  const sectorTrend = (d.sector_trend as string) || '震荡';
  const relativeStrength = (d.relative_strength as number) || 0;
  const rotationSignal = (d.sector_rotation_signal as string) || '稳定';
  const concepts = (d.related_concepts as Record<string, unknown>[]) || [];
  const topPeers = (d.top_peers as Record<string, unknown>[]) || [];
  const analysis = (d.analysis as string) || '';

  const trendColor =
    sectorTrend === '上涨' ? COLORS.stockUp :
    sectorTrend === '下跌' ? COLORS.stockDown :
    COLORS.stockFlat;

  return (
    <Spin spinning={loading}>
      <Space direction="vertical" style={{ width: '100%' }} size={16}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={4} style={{ margin: 0 }}>
            {focus.stock_name} 板块联动分析
          </Title>
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
              <Alert type="warning" message="AI 分析不可用，展示原始板块数据" showIcon />
            )}

            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
              <Card style={{ flex: 1, minWidth: 200 }}>
                <Text type="secondary">所属板块</Text>
                <Title level={3} style={{ margin: '4px 0' }}>{sectorName}</Title>
                <Space>
                  <Tag color={trendColor}>{sectorTrend}</Tag>
                  <Tag>轮动信号: {rotationSignal}</Tag>
                </Space>
              </Card>
              <Card style={{ flex: 1, minWidth: 200 }}>
                <Text type="secondary">相对强度</Text>
                <Title level={3} style={{
                  margin: '4px 0',
                  color: relativeStrength > 0 ? COLORS.stockUp : relativeStrength < 0 ? COLORS.stockDown : COLORS.stockFlat,
                }}>
                  {relativeStrength > 0 ? '+' : ''}{relativeStrength}
                </Title>
              </Card>
            </div>

            {analysis && (
              <Card title="分析摘要">
                <Paragraph>{analysis}</Paragraph>
              </Card>
            )}

            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
              <Card title="相关概念板块" style={{ flex: 1, minWidth: 300 }}>
                {concepts.length > 0 ? (
                  <Space wrap>
                    {concepts.map((c, i) => (
                      <Tag key={i} color="blue">
                        {c.name as string} {c.activity ? `(${c.activity})` : ''}
                      </Tag>
                    ))}
                  </Space>
                ) : (
                  <Empty description="暂无概念板块数据" />
                )}
              </Card>

              <Card title="板块成分股" style={{ flex: 1, minWidth: 300 }}>
                {topPeers.length > 0 ? (
                  <Table
                    dataSource={topPeers.map((p, i) => ({ ...p, key: i }))}
                    columns={[
                      { title: '名称', dataIndex: 'name', key: 'name' },
                      { title: '代码', dataIndex: 'code', key: 'code' },
                      {
                        title: '涨跌幅',
                        dataIndex: 'change_pct',
                        key: 'change_pct',
                        render: (v: number) => (
                          <Text style={{
                            color: v > 0 ? COLORS.stockUp : v < 0 ? COLORS.stockDown : COLORS.stockFlat,
                          }}>
                            {v > 0 ? '+' : ''}{(v || 0).toFixed(2)}%
                          </Text>
                        ),
                      },
                    ]}
                    pagination={false}
                    size="small"
                  />
                ) : (
                  <Empty description="暂无成分股数据" />
                )}
              </Card>
            </div>
          </>
        )}
      </Space>
      {focus && <SnapshotPanel agentType="sector" stockCode={focus.stock_code} />}
    </Spin>
  );
}
