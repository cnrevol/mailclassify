import React, { useEffect, useState, useRef } from 'react';
import { Modal, Progress, Space, Typography, List } from 'antd';
import { RobotOutlined, SyncOutlined } from '@ant-design/icons';
import { message } from 'antd';

const { Title, Text } = Typography;

// 后端WebSocket服务器地址
const WS_BASE_URL = window.location.protocol === 'https:' 
  ? `wss://${window.location.hostname}:8000`
  : `ws://${window.location.hostname}:8000`;

interface MonitoringStatus {
  total_emails: number;
  processing_emails: number;
  processed_emails: number;
  classification_stats: {
    [key: string]: number;
  };
}

interface Props {
  visible: boolean;
  email: string;
  onClose: () => void;
}

const MonitoringDetailModal: React.FC<Props> = ({ visible, email, onClose }) => {
  const [status, setStatus] = useState<MonitoringStatus>({
    total_emails: 0,
    processing_emails: 0,
    processed_emails: 0,
    classification_stats: {}
  });
  const [logs, setLogs] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

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

  return (
    <Modal
      title="邮件监控详情"
      open={visible}
      onCancel={handleClose}
      footer={null}
      width={1024}
      style={{ top: 20 }}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* Progress Section */}
        <div>
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <Space align="center">
                <RobotOutlined 
                  className="monitor-icon" 
                  style={{ fontSize: 20 }} 
                  role="img" 
                  aria-label="robot"
                  onPointerEnterCapture={() => {}}
                  onPointerLeaveCapture={() => {}}
                />
                <Text strong>监控师</Text>
                <Progress
                  percent={calculateProgress(status.total_emails, status.total_emails)}
                  status="active"
                  style={{ width: 300 }}
                />
                <Text>{status.total_emails} 封邮件</Text>
              </Space>
            </div>
            <div>
              <Space align="center">
                <SyncOutlined 
                  className="monitor-icon" 
                  style={{ fontSize: 20 }} 
                  spin 
                  role="img" 
                  aria-label="loading"
                  onPointerEnterCapture={() => {}}
                  onPointerLeaveCapture={() => {}}
                />
                <Text strong>处理智能体</Text>
                <Progress
                  percent={calculateProgress(status.processed_emails, status.total_emails)}
                  status="active"
                  style={{ width: 300 }}
                />
                <Text>
                  {status.processed_emails}/{status.total_emails} 封邮件
                </Text>
              </Space>
            </div>
          </Space>
        </div>

        {/* Statistics Section */}
        <div>
          <Title level={5}>分类统计</Title>
          <List
            grid={{ gutter: 16, column: 3 }}
            dataSource={Object.entries(status.classification_stats)}
            renderItem={([category, count]) => (
              <List.Item>
                <Text strong>{category}:</Text> {count} 封
              </List.Item>
            )}
          />
        </div>

        {/* Logs Section */}
        <div>
          <Title level={5}>处理日志</Title>
          <div
            style={{
              height: '300px',
              overflowY: 'auto',
              padding: '10px',
              backgroundColor: '#f5f5f5',
              borderRadius: '4px'
            }}
          >
            {logs.map((log, index) => (
              <div key={index} style={{ fontFamily: 'monospace' }}>
                {log}
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        </div>
      </Space>
    </Modal>
  );
};

export default MonitoringDetailModal; 