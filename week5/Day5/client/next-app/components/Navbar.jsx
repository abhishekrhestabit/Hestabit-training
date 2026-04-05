import Link from 'next/link';
import Button from './Button';


const Navbar = () => {
    return (
    <nav className="sticky top-0 w-full bg-slate-900/80 backdrop-blur-md border-b border-white/5">
      <div className="max-w-9xl mx-auto px-6 lg:px-8">
        <div className="flex items-center justify-between h-15">
          
          {/* Logo: Clean and Organic */}
          <div className="flex-shrink-0 cursor-pointer group">
            <Link href="/">
              <span className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-teal-200 group-hover:to-white transition-all duration-300">
                HestaTrack
              </span>
            </Link>
          </div>

          {/* Navigation Links (Desktop) */}
          
          {/* Login Button */}
          <div className="flex items-center space-x-6">
            <div className="hidden md:flex items-center space-x-8">
            {['Dashboard', 'Goals', 'Progress'].map((item) => (
              <Link key={item} href={`/${item.toLowerCase()}`} className="text-slate-400 hover:text-emerald-300 text-sm font-medium transition-colors">
                {item}
              </Link>
            ))}
          </div>

            <Link href="/login">
              <Button variant="primary" className="text-sm px-5 py-2">
                Sign In
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;