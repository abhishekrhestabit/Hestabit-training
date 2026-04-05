"use client";

import React, { useEffect, useState, useMemo } from 'react';
import Card from '../../components/Card';
import ProgressBar from '../../components/ProgressBar';

// Helper to format a Date object to YYYY-MM-DD (local time)
const toDateString = (date) => {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
};

export default function Dashboard() {
  const [allTodos, setAllTodos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState(toDateString(new Date()));

  // Fetch all todos from the API
  const fetchTodos = async () => {
    try {
      const res = await fetch('/api/goals');
      const data = await res.json();
      setAllTodos(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTodos();
  }, []);

  // Toggle task completion status
  const handleToggleComplete = async (taskId, currentStatus) => {
    const newStatus = currentStatus === 'completed' ? 'pending' : 'completed';

    try {
      const res = await fetch(`/api/goals/${taskId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      if (res.ok) {
        fetchTodos(); // Refresh the list
      }
    } catch (err) {
      console.error("Failed to update task:", err);
    }
  };

  // Filter todos for the selected date
  const tasksForDate = useMemo(() => {
    return allTodos.filter((todo) => {
      if (!todo.deadline) return false;
      return toDateString(new Date(todo.deadline)) === selectedDate;
    });
  }, [allTodos, selectedDate]);

  const totalTasks = tasksForDate.length;
  const completedTasks = tasksForDate.filter((t) => t.status === 'completed').length;
  const pendingTasks = totalTasks - completedTasks;
  const completionPercent = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;

  // Quick date helpers
  const changeDate = (offset) => {
    const d = new Date(selectedDate + 'T00:00:00');
    d.setDate(d.getDate() + offset);
    setSelectedDate(toDateString(d));
  };

  const isToday = selectedDate === toDateString(new Date());

  const displayDate = new Date(selectedDate + 'T00:00:00').toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  return (
    <div className="w-full max-w-9xl px-6 lg:px-8 py-10">

      {/* --- HEADER --- */}
      <div className="mb-10">
        <h1 className="text-4xl font-bold text-white mb-2">Dashboard</h1>
        <p className="text-slate-400">
          Welcome back, <span className="text-emerald-400">Abhishek</span>.
          {isToday ? " Here's your progress for today." : " Viewing a different day."}
        </p>
      </div>

      {/* --- DATE PICKER --- */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 mb-10">
        <div className="flex items-center gap-2">
          <button
            onClick={() => changeDate(-1)}
            className="w-9 h-9 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:bg-slate-700 hover:text-white transition-colors flex items-center justify-center text-lg"
          >
            ‹
          </button>
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-emerald-500 outline-none"
          />
          <button
            onClick={() => changeDate(1)}
            className="w-9 h-9 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:bg-slate-700 hover:text-white transition-colors flex items-center justify-center text-lg"
          >
            ›
          </button>
        </div>

        {!isToday && (
          <button
            onClick={() => setSelectedDate(toDateString(new Date()))}
            className="text-sm text-emerald-400 hover:text-emerald-300 underline underline-offset-4 transition-colors"
          >
            Jump to Today
          </button>
        )}

        <span className="text-slate-500 text-sm ml-auto">{displayDate}</span>
      </div>

      {/* --- STATS CARDS --- */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
        {/* Completion % Card */}
        <Card className="flex flex-col items-center justify-center text-center py-8">
          <span className={`text-5xl font-bold mb-2 ${
            completionPercent === 100 ? 'text-emerald-400' :
            completionPercent >= 50 ? 'text-teal-400' :
            completionPercent > 0 ? 'text-amber-400' : 'text-slate-600'
          }`}>
            {completionPercent}%
          </span>
          <span className="text-slate-500 text-sm uppercase tracking-wider">Completed</span>
          <div className="w-full mt-4 px-4">
            <ProgressBar progress={completionPercent} />
          </div>
        </Card>

        {/* Tasks Done */}
        <Card className="flex flex-col items-center justify-center text-center py-8">
          <span className="text-5xl font-bold text-emerald-400 mb-2">{completedTasks}</span>
          <span className="text-slate-500 text-sm uppercase tracking-wider">Tasks Done</span>
          <span className="text-slate-600 text-xs mt-2">out of {totalTasks}</span>
        </Card>

        {/* Pending */}
        <Card className="flex flex-col items-center justify-center text-center py-8">
          <span className={`text-5xl font-bold mb-2 ${pendingTasks > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
            {pendingTasks}
          </span>
          <span className="text-slate-500 text-sm uppercase tracking-wider">Pending</span>
        </Card>
      </div>

      {/* --- TASKS LIST --- */}
      <h2 className="text-2xl font-bold text-slate-200 mb-6 border-l-4 border-emerald-500 pl-4">
        {isToday ? "Today's Tasks" : `Tasks for ${new Date(selectedDate + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}`}
      </h2>

      {loading ? (
        <p className="text-slate-400">Loading tasks...</p>
      ) : totalTasks === 0 ? (
        <Card className="flex flex-col items-center justify-center text-center py-12">
          <span className="text-4xl mb-4">📋</span>
          <p className="text-slate-400 text-lg">No tasks scheduled for this date.</p>
          <p className="text-slate-600 text-sm mt-2">
            Head over to the <a href="/goals" className="text-emerald-400 hover:underline">To-Do List</a> to add tasks with a deadline.
          </p>
        </Card>
      ) : (
        <div className="space-y-3">
          {tasksForDate.map((task) => (
            <Card
              key={task._id}
              className={`!p-4 transition-all ${
                task.status === 'completed'
                  ? '!bg-emerald-900/10 !border-emerald-500/20 opacity-70'
                  : '!border-slate-700'
              }`}
            >
              <div className="flex items-center gap-4">
                {/* Status indicator - Clickable */}
                <div 
                  onClick={() => handleToggleComplete(task._id, task.status)}
                  className={`w-6 h-6 rounded-full border-2 flex items-center justify-center flex-shrink-0 cursor-pointer transition-all hover:scale-110 ${
                    task.status === 'completed'
                      ? 'bg-emerald-500 border-emerald-500 hover:bg-emerald-600'
                      : 'border-slate-600 hover:border-emerald-400'
                  }`}
                >
                  {task.status === 'completed' && (
                    <span className="text-black text-sm font-bold">✓</span>
                  )}
                </div>

                {/* Title */}
                <div className="flex-1 min-w-0">
                  <h3 className={`font-medium text-base ${
                    task.status === 'completed'
                      ? 'line-through text-slate-500'
                      : 'text-slate-200'
                  }`}>
                    {task.title}
                  </h3>
                </div>

                {/* Status Badge */}
                <span className={`px-3 py-1 rounded-full text-xs font-bold border ${
                  task.status === 'completed'
                    ? 'bg-emerald-900/30 border-emerald-500 text-emerald-400'
                    : 'bg-amber-900/20 border-amber-500/50 text-amber-400'
                }`}>
                  {task.status === 'completed' ? 'Done' : 'Pending'}
                </span>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* --- SUMMARY FOOTER --- */}
      {totalTasks > 0 && (
        <div className="mt-8 p-4 rounded-xl bg-slate-900/50 border border-slate-800 text-center">
          <p className="text-slate-400 text-sm">
            {completionPercent === 100 ? (
              <span className="text-emerald-400 font-semibold">🎉 All tasks completed! Great work!</span>
            ) : (
              <>
                You've completed <span className="text-emerald-400 font-semibold">{completionPercent}%</span> of
                your tasks for this day. Keep going!
              </>
            )}
          </p>
        </div>
      )}
    </div>
  );
}