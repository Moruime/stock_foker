import { useState, useEffect, useCallback } from 'react';
import { Card, Tag, List, Typography, Spin, Alert, Button, Empty, Space, Tooltip } from 'antd';
import {
  ReloadOutlined,
  SmileOutlined,
  MehOutlined,
  FrownOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { useOutletContext } from 'react-router-dom';
import { runSentimentAgent, clearAgentCache } from '../services/api';
import type { FocusStock, AgentResult } from '../types';
import { COLORS } from '../theme';
import { useAgentCache } from '../contexts/AgentCacheContext';
import SnapshotPanel from '../components/SnapshotPanel';

const { Text, Title, Paragraph } = Typography;

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
    fetchData(true);
  }, [focus, invalidateStock, fetchData]);

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
          </>
        )}
      </Space>
      {focus && <SnapshotPanel agentType="sentiment" stockCode={focus.stock_code} />}
    </Spin>
  );
}
