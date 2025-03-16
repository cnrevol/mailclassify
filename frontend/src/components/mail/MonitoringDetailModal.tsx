import React, { useEffect, useState, useRef, useCallback } from 'react';
import { Modal, Progress, Space, Typography, List, Switch, Card, Tag, Divider } from 'antd';
import { RobotOutlined, SyncOutlined, TeamOutlined } from '@ant-design/icons';
import { message } from 'antd';
import styled from 'styled-components';
import { useTheme } from '../../contexts/ThemeContext';

const { Title, Text } = Typography;

interface ThemeProps {
  $isDark: boolean;
}

// Styled components for theme support
const StyledModal = styled(Modal)<ThemeProps>`
  .ant-modal-content {
    background: ${(props: ThemeProps) => props.$isDark ? '#1f1f1f' : '#ffffff'};
    color: ${(props: ThemeProps) => props.$isDark ? '#ffffff' : '#000000'};
  }
  .ant-modal-header {
    background: ${(props: ThemeProps) => props.$isDark ? '#1f1f1f' : '#ffffff'};
  }
  .ant-modal-title {
    color: ${(props: ThemeProps) => props.$isDark ? '#ffffff' : '#000000'};
  }
`;

const StyledCard = styled(Card)<ThemeProps>`
  background: ${(props: ThemeProps) => props.$isDark ? '#141414' : '#f5f5f5'};
  border: 1px solid ${(props: ThemeProps) => props.$isDark ? '#303030' : '#e8e8e8'};
  margin-bottom: 8px;
`;

const LogsContainer = styled.div<ThemeProps>`
  height: 250px;
  overflow-y: auto;
  padding: 12px;
  background-color: ${(props: ThemeProps) => props.$isDark ? '#141414' : '#f5f5f5'};
  border-radius: 4px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  line-height: 1.4;
  color: ${(props: ThemeProps) => props.$isDark ? '#e1e1e1' : '#1f1f1f'};
  border: 1px solid ${(props: ThemeProps) => props.$isDark ? '#303030' : '#e8e8e8'};
`;

const CategoryItem = styled(List.Item)<ThemeProps>`
  padding: 8px !important;
  background: ${(props: ThemeProps) => props.$isDark ? '#1f1f1f' : '#ffffff'};
  border-radius: 4px;
  margin-bottom: 4px !important;
  border: 1px solid ${(props: ThemeProps) => props.$isDark ? '#303030' : '#e8e8e8'} !important;

  &:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, ${(props: ThemeProps) => props.$isDark ? '0.45' : '0.15'});
  }
`;

// 后端WebSocket服务器地址
const WS_BASE_URL = window.location.protocol === 'https:' 
  ? `wss://${window.location.hostname}:8000`
  : `ws://${window.location.hostname}:8000`;

interface MonitoringStatus {
  total_emails: number;
  processing_emails: number;
  processed_emails: number;
  assigned_emails: number;
  classification_stats: {
    [key: string]: number;
  };
}

interface Props {
  visible: boolean;
  email: string;
  onClose: () => void;
}

// 定义分类的固定顺序
const CATEGORY_ORDER = [
  'Need OCR',
  'OTC Billing',
  'Complaint',
  'unclassified',
  'OTC Order',
  'Technical Support',
  'Angry',
  'OTC Cash'
];

const MonitoringDetailModal: React.FC<Props> = ({ visible, email, onClose }) => {
  const [status, setStatus] = useState<MonitoringStatus>({
    total_emails: 0,
    processing_emails: 0,
    processed_emails: 0,
    assigned_emails: 0,
    classification_stats: {}
  });
  const [logs, setLogs] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const { isDark } = useTheme();

  useEffect(() => {
    if (visible && email) {
      // Connect to WebSocket using the correct backend URL
      const ws = new WebSocket(`${WS_BASE_URL}/ws/email_monitor/${email}/`);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        ws.send(JSON.stringify({ action: 'start_monitoring' }));
      };

      ws.onmessage = handleWebSocketMessage;

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        message.error('WebSocket连接失败，请检查网络连接或刷新页面重试');
      };

      ws.onclose = () => {
        console.log('WebSocket connection closed');
      };

      return () => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ action: 'stop_monitoring' }));
          ws.close();
        }
      };
    }
  }, [visible, email]);

  useEffect(() => {
    // Scroll to bottom when new logs arrive
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  const handleClose = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'stop_monitoring' }));
      wsRef.current.close();
    }
    onClose();
  };

  const calculateProgress = (current: number, total: number) => {
    return total > 0 ? Math.round((current / total) * 100) : 0;
  };

  const handleWebSocketMessage = (event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === 'log_message') {
        // 尝试解析消息为JSON格式
        try {
          const logData = JSON.parse(data.message);
          // 获取消息内容并去掉日志级别
          const message = logData.message || '';
          const cleanMessage = message.replace(/(ERROR|DEBUG|INFO|WARNING|CRITICAL):\s*/, '');
          // 使用日志中的时间戳
          const timestamp = message.match(/\[([^\]]+)\]/)?.[1] || '';
          const messageContent = cleanMessage.replace(/\[[^\]]+\]\s*/, '').trim();
          const formattedLog = `[${timestamp}] ${messageContent}`;
          setLogs(prev => [...prev, formattedLog]);
        } catch (e) {
          // 如果解析JSON失败，说明是普通文本格式
          const message = data.message;
          // 去掉日志级别
          const cleanMessage = message.replace(/(ERROR|DEBUG|INFO|WARNING|CRITICAL):\s*/, '');
          // 提取时间戳和消息内容
          const timestamp = cleanMessage.match(/\[([^\]]+)\]/)?.[1] || '';
          const messageContent = cleanMessage.replace(/\[[^\]]+\]\s*/, '').trim();
          const formattedLog = `[${timestamp}] ${messageContent}`;
          setLogs(prev => [...prev, formattedLog]);
        }
      } else if (data.type === 'status_update') {
        setStatus(data.data);
      }
    } catch (error) {
      console.error('Error handling WebSocket message:', error);
    }
  };

  // 对分类统计进行排序
  const sortedClassificationStats = Object.entries(status.classification_stats)
    .sort((a, b) => {
      const getIndex = (category: string) => {
        const baseCat = category.split(' (')[0];
        return CATEGORY_ORDER.indexOf(baseCat);
      };
      return getIndex(a[0]) - getIndex(b[0]);
    });

  return (
    <StyledModal
      title={
        <Space style={{ width: '100%' }}>
          <Text>邮件监控详情</Text>
        </Space>
      }
      open={visible}
      onCancel={handleClose}
      width={1280}
      footer={null}
      $isDark={isDark}
    >
      <Space direction="vertical" style={{ width: '100%' }} size={8}>
        <StyledCard $isDark={isDark}>
          <Space direction="vertical" style={{ width: '100%' }} size={4}>
            <div>
              <Space align="center">
                <RobotOutlined 
                  className="monitor-icon" 
                  style={{ fontSize: 20, color: isDark ? '#1890ff' : '#1890ff' }}
                  role="img"
                  aria-label="robot"
                  onPointerEnterCapture={() => {}}
                  onPointerLeaveCapture={() => {}}
                />
                <Text strong>监控师</Text>
                <Progress
                  percent={calculateProgress(status.total_emails, status.total_emails)}
                  status="active"
                  style={{ width: 200 }}
                  strokeColor={isDark ? '#1890ff' : '#1890ff'}
                />
                <Text>{status.total_emails} 封邮件</Text>
              </Space>
            </div>
            <div>
              <Space align="center">
                <SyncOutlined 
                  className="monitor-icon" 
                  style={{ fontSize: 20, color: isDark ? '#52c41a' : '#52c41a' }}
                  spin
                  role="img"
                  aria-label="sync"
                  onPointerEnterCapture={() => {}}
                  onPointerLeaveCapture={() => {}}
                />
                <Text strong>处理智能体</Text>
                <Progress
                  percent={calculateProgress(status.processed_emails, status.total_emails)}
                  status="active"
                  style={{ width: 200 }}
                  strokeColor={isDark ? '#52c41a' : '#52c41a'}
                />
                <Text>
                  {status.processed_emails}/{status.total_emails} 封邮件
                </Text>
              </Space>
            </div>
            <div>
              <Space align="center">
                <TeamOutlined 
                  className="monitor-icon" 
                  style={{ fontSize: 20, color: isDark ? '#722ed1' : '#722ed1' }}
                  role="img"
                  aria-label="team"
                  onPointerEnterCapture={() => {}}
                  onPointerLeaveCapture={() => {}}
                />
                <Text strong>分配任务智能体</Text>
                <Progress
                  percent={calculateProgress(status.assigned_emails, status.processed_emails)}
                  status="active"
                  style={{ width: 200 }}
                  strokeColor={isDark ? '#722ed1' : '#722ed1'}
                />
                <Text>
                  {status.assigned_emails}/{status.processed_emails} 封邮件
                </Text>
              </Space>
            </div>
          </Space>
        </StyledCard>

        <StyledCard $isDark={isDark}>
          <Title level={5} style={{ marginBottom: 8 }}>分类统计</Title>
          <List
            grid={{ gutter: 8, column: 3 }}
            dataSource={sortedClassificationStats}
            renderItem={([category, count]) => {
              const match = category.match(/^(.*?)\s*\((.*?)\)$/);
              const categoryName = match ? match[1] : category;
              const assignedTeam = match ? match[2] : '';
              
              return (
                <CategoryItem $isDark={isDark}>
                  <Space direction="vertical" style={{ width: '100%' }} size={2}>
                    <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                      <Text strong>
                        {categoryName}
                      </Text>
                      <Tag color={isDark ? 'blue' : 'blue'} style={{ marginInlineStart: '4px' }}>
                        {count} 封
                      </Tag>
                    </Space>
                    {assignedTeam && (
                      <Text type="secondary" style={{ fontSize: '11px' }}>
                        处理团队: {assignedTeam}
                      </Text>
                    )}
                  </Space>
                </CategoryItem>
              );
            }}
          />
        </StyledCard>

        <StyledCard $isDark={isDark}>
          <Title level={5} style={{ marginBottom: 8 }}>处理日志</Title>
          <LogsContainer $isDark={isDark}>
            {logs.map((log, index) => (
              <div key={index}>{log}</div>
            ))}
            <div ref={logsEndRef} />
          </LogsContainer>
        </StyledCard>
      </Space>
    </StyledModal>
  );
};

export default MonitoringDetailModal; 