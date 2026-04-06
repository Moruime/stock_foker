export interface IndicatorMeta {
  label: string;
  description: string;
  interpret: (value: number, all: Record<string, number>) => string;
}

export const INDICATOR_MAP: Record<string, IndicatorMeta> = {
  current_price: {
    label: '当前价',
    description: '最新收盘价格，是所有技术分析的基础参考价位',
    interpret: () => '',
  },
  macd_dif: {
    label: 'MACD DIF',
    description: '快速与慢速移动平均线的差值。DIF 上穿 DEA 形成金叉为买入信号，下穿为死叉',
    interpret: (v, all) => {
      const dea = all.macd_dea;
      if (dea == null) return '';
      return v > dea ? 'DIF > DEA，MACD 多头排列' : 'DIF < DEA，MACD 空头排列';
    },
  },
  macd_dea: {
    label: 'MACD DEA',
    description: 'DIF 的信号线（移动平均），用于平滑 DIF 波动，与 DIF 交叉产生买卖信号',
    interpret: (v, all) => {
      const dif = all.macd_dif;
      if (dif == null) return '';
      return dif > v ? '当前 DIF 在 DEA 上方，偏多' : '当前 DIF 在 DEA 下方，偏空';
    },
  },
  kdj_k: {
    label: 'KDJ K值',
    description: '随机指标快线，反映价格在近期区间中的相对位置。K < 20 超卖，K > 80 超买',
    interpret: (v) => {
      if (v < 20) return `K=${v.toFixed(1)}，处于超卖区域，可能存在反弹机会`;
      if (v > 80) return `K=${v.toFixed(1)}，处于超买区域，注意回调风险`;
      return `K=${v.toFixed(1)}，处于正常区间`;
    },
  },
  kdj_d: {
    label: 'KDJ D值',
    description: 'K 值的移动平均（慢线）。K 上穿 D 为金叉（买入信号），K 下穿 D 为死叉（卖出信号）',
    interpret: (v, all) => {
      const k = all.kdj_k;
      if (k == null) return '';
      return k > v ? 'K 在 D 上方，短期偏多' : 'K 在 D 下方，短期偏空';
    },
  },
  kdj_j: {
    label: 'KDJ J值',
    description: 'J = 3K - 2D，比 K/D 更敏感。J > 100 极度超买，J < 0 极度超卖',
    interpret: (v) => {
      if (v < 0) return `J=${v.toFixed(1)}，极度超卖信号`;
      if (v > 100) return `J=${v.toFixed(1)}，极度超买信号`;
      return `J=${v.toFixed(1)}，正常范围`;
    },
  },
  rsi: {
    label: 'RSI 相对强弱',
    description: '衡量价格变动的速率和幅度。RSI < 30 超卖（可能被低估），RSI > 70 超买（可能被高估），50 为多空平衡',
    interpret: (v) => {
      if (v < 30) return `RSI=${v.toFixed(1)}，超卖区域，股价可能被低估`;
      if (v < 50) return `RSI=${v.toFixed(1)}，偏弱区间`;
      if (v < 70) return `RSI=${v.toFixed(1)}，偏强区间`;
      return `RSI=${v.toFixed(1)}，超买区域，注意回调风险`;
    },
  },
  ma5: {
    label: 'MA5 均线',
    description: '5 日移动平均线，反映近一周趋势。股价在 MA5 上方为短期偏多，下方为短期偏空',
    interpret: (v, all) => {
      const p = all.current_price;
      if (p == null) return '';
      return p > v ? '股价在 MA5 上方，短期偏多' : '股价在 MA5 下方，短期偏空';
    },
  },
  ma10: {
    label: 'MA10 均线',
    description: '10 日移动平均线，反映近两周趋势。常与 MA5 配合判断短期方向',
    interpret: (v, all) => {
      const p = all.current_price;
      if (p == null) return '';
      return p > v ? '股价在 MA10 上方，偏多' : '股价在 MA10 下方，偏空';
    },
  },
  ma20: {
    label: 'MA20 均线',
    description: '20 日移动平均线，约一个月趋势参考。MA20 常被视为短期多空分界线',
    interpret: (v, all) => {
      const p = all.current_price;
      if (p == null) return '';
      return p > v ? '股价在 MA20 上方，中短期偏多' : '股价在 MA20 下方，中短期偏空';
    },
  },
  boll_upper: {
    label: '布林上轨',
    description: '布林带上边界（中轨 + 2 倍标准差）。股价触及上轨表示涨幅较大，可能有回调压力',
    interpret: (v, all) => {
      const p = all.current_price;
      if (p == null) return '';
      const pct = ((v - p) / p * 100).toFixed(1);
      return p >= v ? '股价已触及布林上轨，注意压力' : `距上轨 ${pct}%`;
    },
  },
  boll_lower: {
    label: '布林下轨',
    description: '布林带下边界（中轨 - 2 倍标准差）。股价触及下轨表示跌幅较大，可能获得支撑',
    interpret: (v, all) => {
      const p = all.current_price;
      if (p == null) return '';
      const pct = ((p - v) / p * 100).toFixed(1);
      return p <= v ? '股价已触及布林下轨，可能获得支撑' : `距下轨 ${pct}%`;
    },
  },
};
