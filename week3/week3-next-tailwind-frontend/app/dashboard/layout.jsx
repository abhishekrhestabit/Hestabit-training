
export default function DashboardLayout({ children }) {
  return (
    <div className="flex-1 w-full bg-[#f8f9fc]">

      {/* 2. FLEX CONTAINER FOR SIDEBAR AND CONTENT */}
      <div className="flex-1  h-[calc(100vh-4rem)] overflow-y-auto w-100%">
        
          <main className="flex-1 p-6 w-full">
            {children}
          </main>
        
        
      </div>
    </div>
  );
}