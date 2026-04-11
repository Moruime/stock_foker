import { useState, useEffect, useCallback } from 'react';
import { Card, Tag, Table, Typography, Spin, Alert, Button, Empty, Space, Tooltip, Statistic, Row, Col } from 'antd';
import { ReloadOutlined, ClockCircleOutlined, FundOutlined, StockOutlined, SyncOutlined } from '@ant-design/icons';
import { useOutletContext } from 'react-router-dom';
import { runSectorAgent, clearAgentCache } from '../services/api';
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

export default function SectorPage() {
  const { focus } = useOutletContext<{ focus: FocusStock | null }>();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AgentResult | null>(null);
  const [error, setError] = useState('');
  const [fromCache, setFromCache] = useState(false);

  const { getAgentCache, setAgentCache, invalidateStock } = useAgentCache();

  // 独立数据源
  const industryValuation = useDataSource(focus?.stock_code, focus?.stock_name, 'industry_valuation');
  const marketData = useDataSource(focus?.stock_code, focus?.stock_name, 'market_data');

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
    invalidateDataSourceCache(focus.stock_code);
    fetchData(true);
    industryValuation.refresh();
    marketData.refresh();
  }, [focus, invalidateStock, fetchData, industryValuation, marketData]);

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

  // 同花顺原始数据（独立数据源）
  const industryRow = ((industryValuation.data?.datas as Record<string, unknown>[]) || [])[0] || {};
  const marketRow = ((marketData.data?.datas as Record<string, unknown>[]) || [])[0] || {};
  const hasIndustryData = Object.keys(industryRow).length > 0;
  const hasMarketData = Object.keys(marketRow).length > 0;

  // 从行业数据中提取常用字段（key 含日期后缀，用模糊匹配）
  const findVal = (row: Record<string, unknown>, keyword: string): number | null => {
    const key = Object.keys(row).find((k) => k.includes(keyword));
    return key !== undefined ? (row[key] as number) ?? null : null;
  };

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

            {/* 行业估值 + 资金流向（独立数据源） */}
            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
              <Card
                title={
                  <Space>
                    <FundOutlined />
                    <span>行业估值指标</span>
                    {industryValuation.loading && <SyncOutlined spin style={{ fontSize: 12 }} />}
                    {industryValuation.timestamp && (
                      <Text type="secondary" style={{ fontSize: 11, fontWeight: 'normal' }}>
                        <ClockCircleOutlined style={{ marginRight: 2 }} />
                        {formatCacheTime(industryValuation.timestamp)}
                      </Text>
                    )}
                  </Space>
                }
                size="small"
                style={{ flex: 1, minWidth: 300 }}
                extra={
                  <Tooltip title="刷新行业估值">
                    <ReloadOutlined
                      style={{ fontSize: 12, cursor: 'pointer' }}
                      onClick={() => industryValuation.refresh()}
                    />
                  </Tooltip>
                }
              >
                {industryValuation.loading ? (
                  <Spin size="small" style={{ display: 'block', margin: '16px auto' }} />
                ) : hasIndustryData ? (
                    <Row gutter={[16, 12]}>
                      {findVal(industryRow, '市盈率') !== null && (
                        <Col span={8}>
                          <Statistic title="PE (市盈率)" value={findVal(industryRow, '市盈率')!} precision={2} />
                        </Col>
                      )}
                      {findVal(industryRow, '市净率') !== null && (
                        <Col span={8}>
                          <Statistic title="PB (市净率)" value={findVal(industryRow, '市净率')!} precision={2} />
                        </Col>
                      )}
                      {findVal(industryRow, '净资产收益率') !== null && (
                        <Col span={8}>
                          <Statistic title="ROE" value={findVal(industryRow, '净资产收益率')!} precision={2} suffix="%" />
                        </Col>
                      )}
                      {findVal(industryRow, '行业中值') !== null && (
                        <Col span={8}>
                          <Statistic title="PE 行业中值" value={findVal(industryRow, '行业中值')!} precision={2} />
                        </Col>
                      )}
                      {(industryRow['所属同花顺二级行业'] as string) && (
                        <Col span={8}>
                          <Text type="secondary">所属行业</Text>
                          <div><Text strong>{industryRow['所属同花顺二级行业'] as string}</Text></div>
                        </Col>
                      )}
                    </Row>
                ) : (
                  <Empty description="暂无行业估值数据" />
                )}
              </Card>

              {(() => {
                  const netInflow = findVal(marketRow, '主力资金流向');
                  const bigOrder = findVal(marketRow, '大单净买入');
                  const turnover = findVal(marketRow, '换手率');
                  const volumeRatio = findVal(marketRow, '量比');
                  const amount = findVal(marketRow, '成交额');
                  return (
                    <Card
                      title={
                        <Space>
                          <StockOutlined />
                          <span>资金流向</span>
                          {marketData.loading && <SyncOutlined spin style={{ fontSize: 12 }} />}
                          {marketData.timestamp && (
                            <Text type="secondary" style={{ fontSize: 11, fontWeight: 'normal' }}>
                              <ClockCircleOutlined style={{ marginRight: 2 }} />
                              {formatCacheTime(marketData.timestamp)}
                            </Text>
                          )}
                        </Space>
                      }
                      size="small"
                      style={{ flex: 1, minWidth: 300 }}
                      extra={
                        <Tooltip title="刷新资金流向">
                          <ReloadOutlined
                            style={{ fontSize: 12, cursor: 'pointer' }}
                            onClick={() => marketData.refresh()}
                          />
                        </Tooltip>
                      }
                    >
                      {marketData.loading ? (
                        <Spin size="small" style={{ display: 'block', margin: '16px auto' }} />
                      ) : hasMarketData ? (
                      <Row gutter={[16, 12]}>
                        {netInflow !== null && (
                          <Col span={8}>
                            <Statistic
                              title="主力净流入"
                              value={netInflow / 10000}
                              precision={0}
                              suffix="万"
                              valueStyle={{ color: netInflow >= 0 ? COLORS.stockUp : COLORS.stockDown }}
                              prefix={netInflow >= 0 ? '+' : ''}
                            />
                          </Col>
                        )}
                        {bigOrder !== null && (
                          <Col span={8}>
                            <Statistic
                              title="大单净买入"
                              value={bigOrder}
                              precision={0}
                              suffix="手"
                              valueStyle={{ color: bigOrder >= 0 ? COLORS.stockUp : COLORS.stockDown }}
                            />
                          </Col>
                        )}
                        {turnover !== null && (
                          <Col span={8}>
                            <Statistic title="换手率" value={turnover} precision={2} suffix="%" />
                          </Col>
                        )}
                        {volumeRatio !== null && (
                          <Col span={8}>
                            <Statistic title="量比" value={volumeRatio} precision={2} />
                          </Col>
                        )}
                        {amount !== null && (
                          <Col span={8}>
                            <Statistic
                              title="成交额"
                              value={amount / 1e8}
                              precision={2}
                              suffix="亿"
                            />
                          </Col>
                        )}
                      </Row>
                      ) : (
                        <Empty description="暂无资金流向数据" />
                      )}
                    </Card>
                  );
                })()}
            </div>

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
