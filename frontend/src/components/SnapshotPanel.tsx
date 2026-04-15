/**
 * SnapshotPanel — Agent 每日历史记录面板
 *
 * 左栏：该股票 + Agent 类型下所有有记录的日期列表（降序）
 * 右栏：所选日期的关键指标展示
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Row,
  Col,
  List,
  Tag,
  Typography,
  Spin,
  Empty,
  Descriptions,
  Divider,
  Progress,
} from 'antd';
import {
  HistoryOutlined,
  SmileOutlined,
  MehOutlined,
  FrownOutlined,
  RiseOutlined,
  FallOutlined,
} from '@ant-design/icons';
import { getSnapshotDates, getSnapshotDetail } from '../services/api';
import type { AgentSnapshot } from '../types';
import { COLORS } from '../theme';

const { Text, Title, Paragraph } = Typography;

// ------------------------------------------------------------------ types

export type AgentTypeWithAdvice = 'sentiment' | 'sector' | 'macro' | 'enhanced_advice';

interface SnapshotPanelProps {
  agentType: AgentTypeWithAdvice;
  stockCode: string;
  /** 外部变更时自动刷新日期列表（例如 Agent 运行完成后 +1） */
  refreshKey?: number;
}

// ------------------------------------------------------------------ helpers

// 使用本地日期（避免 UTC 时区偏差导致日期不匹配）
function todayStr(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

// ------------------------------------------------------------------ Sentiment detail

function SentimentDetail({ data }: { data: Record<string, unknown> }) {
  const score = (data.overall_sentiment as number) ?? 0;
  const label = (data.sentiment_label as string) || '中性';
  const newsCount = (data.raw_news_count as number) ?? 0;
  const noiseRatio = (data.noise_ratio as number) ?? 0;
  const analysis = (data.analysis as string) || '';

  const icon =
    score > 0 ? <SmileOutlined style={{ color: COLORS.stockUp }} /> :
    score < 0 ? <FrownOutlined style={{ color: COLORS.stockDown }} /> :
    <MehOutlined style={{ color: COLORS.stockFlat }} />;

  const color = score > 0 ? COLORS.stockUp : score < 0 ? COLORS.stockDown : COLORS.stockFlat;

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
        <span style={{ fontSize: 32 }}>{icon}</span>
        <div>
          <Title level={4} style={{ margin: 0, color }}>{label}</Title>
          <Text type="secondary">情绪评分: {score}</Text>
        </div>
      </div>
      <Descriptions column={2} size="small" style={{ marginBottom: 12 }}>
        <Descriptions.Item label="新闻数量">{newsCount}</Descriptions.Item>
        <Descriptions.Item label="噪音比例">{noiseRatio.toFixed(0)}%</Descriptions.Item>
      </Descriptions>
      {analysis && (
        <>
          <Divider style={{ margin: '8px 0' }} />
          <Text type="secondary" style={{ fontSize: 12 }}>分析摘要</Text>
          <Paragraph style={{ marginTop: 4, fontSize: 13 }}>{analysis}</Paragraph>
        </>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ Sector detail

function SectorDetail({ data }: { data: Record<string, unknown> }) {
  const sectorName = (data.sector_name as string) || '未知';
  const trend = (data.sector_trend as string) || '震荡';
  const strength = (data.relative_strength as number) ?? 0;
  const rotationSignal = (data.sector_rotation_signal as string) || '稳定';
  const analysis = (data.analysis as string) || '';

  const trendColor =
    trend === '上涨' ? COLORS.stockUp :
    trend === '下跌' ? COLORS.stockDown :
    COLORS.stockFlat;

  return (
    <div>
      <div style={{ marginBottom: 12 }}>
        <Title level={4} style={{ margin: 0 }}>{sectorName}</Title>
        <div style={{ marginTop: 6 }}>
          <Tag color={trendColor}>{trend}</Tag>
          <Tag>轮动: {rotationSignal}</Tag>
        </div>
      </div>
      <Descriptions column={1} size="small" style={{ marginBottom: 12 }}>
        <Descriptions.Item label="相对强度">
          <span style={{
            color: strength > 0 ? COLORS.stockUp : strength < 0 ? COLORS.stockDown : COLORS.stockFlat,
          }}>
            {strength > 0 ? <RiseOutlined /> : strength < 0 ? <FallOutlined /> : null}
            {' '}{strength > 0 ? '+' : ''}{strength}
          </span>
        </Descriptions.Item>
      </Descriptions>
      {analysis && (
        <>
          <Divider style={{ margin: '8px 0' }} />
          <Text type="secondary" style={{ fontSize: 12 }}>分析摘要</Text>
          <Paragraph style={{ marginTop: 4, fontSize: 13 }}>{analysis}</Paragraph>
        </>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ Macro detail

function MacroDetail({ data }: { data: Record<string, unknown> }) {
  const phase = (data.market_phase as string) || '震荡市';
  const sentiment = (data.market_sentiment as number) ?? 0;
  const riskLevel = (data.risk_level as string) || '中';
  const impact = (data.impact_on_stock as string) || '';
  const analysis = (data.analysis as string) || '';

  const riskColor =
    riskLevel === '高' ? COLORS.stockUp :
    riskLevel === '低' ? COLORS.stockDown :
    COLORS.warning;

  const sentimentColor =
    sentiment > 0 ? COLORS.stockUp :
    sentiment < 0 ? COLORS.stockDown :
    COLORS.stockFlat;

  return (
    <div>
      <Descriptions column={2} size="small" style={{ marginBottom: 12 }}>
        <Descriptions.Item label="市场阶段">
          <Text strong>{phase}</Text>
        </Descriptions.Item>
        <Descriptions.Item label="市场情绪">
          <span style={{ color: sentimentColor }}>
            {sentiment > 0 ? <><RiseOutlined /> 偏多</> :
             sentiment < 0 ? <><FallOutlined /> 偏空</> :
             '中性'}
          </span>
        </Descriptions.Item>
        <Descriptions.Item label="风险等级">
          <Tag color={riskColor}>{riskLevel}</Tag>
        </Descriptions.Item>
      </Descriptions>
      {impact && (
        <>
          <Text type="secondary" style={{ fontSize: 12 }}>对该股影响</Text>
          <Paragraph style={{ marginTop: 4, fontSize: 13 }}>{impact}</Paragraph>
        </>
      )}
      {analysis && (
        <>
          <Divider style={{ margin: '8px 0' }} />
          <Text type="secondary" style={{ fontSize: 12 }}>分析摘要</Text>
          <Paragraph style={{ marginTop: 4, fontSize: 13 }}>{analysis}</Paragraph>
        </>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ EnhancedAdvice detail

function EnhancedAdviceDetail({ data }: { data: Record<string, unknown> }) {
  const signal = (data.signal as string) || 'hold';
  const confidence = (data.confidence as number) ?? 0;
  const summary = (data.summary as string) || '';
  const positionAdvice = (data.position_advice as string) || '';
  const reasoning = (data.reasoning as string[]) || [];
  const riskWarnings = (data.risk_warnings as string[]) || [];
  const ds = (data.dimension_scores as Record<string, number>) || {};

  const signalColor = signal === 'buy' ? 'red' : signal === 'sell' ? 'green' : 'default';
  const signalText = signal === 'buy' ? '买入' : signal === 'sell' ? '卖出' : '持有观望';
  const confPct = Math.round(confidence * 100);

  const dimLabels: Record<string, string> = {
    technical: '技术面',
    sentiment: '消息面',
    sector: '板块',
    macro: '宏观',
    fundamental: '基本面',
  };

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
        <Tag color={signalColor} style={{ fontSize: 14, padding: '2px 10px' }}>{signalText}</Tag>
        <Progress
          percent={confPct}
          size="small"
          style={{ width: 120, marginBottom: 0 }}
          format={(p) => `置信度 ${p}%`}
        />
      </div>
      {Object.keys(ds).length > 0 && (
        <Descriptions column={2} size="small" style={{ marginBottom: 10 }}>
          {Object.entries(ds).map(([k, v]) => (
            <Descriptions.Item key={k} label={dimLabels[k] ?? k}>
              {typeof v === 'number' ? v.toFixed(0) : String(v)}
            </Descriptions.Item>
          ))}
        </Descriptions>
      )}
      {summary && (
        <>
          <Text type="secondary" style={{ fontSize: 12 }}>综合评估</Text>
          <Paragraph style={{ marginTop: 4, fontSize: 13 }}>{summary}</Paragraph>
        </>
      )}
      {positionAdvice && (
        <Tag color="success" style={{ marginBottom: 8 }}>仓位建议: {positionAdvice}</Tag>
      )}
      {reasoning.length > 0 && (
        <>
          <Divider style={{ margin: '8px 0' }} />
          <Text type="secondary" style={{ fontSize: 12 }}>分析依据</Text>
          <ul style={{ paddingLeft: 16, marginTop: 4, fontSize: 13 }}>
            {reasoning.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        </>
      )}
      {riskWarnings.length > 0 && (
        <>
          <Divider style={{ margin: '8px 0' }} />
          <Text style={{ fontSize: 12, color: COLORS.warning }}>风险提示</Text>
          <ul style={{ paddingLeft: 16, marginTop: 4, fontSize: 13, color: COLORS.warning }}>
            {riskWarnings.map((w, i) => <li key={i}>{w}</li>)}
          </ul>
        </>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ SnapshotDetail dispatcher

function SnapshotDetail({ snapshot }: { snapshot: AgentSnapshot }) {
  const { agentType: _agentType, snapshot_data: data } = {
    agentType: snapshot.agent_type,
    snapshot_data: snapshot.snapshot_data,
  };

  return (
    <div>
      <div style={{ marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
        <Text strong>{snapshot.date}</Text>
        {snapshot.llm_used
          ? <Tag color="geekblue">AI</Tag>
          : <Tag>规则</Tag>
        }
      </div>
      {snapshot.agent_type === 'sentiment' && <SentimentDetail data={data} />}
      {snapshot.agent_type === 'sector' && <SectorDetail data={data} />}
      {snapshot.agent_type === 'macro' && <MacroDetail data={data} />}
      {snapshot.agent_type === 'enhanced_advice' && <EnhancedAdviceDetail data={data} />}
    </div>
  );
}

// ------------------------------------------------------------------ main component

const AGENT_LABEL: Record<string, string> = {
  sentiment: '消息面',
  sector: '板块联动',
  macro: '宏观环境',
  enhanced_advice: 'AI 综合分析',
};

export default function SnapshotPanel({ agentType, stockCode, refreshKey }: SnapshotPanelProps) {
  const [dates, setDates] = useState<string[]>([]);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [detail, setDetail] = useState<AgentSnapshot | null>(null);
  const [datesLoading, setDatesLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);

  // 加载日期列表
  const loadDates = useCallback(async () => {
    if (!stockCode) return;
    setDatesLoading(true);
    try {
      const list = await getSnapshotDates(agentType, stockCode);
      // 历史记录不含当天
      const historical = list.filter((d) => d !== todayStr());
      setDates(historical);
      // 默认选中最新一天
      if (historical.length > 0) {
        setSelectedDate(historical[0]);
      } else {
        setSelectedDate(null);
        setDetail(null);
      }
    } catch {
      setDates([]);
    } finally {
      setDatesLoading(false);
    }
  }, [agentType, stockCode]);

  // 加载某天详情
  const loadDetail = useCallback(async (date: string) => {
    setDetailLoading(true);
    try {
      const snap = await getSnapshotDetail(agentType, date, stockCode);
      setDetail(snap);
    } catch {
      setDetail(null);
    } finally {
      setDetailLoading(false);
    }
  }, [agentType, stockCode]);

  useEffect(() => {
    loadDates();
  }, [loadDates, refreshKey]);

  useEffect(() => {
    if (selectedDate) {
      loadDetail(selectedDate);
    }
  }, [selectedDate, loadDetail]);

  const title = (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <HistoryOutlined />
      <span>{AGENT_LABEL[agentType]} 历史记录</span>
      {dates.length > 0 && (
        <Tag style={{ marginLeft: 4 }}>{dates.length} 天</Tag>
      )}
    </div>
  );

  return (
    <Card title={title} size="small" style={{ marginTop: 16 }}>
      {datesLoading ? (
        <Spin style={{ display: 'block', margin: '24px auto' }} />
      ) : dates.length === 0 ? (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="暂无历史记录，运行 Agent 后自动保存"
        />
      ) : (
        <Row gutter={16}>
          {/* 左栏：日期列表 */}
          <Col
            span={6}
            style={{
              borderRight: `1px solid rgba(255,255,255,0.08)`,
              paddingRight: 12,
              maxHeight: 360,
              overflowY: 'auto',
            }}
          >
            <List
              size="small"
              dataSource={dates}
              renderItem={(date) => {
                const isSelected = date === selectedDate;
                return (
                  <List.Item
                    onClick={() => setSelectedDate(date)}
                    style={{
                      cursor: 'pointer',
                      padding: '6px 8px',
                      borderRadius: 4,
                      marginBottom: 2,
                      background: isSelected
                        ? 'rgba(77,171,247,0.15)'
                        : 'transparent',
                      borderLeft: isSelected
                        ? `2px solid ${COLORS.primary}`
                        : '2px solid transparent',
                    }}
                  >
                    <Text
                      style={{
                        fontSize: 13,
                        color: isSelected ? COLORS.primary : undefined,
                        fontWeight: isSelected ? 600 : undefined,
                      }}
                    >
                      {date}
                    </Text>
                  </List.Item>
                );
              }}
            />
          </Col>

          {/* 右栏：详情 */}
          <Col span={18} style={{ paddingLeft: 16 }}>
            {detailLoading ? (
              <Spin style={{ display: 'block', margin: '32px auto' }} />
            ) : detail ? (
              <SnapshotDetail snapshot={detail} />
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="选择左侧日期查看详情" />
            )}
          </Col>
        </Row>
      )}
    </Card>
  );
}
