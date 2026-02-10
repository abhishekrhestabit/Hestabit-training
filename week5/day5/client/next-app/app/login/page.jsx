"use client";

import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import Card from '../../components/Card';
import Button from '../../components/Button';

const LoginPage = () => {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  const handleLogin = (e) => {
    e.preventDefault();
    setLoading(true);

    setTimeout(() => {
      setLoading(false);
      router.push('/dashboard'); 
    }, 1500);
  };

  return (
    <div className="min-h-[calc(100vh-80px)] w-full flex items-center justify-center px-4 relative overflow-hidden">
      
      {/* Background decoration (Ambient glow behind the card) */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-emerald-900/20 rounded-full blur-[120px] -z-10 pointer-events-none"></div>

      <Card className="w-full max-w-md p-8 sm:p-10 border-white/5 shadow-2xl shadow-black/50 backdrop-blur-xl bg-slate-900/60">
        
        {/* Header */}
        <div className="text-center mb-10">
          <Link href="/">
            <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-teal-300 cursor-pointer hover:opacity-80 transition-opacity">
              HestaTrack
            </h1>
          </Link>
          <p className="text-slate-400 mt-2 text-sm">
            Enter the forest of your potential.
          </p>
        </div>

        {/* Login Form */}
        <form onSubmit={handleLogin} className="space-y-6">
          
          {/* Email Input */}
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-slate-300 mb-2">
              Email Address
            </label>
            <input
              type="email"
              id="email"
              required
              className="w-full bg-slate-950/50 border border-slate-700 rounded-xl px-4 py-3 text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50 transition-all duration-300"
              placeholder="you@example.com"
            />
          </div>

          {/* Password Input */}
          <div>
            <div className="flex justify-between items-center mb-2">
              <label htmlFor="password" className="block text-sm font-medium text-slate-300">
                Password
              </label>
              <a href="#" className="text-xs text-emerald-500 hover:text-emerald-400 transition-colors">
                Forgot?
              </a>
            </div>
            <input
              type="password"
              id="password"
              required
              className="w-full bg-slate-950/50 border border-slate-700 rounded-xl px-4 py-3 text-slate-200 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50 transition-all duration-300"
              placeholder="••••••••"
            />
          </div>

          {/* Submit Button */}
          <Button 
            variant="primary" 
            className="w-full py-3 mt-4 flex justify-center items-center gap-2 font-semibold tracking-wide"
          >
            {loading ? (
              <>
                <div className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                <span>Logging In...</span>
              </>
            ) : (
              "Sign In"
            )}
          </Button>

        </form>

        {/* Footer Link */}
        <div className="mt-8 text-center text-sm text-slate-500">
          New to HestaTrack?{' '}
          <Link href="/signup" className="text-emerald-400 hover:text-emerald-300 font-medium transition-colors">
            Plant a seed (Sign Up)
          </Link>
        </div>

      </Card>
    </div>
  );
};

export default LoginPage;