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
  Button,
  List,
  message,
} from 'antd';
import { CheckCircleOutlined, QuestionCircleOutlined, RobotOutlined, ReloadOutlined, ClockCircleOutlined, WarningOutlined, LoadingOutlined, ClockCircleFilled } from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';
import type { ECharts } from 'echarts';
import { getStockAnalysis, clearAgentCache, getCachedEnhancedAnalysis, getIwencaiStatus, getBenchmark, streamEnhancedAnalysis } from '../services/api';
import type { BenchmarkData, SSEEvent } from '../services/api';
import type { FocusStock, StockAnalysis, EnhancedAnalysis } from '../types';
import type { IwencaiStatus } from '../services/api';
import { COLORS, chartDarkOption } from '../theme';
import { INDICATOR_MAP } from '../constants/indicators';
import PositionCard from '../components/PositionCard';
import SnapshotPanel from '../components/SnapshotPanel';
import { useAgentCache } from '../contexts/AgentCacheContext';
import { invalidateDataSourceCache } from '../hooks/useDataSource';

const { Title, Text } = Typography;

// ------------------------------------------------------------------ helpers

/** 返回最近一次 09:00 的本地 Date */
function last9am(): Date {
  const now = new Date();
  const boundary = new Date(now);
  boundary.setHours(9, 0, 0, 0);
  if (now < boundary) boundary.setDate(boundary.getDate() - 1);
  return boundary;
}

/** 判断 timestamp 是否在 9am 边界之前（即过期） */
function isStale(timestamp: string): boolean {
  if (!timestamp) return false;
  return new Date(timestamp) < last9am();
}

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
  const [subIndicator, setSubIndicator] = useState<'macd' | 'kdj' | 'rsi'>('macd');
  const [analysis, setAnalysis] = useState<StockAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [snapshotKey, setSnapshotKey] = useState(0);
  const { getEnhancedCache, setEnhancedCache, invalidateStock } = useAgentCache();
  const [iwencaiStatus, setIwencaiStatus] = useState<IwencaiStatus | null>(null);
  const [benchmark, setBenchmark] = useState<BenchmarkData | null>(null);
  const [benchLoading, setBenchLoading] = useState(false);
  const [benchDays, setBenchDays] = useState(120);

  // 同步读取内存缓存作为初始值，避免页面切换回来时闪烁空态
  const [aiAnalysis, setAiAnalysis] = useState<EnhancedAnalysis | null>(() => {
    if (!focus) return null;
    return getEnhancedCache(focus.stock_code);
  });
  const [aiLoading, setAiLoading] = useState(false);
  const [aiStages, setAiStages] = useState<Record<string, 'pending' | 'running' | 'done'>>({});
  const sseAbortRef = useRef<AbortController | null>(null);
  const [aiFromCache, setAiFromCache] = useState(() => {
    if (!focus) return false;
    return getEnhancedCache(focus.stock_code) !== null;
  });
  // 标记是否已完成缓存检查，防止初始渲染闪烁空态
  const [aiChecked, setAiChecked] = useState(() => {
    if (!focus) return true;
    return getEnhancedCache(focus.stock_code) !== null;
  });

  const [klineRefreshing, setKlineRefreshing] = useState(false);

  useEffect(() => {
    if (!focus) return;
    setLoading(true);
    setError('');
    getStockAnalysis(focus.stock_code, period)
      .then(setAnalysis)
      .catch((e) => setError(e.response?.data?.detail || '加载失败'))
      .finally(() => setLoading(false));
  }, [focus, period]);

  const handleKlineRefresh = useCallback(() => {
    if (!focus || klineRefreshing) return;
    setKlineRefreshing(true);
    getStockAnalysis(focus.stock_code, period, undefined, undefined, true)
      .then((data) => {
        setAnalysis(data);
        // 检查最后一条数据是否是今天
        const last = data.kline_data[data.kline_data.length - 1];
        const today = new Date().toISOString().slice(0, 10);
        if (last && last.date < today) {
          message.warning('远程数据拉取失败，当前K线为缓存数据（请检查网络/代理）');
        } else {
          message.success('K线数据已更新');
        }
      })
      .catch(() => { message.error('刷新失败'); })
      .finally(() => setKlineRefreshing(false));
  }, [focus, period, klineRefreshing]);

  // 对比基准数据
  useEffect(() => {
    if (!focus) { setBenchmark(null); return; }
    setBenchLoading(true);
    getBenchmark(focus.stock_code, 'daily', benchDays)
      .then(setBenchmark)
      .catch(() => setBenchmark(null))
      .finally(() => setBenchLoading(false));
  }, [focus?.stock_code, benchDays]);

  // mount 或切换股票时，自动恢复 AI 分析：优先前端内存缓存，其次查询后端 DB 缓存
  useEffect(() => {
    if (!focus) {
      setAiAnalysis(null);
      setAiFromCache(false);
      setAiChecked(true);
      return;
    }
    // 1. 前端内存缓存命中（初始化时已同步读取，但切换股票时需重新检查）
    const cached = getEnhancedCache(focus.stock_code);
    if (cached) {
      setAiAnalysis(cached);
      setAiFromCache(true);
      setAiChecked(true);
      return;
    }
    // 2. 内存无缓存，查询后端 DB（不运行 Agent）
    setAiLoading(true);
    getCachedEnhancedAnalysis(focus.stock_code)
      .then((data) => {
        setAiAnalysis(data);
        setEnhancedCache(focus.stock_code, data);
        setAiFromCache(true);
      })
      .catch(() => {
        // 404 表示当天尚未分析，保持空状态等待用户手动触发
        setAiAnalysis(null);
        setAiFromCache(false);
      })
      .finally(() => { setAiLoading(false); setAiChecked(true); });
  }, [focus?.stock_code]);

  // 问财 API 状态检查
  useEffect(() => {
    getIwencaiStatus().then(setIwencaiStatus).catch(() => {});
  }, []);

  const _STAGE_LABELS: Record<string, string> = {
    sentiment: '消息面分析',
    sector: '板块联动分析',
    macro: '宏观环境分析',
    enhanced: 'AI 综合建议',
  };

  const _handleSSEEvent = useCallback((evt: SSEEvent, stockCode: string) => {
    const stage = evt.stage;
    if (stage === 'cache_hit' || stage === 'complete') {
      const result = evt.data as unknown as EnhancedAnalysis;
      setAiAnalysis(result);
      setEnhancedCache(stockCode, result);
      setAiFromCache(stage === 'cache_hit');
      setAiLoading(false);
      setAiStages({});
      setSnapshotKey((k) => k + 1);
    } else if (stage === 'upstream_start') {
      const agents = (evt.data as { agents: string[] })?.agents || [];
      setAiStages((prev) => {
        const next = { ...prev };
        for (const a of agents) next[a] = 'running';
        return next;
      });
    } else if (stage === 'sentiment_done' || stage === 'sector_done' || stage === 'macro_done') {
      const name = stage.replace('_done', '');
      setAiStages((prev) => ({ ...prev, [name]: 'done' }));
    } else if (stage === 'enhanced_start') {
      setAiStages((prev) => ({ ...prev, enhanced: 'running' }));
    }
  }, [setEnhancedCache]);

  const handleAiAnalysis = useCallback(() => {
    if (!focus) return;
    setAiLoading(true);
    setAiStages({ sentiment: 'pending', sector: 'pending', macro: 'pending', enhanced: 'pending' });
    sseAbortRef.current?.abort();
    const ctrl = streamEnhancedAnalysis(
      focus.stock_code,
      focus.stock_name,
      (evt) => _handleSSEEvent(evt, focus.stock_code),
      () => setAiLoading(false),
      focus.time_frame,
    );
    sseAbortRef.current = ctrl;
  }, [focus, _handleSSEEvent]);

  const handleAiRefresh = useCallback(async () => {
    if (!focus) return;
    try { await clearAgentCache(focus.stock_code); } catch { /* ignore */ }
    invalidateStock(focus.stock_code);
    invalidateDataSourceCache(focus.stock_code);
    setAiAnalysis(null);
    setAiFromCache(false);
    setAiLoading(true);
    setAiStages({ sentiment: 'pending', sector: 'pending', macro: 'pending', enhanced: 'pending' });
    sseAbortRef.current?.abort();
    const ctrl = streamEnhancedAnalysis(
      focus.stock_code,
      focus.stock_name,
      (evt) => _handleSSEEvent(evt, focus.stock_code),
      () => setAiLoading(false),
      focus.time_frame,
    );
    sseAbortRef.current = ctrl;
  }, [focus, invalidateStock, _handleSSEEvent]);

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

  // ---- 副图指标 series 构建 ----
  const subSeries: Record<string, unknown>[] = [];
  const subLegendData: string[] = [];

  if (subIndicator === 'macd' && indicators.macd) {
    subLegendData.push('DIF', 'DEA', 'MACD柱');
    subSeries.push(
      { name: 'DIF', type: 'line', data: indicators.macd.dif, xAxisIndex: 2, yAxisIndex: 2, symbol: 'none', lineStyle: { width: 1, color: '#4dabf7' }, itemStyle: { color: '#4dabf7' } },
      { name: 'DEA', type: 'line', data: indicators.macd.dea, xAxisIndex: 2, yAxisIndex: 2, symbol: 'none', lineStyle: { width: 1, color: '#e8b339' }, itemStyle: { color: '#e8b339' } },
      {
        name: 'MACD柱', type: 'bar', data: indicators.macd.histogram, xAxisIndex: 2, yAxisIndex: 2,
        itemStyle: { color: (p: { value: number }) => p.value >= 0 ? COLORS.stockUp : COLORS.stockDown },
      },
    );
  } else if (subIndicator === 'kdj' && indicators.kdj) {
    subLegendData.push('K', 'D', 'J');
    subSeries.push(
      { name: 'K', type: 'line', data: indicators.kdj.k, xAxisIndex: 2, yAxisIndex: 2, symbol: 'none', lineStyle: { width: 1, color: '#4dabf7' }, itemStyle: { color: '#4dabf7' } },
      { name: 'D', type: 'line', data: indicators.kdj.d, xAxisIndex: 2, yAxisIndex: 2, symbol: 'none', lineStyle: { width: 1, color: '#e8b339' }, itemStyle: { color: '#e8b339' } },
      {
        name: 'J', type: 'line', data: indicators.kdj.j, xAxisIndex: 2, yAxisIndex: 2, symbol: 'none',
        lineStyle: { width: 1, color: '#b388ff' }, itemStyle: { color: '#b388ff' },
        markLine: {
          silent: true, symbol: 'none',
          lineStyle: { type: 'dashed', color: COLORS.textMuted, width: 1 },
          data: [
            { yAxis: 80, label: { formatter: '80', position: 'end', fontSize: 10, color: COLORS.textMuted } },
            { yAxis: 20, label: { formatter: '20', position: 'end', fontSize: 10, color: COLORS.textMuted } },
          ],
        },
      },
    );
  } else if (subIndicator === 'rsi' && indicators.rsi) {
    subLegendData.push('RSI');
    subSeries.push({
      name: 'RSI', type: 'line', data: indicators.rsi, xAxisIndex: 2, yAxisIndex: 2, symbol: 'none',
      lineStyle: { width: 1, color: '#4dabf7' }, itemStyle: { color: '#4dabf7' },
      markLine: {
        silent: true, symbol: 'none',
        lineStyle: { type: 'dashed', color: COLORS.textMuted, width: 1 },
        data: [
          { yAxis: 70, label: { formatter: '70', position: 'end', fontSize: 10, color: COLORS.textMuted } },
          { yAxis: 30, label: { formatter: '30', position: 'end', fontSize: 10, color: COLORS.textMuted } },
        ],
      },
    });
  }

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
        // 副图指标数据
        const subNames = ['DIF', 'DEA', 'MACD柱', 'K', 'D', 'J', 'RSI'];
        for (const p of params) {
          if (subNames.includes(p.seriesName) && typeof p.value === 'number' && p.value != null) {
            html += `<div><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};margin-right:4px"></span>${p.seriesName}: <span style="float:right;margin-left:12px">${p.value.toFixed(2)}</span></div>`;
          }
        }
        html += `</div>`;
        return html;
      },
    },
    legend: [
      {
        data: ['K线', 'MA5', 'MA10', 'MA20', 'MA60'],
        top: 0,
        ...chartDarkOption.legend,
      },
      {
        data: subLegendData,
        top: '73%',
        left: '8%',
        itemWidth: 14,
        itemHeight: 8,
        textStyle: { fontSize: 10, color: COLORS.textSecondary },
      },
    ],
    grid: [
      { left: '8%', right: '4%', top: '8%', height: '42%' },
      { left: '8%', right: '4%', top: '55%', height: '11%' },
      { left: '8%', right: '4%', top: '76%', height: '13%' },
    ],
    xAxis: [
      {
        ...chartDarkOption.axisStyles,
        type: 'category' as const, data: dates, gridIndex: 0, axisLabel: { show: false },
      },
      {
        ...chartDarkOption.axisStyles,
        type: 'category' as const, data: dates, gridIndex: 1, axisLabel: { show: false },
      },
      {
        ...chartDarkOption.axisStyles,
        type: 'category' as const, data: dates, gridIndex: 2,
      },
    ],
    yAxis: [
      { type: 'value' as const, gridIndex: 0, scale: true, ...chartDarkOption.axisStyles },
      { type: 'value' as const, gridIndex: 1, min: 0, ...chartDarkOption.axisStyles },
      { type: 'value' as const, gridIndex: 2, scale: true, ...chartDarkOption.axisStyles },
    ],
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: [0, 1, 2],
        start: 70,
        end: 100,
        zoomOnMouseWheel: false,
        moveOnMouseWheel: false,
        moveOnMouseMove: false,
      },
      {
        type: 'slider',
        xAxisIndex: [0, 1, 2],
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
        data: kline_data.map((d, i) => ({
          value: indicators.volumes[i],
          itemStyle: { color: d.close >= d.open ? COLORS.stockUp : COLORS.stockDown },
        })),
        xAxisIndex: 1,
        yAxisIndex: 1,
      },
      ...subSeries,
    ],
  };

  const signalColor = advice.signal === 'buy' ? 'red' : advice.signal === 'sell' ? 'green' : 'default';
  const signalText = advice.signal === 'buy' ? '买入' : advice.signal === 'sell' ? '卖出' : '持有观望';

  return (
    <div>
      {iwencaiStatus && !iwencaiStatus.available && (
        <Alert
          type="warning"
          showIcon
          icon={<WarningOutlined />}
          message="部分数据源暂不可用"
          description="问财 API 额度耗尽，基本资料/经营数据/股东信息等将展示历史缓存数据，资讯/公告/研报不受影响。可在「设置」页重置熔断。"
          closable
          style={{ marginBottom: 12 }}
        />
      )}
      <Space style={{ marginBottom: 16 }}>
        <Segmented options={periodOptions} value={period} onChange={(v) => setPeriod(v as string)} />
      </Space>

      <PositionCard
        stockCode={focus.stock_code}
        stockName={focus.stock_name}
        currentPrice={advice.indicators_summary.current_price}
      />

      <Card
        title="K线走势与均线"
        size="small"
        style={{ marginBottom: 16 }}
        extra={
          <Tooltip title="强制刷新当日K线">
            <Button
              type="text"
              size="small"
              icon={<ReloadOutlined spin={klineRefreshing} />}
              onClick={handleKlineRefresh}
              loading={klineRefreshing}
            />
          </Tooltip>
        }
      >
        <div style={{ position: 'relative' }}>
          <div ref={wrapperRef} style={{ userSelect: 'none' }}>
            <ReactECharts
              key={`chart_${focus.stock_code}_${period}_${kline_data.length}`}
              option={klineOption}
              notMerge={true}
              style={{ height: 620 }}
              onChartReady={onChartReady}
            />
          </div>
          <div style={{ position: 'absolute', top: '69%', right: 16, zIndex: 10 }}>
            <Segmented
              size="small"
              options={[
                { value: 'macd', label: 'MACD' },
                { value: 'kdj', label: 'KDJ' },
                { value: 'rsi', label: 'RSI' },
              ]}
              value={subIndicator}
              onChange={(v) => setSubIndicator(v as 'macd' | 'kdj' | 'rsi')}
            />
          </div>
        </div>
      </Card>

      {/* 对比基准 */}
      <Card
        title="对比基准"
        size="small"
        style={{ marginBottom: 16 }}
        loading={benchLoading}
        extra={
          <Segmented
            size="small"
            options={[
              { value: 20, label: '近一月' },
              { value: 60, label: '近三月' },
              { value: 120, label: '近半年' },
              { value: 250, label: '近一年' },
            ]}
            value={benchDays}
            onChange={(v) => setBenchDays(v as number)}
          />
        }
      >
        {benchmark && benchmark.dates.length > 0 ? (
          <Row gutter={16}>
            <Col span={18}>
              <ReactECharts
                option={{
                  backgroundColor: chartDarkOption.backgroundColor,
                  textStyle: chartDarkOption.textStyle,
                  tooltip: {
                    trigger: 'axis' as const,
                    ...chartDarkOption.tooltip,
                    formatter: (params: { seriesName: string; value: number; color: string }[]) => {
                      if (!params || params.length === 0) return '';
                      let html = `<div style="font-size:12px;line-height:1.8">`;
                      html += `<div style="font-weight:600;margin-bottom:4px">${benchmark.dates[params[0].value !== undefined ? (params[0] as unknown as { dataIndex: number }).dataIndex : 0]}</div>`;
                      for (const p of params) {
                        const idx = (p as unknown as { dataIndex: number }).dataIndex;
                        const val = typeof p.value === 'number' ? p.value : 0;
                        const color = val >= 0 ? COLORS.stockUp : COLORS.stockDown;
                        const sign = val >= 0 ? '+' : '';
                        html += `<div><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};margin-right:4px"></span>${p.seriesName}: <span style="color:${color};float:right;margin-left:12px">${sign}${val.toFixed(2)}%</span></div>`;
                        void idx;
                      }
                      html += `</div>`;
                      return html;
                    },
                  },
                  legend: {
                    data: [benchmark.stock.name, ...benchmark.benchmarks.map((b) => b.name)],
                    ...chartDarkOption.legend,
                  },
                  grid: { left: '8%', right: '4%', top: '12%', bottom: '12%' },
                  xAxis: {
                    type: 'category' as const,
                    data: benchmark.dates,
                    ...chartDarkOption.axisStyles,
                  },
                  yAxis: {
                    type: 'value' as const,
                    scale: true,
                    ...chartDarkOption.axisStyles,
                    axisLabel: { ...((chartDarkOption.axisStyles as Record<string, unknown>).axisLabel as Record<string, unknown> || {}), formatter: '{value}%' },
                  },
                  series: [
                    {
                      name: benchmark.stock.name,
                      type: 'line',
                      data: benchmark.stock.pct_change,
                      symbol: 'none',
                      lineStyle: { width: 2, color: '#4dabf7' },
                      itemStyle: { color: '#4dabf7' },
                    },
                    ...benchmark.benchmarks.map((b, i) => ({
                      name: b.name,
                      type: 'line' as const,
                      data: b.pct_change,
                      symbol: 'none',
                      lineStyle: { width: 1.5, color: i === 0 ? '#e8b339' : '#888' },
                      itemStyle: { color: i === 0 ? '#e8b339' : '#888' },
                    })),
                  ],
                }}
                style={{ height: 300 }}
              />
            </Col>
            <Col span={6}>
              {(() => {
                const s = benchmark.stats;
                const items = [
                  { label: benchmark.stock.name, value: s.stock_return },
                  { label: '沪深300', value: s.hs300_return },
                  { label: '上证指数', value: s.sh_return },
                ];
                const excessItems = [
                  { label: 'vs 沪深300', value: s.excess_hs300 },
                  { label: 'vs 上证', value: s.excess_sh },
                ];
                const fmtPct = (v: number) => {
                  const sign = v >= 0 ? '+' : '';
                  const color = v >= 0 ? COLORS.stockUp : COLORS.stockDown;
                  return <span style={{ color, fontWeight: 600 }}>{sign}{v.toFixed(2)}%</span>;
                };
                return (
                  <div>
                    <Text strong style={{ display: 'block', marginBottom: 8 }}>区间涨跌幅</Text>
                    {items.map((it) => (
                      <div key={it.label} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                        <Text type="secondary">{it.label}</Text>
                        {fmtPct(it.value)}
                      </div>
                    ))}
                    <div style={{ borderTop: `1px solid ${COLORS.border}`, margin: '10px 0' }} />
                    <Text strong style={{ display: 'block', marginBottom: 8 }}>超额收益</Text>
                    {excessItems.map((it) => (
                      <div key={it.label} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                        <Text type="secondary">{it.label}</Text>
                        {fmtPct(it.value)}
                      </div>
                    ))}
                  </div>
                );
              })()}
            </Col>
          </Row>
        ) : (
          !benchLoading && <Empty description="暂无对比基准数据" />
        )}
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

      {/* AI 综合分析 */}
      <Card
        title={
          <Space>
            <RobotOutlined />
            <span>AI 综合分析</span>
            {aiAnalysis?.enhanced_advice?.llm_used && <Tag color="blue">AI</Tag>}
            {aiAnalysis?.enhanced_advice && !aiAnalysis.enhanced_advice.llm_used && <Tag>规则</Tag>}
            {aiFromCache && aiAnalysis?.enhanced_advice?.timestamp && (
              <Tooltip title={`缓存于 ${new Date(aiAnalysis.enhanced_advice.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`}>
                <Text type="secondary" style={{ fontSize: 12, fontWeight: 'normal', cursor: 'default' }}>
                  <ClockCircleOutlined style={{ marginRight: 3 }} />
                  缓存于 {new Date(aiAnalysis.enhanced_advice.timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                </Text>
              </Tooltip>
            )}
          </Space>
        }
        size="small"
        style={{ marginTop: 16 }}
        extra={
          aiAnalysis ? (
            <Button
              icon={<ReloadOutlined />}
              onClick={handleAiRefresh}
              loading={aiLoading}
            >
              刷新
            </Button>
          ) : (
            <Button
              icon={<RobotOutlined />}
              onClick={handleAiAnalysis}
              loading={aiLoading}
              type="primary"
            >
              开始分析
            </Button>
          )
        }
      >
        {aiLoading && (
          <div style={{ padding: '16px 0' }}>
            {Object.entries(aiStages).map(([key, status]) => {
              const label = _STAGE_LABELS[key] || key;
              const icon =
                status === 'done' ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> :
                status === 'running' ? <LoadingOutlined style={{ color: COLORS.primary }} /> :
                <ClockCircleFilled style={{ color: COLORS.textMuted }} />;
              return (
                <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, fontSize: 13 }}>
                  {icon}
                  <Text style={{ color: status === 'done' ? COLORS.textSecondary : status === 'running' ? COLORS.textPrimary : COLORS.textMuted }}>
                    {label}
                  </Text>
                </div>
              );
            })}
          </div>
        )}
        
          {/* 过期提示：9点后的旧数据 */}
          {!aiLoading && aiFromCache && aiAnalysis?.enhanced_advice?.timestamp && isStale(aiAnalysis.enhanced_advice.timestamp) && (
            <Alert
              type="warning"
              showIcon
              message="当前显示的是 09:00 之前的旧数据，可能不反映今日最新行情"
              description={`数据来自 ${new Date(aiAnalysis.enhanced_advice.timestamp).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })}，建议点击「刷新」获取最新分析`}
              style={{ marginBottom: 14 }}
            />
          )}

        {!aiLoading && !aiAnalysis && aiChecked && (
          <Empty description="点击「开始分析」运行 AI 五维度综合分析" />
        )}

        {!aiLoading && aiAnalysis && (() => {
          const ea = aiAnalysis.enhanced_advice.data;
          const ds = (ea.dimension_scores as Record<string, number>) || {};
          // 将 LLM 输出的 -1~1 归一化到 0~100 供雷达图显示
          // -1 → 0（最差）、0 → 50（中性）、1 → 100（最佳）
          const toRadar = (v: number) => Math.round((Math.max(-1, Math.min(1, v)) + 1) * 50);
          const radarData = [
            toRadar(ds.technical ?? 0),
            toRadar(ds.sentiment ?? 0),
            toRadar(ds.sector ?? 0),
            toRadar(ds.macro ?? 0),
            toRadar(ds.fundamental ?? 0),
          ];
          // 带 LLM 分析结果时才显示图表（不能全是 50 中性占位）
          const hasRadarData = (aiAnalysis.enhanced_advice.llm_used === true) &&
            radarData.some((v) => v !== 50);

          const aiSignal = (ea.signal as string) || 'hold';
          const aiConfidence = (ea.confidence as number) || 0;
          const aiReasoning = (ea.reasoning as string[]) || [];
          const riskWarnings = (ea.risk_warnings as string[]) || [];
          const positionAdvice = ea.position_advice as string;
          const summary = (ea.summary as string) || '';

          const aiSignalColor = aiSignal === 'buy' ? 'red' : aiSignal === 'sell' ? 'green' : 'default';
          const aiSignalText = aiSignal === 'buy' ? '买入' : aiSignal === 'sell' ? '卖出' : '持有观望';

          const radarOption = {
            backgroundColor: 'transparent',
            radar: {
              indicator: [
                { name: '技术面', max: 100 },
                { name: '消息面', max: 100 },
                { name: '板块', max: 100 },
                { name: '宏观', max: 100 },
                { name: '基本面', max: 100 },
              ],
              shape: 'polygon' as const,
              axisName: { color: COLORS.textSecondary },
              splitArea: { areaStyle: { color: ['rgba(77,171,247,0.03)', 'rgba(77,171,247,0.06)'] } },
              splitLine: { lineStyle: { color: COLORS.borderSubtle } },
              axisLine: { lineStyle: { color: COLORS.border } },
            },
            series: [{
              type: 'radar',
              data: [{
                value: radarData,
                name: '五维评分',
                areaStyle: { color: 'rgba(77,171,247,0.25)' },
                lineStyle: { color: COLORS.primary },
                itemStyle: { color: COLORS.primary },
              }],
            }],
          };

          return (
            <Row gutter={16}>
              <Col span={8}>
                {hasRadarData ? (
                  <ReactECharts option={radarOption} style={{ height: 260 }} />
                ) : (
                  <div style={{ height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Text type="secondary">AI 未启用，无评分数据</Text>
                  </div>
                )}
                <div style={{ textAlign: 'center', marginTop: 8 }}>
                  <Space>
                    <Tag color={aiSignalColor} style={{ fontSize: 16, padding: '4px 16px' }}>{aiSignalText}</Tag>
                    <Text type="secondary">置信度: {(aiConfidence * 100).toFixed(0)}%</Text>
                  </Space>
                </div>
              </Col>
              <Col span={16}>
                {summary && (
                  <Alert message={summary} type="info" style={{ marginBottom: 12 }} />
                )}
                {aiReasoning.length > 0 && (
                  <div style={{ marginBottom: 12 }}>
                    <Text strong>分析依据:</Text>
                    <List
                      size="small"
                      dataSource={aiReasoning}
                      renderItem={(item) => <List.Item style={{ padding: '4px 0' }}>{item}</List.Item>}
                    />
                  </div>
                )}
                {riskWarnings.length > 0 && (
                  <div style={{ marginBottom: 12 }}>
                    <Text strong style={{ color: COLORS.warning }}>风险提示:</Text>
                    {riskWarnings.map((w, i) => (
                      <Alert key={i} message={w} type="warning" showIcon style={{ marginTop: 4 }} />
                    ))}
                  </div>
                )}
                {positionAdvice && (
                  <Alert message={`仓位建议: ${positionAdvice}`} type="success" style={{ marginTop: 8 }} />
                )}
              </Col>
            </Row>
          );
        })()}
      </Card>

      {/* AI 综合分析历史记录 */}
      {focus && <SnapshotPanel agentType="enhanced_advice" stockCode={focus.stock_code} refreshKey={snapshotKey} />}
    </div>
  );
}
