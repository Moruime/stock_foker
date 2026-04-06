import { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import {
  Card,
  Row,
  Col,
  Statistic,
  Empty,
  Spin,
  Tag,
  List,
  Progress,
  Typography,
} from 'antd';
import {
  TrophyOutlined,
  FallOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { getTradingProfile } from '../services/api';
import type { FocusStock, TradingProfile } from '../types';

const { Text } = Typography;

export default function ProfilePage() {
  const { focus } = useOutletContext<{ focus: FocusStock | null }>();
  const [profile, setProfile] = useState<TradingProfile | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    getTradingProfile(focus?.stock_code)
      .then(setProfile)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [focus]);

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  if (!profile || profile.total_trades === 0)
    return <Empty description="暂无交易数据，请先添加交易记录" />;

  const winRatePct = (profile.win_rate * 100).toFixed(1);
  const sentimentPct = (profile.sentiment_accuracy * 100).toFixed(1);

  return (
    <div>
      <h3>炒股画像</h3>

      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总交易次数"
              value={profile.total_trades}
              prefix={<ThunderboltOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="胜率"
              value={winRatePct}
              suffix="%"
              prefix={<TrophyOutlined />}
              valueStyle={{ color: parseFloat(winRatePct) >= 50 ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="盈亏比"
              value={profile.profit_loss_ratio}
              precision={2}
              prefix={<FallOutlined />}
              valueStyle={{ color: profile.profit_loss_ratio >= 1 ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平均持仓天数"
              value={profile.avg_hold_days}
              suffix="天"
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={8}>
          <Card title="交易风格" size="small">
            <p>
              <Text type="secondary">交易频率: </Text>
              <Tag>{profile.trade_frequency}</Tag>
            </p>
            <p>
              <Text type="secondary">偏好时间框架: </Text>
              <Tag color="blue">{profile.preferred_time_frame}</Tag>
            </p>
            <p>
              <Text type="secondary">平均盈利: </Text>
              <Tag color="green">+{profile.avg_profit.toFixed(2)}</Tag>
            </p>
            <p>
              <Text type="secondary">平均亏损: </Text>
              <Tag color="red">{profile.avg_loss.toFixed(2)}</Tag>
            </p>
          </Card>
        </Col>
        <Col span={8}>
          <Card title="胜率与情绪准确率" size="small">
            <div style={{ marginBottom: 16 }}>
              <Text>胜率</Text>
              <Progress
                percent={parseFloat(winRatePct)}
                status={parseFloat(winRatePct) >= 50 ? 'success' : 'exception'}
              />
            </div>
            <div>
              <Text>情绪判断准确率</Text>
              <Progress
                percent={parseFloat(sentimentPct)}
                status={parseFloat(sentimentPct) >= 50 ? 'success' : 'exception'}
              />
            </div>
          </Card>
        </Col>
        <Col span={8}>
          <Card title="常见买卖理由" size="small">
            {profile.common_buy_reasons.length > 0 && (
              <>
                <Text strong>买入理由 TOP:</Text>
                <List
                  size="small"
                  dataSource={profile.common_buy_reasons}
                  renderItem={(item) => (
                    <List.Item>
                      <Tag color="red">买</Tag> {item.reason} ({item.count}次)
                    </List.Item>
                  )}
                />
              </>
            )}
            {profile.common_sell_reasons.length > 0 && (
              <>
                <Text strong>卖出理由 TOP:</Text>
                <List
                  size="small"
                  dataSource={profile.common_sell_reasons}
                  renderItem={(item) => (
                    <List.Item>
                      <Tag color="green">卖</Tag> {item.reason} ({item.count}次)
                    </List.Item>
                  )}
                />
              </>
            )}
            {profile.common_buy_reasons.length === 0 &&
              profile.common_sell_reasons.length === 0 && (
                <Text type="secondary">暂无数据</Text>
              )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}
