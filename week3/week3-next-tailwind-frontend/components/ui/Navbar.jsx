'use client';
import Button from './Button';
import Sidebar from './Sidebar';
export default function Navbar({toggleSidebar}) {
  return (
    // fixed top-0 w-full: Forces the navbar to span 100% width at the very top
    // z-30: Higher than the sidebar (z-20)
    <header className=" top-0 left-0 w-full h-16 bg-[#5a87e8] shadow-md flex items-center justify-between px-6 ">
      
      
      
      {/* 1. Brand Title */}
      <div className="text-white text-lg font-bold uppercase tracking-wider flex items-center gap-2">
        <Button variant='primary' className='' onClick={toggleSidebar}><span className=''>☰</span></Button>
        <span>Start Bootstrap</span>
      </div>

      {/* 2. Right Side: Search + Profile */}
      <div className="flex items-center space-x-4">
        
        {/* Search Bar */}
        <div className="hidden md:flex bg-white rounded-md overflow-hidden w-[300px] border border-blue-400/30">
          <input 
            type="text" 
            placeholder="Search for..." 
            className="bg-transparent px-4 py-2 text-sm text-gray-700 focus:outline-none w-full placeholder-gray-400"
          />
          <button className="bg-[#224abe] px-4 text-white hover:bg-[#1a3a9e] transition flex items-center justify-center">
             <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
               <circle cx="11" cy="11" r="8" />
               <line x1="21" y1="21" x2="16.65" y2="16.65" />
             </svg>
          </button>
        </div>

        {/* User Profile */}
        <div className="flex items-center cursor-pointer">
          <a href="/dashboard/profile">
            <div className="h-9 w-9 rounded-full overflow-hidden bg-white/20 flex items-center justify-center text-white hover:bg-white/30 transition border border-white/20">
               <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                 <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
                 <circle cx="12" cy="7" r="4" />
               </svg>
            </div>
          </a>
        </div>

      </div>

    </header>
  );
}