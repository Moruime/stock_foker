import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Layout,
  Menu,
  Input,
  Select,
  AutoComplete,
  Space,
  Typography,
  Button,
  message,
} from 'antd';
import type { InputRef } from 'antd';
import {
  LineChartOutlined,
  UnorderedListOutlined,
  UserOutlined,
  SearchOutlined,
  StarOutlined,
  StarFilled,
  CloseOutlined,
  SwapOutlined,
  MessageOutlined,
  AppstoreOutlined,
  GlobalOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  searchStocks,
  getFocusStock,
  setFocusStock,
  updateTimeFrame,
  getFocusHistory,
} from '../services/api';
import type { FocusStock, StockSearchResult } from '../types';
import { COLORS } from '../theme';

const { Header, Content, Sider } = Layout;
const { Text, Title } = Typography;

const menuItems = [
  { key: '/analysis', icon: <LineChartOutlined />, label: '行情分析' },
  { key: '/sentiment', icon: <MessageOutlined />, label: '消息面' },
  { key: '/sector', icon: <AppstoreOutlined />, label: '板块联动' },
  { key: '/macro', icon: <GlobalOutlined />, label: '宏观环境' },
  { key: '/trades', icon: <UnorderedListOutlined />, label: '操作记录' },
  { key: '/profile', icon: <UserOutlined />, label: '炒股画像' },
  { key: '/settings', icon: <SettingOutlined />, label: 'AI 设置' },
];

export default function MainLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [focus, setFocus] = useState<FocusStock | null>(null);
  const [watchlist, setWatchlist] = useState<FocusStock[]>([]);
  const [searchValue, setSearchValue] = useState('');
  const [searchExpanded, setSearchExpanded] = useState(false);
  const [searchOptions, setSearchOptions] = useState<
    { value: string; label: string; data: StockSearchResult }[]
  >([]);
  const [pendingStock, setPendingStock] = useState<StockSearchResult | null>(null);
  const searchInputRef = useRef<InputRef>(null);

  const loadWatchlist = useCallback(async () => {
    try {
      const history = await getFocusHistory();
      const seen = new Set<string>();
      const unique = history.filter((s) => {
        if (seen.has(s.stock_code)) return false;
        seen.add(s.stock_code);
        return true;
      });
      setWatchlist(unique);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    getFocusStock().then((data) => {
      if (data) setFocus(data);
    });
    loadWatchlist();
  }, [loadWatchlist]);

  const expandSearch = useCallback(() => {
    setSearchExpanded(true);
    setTimeout(() => {
      searchInputRef.current?.focus();
    }, 100);
  }, []);

  const collapseSearch = useCallback(() => {
    setSearchExpanded(false);
    setSearchValue('');
    setSearchOptions([]);
  }, []);

  const handleSearch = useCallback(async (value: string) => {
    if (!value || value.length < 1) {
      setSearchOptions([]);
      return;
    }
    try {
      const results = await searchStocks(value);
      setSearchOptions(
        results.map((s) => ({
          value: `${s.stock_code} ${s.stock_name}`,
          label: `${s.stock_code} - ${s.stock_name}`,
          data: s,
        })),
      );
    } catch {
      setSearchOptions([]);
    }
  }, []);

  const handleSearchSelect = (_: string, option: (typeof searchOptions)[0]) => {
    setPendingStock(option.data);
    setSearchValue('');
    setSearchOptions([]);
    setSearchExpanded(false);
  };

  const handleAddToWatchlist = async () => {
    if (!pendingStock) return;
    try {
      const result = await setFocusStock({
        stock_code: pendingStock.stock_code,
        stock_name: pendingStock.stock_name,
        time_frame: focus?.time_frame || 'short',
      });
      setFocus(result);
      setPendingStock(null);
      await loadWatchlist();
      message.success(`已关注 ${result.stock_name}(${result.stock_code})`);
    } catch {
      message.error('添加关注失败');
    }
  };

  const handleViewOnly = () => {
    if (!pendingStock) return;
    setFocus({
      id: 0,
      stock_code: pendingStock.stock_code,
      stock_name: pendingStock.stock_name,
      time_frame: (focus?.time_frame || 'short') as FocusStock['time_frame'],
      is_active: 0,
      created_at: '',
    });
    setPendingStock(null);
  };

  const handleDismissPending = () => {
    setPendingStock(null);
  };

  const handleSwitchStock = async (stockCode: string) => {
    const target = watchlist.find((s) => s.stock_code === stockCode);
    if (!target) return;
    try {
      const result = await setFocusStock({
        stock_code: target.stock_code,
        stock_name: target.stock_name,
        time_frame: focus?.time_frame || 'short',
      });
      setFocus(result);
      await loadWatchlist();
    } catch {
      message.error('切换失败');
    }
  };

  const handleTimeFrameChange = async (value: string) => {
    try {
      const result = await updateTimeFrame(value);
      setFocus(result);
    } catch {
      message.error('更新时间框架失败');
    }
  };

  const watchlistOptions = watchlist.map((s) => ({
    value: s.stock_code,
    label: `${s.stock_name} (${s.stock_code})`,
  }));

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider theme="dark" width={180}>
        <div style={{ padding: '16px 12px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
          <img src="/logo.png" alt="Stock Foker" style={{ width: 32, height: 32 }} />
          <span style={{ fontWeight: 'bold', fontSize: 16, color: COLORS.textPrimary }}>Stock Foker</span>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: COLORS.bgSurface,
            padding: '0 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: `1px solid ${COLORS.borderSubtle}`,
            height: 64,
          }}
        >
          {/* 左侧：当前股票醒目显示 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, flex: 1, minWidth: 0 }}>
            {focus ? (
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                <Title
                  level={4}
                  style={{ margin: 0, fontSize: 22, lineHeight: '32px', whiteSpace: 'nowrap' }}
                >
                  {focus.stock_name}
                </Title>
                <Text
                  type="secondary"
                  style={{ fontSize: 15, whiteSpace: 'nowrap' }}
                >
                  {focus.stock_code}
                </Text>
                <Select
                  value={focus.time_frame}
                  onChange={handleTimeFrameChange}
                  size="small"
                  variant="borderless"
                  style={{ marginLeft: 4 }}
                  options={[
                    { value: 'short', label: '短线' },
                    { value: 'medium', label: '中线' },
                    { value: 'long', label: '长线' },
                  ]}
                />
              </div>
            ) : (
              <Text type="secondary" style={{ fontSize: 15 }}>
                请搜索并关注一支股票开始分析
              </Text>
            )}

            {/* 搜索后的待确认提示 */}
            {pendingStock && (
              <Space
                size="small"
                style={{
                  background: 'rgba(38,166,154,0.1)',
                  border: '1px solid rgba(38,166,154,0.3)',
                  borderRadius: 6,
                  padding: '4px 12px',
                  marginLeft: 8,
                  whiteSpace: 'nowrap',
                }}
              >
                <Text strong style={{ fontSize: 13 }}>
                  {pendingStock.stock_name} ({pendingStock.stock_code})
                </Text>
                <Button
                  type="primary"
                  size="small"
                  icon={<StarOutlined />}
                  onClick={handleAddToWatchlist}
                >
                  加入关注
                </Button>
                <Button size="small" onClick={handleViewOnly}>
                  仅查看
                </Button>
                <Button size="small" type="text" onClick={handleDismissPending}>
                  取消
                </Button>
              </Space>
            )}
          </div>

          {/* 右侧：关注列表切换 + 搜索按钮 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
            {/* 关注列表切换 */}
            {watchlist.length > 1 && (
              <Space size={4}>
                <SwapOutlined style={{ color: COLORS.textSecondary, fontSize: 13 }} />
                <Select
                  value={focus?.stock_code}
                  options={watchlistOptions}
                  onChange={handleSwitchStock}
                  style={{ width: 160 }}
                  size="small"
                  placeholder="切换股票"
                  suffixIcon={<StarFilled style={{ color: COLORS.warning }} />}
                />
              </Space>
            )}

            {/* 搜索：收缩/展开 */}
            {searchExpanded ? (
              <Space size={4}>
                <AutoComplete
                  style={{ width: 240 }}
                  options={searchOptions}
                  onSearch={handleSearch}
                  onSelect={handleSearchSelect}
                  value={searchValue}
                  onChange={setSearchValue}
                  placeholder="搜索股票代码或名称"
                  onBlur={() => {
                    // 延迟关闭，避免下拉选项点击不到
                    setTimeout(() => {
                      if (!searchValue && !pendingStock) {
                        collapseSearch();
                      }
                    }, 200);
                  }}
                >
                  <Input
                    ref={searchInputRef}
                    placeholder="搜索股票代码或名称"
                    suffix={<SearchOutlined style={{ color: COLORS.textSecondary }} />}
                    allowClear
                  />
                </AutoComplete>
                <Button
                  type="text"
                  size="small"
                  icon={<CloseOutlined />}
                  onClick={collapseSearch}
                />
              </Space>
            ) : (
              <Button
                type="text"
                icon={<SearchOutlined />}
                onClick={expandSearch}
                style={{ fontSize: 16 }}
              />
            )}
          </div>
        </Header>
        <Content style={{ margin: 16, padding: 24, background: COLORS.bgContainer, borderRadius: 8 }}>
          <Outlet context={{ focus }} />
        </Content>
      </Layout>
    </Layout>
  );
}
