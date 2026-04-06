# Stock Foker - 深色主题改造方案

## 背景

当前 UI 使用 Ant Design 默认亮色主题（白色背景、蓝色主色），风格偏通用，不符合股票分析/量化交易类应用的专业审美。目标是实现类似 TradingView/Bloomberg 终端的深色主题，适合长时间看盘，并统一遵循 A 股红涨绿跌的配色惯例。

## 配色方案

### 背景色（4 层级）

| 层级 | 色值 | 用途 |
|------|------|------|
| 0 | `#0d1117` | 应用底色、侧边栏 |
| 1 | `#161b22` | 头部、输入框背景 |
| 2 | `#1c2128` | 卡片、内容区 |
| 3 | `#262c36` | 提示框、悬浮、弹窗 |

### 文字与边框

| 用途 | 色值 |
|------|------|
| 主文字 | `#e6edf3` |
| 次要文字 | `#8b949e` |
| 禁用/占位文字 | `#484f58` |
| 主边框 | `#30363d` |
| 次边框 | `#21262d` |

### 语义色（A 股惯例）

| 含义 | 色值 | 说明 |
|------|------|------|
| 品牌主色 | `#4dabf7` | 深色背景下更柔和的蓝 |
| 上涨/买入/盈利 | `#ef5350` | 红色 = 正面（A 股） |
| 下跌/卖出/亏损 | `#26a69a` | 绿色 = 负面（A 股） |
| 警告/星标 | `#e8b339` | 金色点缀 |

## 实施步骤

### 第 1 步：新建 `frontend/src/theme/index.ts`

集中管理主题配置，导出：

- `darkThemeConfig` — Ant Design ConfigProvider 的 theme 对象，使用 `theme.darkAlgorithm` + 上述色值覆盖
- `COLORS` — 语义色常量，供各组件内联样式引用
- `chartDarkOption` — ECharts 深色图表基础配置（tooltip、坐标轴、dataZoom 样式）

组件级 token 覆盖：
- Layout：siderBg `#0d1117`，headerBg `#161b22`
- Table：headerBg `#161b22`，rowHoverBg `#262c36`
- Card/Modal/Input/Select：深色容器背景
- Menu：深色菜单项背景

### 第 2 步：新建 `frontend/src/styles/global.css`

ConfigProvider 无法控制的全局样式：
- `body { background: #0d1117; }` — 防止页面加载时白色闪烁
- 深色滚动条样式（`::-webkit-scrollbar`）
- `::selection` 选中色

### 第 3 步：修改 `frontend/src/main.tsx`

新增：`import './styles/global.css'`

### 第 4 步：修改 `frontend/src/App.tsx`

- 导入 `darkThemeConfig`
- 替换 `theme={{ token: { colorPrimary: '#1677ff' } }}` 为 `theme={darkThemeConfig}`
- 仅此一步即可让约 80% 的组件自动变为深色

### 第 5 步：修改 `frontend/src/components/MainLayout.tsx`

替换 7 处硬编码的亮色内联样式：
- 侧边栏：`theme="light"` -> `theme="dark"`
- 头部背景：`#fff` -> `COLORS.bgSurface`
- 头部边框：`#f0f0f0` -> `COLORS.borderSubtle`
- 内容区背景：`#fff` -> `COLORS.bgContainer`
- 待确认提示框：绿色背景 -> 半透明深绿 `rgba(38,166,154,0.1)`
- 图标颜色：使用 `COLORS.textSecondary` / `COLORS.warning`

### 第 6 步：修改 `frontend/src/pages/AnalysisPage.tsx`

ECharts 深色适配 + A 股配色修正：
- 将 `chartDarkOption` 合并入 klineOption（深色 tooltip、坐标轴、网格线、dataZoom）
- K 线颜色：从 `COLORS` 引用（当前已正确：红涨绿跌）
- 均线颜色：金/蓝/紫/橙，确保深色背景下清晰可辨
- **修复 BUG**：信号标签 `buy -> 'red'`，`sell -> 'green'`（当前是反的）

### 第 7 步：修改 `frontend/src/pages/TradesPage.tsx`

- 将裸 `<h3>` 替换为 `<Typography.Title level={5}>`，继承深色文字
- **修复 A 股配色**：盈亏标签 — 盈利 -> 红色，亏损 -> 绿色（当前是反的）

### 第 8 步：修改 `frontend/src/pages/ProfilePage.tsx`

- 将裸 `<h3>` 替换为 `<Typography.Title level={5}>`
- **修复**：胜率/盈亏比的 Statistic 组件：好 -> `COLORS.stockUp`（红），差 -> `COLORS.stockDown`（绿）
- Progress 进度条：设置 `strokeColor` 和 `trailColor` 适配深色
- **修复**：平均盈利/亏损标签颜色遵循 A 股惯例

## 涉及文件

| 文件 | 操作 |
|------|------|
| `frontend/src/theme/index.ts` | 新建 — 集中主题配置 |
| `frontend/src/styles/global.css` | 新建 — body 背景、滚动条 |
| `frontend/src/main.tsx` | 导入 global.css |
| `frontend/src/App.tsx` | 应用 darkThemeConfig |
| `frontend/src/components/MainLayout.tsx` | 替换 7 处内联颜色 |
| `frontend/src/pages/AnalysisPage.tsx` | ECharts 深色 + 修复信号标签色 |
| `frontend/src/pages/TradesPage.tsx` | 修复标题 + 盈亏标签色 |
| `frontend/src/pages/ProfilePage.tsx` | 修复标题 + 统计色 + 进度条 |

## A 股配色修正（共 8 处颠倒）

| 元素 | 所在文件 | 当前颜色 | 正确颜色 |
|------|----------|----------|----------|
| 买入信号标签 | AnalysisPage | 绿色 | **红色** |
| 卖出信号标签 | AnalysisPage | 红色 | **绿色** |
| 盈利标签 | TradesPage | 绿色 | **红色** |
| 亏损标签 | TradesPage | 红色 | **绿色** |
| 高胜率数值 | ProfilePage | 绿色 | **红色** |
| 低胜率数值 | ProfilePage | 红色 | **绿色** |
| 高盈亏比数值 | ProfilePage | 绿色 | **红色** |
| 低盈亏比数值 | ProfilePage | 红色 | **绿色** |

## 验证方式

1. `npx tsc --noEmit` — TypeScript 类型检查通过
2. `npx vite build` — 构建成功
3. 启动 dev server 逐页验证：
   - MainLayout：深色侧边栏、头部、内容区
   - AnalysisPage：K 线图深色背景、均线清晰、tooltip 深色
   - TradesPage：表格深色、标签颜色正确
   - ProfilePage：统计卡片深色、进度条颜色正确
4. 确认页面加载无白色闪烁
5. 确认滚动条为深色风格
