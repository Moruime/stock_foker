import { useState, useEffect, useCallback } from 'react';
import {
  Layout,
  Menu,
  Input,
  Select,
  AutoComplete,
  Space,
  Typography,
  Tag,
  message,
} from 'antd';
import {
  LineChartOutlined,
  UnorderedListOutlined,
  UserOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  searchStocks,
  getFocusStock,
  setFocusStock,
  updateTimeFrame,
} from '../services/api';
import type { FocusStock, StockSearchResult } from '../types';

const { Header, Content, Sider } = Layout;
const { Text } = Typography;

const timeFrameOptions = [
  { value: 'short', label: '短线' },
  { value: 'medium', label: '中线' },
  { value: 'long', label: '长线' },
];

const menuItems = [
  { key: '/analysis', icon: <LineChartOutlined />, label: '行情分析' },
  { key: '/trades', icon: <UnorderedListOutlined />, label: '操作记录' },
  { key: '/profile', icon: <UserOutlined />, label: '炒股画像' },
];

export default function MainLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const [focus, setFocus] = useState<FocusStock | null>(null);
  const [searchOptions, setSearchOptions] = useState<
    { value: string; label: string; data: StockSearchResult }[]
  >([]);

  useEffect(() => {
    getFocusStock().then((data) => {
      if (data) setFocus(data);
    });
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

  const handleSelect = async (_: string, option: (typeof searchOptions)[0]) => {
    try {
      const result = await setFocusStock({
        stock_code: option.data.stock_code,
        stock_name: option.data.stock_name,
        time_frame: focus?.time_frame || 'short',
      });
      setFocus(result);
      message.success(`已关注 ${result.stock_name}(${result.stock_code})`);
    } catch {
      message.error('设置关注失败');
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

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider theme="light" width={180}>
        <div style={{ padding: '16px', textAlign: 'center', fontWeight: 'bold', fontSize: 18 }}>
          Stock Foker
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
            background: '#fff',
            padding: '0 24px',
            display: 'flex',
            alignItems: 'center',
            gap: 16,
            borderBottom: '1px solid #f0f0f0',
          }}
        >
          <AutoComplete
            style={{ width: 300 }}
            options={searchOptions}
            onSearch={handleSearch}
            onSelect={handleSelect}
            placeholder="搜索股票代码或名称..."
          >
            <Input prefix={<SearchOutlined />} allowClear />
          </AutoComplete>

          {focus && (
            <Space size="middle">
              <Tag color="blue" style={{ fontSize: 14, padding: '4px 12px' }}>
                {focus.stock_name} ({focus.stock_code})
              </Tag>
              <Space>
                <Text type="secondary">时间框架:</Text>
                <Select
                  value={focus.time_frame}
                  options={timeFrameOptions}
                  onChange={handleTimeFrameChange}
                  style={{ width: 90 }}
                  size="small"
                />
              </Space>
            </Space>
          )}
          {!focus && <Text type="secondary">请搜索并选择一支股票开始分析</Text>}
        </Header>
        <Content style={{ margin: 16, padding: 24, background: '#fff', borderRadius: 8 }}>
          <Outlet context={{ focus }} />
        </Content>
      </Layout>
    </Layout>
  );
}
