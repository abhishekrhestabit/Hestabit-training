import React from 'react';

export default function Input({ label, className = '', ...props }) {
  return (
    <div className="w-full">
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {label}
        </label>
      )}
      <input
        className={`
          block w-full px-3 py-2 
          bg-white border border-gray-300 rounded-md text-sm shadow-sm placeholder-gray-400
          focus:outline-none focus:border-[#4e73df] focus:ring-1 focus:ring-[#4e73df]
          disabled:bg-gray-50 disabled:text-gray-500 disabled:border-gray-200
          transition-colors
          ${className}
        `}
        {...props}
      />
    </div>
  );
}