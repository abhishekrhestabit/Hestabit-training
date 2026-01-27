"use client";
import React, { useState } from 'react';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Modal from '@/components/ui/Modal';
import Badge from '@/components/ui/Badge';
import Table from '@/components/ui/Table';
// 1. Import the Table Components
import {  TableHeader, TableBody, TableRow, TableHead, TableCell } from '@/components/ui/Table';

import AreaChart from '@/components/charts/AreaChart';
import PieChart from '@/components/charts/PieChart';

export default function DashboardPage() {
  const [isModalOpen, setModalOpen] = useState(false);

  // 2. Define Data Source (Hestabit Employees)
  const employees = [
    { id: 1, name: "Aarav Sharma", role: "Frontend Dev", status: "Present", time: "09:00 AM", department: "Engineering" },
    { id: 2, name: "Vivaan Gupta", role: "Backend Dev", status: "Late", time: "10:15 AM", department: "Engineering" },
    { id: 3, name: "Diya Patel", role: "Designer", status: "Present", time: "08:55 AM", department: "Design" },
    { id: 4, name: "Ananya Singh", role: "HR Manager", status: "Absent", time: "-", department: "HR" },
    { id: 5, name: "Kabir Das", role: "QA Engineer", status: "Present", time: "09:05 AM", department: "QA" },
  ];

  return (
    <div className="space-y-6">
      
      {/* --- PAGE HEADER --- */}
      <div className="flex flex-col md:flex-row md:items-center justify-between mb-2 gap-4">
        <h1 className="text-2xl font-light text-[#5a5c69]">Dashboard</h1>
        <Button variant="primary" size="sm" className="shadow-sm" onClick={() => setModalOpen(true)}>
          <span className="mr-2 text-white/90">📥</span> Generate Report
        </Button>
      </div>

      {/* --- STATS CARDS ROW --- */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        
        {/* Card 1: Earnings (Monthly) */}
        <Card borderLeft="primary" className="h-24">
          <div className="flex items-center h-full">
            <div className="flex-1">
              <div className="text-xs font-bold text-[#4e73df] uppercase mb-1 tracking-wide">
                Earnings (Monthly)
              </div>
              <div className="text-xl font-bold text-[#5a5c69]">$40,000</div>
            </div>
            <div className="text-gray-300 text-2xl">
              <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/></svg>
            </div>
          </div>
        </Card>

        {/* Card 2: Earnings (Annual) */}
        <Card borderLeft="success" className="h-24">
          <div className="flex items-center h-full">
            <div className="flex-1">
              <div className="text-xs font-bold text-[#1cc88a] uppercase mb-1 tracking-wide">
                Earnings (Annual)
              </div>
              <div className="text-xl font-bold text-[#5a5c69]">$215,000</div>
            </div>
            <div className="text-gray-300 text-2xl">
              <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" x2="12" y1="1" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
            </div>
          </div>
        </Card>

        {/* Card 3: Tasks */}
        <Card borderLeft="info" className="h-24">
          <div className="flex items-center h-full">
            <div className="flex-1">
              <div className="text-xs font-bold text-[#36b9cc] uppercase mb-1 tracking-wide">
                Tasks
              </div>
              <div className="flex items-center">
                <div className="text-xl font-bold text-[#5a5c69] mr-3">50%</div>
                <div className="flex-1 bg-gray-200 rounded-full h-2 mr-2">
                  <div className="bg-[#36b9cc] h-2 rounded-full w-1/2"></div>
                </div>
              </div>
            </div>
            <div className="text-gray-300 text-2xl">
              <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15.6 2.7a10 10 0 1 0 5.7 5.7"/><path d="M16.9 3.2s-1.5-.5-3-.5a10 10 0 0 0-10 10c0 1.5.5 3 .5 3"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>
            </div>
          </div>
        </Card>

        {/* Card 4: Pending Requests */}
        <Card borderLeft="warning" className="h-24">
          <div className="flex items-center h-full">
            <div className="flex-1">
              <div className="text-xs font-bold text-[#f6c23e] uppercase mb-1 tracking-wide">
                Pending Requests
              </div>
              <div className="text-xl font-bold text-[#5a5c69]">18</div>
            </div>
            <div className="text-gray-300 text-2xl">
               <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/></svg>
            </div>
          </div>
        </Card>

      </div>

      {/* --- CHARTS ROW --- */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
         
         {/* Main Chart Area */}
         <div className="lg:col-span-2 flex flex-col">
            <Card noPadding className="h-full min-h-[400px]">
              {/* Header */}
              <div className="px-4 py-3 border-b border-gray-100 bg-[#f8f9fc] flex justify-between items-center rounded-t">
                  <h6 className="font-bold text-[#4e73df] text-sm">Earnings Overview</h6>
                  <button className="text-gray-400 hover:text-gray-600">⋮</button>
              </div>
              {/* Body */}
              <div className="p-4 h-[350px]">
                 <AreaChart />
              </div>
            </Card>
         </div>

         {/* Pie Chart Area */}
         <div className="flex flex-col">
           <Card noPadding className="h-full min-h-[400px]">
              {/* Header */}
              <div className="px-4 py-3 border-b border-gray-100 bg-[#f8f9fc] flex justify-between items-center rounded-t">
                  <h6 className="font-bold text-[#4e73df] text-sm">Revenue Sources</h6>
                  <button className="text-gray-400 hover:text-gray-600">⋮</button>
              </div>
              {/* Body */}
              <div className="p-4 h-[300px] flex items-center justify-center">
                <PieChart />
              </div>
              <div className="pb-6 flex justify-center gap-4">
                 <div className="flex items-center text-xs text-gray-600"><span className="w-3 h-3 rounded-full bg-[#4e73df] mr-1"></span> Direct</div>
                 <div className="flex items-center text-xs text-gray-600"><span className="w-3 h-3 rounded-full bg-[#1cc88a] mr-1"></span> Social</div>
                 <div className="flex items-center text-xs text-gray-600"><span className="w-3 h-3 rounded-full bg-[#36b9cc] mr-1"></span> Referral</div>
              </div>
           </Card>
         </div>

      </div>

      {/* --- EMPLOYEE TABLE --- */}
      <Card noPadding className="w-full overflow-hidden">
        <div className="px-4 py-3 border-b border-gray-100 bg-[#f8f9fc] flex justify-between items-center">
            <h6 className="font-bold text-[#4e73df] text-sm">Hestabit Employee Attendance</h6>
            <Button variant="secondary" size="sm" className="text-xs h-8">Export to CSV</Button>
        </div>
        
        <Table>
          <TableHeader>
            <TableHead>Employee Name</TableHead>
            <TableHead>Role</TableHead>
            <TableHead>Department</TableHead>
            <TableHead>Check-in Time</TableHead>
            <TableHead>Status</TableHead>
          </TableHeader>
          <TableBody>
            {employees.map((employee) => (
              <TableRow key={employee.id}>
                <TableCell className="font-medium text-gray-900">{employee.name}</TableCell>
                <TableCell>{employee.role}</TableCell>
                <TableCell>{employee.department}</TableCell>
                <TableCell>{employee.time}</TableCell>
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
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      {/* --- REPORT MODAL --- */}
      <Modal 
        isOpen={isModalOpen} 
        onClose={() => setModalOpen(false)}
        title="Generate Report"
      >
        <p className="mb-4 text-sm leading-relaxed">
          Are you sure you want to download the monthly earnings report? This will compile data from all connected sources.
        </p>
        <div className="p-3 bg-yellow-50 text-yellow-700 text-sm rounded border border-yellow-200 flex items-start">
           <span className="mr-2 text-lg">⚠️</span> 
           <span>This process might take a few seconds to complete depending on the server load.</span>
        </div>
      </Modal>

    </div>
  );
}