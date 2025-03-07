import React, { useState } from 'react';
import { Layout, Menu, Button, Input, Avatar, Dropdown, Space, Modal, Tooltip, Select, message } from 'antd';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  SearchOutlined,
  UserOutlined,
  SettingOutlined,
  LogoutOutlined,
  SendOutlined,
  AppstoreOutlined,
  RobotOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import MailConfigPage from '../mail/MailConfigPage';
import ReactMarkdown from 'react-markdown';

const { Header, Sider, Content } = Layout;
const { Option } = Select;

type IconComponent = React.ForwardRefExoticComponent<any>;

const ChatPage: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [messageInput, setMessageInput] = useState('');
  const [searchVisible, setSearchVisible] = useState(false);
  const [searchValue, setSearchValue] = useState('');
  const [selectedMenu, setSelectedMenu] = useState<string>('');
  const [selectedModel, setSelectedModel] = useState('azure-gpt4');
  const [messages, setMessages] = useState<Array<{role: string, content: string, type?: string}>>([]);
  const [loading, setLoading] = useState(false);
  const [hasMessages, setHasMessages] = useState(false);
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.clear();
    navigate('/login');
  };

  const renderIcon = (Icon: IconComponent, size: 'small' | 'default' | 'large' = 'default') => {
    const style = {
      fontSize: size === 'small' ? 14 : size === 'large' ? 20 : 16,
      color: '#595959'
    };
    return <Icon style={style} />;
  };

  const userMenuItems = [
    {
      key: 'settings',
      icon: renderIcon(SettingOutlined),
      label: '设置',
    },
    {
      key: 'logout',
      icon: renderIcon(LogoutOutlined),
      label: '退出登录',
      onClick: handleLogout,
    },
  ];

  const handleSearch = () => {
    // 实现搜索逻辑
    setSearchVisible(false);
  };

  const modelOptions = [
    { value: 'azure-gpt4', label: 'Azure OpenAI GPT-4' },
    { value: 'gpt-4', label: 'OpenAI GPT-4' },
    { value: 'doubao', label: '豆包大模型' },
    { value: 'deepseek', label: 'DeepSeek' },
    { value: 'qwen', label: '通义千问' },
  ];

  const handleSendMessage = async () => {
    if (!messageInput.trim() || loading) return;

    const token = localStorage.getItem('accessToken');
    console.log('Current token:', token); // Debug log

    if (!token) {
      message.error('Please login first');
      navigate('/login');
      return;
    }

    const userMessage = messageInput.trim();
    setMessageInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setHasMessages(true);
    setLoading(true);

    try {
      const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      };
      console.log('Request headers:', headers); // Debug log

      const response = await fetch('/api/chat/', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          message: userMessage,
          model: selectedModel
        }),
      });

      console.log('Response status:', response.status); // Debug log
      
      if (!response.ok) {
        if (response.status === 401) {
          message.error('Session expired. Please login again.');
          localStorage.clear();
          navigate('/login');
          return;
        }
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.success) {
        setMessages(prev => [...prev, { 
          role: 'assistant', 
          content: data.data.content,
          type: data.data.type
        }]);
      } else {
        throw new Error(data.error || 'Failed to get response');
      }
    } catch (error) {
      console.error('Chat error:', error);
      if (error instanceof Error) {
        message.error(error.message);
      } else {
        message.error('Failed to send message');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const renderMessages = () => {
    return messages.map((msg, index) => (
      <div
        key={index}
        style={{
          padding: '20px',
          display: 'flex',
          justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
          marginBottom: '8px'
        }}
      >
        <div style={{ 
          maxWidth: '800px',
          width: 'fit-content',
          padding: '12px 16px',
          borderRadius: '12px',
          background: msg.role === 'user' ? '#f5f5f5' : 'transparent',
          border: msg.role === 'assistant' ? '1px solid #e8e8e8' : 'none',
          marginLeft: msg.role === 'assistant' ? '48px' : 'auto',
          marginRight: msg.role === 'user' ? '48px' : 'auto',
        }}>
          {msg.type === 'markdown' ? (
            <ReactMarkdown>{msg.content}</ReactMarkdown>
          ) : msg.type === 'html' ? (
            <div dangerouslySetInnerHTML={{ __html: msg.content }} />
          ) : (
            <p style={{ 
              whiteSpace: 'pre-wrap',
              margin: 0,
              color: msg.role === 'user' ? '#595959' : '#000000'
            }}>{msg.content}</p>
          )}
        </div>
      </div>
    ));
  };

  const renderContent = () => {
    switch (selectedMenu) {
      case 'mail-config':
        return <MailConfigPage />;
      default:
        return (
          <div style={{ 
            height: '100%', 
            display: 'flex', 
            flexDirection: 'column',
            position: 'relative',
            padding: hasMessages ? '20px 0 120px' : '0'
          }}>
            {!hasMessages ? (
              <div style={{ 
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                alignItems: 'center'
              }}>
                <h1 style={{ fontSize: '32px', marginBottom: '20px' }}>What can I help with?</h1>
              </div>
            ) : (
              <div style={{ paddingBottom: '120px', overflowY: 'auto', height: '100%' }}>
                {renderMessages()}
              </div>
            )}
            <div style={{ 
              position: 'fixed',
              bottom: 0,
              left: collapsed ? 0 : '260px',
              right: 0,
              padding: '12px 20%',
              background: '#ffffff',
              borderTop: '1px solid #e8e8e8',
              zIndex: 1000,
              transition: 'left 0.2s'
            }}>
              <div style={{ 
                maxWidth: '800px',
                margin: '0 auto',
                position: 'relative'
              }}>
                <div style={{ 
                  display: 'flex',
                  gap: '10px',
                  alignItems: 'flex-end',
                  boxShadow: '0 0 10px rgba(0,0,0,0.1)',
                  borderRadius: '12px',
                  padding: '2px',
                  marginBottom: '8px'
                }}>
                  <Input.TextArea
                    placeholder="Ask anything"
                    value={messageInput}
                    onChange={(e) => setMessageInput(e.target.value)}
                    autoSize={{ minRows: 1, maxRows: 6 }}
                    style={{ 
                      resize: 'none',
                      padding: '12px 45px 12px 12px',
                      fontSize: '16px',
                      border: 'none',
                      boxShadow: 'none'
                    }}
                    onKeyDown={handleKeyPress}
                  />
                  <Button 
                    type="text"
                    icon={renderIcon(SendOutlined)}
                    style={{
                      position: 'absolute',
                      right: '8px',
                      bottom: '8px',
                      height: '32px',
                      width: '32px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}
                    onClick={handleSendMessage}
                  />
                </div>
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '0 4px'
                }}>
                  {renderIcon(RobotOutlined, 'small')}
                  <Select
                    value={selectedModel}
                    onChange={setSelectedModel}
                    style={{ width: 160 }}
                    options={modelOptions}
                    bordered={false}
                    dropdownStyle={{ padding: '8px' }}
                    size="small"
                  />
                </div>
              </div>
            </div>
          </div>
        );
    }
  };

  return (
    <Layout style={{ height: '100vh', background: '#ffffff' }}>
      <Sider 
        trigger={null} 
        collapsible 
        collapsed={collapsed} 
        width={260}
        collapsedWidth={0}
        style={{ 
          background: '#ffffff',
          borderRight: '1px solid #e8e8e8'
        }}
      >
        <div style={{ padding: '16px', display: 'flex', gap: '8px' }}>
          <Button 
            type="text" 
            icon={renderIcon(SearchOutlined, 'large')}
            onClick={() => setSearchVisible(true)}
            style={{ 
              flex: 1,
              backgroundColor: '#f5f5f5',
              color: '#595959'
            }}
          />
          <Button 
            type="text" 
            icon={renderIcon(AppstoreOutlined, 'large')}
            style={{
              backgroundColor: '#f5f5f5',
              color: '#595959'
            }}
          />
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedMenu]}
          style={{ 
            border: 'none',
            background: '#ffffff'
          }}
          items={[
            {
              key: 'mail',
              label: '邮件管理',
              children: [
                {
                  key: 'mail-config',
                  label: '邮件配置',
                },
                {
                  key: 'mail-query',
                  label: '邮件查询',
                },
              ],
            }
          ]}
          onClick={({ key }) => setSelectedMenu(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ 
          padding: '0 16px', 
          background: '#ffffff', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          borderBottom: '1px solid #e8e8e8',
          height: '48px',
          lineHeight: '48px'
        }}>
          <Tooltip title={collapsed ? "Open sidebar" : "Close sidebar"}>
            <Button
              type="text"
              icon={collapsed ? renderIcon(MenuUnfoldOutlined) : renderIcon(MenuFoldOutlined)}
              onClick={() => setCollapsed(!collapsed)}
              style={{ border: 'none' }}
            />
          </Tooltip>
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <Avatar icon={renderIcon(UserOutlined)} style={{ cursor: 'pointer', background: '#f0f2f5' }} />
          </Dropdown>
        </Header>
        <Content style={{ 
          background: '#ffffff',
          position: 'relative',
          height: 'calc(100vh - 48px)'
        }}>
          {renderContent()}
        </Content>
      </Layout>
      <Modal
        title="搜索对话"
        open={searchVisible}
        onOk={handleSearch}
        onCancel={() => setSearchVisible(false)}
      >
        <Input
          placeholder="输入关键词搜索"
          value={searchValue}
          onChange={(e) => setSearchValue(e.target.value)}
          style={{ marginTop: '16px' }}
        />
      </Modal>
    </Layout>
  );
};

export default ChatPage; 