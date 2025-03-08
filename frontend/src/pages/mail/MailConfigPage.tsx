import React, { useEffect, useState } from 'react';
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

const MailConfigPage: React.FC = () => {
  const [configs, setConfigs] = useState<MailConfig[]>([]);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [editingId, setEditingId] = useState<number | null>(null);
  const [classifying, setClassifying] = useState<ClassificationStatus>({});
  const [loadingStatus, setLoadingStatus] = useState<ClassificationStatus>({});
  const [authLoading, setAuthLoading] = useState<ClassificationStatus>({});
  
  // 获取查询参数
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const authSuccess = queryParams.get('auth_success');

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
    } catch (error) {
      message.error('获取配置失败');
    }
  };

  useEffect(() => {
    fetchConfigs();
  }, []);

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
    setLoadingStatus(prev => ({ ...prev, [record.id]: true }));
    
    try {
      // 切换分类状态
      const newStatus = !classifying[record.id];
      setClassifying(prev => ({ ...prev, [record.id]: newStatus }));
      
      if (newStatus) {
        // 开始分类
        const response = await axios.post('/api/mail/classify/', 
          { email: record.email, hours: 2, method: 'stepgo' },
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
        } else {
          message.warning('分类完成，但没有返回详细信息');
        }
      } else {
        // 用户手动关闭了分类开关
        message.info('已停止分类');
      }
    } catch (error: any) {
      message.error('分类失败: ' + (error.response?.data?.error || error.message));
      // 发生错误时重置分类状态
      setClassifying(prev => ({ ...prev, [record.id]: false }));
    } finally {
      // 清除加载状态
      setLoadingStatus(prev => ({ ...prev, [record.id]: false }));
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
      title: '邮件分类',
      key: 'classify',
      render: (_: any, record: MailConfig) => (
        <Tooltip title={classifying[record.id] ? '点击停止分类' : '点击开始分类'}>
          <Button
            type={classifying[record.id] ? "primary" : "default"}
            loading={loadingStatus[record.id]}
            onClick={() => handleClassify(record)}
          >
            {classifying[record.id] && <SyncOutlined spin />}
            {classifying[record.id] ? '分类中' : '分类开始'}
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