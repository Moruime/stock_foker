import { useState, useEffect } from 'react';
import { useOutletContext } from 'react-router-dom';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  DatePicker,
  Radio,
  Tag,
  Space,
  Empty,
  message,
  Popconfirm,
  Typography,
} from 'antd';
import { PlusOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import {
  getTradeRecords,
  createTradeRecord,
  updateTradeRecord,
  deleteTradeRecord,
} from '../services/api';
import type { FocusStock, TradeRecord } from '../types';
import PositionCard from '../components/PositionCard';

export default function TradesPage() {
  const { focus } = useOutletContext<{ focus: FocusStock | null }>();
  const [records, setRecords] = useState<TradeRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editRecord, setEditRecord] = useState<TradeRecord | null>(null);
  const [form] = Form.useForm();
  const [editForm] = Form.useForm();
  const [positionKey, setPositionKey] = useState(0);

  const loadRecords = () => {
    setLoading(true);
    getTradeRecords(focus?.stock_code)
      .then(setRecords)
      .catch(() => message.error('加载交易记录失败'))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadRecords();
  }, [focus]);

  const handleCreate = async () => {
    let values;
    try {
      values = await form.validateFields();
    } catch {
      return;
    }
    try {
      await createTradeRecord({
        ...values,
        stock_code: focus?.stock_code || values.stock_code,
        stock_name: focus?.stock_name || values.stock_name,
        traded_at: values.traded_at.toISOString(),
      });
      message.success('记录已添加');
      setModalOpen(false);
      form.resetFields();
      loadRecords();
      if (values.record_mode === 'realtime') {
        setPositionKey((k) => k + 1);
      }
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      message.error(detail || '操作失败，请重试');
    }
  };

  const handleEdit = async () => {
    if (!editRecord) return;
    let values;
    try {
      values = await editForm.validateFields();
    } catch {
      return;
    }
    try {
      const payload: Record<string, unknown> = { ...values };
      if (values.traded_at) {
        payload.traded_at = values.traded_at.toISOString();
      }
      await updateTradeRecord(editRecord.id, payload);
      message.success('记录已更新');
      setEditRecord(null);
      editForm.resetFields();
      loadRecords();
      setPositionKey((k) => k + 1);
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      message.error(detail || '更新失败，请重试');
    }
  };

  const handleDelete = async (id: number) => {
    await deleteTradeRecord(id);
    message.success('已删除');
    loadRecords();
  };

  const columns = [
    {
      title: '日期',
      dataIndex: 'traded_at',
      key: 'traded_at',
      width: 110,
      render: (v: string) => dayjs(v).format('YYYY-MM-DD'),
    },
    {
      title: '股票',
      key: 'stock',
      width: 140,
      render: (_: unknown, r: TradeRecord) => `${r.stock_name}(${r.stock_code})`,
    },
    {
      title: '类型',
      dataIndex: 'trade_type',
      key: 'trade_type',
      width: 120,
      render: (v: string, r: TradeRecord) => (
        <Space size={4}>
          <Tag color={v === 'buy' ? 'red' : 'green'}>{v === 'buy' ? '买入' : '卖出'}</Tag>
          {r.record_mode === 'backfill' && <Tag style={{ fontSize: 11 }}>补录</Tag>}
        </Space>
      ),
    },
    { title: '价格', dataIndex: 'price', key: 'price', width: 80 },
    { title: '数量', dataIndex: 'quantity', key: 'quantity', width: 80 },
    { title: '理由', dataIndex: 'reason', key: 'reason', ellipsis: true },
    {
      title: '情绪判断',
      dataIndex: 'market_sentiment',
      key: 'market_sentiment',
      width: 90,
      render: (v: string) => {
        if (!v) return '-';
        const map: Record<string, { color: string; text: string }> = {
          optimistic: { color: 'red', text: '乐观' },
          neutral: { color: 'default', text: '中性' },
          pessimistic: { color: 'green', text: '悲观' },
        };
        return <Tag color={map[v]?.color}>{map[v]?.text}</Tag>;
      },
    },
    {
      title: '实际盈亏',
      dataIndex: 'actual_result',
      key: 'actual_result',
      width: 100,
      render: (v: number | null) => {
        if (v == null) return <Tag>未结算</Tag>;
        return <Tag color={v >= 0 ? 'red' : 'green'}>{v >= 0 ? '+' : ''}{v.toFixed(2)}</Tag>;
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: unknown, record: TradeRecord) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => {
              setEditRecord(record);
              editForm.setFieldsValue({
                trade_type: record.trade_type,
                price: record.price,
                quantity: record.quantity,
                traded_at: dayjs(record.traded_at),
                reason: record.reason,
                market_sentiment: record.market_sentiment,
                target_price: record.target_price,
                expected_hold_days: record.expected_hold_days,
                actual_result: record.actual_result,
                result_note: record.result_note,
              });
            }}
          >
            编辑
          </Button>
          <Popconfirm title="确认删除?" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Typography.Title level={5} style={{ margin: 0 }}>交易操作记录</Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          新增记录
        </Button>
      </div>

      {focus && (
        <PositionCard key={positionKey} stockCode={focus.stock_code} stockName={focus.stock_name} />
      )}

      {records.length === 0 && !loading ? (
        <Empty description="暂无交易记录" />
      ) : (
        <Table
          dataSource={records}
          columns={columns}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={{ pageSize: 20 }}
        />
      )}

      {/* 新增记录弹窗 */}
      <Modal
        title="新增交易记录"
        open={modalOpen}
        onOk={handleCreate}
        onCancel={() => setModalOpen(false)}
        width={600}
      >
        <Form form={form} layout="vertical" initialValues={{ record_mode: 'realtime' }}>
          <Form.Item name="record_mode" label="记录类型">
            <Radio.Group>
              <Radio.Button value="realtime">实时交易</Radio.Button>
              <Radio.Button value="backfill">历史补录</Radio.Button>
            </Radio.Group>
          </Form.Item>
          {!focus && (
            <>
              <Form.Item name="stock_code" label="股票代码" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
              <Form.Item name="stock_name" label="股票名称" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
            </>
          )}
          <Form.Item name="trade_type" label="操作类型" rules={[{ required: true }]}>
            <Select options={[{ value: 'buy', label: '买入' }, { value: 'sell', label: '卖出' }]} />
          </Form.Item>
          <Form.Item name="price" label="成交价格" rules={[{ required: true }]}>
            <InputNumber style={{ width: '100%' }} min={0} step={0.01} />
          </Form.Item>
          <Form.Item name="quantity" label="成交数量" rules={[{ required: true }]}>
            <InputNumber style={{ width: '100%' }} min={1} step={100} />
          </Form.Item>
          <Form.Item name="traded_at" label="成交日期" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="reason" label="买入/卖出理由">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="market_sentiment" label="当时市场情绪判断">
            <Select
              allowClear
              options={[
                { value: 'optimistic', label: '乐观' },
                { value: 'neutral', label: '中性' },
                { value: 'pessimistic', label: '悲观' },
              ]}
            />
          </Form.Item>
          <Form.Item name="target_price" label="目标价位">
            <InputNumber style={{ width: '100%' }} min={0} step={0.01} />
          </Form.Item>
          <Form.Item name="expected_hold_days" label="预期持有天数">
            <InputNumber style={{ width: '100%' }} min={1} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑记录弹窗 */}
      <Modal
        title="编辑交易记录"
        open={!!editRecord}
        onOk={handleEdit}
        onCancel={() => { setEditRecord(null); editForm.resetFields(); }}
        width={600}
        destroyOnClose
      >
        <Form form={editForm} layout="vertical">
          <Form.Item name="trade_type" label="操作类型" rules={[{ required: true }]}>
            <Select options={[{ value: 'buy', label: '买入' }, { value: 'sell', label: '卖出' }]} />
          </Form.Item>
          <Form.Item name="price" label="成交价格" rules={[{ required: true }]}>
            <InputNumber style={{ width: '100%' }} min={0} step={0.01} />
          </Form.Item>
          <Form.Item name="quantity" label="成交数量" rules={[{ required: true }]}>
            <InputNumber style={{ width: '100%' }} min={1} step={100} />
          </Form.Item>
          <Form.Item name="traded_at" label="成交日期" rules={[{ required: true }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="reason" label="买入/卖出理由">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="market_sentiment" label="当时市场情绪判断">
            <Select
              allowClear
              options={[
                { value: 'optimistic', label: '乐观' },
                { value: 'neutral', label: '中性' },
                { value: 'pessimistic', label: '悲观' },
              ]}
            />
          </Form.Item>
          <Form.Item name="target_price" label="目标价位">
            <InputNumber style={{ width: '100%' }} min={0} step={0.01} />
          </Form.Item>
          <Form.Item name="expected_hold_days" label="预期持有天数">
            <InputNumber style={{ width: '100%' }} min={1} />
          </Form.Item>
          <Form.Item name="actual_result" label="实际盈亏金额">
            <InputNumber style={{ width: '100%' }} step={0.01} />
          </Form.Item>
          <Form.Item name="result_note" label="结果备注">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
