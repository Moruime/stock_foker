import { useState, useEffect, useRef, useCallback } from 'react';
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
  Tooltip,
} from 'antd';
import { QuestionCircleOutlined } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import type { ECharts } from 'echarts';
import { getStockAnalysis } from '../services/api';
import type { FocusStock, StockAnalysis } from '../types';
import { COLORS, chartDarkOption } from '../theme';
import { INDICATOR_MAP } from '../constants/indicators';
import PositionCard from '../components/PositionCard';

const { Title, Text } = Typography;

const periodOptions = [
  { value: 'daily', label: '日K' },
  { value: 'weekly', label: '周K' },
  { value: 'monthly', label: '月K' },
];

function getDataZoom(instance: ECharts) {
  const opt = instance.getOption() as { dataZoom?: { start: number; end: number }[] };
  return opt.dataZoom?.[0];
}

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

  const chartInstance = useRef<ECharts | null>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const dragRef = useRef({ dragging: false, startX: 0, zoomStart: 0, zoomEnd: 0 });

  const onChartReady = useCallback((instance: ECharts) => {
    chartInstance.current = instance;
  }, []);

  // --- 触控板双指滑动平移 + 捏合缩放 ---
  useEffect(() => {
    const wrapper = wrapperRef.current;
    if (!wrapper) return;

    const onWheel = (e: WheelEvent) => {
      const inst = chartInstance.current;
      if (!inst) return;
      e.preventDefault();

      const dz = getDataZoom(inst);
      if (!dz) return;
      const range = dz.end - dz.start;

      if (e.ctrlKey) {
        // 触控板捏合缩放
        const zoomFactor = 1 + e.deltaY * 0.005;
        const center = (dz.start + dz.end) / 2;
        const newRange = Math.max(2, Math.min(100, range * zoomFactor));
        const ns = Math.max(0, Math.min(100 - newRange, center - newRange / 2));
        inst.dispatchAction({ type: 'dataZoom', dataZoomIndex: 0, start: ns, end: ns + newRange });
      } else {
        // 双指滑动平移
        const delta = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY;
        const step = (delta / 800) * range;
        const ns = Math.max(0, Math.min(100 - range, dz.start + step));
        inst.dispatchAction({ type: 'dataZoom', dataZoomIndex: 0, start: ns, end: ns + range });
      }
    };

    const onMouseDown = (e: MouseEvent) => {
      if (e.button !== 0) return;
      const inst = chartInstance.current;
      if (!inst) return;
      const dz = getDataZoom(inst);
      if (!dz) return;
      dragRef.current = { dragging: true, startX: e.clientX, zoomStart: dz.start, zoomEnd: dz.end };
      wrapper.style.cursor = 'grabbing';
      inst.dispatchAction({ type: 'hideTip' });
      e.stopPropagation();
      e.preventDefault();
    };

    const onMouseMove = (e: MouseEvent) => {
      const d = dragRef.current;
      if (!d.dragging) return;
      const inst = chartInstance.current;
      if (!inst) return;
      const range = d.zoomEnd - d.zoomStart;
      const pxPer = wrapper.clientWidth / 100;
      const dp = ((d.startX - e.clientX) / pxPer) * (range / 100);
      const ns = Math.max(0, Math.min(100 - range, d.zoomStart + dp));
      inst.dispatchAction({ type: 'dataZoom', dataZoomIndex: 0, start: ns, end: ns + range });
    };

    const onMouseUp = () => {
      if (!dragRef.current.dragging) return;
      dragRef.current.dragging = false;
      wrapper.style.cursor = 'grab';
    };

    wrapper.style.cursor = 'grab';
    wrapper.addEventListener('wheel', onWheel, { passive: false });
    wrapper.addEventListener('mousedown', onMouseDown, true);
    document.addEventListener('mousemove', onMouseMove, true);
    document.addEventListener('mouseup', onMouseUp, true);
    return () => {
      wrapper.removeEventListener('wheel', onWheel);
      wrapper.removeEventListener('mousedown', onMouseDown, true);
      document.removeEventListener('mousemove', onMouseMove, true);
      document.removeEventListener('mouseup', onMouseUp, true);
    };
  }, [analysis]); // 重新绑定当 analysis 变化（图表重建）

  if (!focus) return <Empty description="请先搜索并关注一支股票" />;
  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  if (error) return <Alert message="加载失败" description={error} type="error" />;
  if (!analysis) return null;

  const { kline_data, indicators, advice } = analysis;
  const dates = kline_data.map((d) => d.date);
  const ohlc = kline_data.map((d) => [d.open, d.close, d.low, d.high]);

  const klineOption = {
    backgroundColor: chartDarkOption.backgroundColor,
    textStyle: chartDarkOption.textStyle,
    tooltip: {
      trigger: 'axis' as const,
      axisPointer: { type: 'cross' as const },
      triggerOn: 'mousemove' as const,
      ...chartDarkOption.tooltip,
      formatter: (params: { seriesName: string; value: number | number[]; dataIndex: number; color: string }[]) => {
        if (!params || params.length === 0) return '';
        const idx = params[0].dataIndex;
        const d = kline_data[idx];
        if (!d) return '';
        const change = d.close - d.open;
        const changePct = d.open !== 0 ? ((change / d.open) * 100).toFixed(2) : '0.00';
        const color = change >= 0 ? COLORS.stockUp : COLORS.stockDown;
        const sign = change >= 0 ? '+' : '';
        const vol = d.volume >= 10000 ? `${(d.volume / 10000).toFixed(1)}万` : `${d.volume}`;
        const amt = d.turnover != null && d.turnover > 0
          ? (d.turnover >= 1e8 ? `${(d.turnover / 1e8).toFixed(2)}亿` : d.turnover >= 1e4 ? `${(d.turnover / 1e4).toFixed(1)}万` : `${d.turnover.toFixed(0)}`)
          : '--';

        let html = `<div style="font-size:12px;line-height:1.8">`;
        html += `<div style="font-weight:600;margin-bottom:4px">${d.date}</div>`;
        html += `<div>开盘: <span style="color:${color};float:right;margin-left:12px">${d.open.toFixed(2)}</span></div>`;
        html += `<div>收盘: <span style="color:${color};float:right;margin-left:12px">${d.close.toFixed(2)}</span></div>`;
        html += `<div>最高: <span style="float:right;margin-left:12px">${d.high.toFixed(2)}</span></div>`;
        html += `<div>最低: <span style="float:right;margin-left:12px">${d.low.toFixed(2)}</span></div>`;
        html += `<div>涨跌: <span style="color:${color};float:right;margin-left:12px">${sign}${change.toFixed(2)} (${sign}${changePct}%)</span></div>`;
        html += `<div>成交量: <span style="float:right;margin-left:12px">${vol}</span></div>`;
        html += `<div>成交额: <span style="float:right;margin-left:12px">${amt}</span></div>`;

        // 均线数据
        for (const p of params) {
          if (p.seriesName.startsWith('MA') && typeof p.value === 'number' && p.value != null) {
            html += `<div><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};margin-right:4px"></span>${p.seriesName}: <span style="float:right;margin-left:12px">${p.value.toFixed(2)}</span></div>`;
          }
        }
        html += `</div>`;
        return html;
      },
    },
    legend: {
      data: ['K线', 'MA5', 'MA10', 'MA20', 'MA60'],
      top: 0,
      ...chartDarkOption.legend,
    },
    grid: [
      { left: '8%', right: '4%', top: '10%', height: '50%' },
      { left: '8%', right: '4%', top: '68%', height: '18%' },
    ],
    xAxis: [
      {
        ...chartDarkOption.axisStyles,
        type: 'category' as const, data: dates, gridIndex: 0, axisLabel: { show: false },
      },
      {
        ...chartDarkOption.axisStyles,
        type: 'category' as const, data: dates, gridIndex: 1,
      },
    ],
    yAxis: [
      { type: 'value' as const, gridIndex: 0, scale: true, ...chartDarkOption.axisStyles },
      { type: 'value' as const, gridIndex: 1, scale: true, ...chartDarkOption.axisStyles },
    ],
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: [0, 1],
        start: 70,
        end: 100,
        zoomOnMouseWheel: false,
        moveOnMouseWheel: false,
        moveOnMouseMove: false,
      },
      {
        type: 'slider',
        xAxisIndex: [0, 1],
        start: 70,
        end: 100,
        top: '92%',
        handleSize: '110%',
        brushSelect: false,
        ...chartDarkOption.dataZoomStyles,
      },
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        data: ohlc,
        xAxisIndex: 0,
        yAxisIndex: 0,
        itemStyle: {
          color: COLORS.stockUp,
          color0: COLORS.stockDown,
          borderColor: COLORS.stockUp,
          borderColor0: COLORS.stockDown,
        },
      },
      ...(indicators.ma5
        ? [
            {
              name: 'MA5',
              type: 'line',
              data: indicators.ma5,
              smooth: true,
              lineStyle: { width: 1, color: chartDarkOption.maColors.ma5 },
              itemStyle: { color: chartDarkOption.maColors.ma5 },
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
              lineStyle: { width: 1, color: chartDarkOption.maColors.ma10 },
              itemStyle: { color: chartDarkOption.maColors.ma10 },
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
              lineStyle: { width: 1, color: chartDarkOption.maColors.ma20 },
              itemStyle: { color: chartDarkOption.maColors.ma20 },
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
              lineStyle: { width: 1, color: chartDarkOption.maColors.ma60 },
              itemStyle: { color: chartDarkOption.maColors.ma60 },
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
            return kline_data[idx]?.close >= kline_data[idx]?.open ? COLORS.stockUp : COLORS.stockDown;
          },
        },
      },
    ],
  };

  const signalColor = advice.signal === 'buy' ? 'red' : advice.signal === 'sell' ? 'green' : 'default';
  const signalText = advice.signal === 'buy' ? '买入' : advice.signal === 'sell' ? '卖出' : '持有观望';

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Segmented options={periodOptions} value={period} onChange={(v) => setPeriod(v as string)} />
      </Space>

      <PositionCard
        stockCode={focus.stock_code}
        stockName={focus.stock_name}
        currentPrice={advice.indicators_summary.current_price}
      />

      <Card title="K线走势与均线" size="small" style={{ marginBottom: 16 }}>
        <div ref={wrapperRef} style={{ userSelect: 'none' }}>
          <ReactECharts
            option={klineOption}
            style={{ height: 500 }}
            onChartReady={onChartReady}
          />
        </div>
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
              {Object.entries(advice.indicators_summary).map(([key, val]) => {
                const meta = INDICATOR_MAP[key];
                const displayLabel = meta ? meta.label : key;
                const interpretation = meta
                  ? meta.interpret(val as number, advice.indicators_summary)
                  : '';
                return (
                  <Descriptions.Item
                    key={key}
                    label={
                      meta ? (
                        <Tooltip
                          title={
                            <div>
                              <div style={{ fontWeight: 600, marginBottom: 4 }}>{meta.label}</div>
                              <div style={{ marginBottom: interpretation ? 6 : 0 }}>{meta.description}</div>
                              {interpretation && (
                                <div style={{ borderTop: '1px solid rgba(255,255,255,0.15)', paddingTop: 4, color: '#ffd666' }}>
                                  {interpretation}
                                </div>
                              )}
                            </div>
                          }
                        >
                          <span style={{ cursor: 'help' }}>
                            {displayLabel} <QuestionCircleOutlined style={{ fontSize: 11, color: COLORS.textMuted }} />
                          </span>
                        </Tooltip>
                      ) : (
                        displayLabel
                      )
                    }
                  >
                    {typeof val === 'number' ? val.toFixed(2) : String(val)}
                  </Descriptions.Item>
                );
              })}
            </Descriptions>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
