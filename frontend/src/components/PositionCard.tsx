import { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Button,
  Modal,
  Form,
  InputNumber,
  DatePicker,
  Input,
  Descriptions,
  Tag,
  Space,
  Popconfirm,
  message,
  Statistic,
  Row,
  Col,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import {
  getPosition,
  createPosition,
  updatePosition,
  deletePosition,
} from '../services/api';
import type { Position, PositionCreate, PositionUpdate } from '../types';
import { COLORS } from '../theme';

interface PositionCardProps {
  stockCode: string;
  stockName: string;
  currentPrice?: number;
}

export default function PositionCard({ stockCode, stockName, currentPrice }: PositionCardProps) {
  const [position, setPosition] = useState<Position | null>(null);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [isEdit, setIsEdit] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  const loadPosition = useCallback(() => {
    if (!stockCode) return;
    setLoading(true);
    getPosition(stockCode)
      .then(setPosition)
      .catch(() => setPosition(null))
      .finally(() => setLoading(false));
  }, [stockCode]);

  useEffect(() => {
    loadPosition();
  }, [loadPosition]);

  const handleSubmit = async () => {
    let values;
    try {
      values = await form.validateFields();
    } catch {
      return;
    }
    setSubmitting(true);
    try {
      if (isEdit) {
        const updateData: PositionUpdate = {
          cost_price: values.cost_price,
          quantity: values.quantity,
          take_profit_price: values.take_profit_price || undefined,
          stop_loss_price: values.stop_loss_price || undefined,
          note: values.note || undefined,
        };
        await updatePosition(stockCode, updateData);
        message.success('持仓已更新');
      } else {
        const createData: PositionCreate = {
          stock_code: stockCode,
          stock_name: stockName,
          cost_price: values.cost_price,
          quantity: values.quantity,
          first_buy_date: values.first_buy_date.format('YYYY-MM-DD'),
          take_profit_price: values.take_profit_price || undefined,
          stop_loss_price: values.stop_loss_price || undefined,
          note: values.note || undefined,
        };
        await createPosition(createData);
        message.success('持仓已添加');
      }
      setModalOpen(false);
      form.resetFields();
      loadPosition();
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      message.error(detail || '操作失败，请重试');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    await deletePosition(stockCode);
    message.success('持仓已删除');
    setPosition(null);
  };

  const openCreateModal = () => {
    setIsEdit(false);
    form.resetFields();
    setModalOpen(true);
  };

  const openEditModal = () => {
    if (!position) return;
    setIsEdit(true);
    form.setFieldsValue({
      cost_price: position.cost_price,
      quantity: position.quantity,
      first_buy_date: dayjs(position.first_buy_date),
      take_profit_price: position.take_profit_price,
      stop_loss_price: position.stop_loss_price,
      note: position.note,
    });
    setModalOpen(true);
  };

  // 计算持仓数据
  const calcPnl = () => {
    if (!position || !currentPrice) return null;
    const marketValue = currentPrice * position.quantity;
    const costTotal = position.cost_price * position.quantity;
    const pnl = marketValue - costTotal;
    const pnlPercent = ((currentPrice - position.cost_price) / position.cost_price) * 100;
    return { marketValue, pnl, pnlPercent };
  };

  const calcHoldDays = () => {
    if (!position) return 0;
    return dayjs().diff(dayjs(position.first_buy_date), 'day');
  };

  const pnlData = calcPnl();
  const holdDays = calcHoldDays();

  // 检查止盈止损预警
  const tpWarning =
    position?.take_profit_price && currentPrice && currentPrice >= position.take_profit_price;
  const slWarning =
    position?.stop_loss_price && currentPrice && currentPrice <= position.stop_loss_price;

  const modal = (
    <Modal
      title={isEdit ? '编辑持仓' : '添加持仓'}
      open={modalOpen}
      onOk={handleSubmit}
      onCancel={() => {
        setModalOpen(false);
        form.resetFields();
      }}
      width={500}
      confirmLoading={submitting}
      destroyOnClose
    >
      <Form form={form} layout="vertical">
        <Form.Item name="cost_price" label="成本价" rules={[{ required: true, message: '请输入成本价' }]}>
          <InputNumber style={{ width: '100%' }} min={0} step={0.001} precision={3} />
        </Form.Item>
        <Form.Item name="quantity" label="持仓数量" rules={[{ required: true, message: '请输入数量' }]}>
          <InputNumber style={{ width: '100%' }} min={1} step={100} />
        </Form.Item>
        {!isEdit && (
          <Form.Item
            name="first_buy_date"
            label="首次买入日期"
            rules={[{ required: true, message: '请选择日期' }]}
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
        )}
        <Form.Item name="take_profit_price" label="止盈价位">
          <InputNumber style={{ width: '100%' }} min={0} step={0.01} precision={2} />
        </Form.Item>
        <Form.Item name="stop_loss_price" label="止损价位">
          <InputNumber style={{ width: '100%' }} min={0} step={0.01} precision={2} />
        </Form.Item>
        <Form.Item name="note" label="备注">
          <Input.TextArea rows={2} />
        </Form.Item>
      </Form>
    </Modal>
  );

  if (!position) {
    return (
      <>
        <Card size="small" loading={loading} style={{ marginBottom: 16 }}>
          <div style={{ textAlign: 'center', padding: '8px 0' }}>
            <Button type="dashed" icon={<PlusOutlined />} onClick={openCreateModal}>
              添加持仓
            </Button>
          </div>
        </Card>
        {modal}
      </>
    );
  }

  return (
    <>
      <Card
        size="small"
        loading={loading}
        style={{ marginBottom: 16 }}
        title={
          <Space>
            <span>持仓信息</span>
            {tpWarning && <Tag color="red">触及止盈</Tag>}
            {slWarning && <Tag color="green">触及止损</Tag>}
          </Space>
        }
        extra={
          <Space>
            <Button type="text" size="small" icon={<EditOutlined />} onClick={openEditModal}>
              编辑
            </Button>
            <Popconfirm title="确认清除持仓记录？" onConfirm={handleDelete}>
              <Button type="text" size="small" danger icon={<DeleteOutlined />}>
                删除
              </Button>
            </Popconfirm>
          </Space>
        }
      >
        <Row gutter={16}>
          <Col span={4}>
            <Statistic
              title="成本价"
              value={position.cost_price}
              precision={3}
              valueStyle={{ fontSize: 16 }}
            />
          </Col>
          <Col span={4}>
            <Statistic title="持仓数量" value={position.quantity} valueStyle={{ fontSize: 16 }} />
          </Col>
          {pnlData && (
            <>
              <Col span={4}>
                <Statistic
                  title="市值"
                  value={pnlData.marketValue}
                  precision={2}
                  valueStyle={{ fontSize: 16 }}
                />
              </Col>
              <Col span={4}>
                <Statistic
                  title="浮动盈亏"
                  value={pnlData.pnl}
                  precision={2}
                  valueStyle={{
                    fontSize: 16,
                    color: pnlData.pnl >= 0 ? COLORS.stockUp : COLORS.stockDown,
                  }}
                  prefix={pnlData.pnl >= 0 ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
                  suffix={
                    <span style={{ fontSize: 12 }}>({pnlData.pnlPercent >= 0 ? '+' : ''}{pnlData.pnlPercent.toFixed(2)}%)</span>
                  }
                />
              </Col>
            </>
          )}
          <Col span={4}>
            <Statistic title="持有天数" value={holdDays} suffix="天" valueStyle={{ fontSize: 16 }} />
          </Col>
          <Col span={4}>
            <Descriptions column={1} size="small" style={{ marginTop: 0 }}>
              <Descriptions.Item label="止盈">
                {position.take_profit_price ? (
                  <span style={{ color: COLORS.stockUp }}>{position.take_profit_price.toFixed(2)}</span>
                ) : (
                  <span style={{ color: COLORS.textMuted }}>未设</span>
                )}
              </Descriptions.Item>
              <Descriptions.Item label="止损">
                {position.stop_loss_price ? (
                  <span style={{ color: COLORS.stockDown }}>{position.stop_loss_price.toFixed(2)}</span>
                ) : (
                  <span style={{ color: COLORS.textMuted }}>未设</span>
                )}
              </Descriptions.Item>
            </Descriptions>
          </Col>
        </Row>
        {position.note && (
          <div style={{ marginTop: 8, color: COLORS.textSecondary, fontSize: 12 }}>
            备注: {position.note}
          </div>
        )}
      </Card>
      {modal}
    </>
  );
}
