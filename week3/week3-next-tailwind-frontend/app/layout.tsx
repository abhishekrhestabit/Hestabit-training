"use client";

import React, { useState } from "react";
import { Geist, Geist_Mono } from "next/font/google";
import Navbar from "@/components/ui/Navbar";
import Sidebar from "@/components/ui/Sidebar";
import "@/app/globals.css"; // Ensure global styles are imported if this acts as Root Layout

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(true);

  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased bg-gray-50 text-gray-900`}>
        <Navbar toggleSidebar={() => setSidebarOpen(!sidebarOpen)} />

        <div className="flex h-screen overflow-hidden w-full">
          {/* Sidebar - Hidden on mobile if closed */}
          {/* We pass the toggle function so the Sidebar's close button works */}
          <Sidebar isopen={sidebarOpen} toggleSidebar={() => setSidebarOpen(!sidebarOpen)} />

          {/* Main Content Wrapper */}
          <div className="flex-1 flex flex-col w-full h-full relative transition-all duration-300">
            
            {/* Navbar - Stays at the top */}
            
            {/* Scrollable Content Area */}
            {/* flex-1 ensures it fills remaining height. overflow-y-auto enables scrolling within this area only. */}
            <main className="flex-1 overflow-y-auto  w-full">
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}