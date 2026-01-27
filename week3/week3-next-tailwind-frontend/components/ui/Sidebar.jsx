'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation'; // Import hook to check current URL


export default function Sidebar({ isopen, toggleSidebar }) {

  if (isopen) return null;
  const pathname = usePathname();
  const isDashboard = pathname?.startsWith('/dashboard');
  if (!isDashboard) return null;


  return (

    <aside className=" left-0   w-64 bg-[#4e73df] text-white flex flex-col shadow-lg overflow-y-auto">

      {/* Navigation */}
      <nav className="flex-1 py-6 font-bold text-[13px]">

        <Link href="/" className="flex items-center px-4 py-3 text-white/80 hover:text-white hover:bg-white/10 transition-colors group">
          <span className="mr-3 opacity-50 group-hover:opacity-100">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.1a2 2 0 0 1-1-1.72v-.51a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          </span>
          <span>Home</span>
        </Link>

        {/* Dashboard Link */}

        {/* Divider */}
        <hr className="my-3 border-white/20 mx-4" />

        {/* Section Header */}
        <div className="px-4 mb-1 text-[10px] text-white/50 uppercase font-bold">Interface</div>


        <Link href="/dashboard" className="flex items-center px-4 py-3 text-white hover:text-white hover:bg-white/10 transition-colors">
          <span className="mr-3 opacity-70">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="m12 14 4-4" />
              <path d="M3.34 19a10 10 0 1 1 17.32 0" />
            </svg>
          </span>
          <span>Dashboard</span>
        </Link>


        {/* Divider */}
        <hr className="my-3 border-white/20 mx-4" />



        {/* Section Header */}
        <div className="px-4 mb-1 text-[10px] text-white/50 uppercase font-bold">Addons</div>

        <Link href="/about" className="flex items-center px-4 py-3 text-white/80 hover:text-white hover:bg-white/10 transition-colors group">
          <span className="mr-3 opacity-50 group-hover:opacity-100">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 3v18h18" />
              <path d="M18 17V9" />
              <path d="M13 17V5" />
              <path d="M8 17v-3" />
            </svg>
          </span>
          <span>About</span>
        </Link>

        <Link href="/dashboard/users" className="flex items-center px-4 py-3 text-white/80 hover:text-white hover:bg-white/10 transition-colors group">
          <span className="mr-3 opacity-50 group-hover:opacity-100">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2h-7z" />
              <path d="M3 9h18" />
              <path d="M9 21V9" />
            </svg>
          </span>
          <span>Tables</span>
        </Link>
      </nav>

      {/* 3. Sidebar Footer (Toggle) */}
      <div className="p-4 text-center">
        <button className="bg-white/20 rounded-full h-10 w-10 flex items-center justify-center hover:bg-white/30 transition mx-auto text-white/50 hover:text-white " onClick={toggleSidebar}>
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
      </div>
    </aside>
  );
}