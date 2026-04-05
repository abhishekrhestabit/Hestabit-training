import React from 'react';

// A simple wrapper for the HTML <table> element
export default function Table({ children, className = '' }) {
  return (
    <div className={`w-full overflow-auto ${className}`}>
      <table className="w-full text-left text-sm text-gray-600 border-collapse">
        {children}
      </table>
    </div>
  );
}

// Table Header section
export function TableHeader({ children }) {
  return (
    <thead className="bg-[#f8f9fc] text-xs uppercase text-gray-500 font-bold border-b border-gray-200">
      <tr>{children}</tr>
    </thead>
  );
}

// Table Body section
export function TableBody({ children }) {
  return <tbody className="divide-y divide-gray-200">{children}</tbody>;
}

// Table Row (for body)
export function TableRow({ children, className = '' }) {
  return <tr className={`hover:bg-gray-50 transition-colors ${className}`}>{children}</tr>;
}

// Table Head Cell (<th>)
export function TableHead({ children, className = '' }) {
  return <th className={`px-6 py-3 tracking-wider ${className}`}>{children}</th>;
}

// Table Data Cell (<td>)
export function TableCell({ children, className = '' }) {
  return <td className={`px-6 py-4 whitespace-nowrap ${className}`}>{children}</td>;
}