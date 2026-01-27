'use client';
import { usePathname } from 'next/navigation'; 
import Link from 'next/link';
import Button from '@/components/ui/Button'; // Fixed casing to lowercase

export default function Navbar({ toggleSidebar }) {
  const pathname = usePathname();
  
  // Logic 1: Are we on the Dashboard?
  const isDashboard = pathname?.startsWith('/dashboard');
  
  // Logic 2: Are we on the Home Page?
  const isHomePage = pathname === '/';

  return (
    <header 
      className={`
        top-0 left-0 w-full h-16 shadow-md flex items-center justify-between px-6 z-30 transition-colors duration-300
        ${isHomePage ? 'bg-gray-900' : 'bg-[#5a87e8]'}
      `}
    >
      
      {/* 1. Left Side: Brand & Sidebar Toggle */}
      <div className="text-white text-lg font-bold uppercase tracking-wider flex items-center gap-2">
        {/* Only show toggle on Dashboard */}
        {isDashboard && (
          <Button 
            variant='primary' 
            className='bg-transparent hover:bg-white/20 border-none p-2 h-auto' 
            onClick={toggleSidebar}
          >
            <span className='text-xl'>☰</span>
          </Button>
        )}
        
        <Link href="/" className="hover:opacity-80 transition-opacity">
          <span>Start Bootstrap</span>
        </Link>
      </div>

      {/* 2. Right Side: Navigation & Tools */}
      <div className="flex items-center space-x-6">
        
        {/* --- PUBLIC NAVIGATION (Hidden on Dashboard) --- */}
        {!isDashboard && (
          <nav className="hidden md:flex items-center gap-6">
            <Link 
              href="/about" 
              className={`text-sm font-medium hover:opacity-80 transition-opacity ${isHomePage ? 'text-gray-300' : 'text-white'}`}
            >
              About
            </Link>
            <Link 
              href="/dashboard" 
              className={`text-sm font-medium hover:opacity-80 transition-opacity ${isHomePage ? 'text-gray-300' : 'text-white'}`}
            >
              Dashboard
            </Link>
          </nav>
        )}

        {/* --- DASHBOARD SEARCH BAR (Hidden on Public Pages) --- */}
        {isDashboard && (
          <div className="hidden sm:flex bg-white rounded-md overflow-hidden w-[300px] border border-blue-400/30">
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
        )}

        {/* --- ACTIONS (Login / Profile) --- */}
        
        {/* Login Button (Only visible if NOT on dashboard) */}
        {!isDashboard && (
          <Link href="/login">
            <Button 
              variant="danger" 
              size="md" 
              className={`
                border-none font-bold shadow-sm transition-colors duration-300
                ${isHomePage 
                  ? 'bg-blue-600 text-white hover:bg-blue-500' // Dark theme style
                  : 'bg-danger text-[#4e73df] hover:bg-gray-100 hover:text-gray-900' // Light theme style
                }
              `}
            >
              Login
            </Button>
          </Link>
        )}

        {/* User Profile (Only visible on Dashboard) */}
        {isDashboard && (
          <div className="flex items-center cursor-pointer">
            <Link href="/dashboard/profile">
              <div className="h-9 w-9 rounded-full overflow-hidden bg-white/20 flex items-center justify-center text-white hover:bg-white/30 transition border border-white/20">
                 <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                   <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
                   <circle cx="12" cy="7" r="4" />
                 </svg>
              </div>
            </Link>
          </div>
        )}

      </div>

    </header>
  );
}