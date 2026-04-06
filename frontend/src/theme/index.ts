import { theme } from 'antd';
import type { ThemeConfig } from 'antd';

// ==================== 语义色常量 ====================
export const COLORS = {
  // A 股惯例
  stockUp: '#ef5350',     // 上涨/买入/盈利 = 红
  stockDown: '#26a69a',   // 下跌/卖出/亏损 = 绿
  stockFlat: '#8b949e',   // 持平/持有/中性

  // 品牌 & 强调
  primary: '#4dabf7',
  warning: '#e8b339',

  // 背景层级
  bgPage: '#0d1117',
  bgSurface: '#161b22',
  bgContainer: '#1c2128',
  bgElevated: '#262c36',

  // 文字
  textPrimary: '#e6edf3',
  textSecondary: '#8b949e',
  textMuted: '#484f58',

  // 边框
  border: '#30363d',
  borderSubtle: '#21262d',
};

// ==================== Ant Design 深色主题配置 ====================
export const darkThemeConfig: ThemeConfig = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: COLORS.primary,
    colorBgContainer: COLORS.bgContainer,
    colorBgElevated: COLORS.bgElevated,
    colorBgLayout: COLORS.bgPage,
    colorBorder: COLORS.border,
    colorBorderSecondary: COLORS.borderSubtle,
    colorText: COLORS.textPrimary,
    colorTextSecondary: COLORS.textSecondary,
    colorTextTertiary: COLORS.textMuted,
    colorBgBase: COLORS.bgPage,
    borderRadius: 6,
  },
  components: {
    Layout: {
      siderBg: COLORS.bgPage,
      headerBg: COLORS.bgSurface,
      bodyBg: COLORS.bgPage,
    },
    Menu: {
      darkItemBg: 'transparent',
      darkItemSelectedBg: COLORS.borderSubtle,
      darkItemHoverBg: COLORS.bgContainer,
    },
    Table: {
      headerBg: COLORS.bgSurface,
      rowHoverBg: COLORS.bgElevated,
      borderColor: COLORS.borderSubtle,
    },
    Card: {
      colorBgContainer: COLORS.bgContainer,
    },
    Modal: {
      contentBg: COLORS.bgContainer,
      headerBg: COLORS.bgContainer,
    },
    Input: {
      colorBgContainer: COLORS.bgSurface,
    },
    Select: {
      colorBgContainer: COLORS.bgSurface,
    },
  },
};

// ==================== ECharts 深色图表基础选项 ====================
export const chartDarkOption = {
  backgroundColor: 'transparent',
  textStyle: { color: COLORS.textSecondary },
  tooltip: {
    backgroundColor: COLORS.bgElevated,
    borderColor: COLORS.border,
    textStyle: { color: COLORS.textPrimary },
  },
  legend: {
    textStyle: { color: COLORS.textSecondary },
    inactiveColor: COLORS.textMuted,
  },
  axisStyles: {
    axisLine: { lineStyle: { color: COLORS.border } },
    axisLabel: { color: COLORS.textSecondary },
    splitLine: { lineStyle: { color: COLORS.borderSubtle } },
  },
  dataZoomStyles: {
    backgroundColor: COLORS.bgSurface,
    borderColor: COLORS.border,
    fillerColor: 'rgba(77,171,247,0.15)',
    handleStyle: { color: COLORS.primary },
    textStyle: { color: COLORS.textSecondary },
    dataBackground: {
      lineStyle: { color: COLORS.border },
      areaStyle: { color: COLORS.borderSubtle },
    },
  },
  // 均线颜色（深色背景下高对比度）
  maColors: {
    ma5: '#e6b422',
    ma10: '#4dabf7',
    ma20: '#da70d6',
    ma60: '#ff8c42',
  },
};
