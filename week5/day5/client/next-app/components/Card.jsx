const Card = ({ children, title, className = '' }) => {
  return (
    <div className={`relative overflow-hidden bg-white/5 backdrop-blur-lg border border-white/10 rounded-2xl p-6 hover:bg-white/10 transition-colors duration-300 ${className}`}>
      
      {/* Optional: A subtle gradient orb in the corner for "Natural" feel */}
      <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/10 rounded-full blur-3xl -z-10 pointer-events-none"></div>

      {title && (
        <h3 className="text-xl font-semibold text-emerald-100 mb-3 tracking-tight">
          {title}
        </h3>
      )}
      <div className="text-slate-300 leading-relaxed">
        {children}
      </div>
    </div>
  );
};

export default Card;