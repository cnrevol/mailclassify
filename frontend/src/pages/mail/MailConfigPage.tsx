import React, { useEffect, useState, useRef } from 'react';
import { Table, Button, Modal, Form, Input, Space, message, Switch, Tooltip } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, SyncOutlined, KeyOutlined } from '@ant-design/icons';
import axios from 'axios';
import { useLocation } from 'react-router-dom';

interface MailConfig {
  id: number;
  email: string;
  client_id: string;
  client_secret: string;
  is_active: boolean;
}

interface ClassificationStatus {
  [key: number]: boolean;
}

interface MonitoringStatus {
  email: string;
  is_monitoring: boolean;
  last_check_time: string | null;
  last_found_emails: number;
  total_classified_emails: number;
  updated_at: string | null;
}

// 默认分类方法
const DEFAULT_CLASSIFICATION_METHOD = 'stepgo';

const MailConfigPage: React.FC = () => {
  const [configs, setConfigs] = useState<MailConfig[]>([]);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [editingId, setEditingId] = useState<number | null>(null);
  const [classifying, setClassifying] = useState<ClassificationStatus>({});
  const [loadingStatus, setLoadingStatus] = useState<ClassificationStatus>({});
  const [authLoading, setAuthLoading] = useState<ClassificationStatus>({});
  const [monitoringStatus, setMonitoringStatus] = useState<{[key: string]: MonitoringStatus}>({});
  const [monitoringLoading, setMonitoringLoading] = useState<{[key: number]: boolean}>({});
  
  // 获取查询参数
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const authSuccess = queryParams.get('auth_success');

  // 添加定时器引用
  const statusCheckTimerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // 如果有授权成功的参数，显示成功消息
    if (authSuccess === 'true') {
      message.success('授权成功！现在可以获取和分类邮件了。');
      // 清除 URL 中的查询参数，避免刷新页面时重复显示消息
      window.history.replaceState({}, document.title, window.location.pathname);
      // 刷新配置列表
      fetchConfigs();
    }
  }, [authSuccess]);

  const fetchConfigs = async () => {
    try {
      const response = await axios.get('/api/mail-info/', {
        headers: { Authorization: `Bearer ${localStorage.getItem('accessToken')}` }
      });
      setConfigs(response.data);
      
      // 获取所有配置的监控状态
      for (const config of response.data) {
        await checkMonitoringStatus(config.email);
      }
    } catch (error) {
      message.error('获取配置失败');
    }
  };

  useEffect(() => {
    fetchConfigs();
  }, []);

  // 在 useEffect 中添加状态检查定时器
  useEffect(() => {
    // 启动定时检查
    statusCheckTimerRef.current = setInterval(() => {
      checkAllMonitoringStatus();
    }, 30000); // 每30秒检查一次
    
    // 组件卸载时清除定时器
    return () => {
      if (statusCheckTimerRef.current) {
        clearInterval(statusCheckTimerRef.current);
      }
    };
  }, []);
  
  // 检查所有邮箱的监控状态
  const checkAllMonitoringStatus = async () => {
    try {
      // 只检查已加载的配置
      for (const config of configs) {
        await checkMonitoringStatus(config.email);
      }
    } catch (error) {
      console.error('检查监控状态失败:', error);
    }
  };
  
  // 检查单个邮箱的监控状态
  const checkMonitoringStatus = async (email: string) => {
    try {
      const response = await axios.get(`/api/mail/monitor/?email=${email}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('accessToken')}` }
      });
      
      if (response.data.status === 'success') {
        setMonitoringStatus(prev => ({
          ...prev,
          [email]: response.data.monitoring_status
        }));
      }
    } catch (error) {
      console.error(`检查邮箱 ${email} 监控状态失败:`, error);
    }
  };

  const handleAdd = () => {
    form.resetFields();
    setEditingId(null);
    setIsModalVisible(true);
  };

  const handleEdit = (record: MailConfig) => {
    form.setFieldsValue(record);
    setEditingId(record.id);
    setIsModalVisible(true);
  };

  const handleDelete = async (id: number) => {
    try {
      await axios.delete(`/api/mail-info/${id}/`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('accessToken')}` }
      });
      message.success('删除成功');
      fetchConfigs();
    } catch (error) {
      message.error('删除失败');
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingId) {
        await axios.put(`/api/mail-info/${editingId}/`, values, {
          headers: { Authorization: `Bearer ${localStorage.getItem('accessToken')}` }
        });
      } else {
        await axios.post('/api/mail-info/', values, {
          headers: { Authorization: `Bearer ${localStorage.getItem('accessToken')}` }
        });
      }
      message.success(`${editingId ? '更新' : '添加'}成功`);
      setIsModalVisible(false);
      fetchConfigs();
    } catch (error) {
      message.error(`${editingId ? '更新' : '添加'}失败`);
    }
  };

  const handleAuth = async (record: MailConfig) => {
    setAuthLoading(prev => ({ ...prev, [record.id]: true }));
    
    try {
      const response = await axios.get(`/api/mail/oauth/authorize`, {
        params: { 
          email: record.email,
          email_id: record.id  // 添加邮箱 ID
        },
        headers: { 
          Authorization: `Bearer ${localStorage.getItem('accessToken')}` 
        },
        withCredentials: true
      });
      
      if (response.data.auth_url) {
        // 直接在当前窗口重定向到授权 URL
        window.location.href = response.data.auth_url;
      } else {
        message.error('获取授权链接失败');
        setAuthLoading(prev => ({ ...prev, [record.id]: false }));
      }
    } catch (error: any) {
      message.error('获取授权链接失败: ' + (error.response?.data?.error || error.message));
      setAuthLoading(prev => ({ ...prev, [record.id]: false }));
    }
  };

  const handleClassify = async (record: MailConfig) => {
    // 设置加载状态
    setMonitoringLoading(prev => ({ ...prev, [record.id]: true }));
    
    try {
      // 获取当前监控状态
      const currentStatus = monitoringStatus[record.email]?.is_monitoring || false;
      
      // 切换监控状态
      const action = currentStatus ? 'stop' : 'start';
      
      // 调用监控API
      const response = await axios.post('/api/mail/monitor/', 
        { email: record.email, action },
        { headers: { Authorization: `Bearer ${localStorage.getItem('accessToken')}` } }
      );
      
      if (response.data.status === 'success') {
        // 更新监控状态
        setMonitoringStatus(prev => ({
          ...prev,
          [record.email]: response.data.monitoring_status
        }));
        
        // 显示操作结果
        message.success(response.data.message);
        
        // 如果是开始监控，立即执行一次分类
        if (action === 'start') {
          await runClassification(record.email);
        }
      } else {
        message.warning(response.data.message || '操作失败');
      }
    } catch (error: any) {
      message.error('操作失败: ' + (error.response?.data?.error || error.message));
    } finally {
      // 清除加载状态
      setMonitoringLoading(prev => ({ ...prev, [record.id]: false }));
    }
  };

  // 添加执行分类的方法
  const runClassification = async (email: string) => {
    try {
      // 执行一次分类
      const response = await axios.post('/api/mail/classify/', 
        { email, hours: 2, method: DEFAULT_CLASSIFICATION_METHOD },
        { headers: { Authorization: `Bearer ${localStorage.getItem('accessToken')}` } }
      );
      
      // 显示分类结果
      if (response.data.status === 'success') {
        message.success(response.data.message);
        
        // 如果有分类统计信息，显示更详细的消息
        if (response.data.classification_stats) {
          const stats = response.data.classification_stats;
          const statsMessage = Object.entries(stats)
            .map(([category, count]) => `${category}: ${count}封`)
            .join(', ');
          
          if (statsMessage) {
            message.info(`分类详情: ${statsMessage}`);
          }
        }
      }
    } catch (error: any) {
      message.error('分类失败: ' + (error.response?.data?.error || error.message));
    }
  };

  const columns = [
    {
      title: '邮箱地址',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: '客户端ID',
      dataIndex: 'client_id',
      key: 'client_id',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: MailConfig) => (
        <Space>
          <Button 
            type="text" 
            onClick={() => handleEdit(record)}
          >
            <EditOutlined />
          </Button>
          <Button 
            type="text" 
            onClick={() => handleDelete(record.id)}
            danger
          >
            <DeleteOutlined />
          </Button>
        </Space>
      ),
    },
    {
      title: '授权',
      key: 'auth',
      render: (_: any, record: MailConfig) => (
        <Button
          type="default"
          loading={authLoading[record.id]}
          onClick={() => handleAuth(record)}
          icon={<KeyOutlined />}
        >
          授权
        </Button>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record: MailConfig) => (
        <Tooltip title="开始/停止邮件监控和分类">
          <Button
            type={monitoringStatus[record.email]?.is_monitoring ? "primary" : "default"}
            loading={monitoringLoading[record.id]}
            onClick={() => handleClassify(record)}
          >
            {monitoringStatus[record.email]?.is_monitoring ? (
              <>
                <SyncOutlined spin /> 监控中
                {monitoringStatus[record.email]?.last_found_emails > 0 && 
                  ` (${monitoringStatus[record.email]?.total_classified_emails}封)`}
              </>
            ) : '开始监控'}
          </Button>
        </Tooltip>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '16px' }}>
        <Button 
          type="primary" 
          onClick={handleAdd}
        >
          <PlusOutlined />
          添加配置
        </Button>
      </div>
      <Table 
        columns={columns} 
        dataSource={configs}
        rowKey="id"
      />
      <Modal
        title={editingId ? '编辑配置' : '添加配置'}
        open={isModalVisible}
        onOk={handleSubmit}
        onCancel={() => setIsModalVisible(false)}
      >
        <Form
          form={form}
          layout="vertical"
        >
          <Form.Item
            name="email"
            label="邮箱地址"
            rules={[{ required: true, message: '请输入邮箱地址' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="client_id"
            label="客户端ID"
            rules={[{ required: true, message: '请输入客户端ID' }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="client_secret"
            label="客户端密钥"
            rules={[{ required: true, message: '请输入客户端密钥' }]}
          >
            <Input.Password />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default MailConfigPage; 