"use client";
import React from 'react';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import Input from '@/components/ui/Input';
import Link from 'next/link';
export default function LoginPage() {
  return (
    <div className="min-h-screen  flex items-center justify-center p-4">
      
      {/* Container Card */}
      <div className="w-full  max-w-md">
        <Card className="overflow-hidden rounded-lg shadow-xl  shadow-2xl border-0">
          <div className="p-8">
            
            {/* Header */}
            <div className="text-center mb-8">
              <h1 className="text-2xl font-bold text-gray-900 mb-2">Welcome Back!</h1>
              <p className="text-sm text-gray-500">Enter your credentials to access the Hestabit dashboard.</p>
            </div>

            {/* Login Form */}
            <form className="space-y-6">
              <Input 
                label="Email Address" 
                type="email" 
                placeholder="name@hestabit.com" 
                required 
              />
              
              <div>
                <Input 
                  label="Password" 
                  type="password" 
                  placeholder="••••••••" 
                  required 
                />
                <div className="flex justify-end mt-1">
                  <a href="#" className="text-xs text-[#4e73df] hover:underline">Forgot Password?</a>
                </div>
              </div>

              {/* Login Button */}
              <Link href="/dashboard">
                <Button variant="primary" className="w-full shadow-lg" size="lg" >
                  Login
                </Button>
              </Link>
              {/* Divider */}
              <div className="relative my-6">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-200"></div>
                </div>
                <div className="relative flex justify-center text-sm">
                  <span className="px-2 bg-white text-gray-500">Or continue with</span>
                </div>
              </div>

              {/* Social Login Buttons */}
              <div className="grid grid-cols-2 gap-3">
                <Button variant="secondary" className="bg-red-500 hover:bg-red-600 text-white border-none flex gap-2 justify-center">
                  <span className="font-bold">G</span> Google
                </Button>
                <Button variant="secondary" className="bg-blue-800 hover:bg-blue-900 text-white border-none flex gap-2 justify-center">
                  <span className="font-bold">f</span> Facebook
                </Button>
              </div>

            </form>

            {/* Footer Links */}
            <div className="mt-8 text-center text-sm">
              <span className="text-gray-500">Don't have an account? </span>
              <a href="#" className="text-[#4e73df] font-medium hover:underline">Create an Account</a>
            </div>

          </div>
        </Card>
      </div>

    </div>
  );
}