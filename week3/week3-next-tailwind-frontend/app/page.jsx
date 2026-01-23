"use client"; 
import Button from "@/components/ui/Button";

export default function LandingPage() {
  return (
    <div className="bg-blue-500 text-black w-screen  flex flex-col justify-center items-center space-y-10 py-20">
      <div className="text-center space-y-6 max-w-lg px-6">
        <h1 className="text-5xl font-bold tracking-tight">Hestabit</h1>
        <p className="text-blue-100 text-lg">
          A modern dashboard template rebuilt with Next.js 15, Tailwind CSS, and Atomic Design principles.
        </p>
        
        <div className="flex justify-center gap-4 pt-4">
          <a href="/dashboard">
            <Button variant="warning" size="lg" className="shadow-xl">
              Enter Dashboard 
            </Button>
          </a>
          <a href="/about">
            <Button variant="secondary" size="lg" className="bg-white/10 border border-white/20 hover:bg-white/20">
              About Project
            </Button>
          </a>
        </div>
      </div>
    </div>
  );
}