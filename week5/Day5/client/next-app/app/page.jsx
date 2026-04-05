import React from 'react';
import Link from 'next/link';
import Button from '../components/Button';
import Card from '../components/Card';

export default function Home() {
  return (
    <div className="w-screen max-w-9xl px-6 lg:px-8 py-12 flex flex-col items-center">
      
      {/* --- HERO SECTION --- */}
      <section className="text-center py-20 lg:py-32 relative">
        {/* Ambient Glow Effect behind text */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-emerald-500/10 rounded-full blur-[100px] -z-10"></div>

        <h1 className="text-5xl md:text-7xl font-bold tracking-tight text-white mb-6">
          Find Clarity in <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-teal-300">
            Natural Progression
          </span>
        </h1>
        
        <p className="text-xl text-slate-400 max-w-2xl mx-auto mb-10 leading-relaxed">
          Break down your biggest dreams into daily steps. 
          From <span className="text-emerald-300">Yearly Goals</span> to <span className="text-emerald-300">Daily Tasks</span>, 
          watch your progress grow organically like a tree.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link href="/dashboard">
            <Button className="px-8 py-3 text-lg">
              Start Growing
            </Button>
          </Link>
          <Link href="/about">
            <Button variant="outline" className="px-8 py-3 text-lg">
              Learn More
            </Button>
          </Link>
        </div>
      </section>

      {/* --- FEATURES GRID --- */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-8 w-full mt-10 mb-20">
        
        <Card title="Macro to Micro" className="h-full">
          Start with a Yearly vision. Zoom in to Quarterly milestones, Monthly targets, Weekly sprints, and finally, Daily actions.
        </Card>

        <Card title="Organic Growth" className="h-full">
          Visual data charts that feel natural. Watch your "tree" of goals fill up as you complete tasks, giving you a sense of life and motion.
        </Card>

        <Card title="Focus & Calm" className="h-full">
          No clutter. No red badges. Just a deep, dark interface designed to help you focus on what matters most right now.
        </Card>

      </section>

      {/* --- FOOTER (Simple) --- */}
      <footer className="text-slate-500 text-sm py-8 border-t border-white/5 w-full text-center">
        &copy; {new Date().getFullYear()} HestaTrack. Grow at your own pace.
      </footer>
    </div>
  );
}