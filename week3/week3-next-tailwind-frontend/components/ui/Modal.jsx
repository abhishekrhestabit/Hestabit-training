"use client";

import React, { useEffect } from 'react';
import Card from './Card';
import Button from './Button';

export default function Modal({ isOpen, onClose, title, children }) {
  
  // Close on Escape key
  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/50 transition-opacity backdrop-blur-sm" 
        onClick={onClose}
      ></div>

      {/* Modal Content */}
      <div className="relative z-10 w-full max-w-md animate-in fade-in zoom-in duration-200">
        <Card noPadding className="overflow-hidden shadow-2xl">
            {/* Header */}
            <div className="px-4 py-3 border-b border-gray-100 bg-[#f8f9fc] flex justify-between items-center">
              <h3 className="text-lg font-bold text-[#4e73df]">{title}</h3>
              <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
                <span className="text-xl">×</span>
              </button>
            </div>
            
            {/* Body */}
            <div className="p-6 text-gray-600">
              {children}
            </div>

            {/* Footer */}
            <div className="px-4 py-3 bg-gray-50 border-t border-gray-100 flex justify-end space-x-2">
              <Button variant="secondary" size="sm" onClick={onClose}>Cancel</Button>
              <Button variant="primary" size="sm" onClick={() => { alert('Success!'); onClose(); }}>Confirm</Button>
            </div>
        </Card>
      </div>
    </div>
  );
}