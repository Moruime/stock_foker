import { useState, useEffect } from 'react';
import { Card, Tag, List, Typography, Spin, Alert, Button, Empty, Space } from 'antd';
import {
  ReloadOutlined,
  SmileOutlined,
  MehOutlined,
  FrownOutlined,
} from '@ant-design/icons';
import { useOutletContext } from 'react-router-dom';
import { runSentimentAgent } from '../services/api';
import type { FocusStock, AgentResult } from '../types';
import { COLORS } from '../theme';

const { Text, Title, Paragraph } = Typography;

export default function SentimentPage() {
  const { focus } = useOutletContext<{ focus: FocusStock | null }>();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AgentResult | null>(null);
  const [error, setError] = useState('');

  const fetchData = async () => {
    if (!focus) return;
    setLoading(true);
    setError('');
    try {
      const data = await runSentimentAgent(focus.stock_code, focus.stock_name);
      setResult(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : '获取消息面分析失败');
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
          <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>
            刷新
          </Button>
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
    </Spin>
  );
}
