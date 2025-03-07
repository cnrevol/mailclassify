import React from 'react';
import { AntdIconProps } from '@ant-design/icons/lib/components/AntdIcon';
import * as AntIcons from '@ant-design/icons';

interface IconProps {
  type: keyof typeof AntIcons;
  size?: 'small' | 'default' | 'large';
}

const Icon: React.FC<IconProps> = ({ type, size = 'default' }) => {
  const IconComponent = AntIcons[type];
  const className = size === 'default' ? 'anticon' : `anticon-${size}`;
  
  return <IconComponent className={className} />;
};

export default Icon; 