
const ProgressBar = ({ progress = 0, className = '' }) => {
  // Ensure progress stays between 0 and 100
  const cleanProgress = Math.min(100, Math.max(0, progress));

  return (
    <div className={`w-full h-3 bg-slate-800 rounded-full overflow-hidden ${className}`}>
      <div 
        className="h-full bg-gradient-to-r from-emerald-600 to-teal-400 transition-all duration-1000 ease-out rounded-full shadow-[0_0_10px_rgba(16,185,129,0.4)]"
        style={{ width: `${cleanProgress}%` }}
      ></div>
    </div>
  );
};

export default ProgressBar;