"use client";
import React from 'react';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import Input from '@/components/ui/Input';
import Table from '@/components/ui/Table';
import {  TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table';

export default function UsersPage() {
  
  // Updated Data Model: Added Email, Created/Updated At. Removed Department.
  const employees = [
    { 
        id: 1, 
        name: "Aarav Sharma", 
        email: "aarav.s@hestabit.com",
        role: "Frontend Dev", 
        status: "Present", 
        time: "09:00 AM", 
        createdAt: "2023-01-10",
        updatedAt: "2023-11-25"
    },
    { 
        id: 2, 
        name: "Vivaan Gupta", 
        email: "vivaan.g@hestabit.com",
        role: "Backend Dev", 
        status: "Late", 
        time: "10:15 AM", 
        createdAt: "2023-03-15",
        updatedAt: "2024-01-02"
    },
    { 
        id: 3, 
        name: "Diya Patel", 
        email: "diya.p@hestabit.com",
        role: "Designer", 
        status: "Present", 
        time: "08:55 AM", 
        createdAt: "2022-11-05",
        updatedAt: "2023-12-10"
    },
    { 
        id: 4, 
        name: "Ananya Singh", 
        email: "ananya.s@hestabit.com",
        role: "HR Manager", 
        status: "Absent", 
        time: "-", 
        createdAt: "2021-06-20",
        updatedAt: "2024-02-14"
    },
    { 
        id: 5, 
        name: "Kabir Das", 
        email: "kabir.d@hestabit.com",
        role: "QA Engineer", 
        status: "Present", 
        time: "09:05 AM", 
        createdAt: "2023-08-12",
        updatedAt: "2024-01-28"
    },
  ];

  return (
    <div className="space-y-6">
      
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-light text-[#5a5c69]">Users & Attendance</h1>
          <p className="text-sm text-gray-500 mt-1">Manage employee roles, status, and daily logs.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm">Export CSV</Button>
          <Button variant="primary" size="sm">+ Add New User</Button>
        </div>
      </div>

      {/* Filters & Search Bar */}
      <Card className="p-4 flex flex-col md:flex-row gap-4 items-end md:items-center justify-between">
        <div className="w-full md:w-1/3">
          <Input placeholder="Search by name or email..." />
        </div>
        <div className="flex gap-2">
           {/* Changed filter from Department to Role since Department was removed */}
           <select className="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-md focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 outline-none">
              <option>All Roles</option>
              <option>Developers</option>
              <option>Designers</option>
              <option>HR</option>
           </select>
           <select className="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-md focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 outline-none">
              <option>All Status</option>
              <option>Present</option>
              <option>Absent</option>
              <option>Late</option>
           </select>
        </div>
      </Card>

      {/* Main Table */}
      <Card noPadding className="overflow-hidden">
        <Table>
          <TableHeader>
            <TableHead>Employee Name</TableHead>
            <TableHead>Email</TableHead>
            <TableHead>Role</TableHead>
            <TableHead>Check-in Time</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Created At</TableHead>
            <TableHead>Updated At</TableHead>
          </TableHeader>
          <TableBody>
            {employees.map((employee) => (
              <TableRow key={employee.id}>
                <TableCell className="font-medium text-gray-900">{employee.name}</TableCell>
                <TableCell className="text-gray-500">{employee.email}</TableCell>
                <TableCell>{employee.role}</TableCell>
                <TableCell className="font-mono text-xs">{employee.time}</TableCell>
                <TableCell>
                  <Badge 
                    variant={
                      employee.status === 'Present' ? 'success' : 
                      employee.status === 'Late' ? 'warning' : 'danger'
                    }
                  >
                    {employee.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-xs text-gray-500">{employee.createdAt}</TableCell>
                <TableCell className="text-xs text-gray-500">{employee.updatedAt}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        
        {/* Pagination Footer */}
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-200 flex items-center justify-between">
           <span className="text-xs text-gray-500">Showing <strong>1-5</strong> of <strong>5</strong> users</span>
           <div className="flex gap-1">
              <button className="px-3 py-1 border border-gray-300 bg-white text-gray-500 text-xs rounded hover:bg-gray-50 disabled:opacity-50">Prev</button>
              <button className="px-3 py-1 border border-gray-300 bg-blue-50 text-blue-600 text-xs rounded font-bold">1</button>
              <button className="px-3 py-1 border border-gray-300 bg-white text-gray-500 text-xs rounded hover:bg-gray-50">Next</button>
           </div>
        </div>
      </Card>

    </div>
  );
}