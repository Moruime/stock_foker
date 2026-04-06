import { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import {
  Card,
  Segmented,
  Spin,
  Empty,
  Alert,
  Tag,
  Typography,
  Descriptions,
  Space,
  Row,
  Col,
} from 'antd';
import ReactECharts from 'echarts-for-react';
import { getStockAnalysis } from '../services/api';
import type { FocusStock, StockAnalysis } from '../types';

const { Title, Text } = Typography;

const periodOptions = [
  { value: 'daily', label: '日K' },
  { value: 'weekly', label: '周K' },
  { value: 'monthly', label: '月K' },
];

export default function AnalysisPage() {
  const { focus } = useOutletContext<{ focus: FocusStock | null }>();
  const [period, setPeriod] = useState('daily');
  const [analysis, setAnalysis] = useState<StockAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!focus) return;
    setLoading(true);
    setError('');
    getStockAnalysis(focus.stock_code, period)
      .then(setAnalysis)
      .catch((e) => setError(e.response?.data?.detail || '加载失败'))
      .finally(() => setLoading(false));
  }, [focus, period]);

  if (!focus) return <Empty description="请先搜索并关注一支股票" />;
  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  if (error) return <Alert message="加载失败" description={error} type="error" />;
  if (!analysis) return null;

  const { kline_data, indicators, advice } = analysis;
  const dates = kline_data.map((d) => d.date);
  const ohlc = kline_data.map((d) => [d.open, d.close, d.low, d.high]);

  const klineOption = {
    tooltip: { trigger: 'axis' as const, axisPointer: { type: 'cross' as const } },
    legend: { data: ['K线', 'MA5', 'MA10', 'MA20', 'MA60'], top: 0 },
    grid: [
      { left: '8%', right: '4%', top: '10%', height: '50%' },
      { left: '8%', right: '4%', top: '68%', height: '18%' },
    ],
    xAxis: [
      { type: 'category' as const, data: dates, gridIndex: 0, axisLabel: { show: false } },
      { type: 'category' as const, data: dates, gridIndex: 1 },
    ],
    yAxis: [
      { type: 'value' as const, gridIndex: 0, scale: true },
      { type: 'value' as const, gridIndex: 1, scale: true },
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], start: 70, end: 100 },
      { type: 'slider', xAxisIndex: [0, 1], start: 70, end: 100, top: '92%' },
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        data: ohlc,
        xAxisIndex: 0,
        yAxisIndex: 0,
        itemStyle: {
          color: '#ef5350',
          color0: '#26a69a',
          borderColor: '#ef5350',
          borderColor0: '#26a69a',
        },
      },
      ...(indicators.ma5
        ? [
            {
              name: 'MA5',
              type: 'line',
              data: indicators.ma5,
              smooth: true,
              lineStyle: { width: 1 },
              symbol: 'none',
              xAxisIndex: 0,
              yAxisIndex: 0,
            },
          ]
        : []),
      ...(indicators.ma10
        ? [
            {
              name: 'MA10',
              type: 'line',
              data: indicators.ma10,
              smooth: true,
              lineStyle: { width: 1 },
              symbol: 'none',
              xAxisIndex: 0,
              yAxisIndex: 0,
            },
          ]
        : []),
      ...(indicators.ma20
        ? [
            {
              name: 'MA20',
              type: 'line',
              data: indicators.ma20,
              smooth: true,
              lineStyle: { width: 1 },
              symbol: 'none',
              xAxisIndex: 0,
              yAxisIndex: 0,
            },
          ]
        : []),
      ...(indicators.ma60
        ? [
            {
              name: 'MA60',
              type: 'line',
              data: indicators.ma60,
              smooth: true,
              lineStyle: { width: 1 },
              symbol: 'none',
              xAxisIndex: 0,
              yAxisIndex: 0,
            },
          ]
        : []),
      {
        name: '成交量',
        type: 'bar',
        data: indicators.volumes,
        xAxisIndex: 1,
        yAxisIndex: 1,
        itemStyle: {
          color: (params: { dataIndex: number }) => {
            const idx = params.dataIndex;
            return kline_data[idx]?.close >= kline_data[idx]?.open ? '#ef5350' : '#26a69a';
          },
        },
      },
    ],
  };

  const signalColor = advice.signal === 'buy' ? 'green' : advice.signal === 'sell' ? 'red' : 'default';
  const signalText = advice.signal === 'buy' ? '买入' : advice.signal === 'sell' ? '卖出' : '持有观望';

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Segmented options={periodOptions} value={period} onChange={(v) => setPeriod(v as string)} />
      </Space>

      <Card title="K线走势与均线" size="small" style={{ marginBottom: 16 }}>
        <ReactECharts option={klineOption} style={{ height: 500 }} />
      </Card>

      <Row gutter={16}>
        <Col span={16}>
          <Card
            title={
              <Space>
                <span>买卖建议</span>
                <Tag color={signalColor} style={{ fontSize: 14 }}>
                  {signalText}
                </Tag>
                <Text type="secondary">置信度: {(advice.confidence * 100).toFixed(0)}%</Text>
              </Space>
            }
            size="small"
          >
            <Title level={5}>推理过程:</Title>
            {advice.reasoning.map((r, i) => (
              <Alert
                key={i}
                message={r}
                type="info"
                showIcon={false}
                style={{ marginBottom: 8 }}
              />
            ))}
          </Card>
        </Col>
        <Col span={8}>
          <Card title="指标概览" size="small">
            <Descriptions column={1} size="small">
              {Object.entries(advice.indicators_summary).map(([key, val]) => (
                <Descriptions.Item key={key} label={key}>
                  {typeof val === 'number' ? val.toFixed(2) : String(val)}
                </Descriptions.Item>
              ))}
            </Descriptions>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
