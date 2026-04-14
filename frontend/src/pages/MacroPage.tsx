import { useState, useEffect, useCallback } from 'react';
import {
  Card, Tag, List, Typography, Spin, Alert, Button, Empty, Space,
  Tooltip, Row, Col, Statistic, Table, Divider,
} from 'antd';
import {
  ReloadOutlined, RiseOutlined, FallOutlined,
  ClockCircleOutlined, SyncOutlined,
} from '@ant-design/icons';
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

/** 从对象中模糊匹配字段 */
function findVal(row: Record<string, unknown>, keyword: string): unknown {
  const key = Object.keys(row).find((k) => k.includes(keyword));
  return key !== undefined ? row[key] : null;
}

function findNum(row: Record<string, unknown>, keyword: string): number | null {
  const v = findVal(row, keyword);
  return typeof v === 'number' ? v : null;
}

/** 数据源卡片标题（带 loading + 缓存时间） */
function DsCardTitle({ title, loading, timestamp }: { title: string; loading: boolean; timestamp: string }) {
  return (
    <Space>
      <span>{title}</span>
      {loading && <SyncOutlined spin style={{ fontSize: 12 }} />}
      {timestamp && (
        <Text type="secondary" style={{ fontSize: 11, fontWeight: 'normal' }}>
          <ClockCircleOutlined style={{ marginRight: 2 }} />
          {formatCacheTime(timestamp)}
        </Text>
      )}
    </Space>
  );
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
  const northFlow = useDataSource(focus?.stock_code, focus?.stock_name, 'north_flow');
  const marketOverview = useDataSource(focus?.stock_code, focus?.stock_name, 'market_overview');
  const hithinkMacro = useDataSource(focus?.stock_code, focus?.stock_name, 'hithink_macro');

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
    northFlow.refresh();
    marketOverview.refresh();
    hithinkMacro.refresh();
  }, [focus, invalidateStock, fetchData, hithinkIndex, northFlow, marketOverview, hithinkMacro]);

  useEffect(() => {
    fetchData();
  }, [focus?.stock_code]);

  if (!focus) {
    return <Empty description="请先关注一支股票" />;
  }

  // ---- AI 结果解析 ----
  const d = result?.data || {};
  const marketPhase = (d.market_phase as string) || '震荡市';
  const marketSentiment = (d.market_sentiment as number) || 0;
  const riskLevel = (d.risk_level as string) || '中';
  const keyIndicators = (d.key_indicators as Record<string, unknown>[]) || [];
  const impactOnStock = (d.impact_on_stock as string) || '';
  const analysis = (d.analysis as string) || '';

  // ---- 指数数据 ----
  const indexRows = (hithinkIndex.data?.datas as Record<string, unknown>[]) || [];

  // ---- 涨跌概况 ----
  const overviewRow = ((marketOverview.data?.datas as Record<string, unknown>[]) || [])[0] || {};
  const riseCount = findNum(overviewRow, '上涨家数');
  const fallCount = findNum(overviewRow, '下跌家数');
  const limitUpCount = findNum(overviewRow, '涨停家数');
  const limitDownCount = findNum(overviewRow, '跌停家数');
  const hasOverview = riseCount !== null || fallCount !== null;

  // ---- 北向资金 ----
  const northRows = (northFlow.data?.datas as Record<string, unknown>[]) || [];

  // ---- 宏观指标 ----
  const macroData = (hithinkMacro.data || {}) as Record<string, Record<string, unknown>>;
  const macroItems: { label: string; value: string; numVal: number; suffix: string; time: string }[] = [];
  // 通用解析：每个子查询返回 {datas: [{指标, 指标值, 时间, ...}]}
  const macroCategories: { key: string; label: string; isPmi?: boolean; decimals?: number }[] = [
    { key: 'cpi', label: 'CPI同比' },
    { key: 'ppi', label: 'PPI同比' },
    { key: 'pmi', label: '制造业PMI', isPmi: true },
    { key: 'lpr', label: 'LPR(1Y)', decimals: 2 },
    { key: 'm2', label: 'M2同比' },
    { key: 'shibor', label: '社融同比' },
  ];
  for (const cat of macroCategories) {
    const row = ((macroData[cat.key]?.datas as Record<string, unknown>[]) || [])[0];
    if (row) {
      const v = (row['指标值'] as number) ?? null;
      const time = (row['时间'] as string) || '';
      if (v !== null) {
        macroItems.push({
          label: cat.label,
          value: v.toFixed(cat.decimals ?? 1),
          numVal: v,
          suffix: cat.isPmi ? '' : '%',
          time,
        });
      }
    }
  }

  const riskColor =
    riskLevel === '高' ? COLORS.stockUp :
    riskLevel === '低' ? COLORS.stockDown :
    COLORS.warning;

  // ---- 北向资金表格列 ----
  const northColumns = [
    {
      title: '#',
      key: 'idx',
      width: 36,
      render: (_: unknown, __: unknown, i: number) => i + 1,
    },
    {
      title: '代码',
      key: 'code',
      width: 90,
      render: (_: unknown, row: Record<string, unknown>) => {
        const code = (row['股票代码'] as string) || '';
        return <Text type="secondary" style={{ fontSize: 12 }}>{code.replace(/\.(SH|SZ)$/, '')}</Text>;
      },
    },
    {
      title: '股票简称',
      key: 'name',
      width: 90,
      ellipsis: true,
      render: (_: unknown, row: Record<string, unknown>) =>
        (row['股票简称'] as string) || '--',
    },
    {
      title: '主力资金流(万)',
      key: 'amount',
      width: 110,
      align: 'right' as const,
      render: (_: unknown, row: Record<string, unknown>) => {
        const v = findNum(row, '主力资金流向');
        if (v === null) return '--';
        const wan = v / 1e4; // 元 → 万元
        return (
          <Text style={{ color: wan > 0 ? COLORS.stockUp : wan < 0 ? COLORS.stockDown : COLORS.stockFlat }}>
            {wan > 0 ? '+' : ''}{wan.toFixed(0)}
          </Text>
        );
      },
    },
    {
      title: '涨跌幅',
      key: 'change',
      width: 80,
      align: 'right' as const,
      render: (_: unknown, row: Record<string, unknown>) => {
        const v = findNum(row, '涨跌幅');
        if (v === null) return '--';
        return (
          <Text style={{ color: v > 0 ? COLORS.stockUp : v < 0 ? COLORS.stockDown : COLORS.stockFlat }}>
            {v > 0 ? '+' : ''}{v.toFixed(2)}%
          </Text>
        );
      },
    },
  ];

  return (
    <Spin spinning={loading}>
      <Space direction="vertical" style={{ width: '100%' }} size={16}>
        {/* ===== Header ===== */}
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

            {/* ===== AI 概览 ===== */}
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
          </>
        )}

        {/* ===== 指数行情 + 涨跌概况 并排 ===== */}
        <Row gutter={16}>
          <Col span={hasOverview ? 16 : 24}>
            <Card
              title={<DsCardTitle title="主要指数行情" loading={hithinkIndex.loading} timestamp={hithinkIndex.timestamp} />}
              size="small"
              extra={
                <Tooltip title="刷新指数行情">
                  <ReloadOutlined style={{ fontSize: 12, cursor: 'pointer' }} onClick={() => hithinkIndex.refresh()} />
                </Tooltip>
              }
            >
              {hithinkIndex.loading ? (
                <Spin size="small" style={{ display: 'block', margin: '16px auto' }} />
              ) : indexRows.length > 0 ? (
                <Row gutter={[16, 12]}>
                  {indexRows.map((row, i) => {
                    const name = (row['指数简称'] as string) || `指数${i + 1}`;
                    const price = findNum(row, '收盘价') ?? findNum(row, '最新价') ?? (row['最新价'] as number);
                    const changePct = findNum(row, '涨跌幅');
                    const amount = findNum(row, '成交额');
                    return (
                      <Col span={8} key={i}>
                        <Card size="small" style={{ textAlign: 'center' }}>
                          <Text type="secondary" style={{ fontSize: 12 }}>{name}</Text>
                          {price !== null && price !== undefined && (
                            <div><Text strong style={{ fontSize: 20 }}>{price.toFixed(2)}</Text></div>
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
          </Col>

          {/* 涨跌概况 */}
          {hasOverview && (
            <Col span={8}>
              <Card
                title={<DsCardTitle title="涨跌概况" loading={marketOverview.loading} timestamp={marketOverview.timestamp} />}
                size="small"
                style={{ height: '100%' }}
                extra={
                  <Tooltip title="刷新涨跌概况">
                    <ReloadOutlined style={{ fontSize: 12, cursor: 'pointer' }} onClick={() => marketOverview.refresh()} />
                  </Tooltip>
                }
              >
                {marketOverview.loading ? (
                  <Spin size="small" style={{ display: 'block', margin: '16px auto' }} />
                ) : (
                  <Row gutter={[12, 16]}>
                    <Col span={12}>
                      <Statistic
                        title="上涨"
                        value={riseCount ?? '--'}
                        valueStyle={{ color: COLORS.stockUp, fontSize: 22 }}
                      />
                    </Col>
                    <Col span={12}>
                      <Statistic
                        title="下跌"
                        value={fallCount ?? '--'}
                        valueStyle={{ color: COLORS.stockDown, fontSize: 22 }}
                      />
                    </Col>
                    <Col span={12}>
                      <Statistic
                        title="涨停"
                        value={limitUpCount ?? '--'}
                        valueStyle={{ color: COLORS.stockUp, fontSize: 22 }}
                        suffix="家"
                      />
                    </Col>
                    <Col span={12}>
                      <Statistic
                        title="跌停"
                        value={limitDownCount ?? '--'}
                        valueStyle={{ color: COLORS.stockDown, fontSize: 22 }}
                        suffix="家"
                      />
                    </Col>
                  </Row>
                )}
              </Card>
            </Col>
          )}
        </Row>

        {/* ===== 宏观经济指标 ===== */}
        <Card
          title={<DsCardTitle title="宏观经济指标" loading={hithinkMacro.loading} timestamp={hithinkMacro.timestamp} />}
          size="small"
          extra={
            <Tooltip title="刷新宏观指标">
              <ReloadOutlined style={{ fontSize: 12, cursor: 'pointer' }} onClick={() => hithinkMacro.refresh()} />
            </Tooltip>
          }
        >
          {hithinkMacro.loading ? (
            <Spin size="small" style={{ display: 'block', margin: '16px auto' }} />
          ) : macroItems.length > 0 ? (
            <div style={{ display: 'flex', gap: 0 }}>
              {macroItems.map((item) => {
                const timeFmt = item.time ? `${item.time.slice(0, 4)}-${item.time.slice(4, 6)}` : '';
                return (
                  <div key={item.label} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                    <Tooltip title={timeFmt ? `数据期: ${timeFmt}` : undefined}>
                      <div style={{ textAlign: 'center' }}>
                        <Statistic
                          title={item.label}
                          value={item.value}
                          suffix={item.suffix}
                          valueStyle={{
                            fontSize: 20,
                            color: item.label === '制造业PMI'
                              ? (item.numVal >= 50 ? COLORS.stockUp : COLORS.stockDown)
                              : (item.numVal > 0 ? COLORS.stockUp : item.numVal < 0 ? COLORS.stockDown : COLORS.stockFlat),
                          }}
                        />
                        {timeFmt && <Text type="secondary" style={{ fontSize: 10 }}>{timeFmt}</Text>}
                      </div>
                    </Tooltip>
                  </div>
                );
              })}
            </div>
          ) : (
            <Empty description="暂无宏观指标数据" />
          )}
        </Card>

        {/* ===== 北向资金 Top10 ===== */}
        {(northRows.length > 0 || northFlow.loading) && (
          <Card
            title={<DsCardTitle title="主力资金流向 Top10" loading={northFlow.loading} timestamp={northFlow.timestamp} />}
            size="small"
            extra={
              <Tooltip title="刷新北向资金">
                <ReloadOutlined style={{ fontSize: 12, cursor: 'pointer' }} onClick={() => northFlow.refresh()} />
              </Tooltip>
            }
          >
            {northFlow.loading ? (
              <Spin size="small" style={{ display: 'block', margin: '16px auto' }} />
            ) : (
              <Table
                size="small"
                dataSource={northRows.map((r, i) => ({ ...r, key: i }))}
                columns={northColumns}
                pagination={false}
              />
            )}
          </Card>
        )}

        {/* ===== AI 综合分析 ===== */}
        {result && (keyIndicators.length > 0 || impactOnStock || analysis) && (
          <Card title={`AI 综合分析${focus.stock_name ? ' — ' + focus.stock_name : ''}`} size="small">
            {keyIndicators.length > 0 && (
              <>
                <Text strong style={{ fontSize: 13 }}>关键指标</Text>
                <List
                  size="small"
                  dataSource={keyIndicators}
                  style={{ marginTop: 8 }}
                  renderItem={(item) => (
                    <List.Item style={{ padding: '6px 0' }}>
                      <Space>
                        <Tag color="blue">{item.name as string}</Tag>
                        <Text strong>{item.value as string}</Text>
                        <Text type="secondary" style={{ fontSize: 12 }}>{item.interpretation as string}</Text>
                      </Space>
                    </List.Item>
                  )}
                />
              </>
            )}
            {impactOnStock && (
              <>
                <Divider style={{ margin: '12px 0' }} />
                <Text strong style={{ fontSize: 13 }}>对 {focus.stock_name} 的影响</Text>
                <Paragraph style={{ marginTop: 8 }}>{impactOnStock}</Paragraph>
              </>
            )}
            {analysis && (
              <>
                <Divider style={{ margin: '12px 0' }} />
                <Text strong style={{ fontSize: 13 }}>分析摘要</Text>
                <Paragraph style={{ marginTop: 8 }}>{analysis}</Paragraph>
              </>
            )}
          </Card>
        )}
      </Space>
      {focus && <SnapshotPanel agentType="macro" stockCode={focus.stock_code} />}
    </Spin>
  );
}
