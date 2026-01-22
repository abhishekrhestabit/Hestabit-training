
export default function DashboardLayout({ children }) {
  return (
    <div className="flex bg-[#f8f9fc]">

      {/* 2. FLEX CONTAINER FOR SIDEBAR AND CONTENT */}
      <div className="flex pt-16 w-full">
        
        {/* Main Content Wrapper */}
          <main className="flex-1 ml-64 min-h-screen p-6">
            {children}
          </main>
        
        
      </div>
    </div>
  );
}