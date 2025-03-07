import React, { useState } from 'react';
import { Layout, Menu, Button, Input, Avatar, Dropdown, Space, Modal, Tooltip } from 'antd';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  SearchOutlined,
  UserOutlined,
  SettingOutlined,
  LogoutOutlined,
  SendOutlined,
  AppstoreOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import MailConfigPage from '../mail/MailConfigPage';

const { Header, Sider, Content } = Layout;

const ChatPage: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [messageInput, setMessageInput] = useState('');
  const [searchVisible, setSearchVisible] = useState(false);
  const [searchValue, setSearchValue] = useState('');
  const [selectedMenu, setSelectedMenu] = useState<string>('');
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.clear();
    navigate('/login');
  };

  const userMenuItems = [
    {
      key: 'settings',
      icon: <SettingOutlined style={{ fontSize: '16px' }} />,
      label: '设置',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined style={{ fontSize: '16px' }} />,
      label: '退出登录',
      onClick: handleLogout,
    },
  ];

  const handleSearch = () => {
    // 实现搜索逻辑
    setSearchVisible(false);
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
            justifyContent: 'center',
            alignItems: 'center',
            padding: '0 15%'
          }}>
            <div style={{ 
              flex: 1,
              width: '100%',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              alignItems: 'center'
            }}>
              <h1 style={{ fontSize: '32px', marginBottom: '20px' }}>What can I help with?</h1>
            </div>
            <div style={{ 
              width: '100%',
              padding: '20px 0 40px',
              borderTop: '1px solid #e8e8e8'
            }}>
              <div style={{ 
                display: 'flex',
                gap: '10px',
                alignItems: 'flex-end'
              }}>
                <Input.TextArea
                  placeholder="Ask anything"
                  value={messageInput}
                  onChange={(e) => setMessageInput(e.target.value)}
                  autoSize={{ minRows: 1, maxRows: 6 }}
                  style={{ 
                    resize: 'none',
                    padding: '12px',
                    borderRadius: '8px',
                    backgroundColor: '#f0f2f5',
                    border: 'none'
                  }}
                />
                <Button 
                  type="text"
                  icon={<SendOutlined style={{ fontSize: '20px' }} />} 
                  style={{
                    height: '42px',
                    width: '42px',
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                />
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
            icon={<SearchOutlined style={{ fontSize: '20px', color: '#595959' }} />}
            onClick={() => setSearchVisible(true)}
            style={{ 
              flex: 1,
              backgroundColor: '#f5f5f5',
              color: '#595959'
            }}
          />
          <Button 
            type="text" 
            icon={<AppstoreOutlined style={{ fontSize: '20px', color: '#595959' }} />}
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
              icon={collapsed ? <MenuUnfoldOutlined style={{ fontSize: '16px' }} /> : <MenuFoldOutlined style={{ fontSize: '16px' }} />}
              onClick={() => setCollapsed(!collapsed)}
              style={{ border: 'none' }}
            />
          </Tooltip>
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <Avatar icon={<UserOutlined style={{ fontSize: '18px' }} />} style={{ cursor: 'pointer', background: '#f0f2f5' }} />
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