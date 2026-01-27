"use client";
import Image from "next/image";
import Button from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";

export default function LandingPage() {
  return (
    <div className="flex flex-col min-h-screen w-full bg-white font-sans text-gray-900 overflow-x-hidden">

      {/* --- HERO SECTION --- */}
      <section className="relative w-full overflow-hidden bg-gradient-to-b from-gray-900 via-gray-800 to-gray-900 text-white pt-32 pb-40">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full z-0 overflow-hidden opacity-40 pointer-events-none">
          <div className="absolute top-[-10%] left-[20%] w-[500px] h-[500px] bg-blue-600 rounded-full blur-[120px]"></div>
          <div className="absolute bottom-[-10%] right-[20%] w-[400px] h-[400px] bg-purple-600 rounded-full blur-[120px]"></div>
        </div>

        <div className="container mx-auto px-6 relative z-10 text-center max-w-5xl">
          <Badge variant="primary" className="mb-6 px-4 py-1.5 text-sm bg-blue-500/10 text-blue-300 border border-blue-500/20 backdrop-blur-md rounded-full">
            ✨ Introducing Hestabit 2.0
          </Badge>

          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight mb-8 leading-tight">
            The Dashboard that <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400">Works for You.</span>
          </h1>

          <p className="text-xl text-gray-300 mb-10 max-w-2xl mx-auto leading-relaxed">
            Stop wrestling with clunky admin panels. Hestabit provides the ultimate developer experience with pre-built components, atomic design, and lightning-fast performance.
          </p>

          <div className="flex flex-col sm:flex-row justify-center gap-4">
            <a href="/dashboard">
              <Button size="lg" className="w-full sm:w-auto bg-blue-600 hover:bg-blue-500 text-white px-8 py-6 text-lg shadow-lg shadow-blue-900/50 transition-all hover:scale-105">
                Start Building Free
              </Button>
            </a>
            <a href="/dashboard/profile">

              <Button size="lg" variant="secondary" className="w-full sm:w-auto bg-white/5 border border-white/10 hover:bg-white/10 text-white px-8 py-6 text-lg backdrop-blur-sm">
                Profile
              </Button>
            </a>

          </div>

          <div className="mt-20 -mb-64 relative rounded-xl border border-gray-700 bg-gray-800/50 shadow-2xl p-2 backdrop-blur-sm w-full">
            <div className="relative rounded-xl border border-gray-700 bg-gray-800/50 shadow-2xl p-2 backdrop-blur-sm w-full">
              <Image
                src="/dbpf.png" // Path to your file in public folder
                alt="Hestabit Dashboard Preview"
                width={1200} // The natural width of your screenshot
                height={675} // The natural height of your screenshot
                className="rounded-lg w-full h-auto"
                priority // Loads this image immediately (good for SEO)
              />
            </div>
          </div>
        </div>
      </section>


      {/* --- FEATURES GRID --- */}
      <section className="pt-64 pb-24 bg-gray-50 w-full">
        <div className="container mx-auto px-6">
          <div className="text-center max-w-3xl mx-auto mb-20">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-6">Why Top Teams Choose Hestabit</h2>
            <p className="text-lg text-gray-600">
              We've abstracted away the boring parts of web development.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="group p-8 bg-white rounded-2xl shadow-sm border border-gray-100 hover:shadow-xl hover:-translate-y-1 transition-all duration-300">
              <div className="w-14 h-14 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center text-2xl mb-6 group-hover:scale-110 transition-transform">🚀</div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">Next.js 15 Ready</h3>
              <p className="text-gray-600 leading-relaxed">Leverage Server Actions and Partial Prerendering out of the box.</p>
            </div>
            <div className="group p-8 bg-white rounded-2xl shadow-sm border border-gray-100 hover:shadow-xl hover:-translate-y-1 transition-all duration-300">
              <div className="w-14 h-14 bg-purple-50 text-purple-600 rounded-xl flex items-center justify-center text-2xl mb-6 group-hover:scale-110 transition-transform">💎</div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">Atomic Components</h3>
              <p className="text-gray-600 leading-relaxed">A complete library of Buttons, Cards, Inputs, and Modals built with Tailwind.</p>
            </div>
            <div className="group p-8 bg-white rounded-2xl shadow-sm border border-gray-100 hover:shadow-xl hover:-translate-y-1 transition-all duration-300">
              <div className="w-14 h-14 bg-orange-50 text-orange-600 rounded-xl flex items-center justify-center text-2xl mb-6 group-hover:scale-110 transition-transform">📊</div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">Smart Analytics</h3>
              <p className="text-gray-600 leading-relaxed">Integrated responsive Chart.js visualizations.</p>
            </div>
          </div>
        </div>
      </section>





      {/* --- TESTIMONIALS --- */}
      <section className="py-24 bg-gray-50 w-full">
        <div className="container mx-auto px-6">
          <div className="flex flex-col md:flex-row justify-between items-end mb-12">
            <div className="max-w-2xl">
              <Badge variant="primary" className="mb-4 bg-blue-50 text-blue-600">Wall of Love</Badge>
              <h2 className="text-4xl font-bold text-gray-900">Loved by Developers.</h2>
              <h2 className="text-4xl font-bold text-gray-300">Trusted by Enterprises.</h2>
            </div>
            <div className="mt-6 md:mt-0">
              <Button variant="secondary" className="border-gray-200">Read all reviews</Button>
            </div>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            <Card className="p-6 bg-white border-none shadow-sm h-full flex flex-col">
              <div className="flex text-yellow-400 mb-4 text-sm">★★★★★</div>
              <p className="text-gray-700 font-medium text-lg mb-6 flex-1">"Hestabit is the single most important tool in our stack. It saved us months."</p>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-white font-bold">JD</div>
                <div>
                  <div className="font-bold text-gray-900">Abhishek Rai</div>
                  <div className="text-sm text-gray-500">Eng. Manager</div>
                </div>
              </div>
            </Card>
            <Card className="p-6 bg-white border-none shadow-sm h-full flex flex-col">
              <div className="flex text-yellow-400 mb-4 text-sm">★★★★★</div>
              <p className="text-gray-700 font-medium text-lg mb-6 flex-1">"The component library is just beautiful. Clean and accessible."</p>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-purple-600 flex items-center justify-center text-white font-bold">AS</div>
                <div>
                  <div className="font-bold text-gray-900">Pranshu Kothari</div>
                  <div className="text-sm text-gray-500">Frontend Lead</div>
                </div>
              </div>
            </Card>
            <Card className="p-6 bg-white border-none shadow-sm h-full flex flex-col">
              <div className="flex text-yellow-400 mb-4 text-sm">★★★★★</div>
              <p className="text-gray-700 font-medium text-lg mb-6 flex-1">"Superior code quality. Highly recommend."</p>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-green-600 flex items-center justify-center text-white font-bold">MR</div>
                <div>
                  <div className="font-bold text-gray-900">Harshit Nautiyal</div>
                  <div className="text-sm text-gray-500">CTO, TechCorp</div>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </section>

      {/* --- PRICING SECTION --- */}


      <section className="py-24 bg-white w-full border-t border-gray-100">
        <div className="container mx-auto px-6">
          <div className="text-center max-w-3xl mx-auto mb-16">
            <Badge variant="primary" className="mb-4 bg-purple-100 text-purple-700 hover:bg-purple-200">Flexible Plans</Badge>
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-6">Simple, Transparent Pricing</h2>
            <p className="text-lg text-gray-600">
              Start for free and scale as you grow. No hidden fees.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">

            {/* Plan 1: Starter */}
            <Card className="p-8 border border-gray-100 shadow-xl hover:shadow-md hover:bg-blue-50 hover:scale-104 transition-transform duration-300 transition-shadow relative z-5">
              <h3 className="text-xl font-bold text-gray-900 mb-2">Starter</h3>
              <div className="flex items-baseline gap-1 mb-6">
                <span className="text-4xl font-extrabold text-gray-900">$0</span>
                <span className="text-gray-500">/month</span>
              </div>
              <p className="text-gray-500 mb-6 text-sm">Perfect for hobby projects and prototypes.</p>
              <Button variant="secondary" className="w-full mb-8 border-gray-200">Start for Free</Button>
              <ul className="space-y-4 text-sm text-gray-600">
                <li className="flex items-center gap-3"><span className="text-green-500">✓</span> 1 Admin User</li>
                <li className="flex items-center gap-3"><span className="text-green-500">✓</span> 5,000 Monthly Views</li>
                <li className="flex items-center gap-3"><span className="text-green-500">✓</span> Basic Charts</li>
                <li className="flex items-center gap-3"><span className="text-gray-400">✕</span> Export Data</li>
              </ul>
            </Card>

            {/* Plan 2: Pro (Highlighted) */}
            <Card className="p-8 border-2 border-blue-600 shadow-xl relative hover:bg-blue-100 scale-105 hover:scale-110 transition-transform duration-300  z-10 ">
              <div className="absolute top-0 right-0 bg-blue-600 text-white text-xs font-bold px-3 py-1 rounded-bl-lg rounded-tr-lg uppercase tracking-wide">
                Most Popular
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-2">Pro</h3>
              <div className="flex items-baseline gap-1 mb-6">
                <span className="text-4xl font-extrabold text-gray-900">$49</span>
                <span className="text-gray-500">/month</span>
              </div>
              <p className="text-gray-500 mb-6 text-sm">For growing teams building serious tools.</p>
              <Button variant="primary" className="w-full mb-8 shadow-lg shadow-blue-200">Get Started</Button>
              <ul className="space-y-4 text-sm text-gray-600">
                <li className="flex items-center gap-3"><span className="text-blue-600">✓</span> <strong>Unlimited</strong> Users</li>
                <li className="flex items-center gap-3"><span className="text-blue-600">✓</span> 100k Monthly Views</li>
                <li className="flex items-center gap-3"><span className="text-blue-600">✓</span> Advanced Analytics</li>
                <li className="flex items-center gap-3"><span className="text-blue-600">✓</span> CSV/PDF Exports</li>
                <li className="flex items-center gap-3"><span className="text-blue-600">✓</span> Priority Support</li>
              </ul>
            </Card>

            {/* Plan 3: Enterprise */}
            <Card className="p-8 border border-gray-100 shadow-xl hover:shadow-md hover:bg-blue-50 hover:scale-104 transition-transform duration-300 transition-shadow z-5">
              <h3 className="text-xl font-bold text-gray-900 mb-2">Enterprise</h3>
              <div className="flex items-baseline gap-1 mb-6">
                <span className="text-4xl font-extrabold text-gray-900">Custom</span>
              </div>
              <p className="text-gray-500 mb-6 text-sm">For large organizations needing control.</p>
              <Button variant="secondary" className="w-full mb-8 border-gray-200">Contact Sales</Button>
              <ul className="space-y-4 text-sm text-gray-600">
                <li className="flex items-center gap-3"><span className="text-green-500">✓</span> Everything in Pro</li>
                <li className="flex items-center gap-3"><span className="text-green-500">✓</span> SSO & Audit Logs</li>
                <li className="flex items-center gap-3"><span className="text-green-500">✓</span> Dedicated Manager</li>
                <li className="flex items-center gap-3"><span className="text-green-500">✓</span> 99.9% SLA</li>
              </ul>
            </Card>

          </div>
        </div>
      </section>


      {/* --- CTA SECTION --- */}
      <section className="py-24 bg-blue-600 text-white w-full">
        <div className="container mx-auto px-6 text-center max-w-3xl">
          <h2 className="text-3xl md:text-4xl font-bold mb-6">Ready to speed up your development?</h2>
          <p className="text-blue-100 text-lg mb-10">Join 10,000+ developers building faster with Hestabit today.</p>
          <a href="/dashboard">
            <button className="bg-white text-blue-600 font-bold py-4 px-10 rounded-full text-lg shadow-xl hover:bg-gray-100 transition-colors">
              Get Started for Free
            </button>
          </a>
        </div>
      </section>


      {/* --- FOOTER --- */}
      <footer className="bg-gray-900 text-gray-400 py-16 border-t border-gray-800 w-full">
        <div className="container mx-auto px-6 grid md:grid-cols-5 gap-12">
          <div className="col-span-1 md:col-span-2">
            <h3 className="text-2xl font-bold text-white mb-6 tracking-tight">Hestabit</h3>
            <p className="mb-6 leading-relaxed">The modern standard for building high-performance dashboards.</p>
          </div>
          <div>
            <h4 className="font-bold text-white mb-6 uppercase text-sm tracking-wider">Product</h4>
            <ul className="space-y-3 text-sm">
              <li><a href="#" className="hover:text-blue-400 transition">Features</a></li>
              <li><a href="#" className="hover:text-blue-400 transition">Pricing</a></li>
            </ul>
          </div>
          <div>
            <h4 className="font-bold text-white mb-6 uppercase text-sm tracking-wider">Company</h4>
            <ul className="space-y-3 text-sm">
              <li><a href="#" className="hover:text-blue-400 transition">About</a></li>
              <li><a href="#" className="hover:text-blue-400 transition">Contact</a></li>
            </ul>
          </div>
        </div>
        <div className="container mx-auto px-6 pt-8 mt-16 border-t border-gray-800 text-center text-sm">
          © 2026 Hestabit Inc. All rights reserved.
        </div>
      </footer>

    </div>
  );
}