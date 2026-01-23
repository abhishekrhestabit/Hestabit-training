"use client";
import React, { useState } from "react";

import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/ui/Navbar";
import Sidebar from "@/components/ui/Sidebar";
const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});



export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {

  const [open, setOpen] = useState(true);

  
  return (
    <html lang="en">
      {/* This is now a clean shell. 
        No Sidebar. No Navbar. Just fonts and global CSS. 
      */}
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased bg-gray-50 text-gray-900`}>
        <Navbar toggleSidebar={() => setOpen(!open)} />
        <div className="flex h-[calc(100vh-4rem)]">        
          <Sidebar toggleSidebar={() => setOpen(!open)}  isopen={open}/>
          {children}
        </div>

        
      </body>
    </html>
  );
}