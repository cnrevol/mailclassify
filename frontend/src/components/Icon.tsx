import React from 'react';
import * as Icons from '@ant-design/icons';
import type { AntdIconProps } from '@ant-design/icons/lib/components/AntdIcon';

interface IconProps {
  name: keyof typeof Icons;
  className?: string;
}

const Icon: React.FC<IconProps> = ({ name, className }) => {
  const IconComponent = Icons[name] as React.ComponentType<AntdIconProps>;
  if (!IconComponent) {
    console.error(`Icon ${name} not found`);
    return null;
  }
  return <IconComponent className={className} />;
};

export default Icon; 