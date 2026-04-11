import { useState, useEffect, useCallback } from 'react';
import { Card, Tag, List, Typography, Spin, Alert, Button, Empty, Space, Tooltip, Collapse, Tabs, Table, Descriptions } from 'antd';
import {
  ReloadOutlined,
  SmileOutlined,
  MehOutlined,
  FrownOutlined,
  LinkOutlined,
  ClockCircleOutlined,
  NotificationOutlined,
  FileTextOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import { useOutletContext } from 'react-router-dom';
import { runSentimentAgent, clearAgentCache } from '../services/api';
import type { FocusStock, AgentResult } from '../types';
import { COLORS } from '../theme';
import { useAgentCache } from '../contexts/AgentCacheContext';
import { useDataSource, invalidateDataSourceCache } from '../hooks/useDataSource';
import SnapshotPanel from '../components/SnapshotPanel';

const { Text, Title, Paragraph } = Typography;

/** 摘要省略配置：最多 2 行 */
const summaryEllipsis = { rows: 2 } as const;

/** 从 item 中提取短来源名称（如“搜狐”“华安证券”） */
function getSourceLabel(item: Record<string, unknown>): string | undefined {
  const extra = item.extra as Record<string, unknown> | undefined;
  // 资讯用 publish_source，研报用 organization
  return (extra?.publish_source as string) || (extra?.organization as string) || undefined;
}

/** 将 publish_time 解析为毫秒时间戳，用于排序 */
function parsePublishTimeMs(val: unknown): number {
  if (!val) return 0;
  if (typeof val === 'number') return val > 1e12 ? val : val * 1000;
  const s = String(val);
  if (/^\d{10,13}$/.test(s)) { const n = Number(s); return n > 1e12 ? n : n * 1000; }
  const t = Date.parse(s);
  return isNaN(t) ? 0 : t;
}

/** 按 publish_time 降序排列（最新在前） */
function sortByTimeDesc(list: Record<string, unknown>[]): Record<string, unknown>[] {
  return [...list].sort((a, b) => parsePublishTimeMs(b.publish_time) - parsePublishTimeMs(a.publish_time));
}

/** 将 publish_time 格式化为可读日期（支持 Unix 秒级时间戳和日期字符串） */
function formatPublishTime(val: unknown): string | undefined {
  if (!val) return undefined;
  if (typeof val === 'number') {
    // Unix 秒级时间戳
    const d = new Date(val > 1e12 ? val : val * 1000);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  }
  const s = String(val);
  // 纯数字字符串（如 "1743609600"）
  if (/^\d{10,13}$/.test(s)) {
    const n = Number(s);
    const d = new Date(n > 1e12 ? n : n * 1000);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  }
  return s;
}

function formatCacheTime(isoStr: string): string {
  const d = new Date(isoStr);
  return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}

export default function SentimentPage() {
  const { focus } = useOutletContext<{ focus: FocusStock | null }>();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AgentResult | null>(null);
  const [error, setError] = useState('');
  const [fromCache, setFromCache] = useState(false);

  const { getAgentCache, setAgentCache, invalidateStock } = useAgentCache();

  // 独立数据源 hook
  const hithinkNews = useDataSource(focus?.stock_code, focus?.stock_name, 'hithink_news');
  const announcements = useDataSource(focus?.stock_code, focus?.stock_name, 'announcements');
  const reportsDS = useDataSource(focus?.stock_code, focus?.stock_name, 'reports');
  const basicinfoDS = useDataSource(focus?.stock_code, focus?.stock_name, 'basicinfo');
  const businessDS = useDataSource(focus?.stock_code, focus?.stock_name, 'business');
  const shareholdersDS = useDataSource(focus?.stock_code, focus?.stock_name, 'shareholders');

  const fetchData = useCallback(async (forceRefresh = false) => {
    if (!focus) return;

    // 非强制刷新时先查前端缓存
    if (!forceRefresh) {
      const cached = getAgentCache(focus.stock_code, 'sentiment');
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
      const data = await runSentimentAgent(focus.stock_code, focus.stock_name);
      setResult(data);
      setAgentCache(focus.stock_code, 'sentiment', data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '获取消息面分析失败');
    } finally {
      setLoading(false);
    }
  }, [focus, getAgentCache, setAgentCache]);

  const handleRefresh = useCallback(async () => {
    if (!focus) return;
    // 清除后端 DB 缓存 + 前端内存缓存
    try { await clearAgentCache(focus.stock_code); } catch { /* ignore */ }
    invalidateStock(focus.stock_code);
    invalidateDataSourceCache(focus.stock_code);
    fetchData(true);
    hithinkNews.refresh();
    announcements.refresh();
    reportsDS.refresh();
    basicinfoDS.refresh();
    businessDS.refresh();
    shareholdersDS.refresh();
  }, [focus, invalidateStock, fetchData, hithinkNews, announcements, reportsDS, basicinfoDS, businessDS, shareholdersDS]);

  useEffect(() => {
    fetchData();
  }, [focus?.stock_code]);

  if (!focus) {
    return <Empty description="请先关注一支股票" />;
  }

  const d = result?.data || {};
  const sentimentLabel = (d.sentiment_label as string) || '中性';
  const overallSentiment = (d.overall_sentiment as number) || 0;
  const keyNews = (d.key_news as Record<string, unknown>[]) || [];
  const analysis = (d.analysis as string) || '';
  const rawNewsCount = (d.raw_news_count as number) || 0;

  // 从独立数据源 hook 获取资讯 / 公告
  const hithinkNewsList = sortByTimeDesc((hithinkNews.data?.data as Record<string, unknown>[]) || []);
  const announcementsList = sortByTimeDesc((announcements.data?.data as Record<string, unknown>[]) || []);

  const sentimentIcon =
    overallSentiment > 0 ? <SmileOutlined style={{ color: COLORS.stockUp }} /> :
    overallSentiment < 0 ? <FrownOutlined style={{ color: COLORS.stockDown }} /> :
    <MehOutlined style={{ color: COLORS.stockFlat }} />;

  const sentimentColor =
    overallSentiment > 0 ? COLORS.stockUp :
    overallSentiment < 0 ? COLORS.stockDown :
    COLORS.stockFlat;

  return (
    <Spin spinning={loading}>
      <Space direction="vertical" style={{ width: '100%' }} size={16}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={4} style={{ margin: 0 }}>
            {focus.stock_name} 消息面情绪分析
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
              <Alert type="warning" message="AI 分析不可用，展示原始数据" showIcon />
            )}

            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
              <Card style={{ flex: 1, minWidth: 200 }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 48, marginBottom: 8 }}>{sentimentIcon}</div>
                  <Title level={3} style={{ margin: 0, color: sentimentColor }}>
                    {sentimentLabel}
                  </Title>
                  <Text type="secondary">情绪评分: {overallSentiment}</Text>
                </div>
              </Card>
              <Card style={{ flex: 1, minWidth: 200 }}>
                <Text type="secondary">新闻数量</Text>
                <Title level={3} style={{ margin: '4px 0' }}>{rawNewsCount}</Title>
                <Text type="secondary">噪音比例</Text>
                <Title level={4} style={{ margin: '4px 0' }}>
                  {((d.noise_ratio as number) || 0).toFixed(0)}%
                </Title>
              </Card>
            </div>

            {analysis && (
              <Card title="分析摘要">
                <Paragraph>{analysis}</Paragraph>
              </Card>
            )}

            <Card title={`重点新闻 (${keyNews.length})`}>
              {keyNews.length > 0 ? (
                <List
                  dataSource={keyNews}
                  renderItem={(item) => (
                    <List.Item>
                      <List.Item.Meta
                        title={
                          <Space>
                            <Text>{item.title as string}</Text>
                            <Tag color={
                              (item.sentiment as string) === '利好' ? 'red' :
                              (item.sentiment as string) === '利空' ? 'green' :
                              'default'
                            }>
                              {(item.sentiment as string) || '中性'}
                            </Tag>
                            {item.impact_level ? (
                              <Tag>{`影响: ${item.impact_level as string}`}</Tag>
                            ) : null}
                          </Space>
                        }
                        description={
                          <Space>
                            <Text type="secondary">{item.date as string}</Text>
                            {item.summary ? (
                              <Text type="secondary" style={{ fontSize: 12 }}>
                                {item.summary as string}
                              </Text>
                            ) : null}
                          </Space>
                        }
                      />
                    </List.Item>
                  )}
                />
              ) : (
                <Empty description="暂无新闻数据" />
              )}
            </Card>

            {/* 同花顺财经资讯 + 公告 — 独立数据源 */}
            <Collapse
              ghost
              items={[
                {
                  key: 'hithink_news',
                  label: (
                    <Space>
                      <NotificationOutlined />
                      <span>同花顺财经资讯{hithinkNewsList.length > 0 ? ` (${hithinkNewsList.length})` : ''}</span>
                      {hithinkNews.loading && <SyncOutlined spin style={{ fontSize: 12 }} />}
                      {hithinkNews.timestamp && (
                        <Text type="secondary" style={{ fontSize: 11 }}>
                          <ClockCircleOutlined style={{ marginRight: 2 }} />
                          {formatCacheTime(hithinkNews.timestamp)}
                        </Text>
                      )}
                      <Tooltip title="刷新资讯">
                        <ReloadOutlined
                          style={{ fontSize: 12, cursor: 'pointer', color: COLORS.textSecondary }}
                          onClick={(e) => { e.stopPropagation(); hithinkNews.refresh(); }}
                        />
                      </Tooltip>
                    </Space>
                  ),
                  children: hithinkNews.loading ? (
                    <Spin size="small" style={{ display: 'block', margin: '16px auto' }} />
                  ) : hithinkNewsList.length > 0 ? (
                    <List
                      size="small"
                      dataSource={hithinkNewsList}
                      renderItem={(item) => (
                        <List.Item style={{ overflow: 'hidden' }}>
                          <List.Item.Meta
                            title={
                              <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {(item.url as string) ? (
                                  <a href={item.url as string} target="_blank" rel="noopener noreferrer" style={{ color: COLORS.primary }}>
                                    {(item.title as string) || '无标题'}
                                    <LinkOutlined style={{ marginLeft: 4, fontSize: 11 }} />
                                  </a>
                                ) : (
                                  <Text>{(item.title as string) || '无标题'}</Text>
                                )}
                              </div>
                            }
                            description={
                              <div>
                                {getSourceLabel(item) && (
                                  <Tag style={{ marginRight: 4 }}>{getSourceLabel(item)}</Tag>
                                )}
                                {formatPublishTime(item.publish_time) && (
                                  <Text type="secondary" style={{ fontSize: 12 }}>{formatPublishTime(item.publish_time)}</Text>
                                )}
                                {(item.summary as string) && (
                                  <Paragraph type="secondary" ellipsis={summaryEllipsis} style={{ fontSize: 12, margin: '4px 0 0' }}>
                                    {item.summary as string}
                                  </Paragraph>
                                )}
                              </div>
                            }
                          />
                        </List.Item>
                      )}
                    />
                  ) : (
                    <Empty description="暂无资讯数据" />
                  ),
                },
                {
                  key: 'announcements',
                  label: (
                    <Space>
                      <FileTextOutlined />
                      <span>公司公告{announcementsList.length > 0 ? ` (${announcementsList.length})` : ''}</span>
                      {announcements.loading && <SyncOutlined spin style={{ fontSize: 12 }} />}
                      {announcements.timestamp && (
                        <Text type="secondary" style={{ fontSize: 11 }}>
                          <ClockCircleOutlined style={{ marginRight: 2 }} />
                          {formatCacheTime(announcements.timestamp)}
                        </Text>
                      )}
                      <Tooltip title="刷新公告">
                        <ReloadOutlined
                          style={{ fontSize: 12, cursor: 'pointer', color: COLORS.textSecondary }}
                          onClick={(e) => { e.stopPropagation(); announcements.refresh(); }}
                        />
                      </Tooltip>
                    </Space>
                  ),
                  children: announcements.loading ? (
                    <Spin size="small" style={{ display: 'block', margin: '16px auto' }} />
                  ) : announcementsList.length > 0 ? (
                    <List
                      size="small"
                      dataSource={announcementsList}
                      renderItem={(item) => (
                        <List.Item style={{ overflow: 'hidden' }}>
                          <List.Item.Meta
                            title={
                              <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                {(item.url as string) ? (
                                  <a href={item.url as string} target="_blank" rel="noopener noreferrer" style={{ color: COLORS.primary }}>
                                    {(item.title as string) || '无标题'}
                                    <LinkOutlined style={{ marginLeft: 4, fontSize: 11 }} />
                                  </a>
                                ) : (
                                  <Text>{(item.title as string) || '无标题'}</Text>
                                )}
                              </div>
                            }
                            description={
                              <div>
                                {getSourceLabel(item) && (
                                  <Tag style={{ marginRight: 4 }}>{getSourceLabel(item)}</Tag>
                                )}
                                {formatPublishTime(item.publish_time) && (
                                  <Text type="secondary" style={{ fontSize: 12 }}>{formatPublishTime(item.publish_time)}</Text>
                                )}
                                {(item.summary as string) && (
                                  <Paragraph type="secondary" ellipsis={summaryEllipsis} style={{ fontSize: 12, margin: '4px 0 0' }}>
                                    {item.summary as string}
                                  </Paragraph>
                                )}
                              </div>
                            }
                          />
                        </List.Item>
                      )}
                    />
                  ) : (
                    <Empty description="暂无公告数据" />
                  ),
                },
              ]}
            />
          </>
        )}

        {/* 数据详情 — 研报/公司概况/股东信息 */}
        {(() => {
          const reportsList = sortByTimeDesc((reportsDS.data?.data as Record<string, unknown>[]) || []);
          const basicinfoRow = ((basicinfoDS.data?.datas as Record<string, unknown>[]) || [])[0] || {};
          const businessRows = (businessDS.data?.datas as Record<string, unknown>[]) || [];
          const shareholderRows = (shareholdersDS.data?.datas as Record<string, unknown>[]) || [];

          const hasBasicinfo = Object.keys(basicinfoRow).length > 0;
          const anyLoading = reportsDS.loading || basicinfoDS.loading || businessDS.loading || shareholdersDS.loading;
          const hasAnyData = reportsList.length > 0 || hasBasicinfo || businessRows.length > 0 || shareholderRows.length > 0;
          if (!hasAnyData && !anyLoading) return null;

          const findVal = (row: Record<string, unknown>, keyword: string): unknown => {
            const key = Object.keys(row).find((k) => k.includes(keyword));
            return key !== undefined ? row[key] : null;
          };

          const tabItems = [
            {
              key: 'reports',
              label: (
                <Space>
                  <span>研报观点{reportsList.length > 0 ? ` (${reportsList.length})` : ''}</span>
                  {reportsDS.loading && <SyncOutlined spin style={{ fontSize: 11 }} />}
                  <Tooltip title="刷新研报">
                    <ReloadOutlined
                      style={{ fontSize: 11, cursor: 'pointer' }}
                      onClick={(e) => { e.stopPropagation(); reportsDS.refresh(); }}
                    />
                  </Tooltip>
                </Space>
              ),
              children: reportsDS.loading ? (
                <Spin size="small" style={{ display: 'block', margin: '16px auto' }} />
              ) : reportsList.length > 0 ? (
                <List
                  size="small"
                  dataSource={reportsList}
                  renderItem={(item) => (
                    <List.Item style={{ overflow: 'hidden' }}>
                      <List.Item.Meta
                        title={
                          <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {(item.url as string) ? (
                              <a href={item.url as string} target="_blank" rel="noopener noreferrer" style={{ color: COLORS.primary }}>
                                {(item.title as string) || '无标题'}
                                <LinkOutlined style={{ marginLeft: 4, fontSize: 11 }} />
                              </a>
                            ) : (
                              <Text>{(item.title as string) || '无标题'}</Text>
                            )}
                          </div>
                        }
                        description={
                          <div>
                            {getSourceLabel(item) && (
                              <Tag style={{ marginRight: 4 }}>{getSourceLabel(item)}</Tag>
                            )}
                            {formatPublishTime(item.publish_time) && (
                              <Text type="secondary" style={{ fontSize: 12 }}>{formatPublishTime(item.publish_time)}</Text>
                            )}
                            {(item.summary as string) && (
                              <Paragraph type="secondary" ellipsis={summaryEllipsis} style={{ fontSize: 12, margin: '4px 0 0' }}>
                                {item.summary as string}
                              </Paragraph>
                            )}
                          </div>
                        }
                      />
                    </List.Item>
                  )}
                />
              ) : (
                <Empty description="暂无研报数据" />
              ),
            },
            {
              key: 'company',
              label: (
                <Space>
                  <span>公司概况</span>
                  {(basicinfoDS.loading || businessDS.loading) && <SyncOutlined spin style={{ fontSize: 11 }} />}
                  <Tooltip title="刷新公司数据">
                    <ReloadOutlined
                      style={{ fontSize: 11, cursor: 'pointer' }}
                      onClick={(e) => { e.stopPropagation(); basicinfoDS.refresh(); businessDS.refresh(); }}
                    />
                  </Tooltip>
                </Space>
              ),
              children: (basicinfoDS.loading || businessDS.loading) ? (
                <Spin size="small" style={{ display: 'block', margin: '16px auto' }} />
              ) : (hasBasicinfo || businessRows.length > 0) ? (
                <div>
                  {hasBasicinfo && (
                    <Descriptions column={3} size="small" bordered style={{ marginBottom: 16 }}>
                      {(basicinfoRow['所属同花顺行业'] as string[])?.length > 0 && (
                        <Descriptions.Item label="所属行业">
                          {(basicinfoRow['所属同花顺行业'] as string[]).join(' > ')}
                        </Descriptions.Item>
                      )}
                      {(basicinfoRow['上市日期'] as string) && (
                        <Descriptions.Item label="上市日期">{basicinfoRow['上市日期'] as string}</Descriptions.Item>
                      )}
                      {(basicinfoRow['上市板块'] as string) && (
                        <Descriptions.Item label="上市板块">{basicinfoRow['上市板块'] as string}</Descriptions.Item>
                      )}
                      {findVal(basicinfoRow, '总市值') !== null && (
                        <Descriptions.Item label="总市值">
                          {((findVal(basicinfoRow, '总市值') as number) / 1e8).toFixed(0)}亿
                        </Descriptions.Item>
                      )}
                      {findVal(basicinfoRow, '总股本') !== null && (
                        <Descriptions.Item label="总股本">
                          {((findVal(basicinfoRow, '总股本') as number) / 1e8).toFixed(2)}亿股
                        </Descriptions.Item>
                      )}
                      {findVal(basicinfoRow, '动态市盈率') !== null && (
                        <Descriptions.Item label="动态PE">
                          {(findVal(basicinfoRow, '动态市盈率') as number).toFixed(2)}
                        </Descriptions.Item>
                      )}
                    </Descriptions>
                  )}
                  {businessRows.length > 0 && (
                    <>
                      <Text strong style={{ display: 'block', marginBottom: 8 }}>主营业务构成</Text>
                      <Table
                        size="small"
                        dataSource={businessRows.map((r, i) => ({ ...r, key: i }))}
                        columns={[
                          { title: '项目', dataIndex: '项目名称', key: 'name' },
                          {
                            title: '收入占比',
                            dataIndex: '收入占比',
                            key: 'pct',
                            render: (v: number) => v != null ? `${v.toFixed(1)}%` : '--',
                          },
                          {
                            title: '毛利率',
                            dataIndex: '毛利率',
                            key: 'margin',
                            render: (v: number) => v != null ? `${v.toFixed(1)}%` : '--',
                          },
                          { title: '分类', dataIndex: '分类标准', key: 'cat' },
                        ]}
                        pagination={false}
                      />
                    </>
                  )}
                </div>
              ) : (
                <Empty description="暂无公司数据" />
              ),
            },
            {
              key: 'shareholders',
              label: (
                <Space>
                  <span>股东信息</span>
                  {shareholdersDS.loading && <SyncOutlined spin style={{ fontSize: 11 }} />}
                  <Tooltip title="刷新股东数据">
                    <ReloadOutlined
                      style={{ fontSize: 11, cursor: 'pointer' }}
                      onClick={(e) => { e.stopPropagation(); shareholdersDS.refresh(); }}
                    />
                  </Tooltip>
                </Space>
              ),
              children: shareholdersDS.loading ? (
                <Spin size="small" style={{ display: 'block', margin: '16px auto' }} />
              ) : shareholderRows.length > 0 ? (
                <div>
                  {findVal(shareholderRows[0], '总户数') !== null && (
                    <Descriptions column={3} size="small" style={{ marginBottom: 12 }}>
                      <Descriptions.Item label="股东总户数">
                        {(findVal(shareholderRows[0], '总户数') as number)?.toLocaleString()}
                      </Descriptions.Item>
                      {findVal(shareholderRows[0], '户均持股') !== null && (
                        <Descriptions.Item label="户均持股">
                          {(findVal(shareholderRows[0], '户均持股') as number)?.toLocaleString()}股
                        </Descriptions.Item>
                      )}
                    </Descriptions>
                  )}
                  <Table
                    size="small"
                    dataSource={(() => {
                      const seen = new Set<string>();
                      return shareholderRows
                        .filter((r) => {
                          const name = r['大股东名称'] as string;
                          if (!name || seen.has(name)) return false;
                          seen.add(name);
                          return true;
                        })
                        .sort((a, b) => ((a['排名'] as number) || 99) - ((b['排名'] as number) || 99))
                        .map((r, i) => ({ ...r, key: i }));
                    })()}
                    columns={[
                      { title: '#', dataIndex: '排名', key: 'rank', width: 40, render: (v: unknown) => v != null ? Math.round(v as number) : '-' },
                      { title: '股东名称', dataIndex: '大股东名称', key: 'name', ellipsis: true },
                      { title: '持股比例', key: 'ratio', width: 80, render: (_: unknown, row: Record<string, unknown>) => {
                        const k = Object.keys(row).find((k) => k.startsWith('持股比例'));
                        return k && row[k] != null ? `${(row[k] as number).toFixed(2)}%` : '-';
                      }},
                      { title: '类型', dataIndex: '类型', key: 'type', width: 220, render: (v: unknown) => {
                        const parts = Array.isArray(v) ? (v as string[]).join(';').split(';').map(s => s.trim()).filter(Boolean) : ((v as string) || '').split(';').map(s => s.trim()).filter(Boolean);
                        if (!parts.length) return '-';
                        const show = parts.slice(0, 5);
                        return <Space size={[4, 4]} wrap>{show.map((t, i) => <Tag key={i} style={{ fontSize: 11 }}>{t}</Tag>)}{parts.length > 5 && <Tag style={{ fontSize: 11 }}>+{parts.length - 5}</Tag>}</Space>;
                      }},
                    ]}
                    pagination={false}
                  />
                </div>
              ) : (
                <Empty description="暂无股东数据" />
              ),
            },
          ];

          return (
            <Card title="数据详情" size="small">
              <Tabs items={tabItems} size="small" />
            </Card>
          );
        })()}
      </Space>
      {focus && <SnapshotPanel agentType="sentiment" stockCode={focus.stock_code} />}
    </Spin>
  );
}
