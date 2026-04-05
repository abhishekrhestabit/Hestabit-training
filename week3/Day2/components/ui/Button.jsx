import React from 'react';

export default function Button({ 
  variant = 'primary', 
  size = 'md', 
  className = '', 
  children, 
  ...props 
}) {
  
  // Base styles
  const baseStyles = "inline-flex items-center justify-center font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2";
  
  // Variants map
  const variants = {
    primary: "bg-[#4e73df] hover:bg-[#2e59d9] text-white focus:ring-[#4e73df]",
    secondary: "bg-[#858796] hover:bg-[#60616f] text-white focus:ring-[#858796]",
    success: "bg-[#1cc88a] hover:bg-[#17a673] text-white focus:ring-[#1cc88a]",
    danger: "bg-[#e74a3b] hover:bg-[#be2617] text-white focus:ring-[#e74a3b]",
    warning: "bg-[#f6c23e] hover:bg-[#dfa00d] text-white focus:ring-[#f6c23e]",
  };

  // Sizes map
  const sizes = {
    sm: "px-2.5 py-1.5 text-xs",
    md: "px-4 py-2 text-sm",
    lg: "px-6 py-3 text-base",
  };

  return (
    <button 
      className={`${baseStyles} ${variants[variant] || variants.primary} ${sizes[size] || sizes.md} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}