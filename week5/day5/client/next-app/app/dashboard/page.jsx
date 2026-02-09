// src/app/dashboard/page.tsx
"use client";

import React, { useState } from 'react';
import Card from '../../components/Card';
import Button from '../../components/Button';
import ProgressBar from '../../components/ProgressBar';

// --- MOCK DATA (The "Tree" Structure) ---
const YEARLY_GOALS = [
  {
    id: 1,
    title: "Master Full-Stack Development",
    deadline: "Dec 31, 2026",
    progress: 35, // Calculated from sub-goals
    status: "In Progress",
    description: "Become proficient in Next.js, Docker, and NGINX."
  },
  {
    id: 2,
    title: "Physical Transformation",
    deadline: "Dec 31, 2026",
    progress: 60,
    status: "On Track",
    description: "Consistent gym routine and clean organic diet."
  },
  {
    id: 3,
    title: "Financial Independence",
    deadline: "Dec 31, 2026",
    progress: 15,
    status: "Behind",
    description: "Save $20k and start a passive income stream."
  }
];

export default function Dashboard() {
  const [goals] = useState(YEARLY_GOALS);

  return (
    <div className="w-full max-w-9xl px-6 lg:px-8 py-10">
      
      {/* --- HEADER SECTION --- */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-12 gap-4">
        <div>
          <h1 className="text-4xl font-bold text-white mb-2">
            Dashboard
          </h1>
          <p className="text-slate-400">
            Welcome back, <span className="text-emerald-400">Abhishek</span>. 
            Your forest is growing.
          </p>
        </div>
        
        <Button className="flex items-center gap-2">
          <span>+</span> Plant New Year Goal
        </Button>
      </div>

      {/* --- STATS OVERVIEW (The "Soil" Check) --- */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        <Card className="flex flex-col items-center justify-center text-center py-8">
          <span className="text-5xl font-bold text-emerald-400 mb-2">3</span>
          <span className="text-slate-500 text-sm uppercase tracking-wider">Active Roots (Yearly)</span>
        </Card>
        <Card className="flex flex-col items-center justify-center text-center py-8">
          <span className="text-5xl font-bold text-teal-400 mb-2">85%</span>
          <span className="text-slate-500 text-sm uppercase tracking-wider">Consistency Score</span>
        </Card>
        <Card className="flex flex-col items-center justify-center text-center py-8">
          <span className="text-5xl font-bold text-indigo-400 mb-2">12</span>
          <span className="text-slate-500 text-sm uppercase tracking-wider">Tasks for Today</span>
        </Card>
      </div>

      {/* --- MAIN CONTENT: YEARLY GOALS --- */}
      <h2 className="text-2xl font-bold text-slate-200 mb-6 border-l-4 border-emerald-500 pl-4">
        2026 Yearly Overview
      </h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {goals.map((goal) => (
          <Card key={goal.id} className="group cursor-pointer hover:border-emerald-500/30">
            
            {/* Goal Header */}
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-xl font-bold text-emerald-100 group-hover:text-emerald-400 transition-colors">
                  {goal.title}
                </h3>
                <p className="text-slate-500 text-sm mt-1">{goal.description}</p>
              </div>
              <span className={`px-3 py-1 rounded-full text-xs font-bold border ${
                goal.status === 'On Track' ? 'bg-emerald-900/30 border-emerald-500 text-emerald-400' :
                goal.status === 'Behind' ? 'bg-rose-900/20 border-rose-500/50 text-rose-400' :
                'bg-blue-900/20 border-blue-500/50 text-blue-400'
              }`}>
                {goal.status}
              </span>
            </div>

            {/* Progress Visualization */}
            <div className="mt-6">
              <div className="flex justify-between text-sm text-slate-400 mb-2">
                <span>Progress</span>
                <span>{goal.progress}%</span>
              </div>
              <ProgressBar progress={goal.progress} />
            </div>

            {/* Drill Down Hint */}
            <div className="mt-6 flex justify-between items-center text-sm">
              <span className="text-slate-600 group-hover:text-slate-400 transition-colors">
                Deadline: {goal.deadline}
              </span>
              <span className="text-emerald-500/50 group-hover:text-emerald-400 transition-colors flex items-center gap-1">
                View Quarters &rarr;
              </span>
            </div>
            
          </Card>
        ))}

        {/* Empty State / Add New Placeholder */}
        <div className="border-2 border-dashed border-slate-800 rounded-2xl flex flex-col items-center justify-center p-10 text-slate-600 hover:border-emerald-500/30 hover:text-emerald-500/50 transition-all cursor-pointer group">
          <div className="w-16 h-16 rounded-full bg-slate-900 flex items-center justify-center mb-4 group-hover:bg-emerald-900/20 transition-colors">
            <span className="text-3xl">+</span>
          </div>
          <p>Plant a new Goal</p>
        </div>

      </div>
    </div>
  );
}