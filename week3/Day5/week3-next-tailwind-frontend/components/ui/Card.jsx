import React from 'react';

export default function Card({ children, className = '', borderLeft, noPadding = false }) {
  
  const borderColors = {
    primary: 'border-l-[4px] border-l-[#4e73df]',
    success: 'border-l-[4px] border-l-[#1cc88a]',
    warning: 'border-l-[4px] border-l-[#f6c23e]',
    danger: 'border-l-[4px] border-l-[#e74a3b]',
    info: 'border-l-[4px] border-l-[#36b9cc]',
  };

  return (
    <div 
      className={`
        bg-white rounded shadow-sm border border-gray-100 flex flex-col h-full
        ${borderLeft ? borderColors[borderLeft] : ''} 
        ${className}
      `}
    >
      <div className={noPadding ? '' : 'p-5 flex-1'}>
        {children}
      </div>
    </div>
  );
}