import { useState, useEffect } from 'react';
import { Card, Descriptions, Tag, Typography, Spin, Alert, Space, Button, message } from 'antd';
import { CheckCircleOutlined, CloseCircleOutlined, ReloadOutlined } from '@ant-design/icons';
import { getLLMStatus, reloadLLMConfig } from '../services/api';
import type { LLMStatus } from '../types';
import { COLORS } from '../theme';

const { Title, Text } = Typography;

export default function SettingsPage() {
  const [loading, setLoading] = useState(false);
  const [reloading, setReloading] = useState(false);
  const [status, setStatus] = useState<LLMStatus | null>(null);
  const [error, setError] = useState('');

  const fetchStatus = () => {
    setLoading(true);
    getLLMStatus()
      .then(setStatus)
      .catch((e) => setError(e instanceof Error ? e.message : '获取 LLM 状态失败'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleReload = async () => {
    setReloading(true);
    try {
      const newStatus = await reloadLLMConfig();
      setStatus(newStatus);
      message.success(newStatus.available ? 'LLM 配置已重新加载，AI 功能可用' : 'LLM 配置已重新加载，但 AI 功能不可用');
    } catch {
      message.error('重新加载失败');
    } finally {
      setReloading(false);
    }
  };

  return (
    <Space direction="vertical" style={{ width: '100%' }} size={16}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={4} style={{ margin: 0 }}>AI 设置</Title>
        <Button
          type="primary"
          icon={<ReloadOutlined />}
          onClick={handleReload}
          loading={reloading}
        >
          重新加载配置
        </Button>
      </div>

      {error && <Alert type="error" message={error} showIcon />}

      <Spin spinning={loading}>
        {status && (
          <Card title="LLM 配置状态">
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="启用状态">
                {status.enabled ? (
                  <Tag icon={<CheckCircleOutlined />} color="success">已启用</Tag>
                ) : (
                  <Tag icon={<CloseCircleOutlined />} color="error">未启用</Tag>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="可用性">
                {status.available ? (
                  <Tag color="success">可用</Tag>
                ) : (
                  <Tag color="warning">不可用 (API Key 未配置或已禁用)</Tag>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="供应商">
                <Text>{status.provider}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="API Key">
                <Text code>{status.api_key || '(空)'}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Base URL">
                <Text copyable>{status.base_url}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="模型">
                <Text>{status.model}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Temperature">
                <Text>{status.temperature}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Max Tokens">
                <Text>{status.max_tokens}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Timeout">
                <Text>{status.timeout}s</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Thinking 模式">
                {status.enable_thinking ? (
                  <Tag color="blue">已开启</Tag>
                ) : (
                  <Tag>已关闭</Tag>
                )}
              </Descriptions.Item>
            </Descriptions>
          </Card>
        )}
      </Spin>

      <Card title="配置说明" style={{ background: COLORS.bgSurface }}>
        <Typography>
          <Typography.Paragraph>
            LLM 配置通过后端 <Text code>.env</Text> 文件管理。修改后点击上方「重新加载配置」按钮即可生效，无需重启后端。
          </Typography.Paragraph>
          <Typography.Paragraph>
            主要配置项:
          </Typography.Paragraph>
          <ul style={{ color: COLORS.textSecondary }}>
            <li><Text code>LLM_ENABLED</Text> - 是否启用 AI 分析 (true/false)</li>
            <li><Text code>LLM_API_KEY</Text> - API 密钥</li>
            <li><Text code>LLM_BASE_URL</Text> - API 地址 (支持 DeepSeek/Moonshot/GLM/Qwen/OpenAI)</li>
            <li><Text code>LLM_MODEL</Text> - 模型名称</li>
            <li><Text code>LLM_TEMPERATURE</Text> - 生成温度 (0.0-1.0)</li>
            <li><Text code>LLM_ENABLE_THINKING</Text> - 是否启用推理模式 (true/false)，Qwen3 等推理模型关闭后响应更快</li>
          </ul>
          <Typography.Paragraph>
            参考 <Text code>backend/.env.example</Text> 获取完整配置模板。
          </Typography.Paragraph>
        </Typography>
      </Card>
    </Space>
  );
}
