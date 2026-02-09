"use client";

import React, { useEffect, useState } from 'react';
import Button from '../../components/Button';
import Modal from '../../components/Modal';

const GoalsPage = () => {
  const [todos, setTodos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState({ title: '', deadline: '' });

  // --- FETCH ---
  const fetchTodos = async () => {
    try {
      const res = await fetch('/api/goals');
      const data = await res.json();
      setTodos(data);
    } catch (err) { 
      console.error(err); 
    } finally { 
      setLoading(false); 
    }
  };

  useEffect(() => { fetchTodos(); }, []);

  // --- CREATE ---
  const handleSubmit = async (e) => {
    e.preventDefault();
    await fetch('/api/goals', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData),
    });
    setIsModalOpen(false);
    setFormData({ title: '', deadline: '' });
    fetchTodos();
  };

  // --- DELETE ---
  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this todo?')) return;
    
    try {
      const res = await fetch(`/api/goals/${id}`, {
        method: 'DELETE',
      });
      if (res.ok) fetchTodos();
    } catch (err) {
      console.error("Failed to delete:", err);
    }
  };

  // --- TOGGLE COMPLETE ---
  const handleToggle = async (id, currentStatus) => {
    const newStatus = currentStatus === 'completed' ? 'pending' : 'completed';

    try {
      const res = await fetch(`/api/goals/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      if (res.ok) fetchTodos();
    } catch (err) {
      console.error("Failed to update:", err);
    }
  };

  return (
    <div className="w-full max-w-3xl px-6 lg:px-8 py-12 pb-32">
      
      {/* Header */}
      <div className="flex justify-between items-end mb-10 border-b border-white/10 pb-6">
        <div>
          <h1 className="text-4xl font-bold text-white mb-2">To-Do List</h1>
          <p className="text-slate-400">Simple task management</p>
        </div>
        <Button onClick={() => setIsModalOpen(true)}>+ Add Todo</Button>
      </div>

      {/* Todo List */}
      {loading ? (
        <p className="text-slate-400">Loading...</p>
      ) : todos.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-slate-500 text-lg">No todos yet. Add one to get started!</p>
        </div>
      ) : (
        <div className="space-y-3">
          {todos.map((todo) => (
            <div 
              key={todo._id}
              className={`p-4 rounded-lg border backdrop-blur-sm transition-all group ${
                todo.status === 'completed' 
                  ? 'border-slate-700 bg-slate-900/30 opacity-60' 
                  : 'border-emerald-500/30 bg-emerald-900/10'
              }`}
            >
              <div className="flex items-center gap-4">
                {/* Checkbox */}
                <div 
                  onClick={() => handleToggle(todo._id, todo.status)}
                  className={`w-6 h-6 rounded border cursor-pointer flex items-center justify-center transition-colors flex-shrink-0 ${
                    todo.status === 'completed' 
                      ? 'bg-emerald-500 border-emerald-500' 
                      : 'border-slate-500 hover:border-emerald-400'
                  }`}
                >
                  {todo.status === 'completed' && (
                    <span className="text-black text-sm font-bold">✓</span>
                  )}
                </div>

                {/* Title & Deadline */}
                <div className="flex-1 min-w-0">
                  <h3 className={`font-medium text-base ${
                    todo.status === 'completed' 
                      ? 'line-through text-slate-500' 
                      : 'text-slate-200'
                  }`}>
                    {todo.title}
                  </h3>
                  {todo.deadline && (
                    <p className="text-xs text-slate-400 mt-1">
                      Due: {new Date(todo.deadline).toLocaleDateString()}
                    </p>
                  )}
                </div>

                {/* Delete Button */}
                <button
                  onClick={() => handleDelete(todo._id)}
                  className="p-2 hover:bg-rose-500/20 rounded text-sm text-rose-400 border border-rose-500/30 transition-colors opacity-0 group-hover:opacity-100"
                  title="Delete"
                >
                  🗑️
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* --- MODAL --- */}
      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Add New Todo">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-1">Title</label>
            <input 
              type="text" 
              required
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-emerald-500 outline-none"
              value={formData.title}
              onChange={(e) => setFormData({...formData, title: e.target.value})}
              placeholder="What needs to be done?"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-1">Deadline (optional)</label>
            <input 
              type="date"
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2 text-white focus:ring-2 focus:ring-emerald-500 outline-none"
              value={formData.deadline}
              onChange={(e) => setFormData({...formData, deadline: e.target.value})}
            />
          </div>
          <div className="flex justify-end gap-3 mt-6">
            <button 
              type="button" 
              onClick={() => {
                setIsModalOpen(false);
                setFormData({ title: '', deadline: '' });
              }} 
              className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <Button type="submit">Add Todo</Button>
          </div>
        </form>
      </Modal>

    </div>
  );
};

export default GoalsPage;