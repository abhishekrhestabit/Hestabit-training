import React from 'react';

export default function Badge({ variant = 'primary', children, className = '' }) {
  
  const variants = {
    primary: 'bg-[#4e73df] text-white',
    danger: 'bg-[#e74a3b] text-white',
    warning: 'bg-[#f6c23e] text-white',
    success: 'bg-[#1cc88a] text-white',
    secondary: 'bg-[#858796] text-white',
  };

  return (
    <span className={`inline-flex items-center px-2 py-1 rounded text-[10px] font-bold leading-none ${variants[variant] || variants.primary} ${className}`}>
      {children}
    </span>
  );
}