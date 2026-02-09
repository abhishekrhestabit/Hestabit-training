import React, { useState } from 'react';
import ProgressBar from './ProgressBar';

const GoalNode = ({ goal, level = 0, onAddChild, onDelete, onToggleComplete }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  
  // 1. DETERMINE LABELS (Year -> Quarter -> Month...)
  const hierarchy = ['Year', 'Quarter', 'Month', 'Week', 'Day'];
  const currentType = hierarchy[level];
  const childType = hierarchy[level + 1]; // This determines the button label!
  
  // 2. LIMITS LOGIC
  const maxChildren = [null, 4, 3, 4, 7]; 
  const currentChildrenCount = goal.subGoals ? goal.subGoals.length : 0;
  
  // Check if we can add more children AND if we haven't reached the max depth (Day)
  const canAddChild = level < 4 && (maxChildren[level + 1] === null || currentChildrenCount < maxChildren[level + 1]);

  // 3. LEAF NODE CHECK (For checkbox)
  const isLeafNode = level > 3; // 3=Week, 4=Day

  // Indentation
  const indentClass = level === 0 ? '' : 'ml-6 border-l border-slate-700 pl-4';
  
  // Dynamic Styling
  const colors = [
    'border-emerald-500/30 bg-emerald-900/10', // Year
    'border-teal-500/30 bg-teal-900/10',       // Quarter
    'border-cyan-500/30 bg-cyan-900/10',       // Month
    'border-sky-500/30 bg-sky-900/10',         // Week
    'border-slate-500/30 bg-slate-800/50'      // Day
  ];
  
  const baseColor = colors[Math.min(level, colors.length - 1)];
  const cardStyle = goal.status === 'Completed' 
    ? 'border-slate-700 bg-slate-900/30 opacity-60' 
    : baseColor;

  return (
    <div className={`transition-all duration-300 ${indentClass} mt-3`}>
      
      {/* --- CARD --- */}
      <div className={`relative p-4 rounded-xl border backdrop-blur-sm transition-all group ${cardStyle}`}>
        <div className="flex justify-between items-start">
          
          {/* LEFT SIDE: Checkbox & Title */}
          <div className="flex items-start gap-3 flex-1">
            
            {/* CHECKBOX (Only for Week/Day) */}
            {isLeafNode && (
              <div 
                onClick={(e) => {
                  e.stopPropagation();
                  onToggleComplete(goal._id, goal.status === 'Completed');
                }}
                className={`
                  mt-1 w-5 h-5 rounded border cursor-pointer flex items-center justify-center transition-colors
                  ${goal.status === 'Completed' ? 'bg-emerald-500 border-emerald-500' : 'border-slate-500 hover:border-emerald-400'}
                `}
              >
                {goal.status === 'Completed' && <span className="text-black text-xs font-bold">✓</span>}
              </div>
            )}

            {/* TITLE & EXPAND */}
            <div 
              className="flex-1 cursor-pointer"
              onClick={() => goal.subGoals?.length > 0 && setIsExpanded(!isExpanded)}
            >
              <div className="flex items-center gap-2 mb-2">
                {goal.subGoals?.length > 0 && (
                  <span className={`text-xs text-slate-400 transition-transform duration-300 ${isExpanded ? 'rotate-90' : ''}`}>▶</span>
                )}
                
                <h4 className={`font-semibold tracking-wide ${level === 0 ? 'text-lg' : 'text-base'} ${goal.status === 'Completed' ? 'line-through text-slate-500' : 'text-slate-200'}`}>
                  {goal.title}
                </h4>
                
                <span className="text-[10px] uppercase tracking-wider bg-black/20 px-1.5 py-0.5 rounded text-slate-500">
                  {currentType}
                </span>
              </div>

              {!isLeafNode && (
                <div className="flex items-center gap-4">
                  <ProgressBar progress={goal.progress} className="h-1.5 flex-1 bg-black/30" />
                  <span className="text-xs font-mono opacity-60">{goal.progress}%</span>
                </div>
              )}
            </div>
          </div>

          {/* RIGHT SIDE: Action Buttons (Hover Only) */}
          <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
            
            {/* --- ADD CHILD BUTTON (Fixed Logic) --- */}
            {/* Logic: Show button if we CAN add a child AND the goal is NOT completed */}
            {canAddChild && goal.status !== 'Completed' && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onAddChild(goal._id, childType); // Passes 'Quarter' or 'Month' to parent
                }}
                className="p-1.5 hover:bg-emerald-500/20 rounded text-xs text-emerald-400 border border-emerald-500/30 transition-colors"
                title={`Add ${childType}`}
              >
                + {childType}
              </button>
            )}

            {/* DELETE BUTTON */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                if(confirm('Are you sure you want to delete this goal?')) {
                  onDelete(goal._id);
                }
              }}
              className="p-1.5 hover:bg-rose-500/20 rounded text-xs text-rose-400 border border-rose-500/30 transition-colors"
              title="Delete Goal"
            >
              🗑️
            </button>
          </div>
        </div>
      </div>

      {/* --- RECURSIVE CHILDREN --- */}
      {isExpanded && goal.subGoals && (
        <div className="animate-in fade-in slide-in-from-top-2 duration-300 border-l border-white/5 ml-3">
          {goal.subGoals.map((subGoal) => (
            <GoalNode 
              key={subGoal._id} 
              goal={subGoal} 
              level={level + 1} 
              onAddChild={onAddChild}
              onDelete={onDelete}
              onToggleComplete={onToggleComplete}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default GoalNode;