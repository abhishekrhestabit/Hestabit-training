"use client";
import { useState } from 'react';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import Modal from '@/components/ui/Modal';

export default function Home() {
  const [isModalOpen, setModalOpen] = useState(false);

  return (
    <div className="flex flex-col space-y-6">
      
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
            <Card noPadding className="h-full">
              {/* Header */}
              <div className="px-4 py-3 border-b border-gray-100 bg-[#f8f9fc] flex justify-between items-center rounded-t">
                  <h6 className="font-bold text-[#4e73df] text-sm">Earnings Overview</h6>
                  <button className="text-gray-400 hover:text-gray-600">⋮</button>
              </div>
              {/* Body */}
              <div className="p-4 h-[20rem] flex flex-col items-center justify-center text-gray-400">
                 <svg className="w-16 h-16 mb-2 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z"></path></svg>
                 <span className="text-sm">[ Area Chart Component Would Go Here ]</span>
              </div>
            </Card>
         </div>

         {/* Pie Chart Area */}
         <div className="flex flex-col">
           <Card noPadding className="h-full">
              {/* Header */}
              <div className="px-4 py-3 border-b border-gray-100 bg-[#f8f9fc] flex justify-between items-center rounded-t">
                  <h6 className="font-bold text-[#4e73df] text-sm">Revenue Sources</h6>
                  <button className="text-gray-400 hover:text-gray-600">⋮</button>
              </div>
              {/* Body */}
              <div className="p-4 h-[20rem] flex flex-col items-center justify-center text-gray-400">
                 <svg className="w-16 h-16 mb-2 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z"></path><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z"></path></svg>
                 <span className="text-sm mb-4">[ Pie Chart Component ]</span>
                 
                 {/* Legend */}
                 <div className="flex justify-center gap-2 mt-auto">
                    <Badge variant="primary" className="font-normal">Direct</Badge>
                    <Badge variant="success" className="font-normal">Social</Badge>
                    <Badge variant="secondary" className="font-normal">Referral</Badge>
                 </div>
              </div>
           </Card>
         </div>

      </div>

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