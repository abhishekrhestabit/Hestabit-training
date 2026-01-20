import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/ui/Sidebar";
import Navbar from "@/components/ui/Navbar";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "SB Admin Dashboard",
  description: "Next.js 15 Dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased text-[#5a5c69] bg-[#f8f9fc]`}>
        
        {/* 1. TOP: FULL WIDTH NAVBAR */}
        {/* Positioned fixed at the top, z-index higher than sidebar */}
        <Navbar />

        {/* 2. FLEX CONTAINER FOR SIDEBAR AND CONTENT */}
        <div className="flex pt-16"> {/* pt-16 pushes everything down by header height */}
          
          {/* Sidebar (Fixed Left, starts below header) */}
          <Sidebar />

          {/* Main Content Wrapper */}
          {/* ml-64: Pushes content right to respect the sidebar width */}
          <div className="flex-1 ml-64 min-h-screen">
            <main className="p-6">
              {children}
            </main>
          </div>
          
        </div>

      </body>
    </html>
  );
}