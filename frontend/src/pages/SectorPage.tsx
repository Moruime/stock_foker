import { useState, useEffect, useCallback } from 'react';
import { Card, Tag, Table, Tabs, Typography, Spin, Alert, Button, Empty, Space, Tooltip, Statistic, Row, Col, Divider } from 'antd';
import { ReloadOutlined, ClockCircleOutlined, SyncOutlined } from '@ant-design/icons';
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
  const industryFinance = useDataSource(focus?.stock_code, focus?.stock_name, 'industry_finance');
  const industryPeers = useDataSource(focus?.stock_code, focus?.stock_name, 'industry_peers');
  const conceptBoards = useDataSource(focus?.stock_code, focus?.stock_name, 'concept_boards');

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
    industryFinance.refresh();
    industryPeers.refresh();
    conceptBoards.refresh();
  }, [focus, invalidateStock, fetchData, industryValuation, marketData, industryFinance, industryPeers, conceptBoards]);

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
  const analysis = (d.analysis as string) || '';
  const industryRank = (d.industry_rank as string) || '';

  // 同花顺原始数据（独立数据源）
  const industryRow = ((industryValuation.data?.datas as Record<string, unknown>[]) || [])[0] || {};
  const marketRow = ((marketData.data?.datas as Record<string, unknown>[]) || [])[0] || {};
  const financeRows = (industryFinance.data?.datas as Record<string, unknown>[]) || [];
  const financeRow = financeRows[0] || {};
  const conceptRows = (conceptBoards.data?.datas as Record<string, unknown>[]) || [];
  // 按成份股数量升序排序（越少越聚焦 = 关联度越高）
  const sortedConceptRows = [...conceptRows].sort((a, b) => {
    const ca = (a['成份股数量'] as number) ?? 9999;
    const cb = (b['成份股数量'] as number) ?? 9999;
    return ca - cb;
  });
  const peerRows = (industryPeers.data?.datas as Record<string, unknown>[]) || [];
  const hasIndustryData = Object.keys(industryRow).length > 0;
  const hasMarketData = Object.keys(marketRow).length > 0;
  const hasFinanceData = financeRows.length > 0;
  const hasConceptData = sortedConceptRows.length > 0;
  const hasPeerData = peerRows.length > 0;

  // 从行业数据中提取常用字段（key 含日期后缀，用模糊匹配）
  const findVal = (row: Record<string, unknown>, keyword: string): number | null => {
    const key = Object.keys(row).find((k) => k.includes(keyword));
    return key !== undefined ? (row[key] as number) ?? null : null;
  };

  const trendColor =
    sectorTrend === '强势' ? COLORS.stockUp :
    sectorTrend === '弱势' ? COLORS.stockDown :
    COLORS.stockFlat;

  // 资金流向提取
  const netInflow = findVal(marketRow, '主力资金流向');
  const bigOrder = findVal(marketRow, '大单净买入');
  const turnover = findVal(marketRow, '换手率');
  const volumeRatio = findVal(marketRow, '量比');
  const amount = findVal(marketRow, '成交额');
  const amplitude = findVal(marketRow, '振幅');
  const addPosition = findVal(marketRow, '主力增仓占比');
  const volume = findVal(marketRow, '成交量');

  // Tab 标签复用组件
  const dsTabLabel = (text: string, isLoading: boolean, onRefresh: () => void) => (
    <Space size={4}>
      <span>{text}</span>
      {isLoading && <SyncOutlined spin style={{ fontSize: 11 }} />}
      <Tooltip title={`刷新${text}`}>
        <ReloadOutlined
          style={{ fontSize: 11, cursor: 'pointer' }}
          onClick={(e) => { e.stopPropagation(); onRefresh(); }}
        />
      </Tooltip>
    </Space>
  );

  return (
    <Spin spinning={loading}>
      <Space direction="vertical" style={{ width: '100%' }} size={16}>
        {/* ===== Header ===== */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={4} style={{ margin: 0 }}>
            {focus.stock_name} 板块联动分析
          </Title>
          <Space>
            {fromCache && result?.timestamp && (
              <Text type="secondary" style={{ fontSize: 12, cursor: 'default' }}>
                <ClockCircleOutlined style={{ marginRight: 4 }} />
                缓存于 {formatCacheTime(result.timestamp)}
              </Text>
            )}
            <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={loading}>
              刷新
            </Button>
          </Space>
        </div>

        {error && <Alert type="error" message={error} showIcon />}

        {/* ===== 区域 1：AI 板块总览 ===== */}
        {result && (
          <Card size="small">
            {result.status === 'degraded' && (
              <Alert type="warning" message="AI 分析不可用，展示原始板块数据" showIcon style={{ marginBottom: 12 }} />
            )}
            <div style={{ display: 'flex', alignItems: 'stretch', gap: 0, flexWrap: 'wrap' }}>
              {/* 板块信息 */}
              <div style={{ flex: '0 0 auto', padding: '8px 20px 8px 8px', borderRight: '1px solid rgba(255,255,255,0.08)' }}>
                <Title level={4} style={{ margin: 0 }}>{sectorName}</Title>
                <Space style={{ marginTop: 4 }}>
                  <Tag color={trendColor}>{sectorTrend}</Tag>
                  <Tag>轮动: {rotationSignal}</Tag>
                  {industryRank && <Tag color="blue">排名: {industryRank}</Tag>}
                </Space>
              </div>
              {/* 统计指标 */}
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'space-around', padding: '8px 16px', minWidth: 200 }}>
                <div style={{ textAlign: 'center' }}>
                  <Text type="secondary" style={{ fontSize: 11 }}>相对强度</Text>
                  <Title level={4} style={{
                    margin: 0,
                    color: relativeStrength > 0 ? COLORS.stockUp : relativeStrength < 0 ? COLORS.stockDown : COLORS.stockFlat,
                  }}>
                    {relativeStrength > 0 ? '+' : ''}{relativeStrength}
                  </Title>
                </div>
                {findVal(industryRow, '市盈率') !== null && (
                  <div style={{ textAlign: 'center' }}>
                    <Text type="secondary" style={{ fontSize: 11 }}>PE</Text>
                    <Title level={4} style={{ margin: 0 }}>{findVal(industryRow, '市盈率')!.toFixed(1)}</Title>
                  </div>
                )}
                {findVal(industryRow, '市净率') !== null && (
                  <div style={{ textAlign: 'center' }}>
                    <Text type="secondary" style={{ fontSize: 11 }}>PB</Text>
                    <Title level={4} style={{ margin: 0 }}>{findVal(industryRow, '市净率')!.toFixed(2)}</Title>
                  </div>
                )}
                {findVal(industryRow, '净资产收益率') !== null && (
                  <div style={{ textAlign: 'center' }}>
                    <Text type="secondary" style={{ fontSize: 11 }}>ROE</Text>
                    <Title level={4} style={{ margin: 0 }}>{findVal(industryRow, '净资产收益率')!.toFixed(1)}%</Title>
                  </div>
                )}
                {netInflow !== null && (
                  <div style={{ textAlign: 'center' }}>
                    <Text type="secondary" style={{ fontSize: 11 }}>主力净流入</Text>
                    <Title level={4} style={{ margin: 0, color: netInflow >= 0 ? COLORS.stockUp : COLORS.stockDown }}>
                      {netInflow >= 0 ? '+' : ''}{(netInflow / 10000).toFixed(0)}万
                    </Title>
                  </div>
                )}
              </div>
            </div>
            {analysis && (
              <>
                <Divider style={{ margin: '10px 0' }} />
                <Paragraph type="secondary" ellipsis={{ rows: 3, expandable: true, symbol: '展开' }} style={{ margin: 0, fontSize: 13 }}>
                  {analysis}
                </Paragraph>
              </>
            )}
          </Card>
        )}

        {/* ===== 区域 2：数据详情 (2 Tabs) ===== */}
        <Card title="数据详情" size="small">
          <Tabs
            size="small"
            items={[
              {
                key: 'overview',
                label: dsTabLabel('行业概况', industryValuation.loading || industryFinance.loading, () => { industryValuation.refresh(); industryFinance.refresh(); }),
                children: (industryValuation.loading || industryFinance.loading) ? (
                  <Spin size="small" style={{ display: 'block', margin: '16px auto' }} />
                ) : (hasIndustryData || hasFinanceData) ? (
                  <Row gutter={[16, 12]}>
                    {(industryRow['所属同花顺二级行业'] as string) && (
                      <Col span={8}>
                        <Text type="secondary" style={{ fontSize: 12 }}>所属行业</Text>
                        <div><Text strong>{industryRow['所属同花顺二级行业'] as string}</Text></div>
                      </Col>
                    )}
                    {findVal(industryRow, '最新涨跌幅') !== null && (
                      <Col span={8}>
                        <Statistic title="个股涨跌幅" value={findVal(industryRow, '最新涨跌幅')!} precision={2} suffix="%"
                          valueStyle={{ color: (findVal(industryRow, '最新涨跌幅') ?? 0) >= 0 ? COLORS.stockUp : COLORS.stockDown }}
                        />
                      </Col>
                    )}
                    {findVal(industryRow, '市盈率') !== null && (
                      <Col span={8}><Statistic title="PE (市盈率)" value={findVal(industryRow, '市盈率')!} precision={2} /></Col>
                    )}
                    {findVal(industryRow, '市净率') !== null && (
                      <Col span={8}><Statistic title="PB (市净率)" value={findVal(industryRow, '市净率')!} precision={2} /></Col>
                    )}
                    {findVal(industryRow, '净资产收益率') !== null && (
                      <Col span={8}><Statistic title="ROE" value={findVal(industryRow, '净资产收益率')!} precision={2} suffix="%" /></Col>
                    )}
                    {/* 行业财务中位值 */}
                    {findVal(financeRow, '营业收入同比增长率中位值') !== null && (
                      <Col span={8}><Statistic title="行业营收增速(中位)" value={(findVal(financeRow, '营业收入同比增长率中位值')! * 100)} precision={2} suffix="%" /></Col>
                    )}
                    {findVal(financeRow, '归母净利润同比增长率中位值') !== null && (
                      <Col span={8}><Statistic title="行业净利增速(中位)" value={(findVal(financeRow, '归母净利润同比增长率中位值')! * 100)} precision={2} suffix="%" /></Col>
                    )}
                    {findVal(financeRow, '销售毛利率中位值') !== null && (
                      <Col span={8}><Statistic title="行业毛利率(中位)" value={(findVal(financeRow, '销售毛利率中位值')! * 100)} precision={2} suffix="%" /></Col>
                    )}
                    {findVal(financeRow, '销售净利率中位值') !== null && (
                      <Col span={8}><Statistic title="行业净利率(中位)" value={(findVal(financeRow, '销售净利率中位值')! * 100)} precision={2} suffix="%" /></Col>
                    )}
                  </Row>
                ) : <Empty description="暂无行业概况数据" />,
              },
              {
                key: 'fund_flow',
                label: dsTabLabel('资金流向', marketData.loading, marketData.refresh),
                children: marketData.loading ? (
                  <Spin size="small" style={{ display: 'block', margin: '16px auto' }} />
                ) : hasMarketData ? (
                  <Row gutter={[16, 12]}>
                    {netInflow !== null && (
                      <Col span={8}>
                        <Statistic title="主力净流入" value={netInflow / 10000} precision={0} suffix="万"
                          valueStyle={{ color: netInflow >= 0 ? COLORS.stockUp : COLORS.stockDown }}
                          prefix={netInflow >= 0 ? '+' : ''}
                        />
                      </Col>
                    )}
                    {bigOrder !== null && (
                      <Col span={8}>
                        <Statistic title="大单净买入" value={bigOrder} precision={0} suffix="手"
                          valueStyle={{ color: bigOrder >= 0 ? COLORS.stockUp : COLORS.stockDown }}
                        />
                      </Col>
                    )}
                    {turnover !== null && (
                      <Col span={8}><Statistic title="换手率" value={turnover} precision={2} suffix="%" /></Col>
                    )}
                    {volumeRatio !== null && (
                      <Col span={8}><Statistic title="量比" value={volumeRatio} precision={2} /></Col>
                    )}
                    {amplitude !== null && (
                      <Col span={8}><Statistic title="振幅" value={amplitude} precision={2} suffix="%" /></Col>
                    )}
                    {addPosition !== null && (
                      <Col span={8}><Statistic title="主力增仓占比" value={(addPosition * 100)} precision={2} suffix="%" /></Col>
                    )}
                    {volume !== null && (
                      <Col span={8}><Statistic title="成交量" value={volume / 10000} precision={0} suffix="万手" /></Col>
                    )}
                    {amount !== null && (
                      <Col span={8}><Statistic title="成交额" value={amount / 1e8} precision={2} suffix="亿" /></Col>
                    )}
                  </Row>
                ) : <Empty description="暂无资金流向数据" />,
              },
            ]}
          />
        </Card>

        {/* ===== 区域 3：同行对比与概念板块 (2 Tabs) ===== */}
        <Card title="关联分析" size="small">
          <Tabs
            size="small"
            items={[
              {
                key: 'peers',
                label: dsTabLabel(`同行对比${peerRows.length > 0 ? ` (${peerRows.length})` : ''}`, industryPeers.loading, industryPeers.refresh),
                children: industryPeers.loading ? (
                  <Spin size="small" style={{ display: 'block', margin: '16px auto' }} />
                ) : hasPeerData ? (
                  <Table
                    dataSource={peerRows.map((r, i) => ({ ...r, key: i }))}
                    columns={[
                      {
                        title: '#', key: 'rank', width: 40,
                        render: (_: unknown, __: unknown, idx: number) => (
                          <Text type="secondary">{idx + 1}</Text>
                        ),
                      },
                      {
                        title: '股票简称', dataIndex: '股票简称', key: 'name', width: 90,
                        render: (v: string, row: Record<string, unknown>) => (
                          <Tooltip title={row['股票代码'] as string}><Text strong>{v}</Text></Tooltip>
                        ),
                      },
                      {
                        title: '最新价', key: 'price', width: 80,
                        render: (_: unknown, row: Record<string, unknown>) => {
                          const p = row['最新价'] as number;
                          return p != null ? `¥${p.toFixed(2)}` : '-';
                        },
                      },
                      {
                        title: '涨跌幅', key: 'change', width: 80,
                        render: (_: unknown, row: Record<string, unknown>) => {
                          const v = findVal(row, '最新涨跌幅') ?? findVal(row, '涨跌幅[');
                          if (v == null) return '-';
                          return <Text style={{ color: v > 0 ? COLORS.stockUp : v < 0 ? COLORS.stockDown : COLORS.stockFlat }}>{v > 0 ? '+' : ''}{v.toFixed(2)}%</Text>;
                        },
                      },
                      {
                        title: 'PE(TTM)', key: 'pe', width: 80,
                        render: (_: unknown, row: Record<string, unknown>) => {
                          const v = findVal(row, '市盈率');
                          return v != null ? v.toFixed(1) : '-';
                        },
                      },
                      {
                        title: '总市值', key: 'mv', width: 90,
                        render: (_: unknown, row: Record<string, unknown>) => {
                          const v = findVal(row, '总市值');
                          if (v == null) return '-';
                          return `${(v / 1e8).toFixed(0)}亿`;
                        },
                      },
                      {
                        title: '主力净流入', key: 'flow', width: 100,
                        render: (_: unknown, row: Record<string, unknown>) => {
                          const v = findVal(row, '主力资金');
                          if (v == null) return '-';
                          return <Text style={{ color: v >= 0 ? COLORS.stockUp : COLORS.stockDown }}>{v >= 0 ? '+' : ''}{(v / 10000).toFixed(0)}万</Text>;
                        },
                      },
                    ]}
                    pagination={false}
                    size="small"
                    scroll={{ x: 520 }}
                  />
                ) : <Empty description="暂无同行对比数据" />,
              },
              {
                key: 'concepts',
                label: dsTabLabel(`相关概念${sortedConceptRows.length > 0 ? ` (${sortedConceptRows.length})` : ''}`, conceptBoards.loading, conceptBoards.refresh),
                children: conceptBoards.loading ? (
                  <Spin size="small" style={{ display: 'block', margin: '16px auto' }} />
                ) : hasConceptData ? (
                  <Table
                    dataSource={sortedConceptRows.map((r, i) => ({ ...r, key: i }))}
                    columns={[
                      {
                        title: '概念板块', key: 'name', width: 140,
                        render: (_: unknown, row: Record<string, unknown>) => {
                          const name = (row['指数简称'] as string) || (row['股票简称'] as string) || (row['板块名称'] as string) || '-';
                          return <Tooltip title={row['指数代码'] as string}><Text strong>{name}</Text></Tooltip>;
                        },
                      },
                      {
                        title: '关联度', key: 'relevance', width: 80,
                        render: (_: unknown, row: Record<string, unknown>) => {
                          const cnt = (row['成份股数量'] as number) ?? null;
                          if (cnt == null) return '-';
                          const level = cnt <= 100 ? '高' : cnt <= 300 ? '中' : '低';
                          const bg = cnt <= 100 ? 'rgba(82,196,26,0.15)' : cnt <= 300 ? 'rgba(250,173,20,0.15)' : 'rgba(140,140,140,0.12)';
                          const fg = cnt <= 100 ? '#95de64' : cnt <= 300 ? '#ffd666' : '#8c8c8c';
                          return <Tag style={{ margin: 0, background: bg, color: fg, borderColor: fg }}>{level}</Tag>;
                        },
                      },
                      {
                        title: '成份股', key: 'count', width: 70,
                        render: (_: unknown, row: Record<string, unknown>) => {
                          const cnt = (row['成份股数量'] as number) ?? null;
                          return cnt != null ? `${Math.round(cnt)}只` : '-';
                        },
                      },
                      {
                        title: '涨跌幅', key: 'change', width: 90,
                        render: (_: unknown, row: Record<string, unknown>) => {
                          const v = findVal(row, '涨跌幅');
                          if (v == null) return '-';
                          return <Text style={{ color: v > 0 ? COLORS.stockUp : v < 0 ? COLORS.stockDown : COLORS.stockFlat }}>{v > 0 ? '+' : ''}{v.toFixed(2)}%</Text>;
                        },
                      },
                    ]}
                    pagination={false}
                    size="small"
                  />
                ) : (
                  concepts.length > 0 ? (
                    <Space wrap size={[6, 6]}>
                      {concepts.map((c, i) => (
                        <Tag key={i} color="blue">
                          {c.name as string} {c.activity ? `(${c.activity})` : ''}
                        </Tag>
                      ))}
                    </Space>
                  ) : <Empty description="暂无概念板块数据" />
                ),
              },
            ]}
          />
        </Card>
      </Space>
      {focus && <SnapshotPanel agentType="sector" stockCode={focus.stock_code} />}
    </Spin>
  );
}
