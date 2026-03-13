import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

export function DevelopmentCard({ development }) {
  const [expanded, setExpanded] = useState(false);
  const region = development.region || 'GLOBAL';
  const domain = development.domain || 'MACRO';
  const impact = development.impact || 'HIGH';
  const keyFacts = Array.isArray(development.key_facts) ? development.key_facts : [];
  const sources = Array.isArray(development.sources) ? development.sources : [];

  const toggleExpanded = () => setExpanded((prev) => !prev);
  const onKeyToggle = (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      toggleExpanded();
    }
  };

  return (
    <div className="bg-transparent border-b border-slate-200 dark:border-slate-800 py-5 first:pt-2 last:border-0 transition-all duration-200">
      <div className="flex items-center justify-between mb-3 pl-10">
        <div className="flex items-center gap-2 text-[10px] font-mono uppercase tracking-widest text-slate-500 dark:text-slate-400">
          <span>{region}</span>
          <span className="text-slate-300 dark:text-slate-700">|</span>
          <span>{domain}</span>
        </div>
        <div className="text-[10px] font-mono uppercase tracking-widest text-slate-900 dark:text-slate-100 font-semibold bg-slate-200/50 dark:bg-slate-800/50 px-2 py-0.5 rounded-[3px]">
          Impact: {impact}
        </div>
      </div>

      <div
        className="group cursor-pointer outline-none"
        onClick={toggleExpanded}
        onKeyDown={onKeyToggle}
        role="button"
        tabIndex={0}
      >
        <div className="flex gap-4 items-start">
          <div className="text-2xl mt-0.5 grayscale opacity-80 group-hover:grayscale-0 group-hover:opacity-100 transition-all duration-300">
            {development.icon}
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-[17px] leading-snug mb-1.5 transition-colors">
              {development.headline}
            </h3>
            <p className="text-slate-600 dark:text-slate-400 text-[14px] leading-relaxed line-clamp-2">
              {development.executive_summary}
            </p>
          </div>
          <div className="ml-3 text-slate-400 group-hover:text-slate-900 dark:group-hover:text-slate-100 mt-1 transition-colors">
            {expanded ? <ChevronUp size={18} strokeWidth={1.5} /> : <ChevronDown size={18} strokeWidth={1.5} />}
          </div>
        </div>
      </div>

      {expanded && (
        <div className="mt-5 pl-10 pr-6 pb-2 animate-in fade-in slide-in-from-top-2 duration-200">
          <h4 className="text-[10px] font-mono font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-3">
            Key Facts
          </h4>
          <ul className="space-y-3 mb-6">
            {keyFacts.map((fact, index) => (
              <li key={index} className="flex gap-3 text-[13px] text-slate-700 dark:text-slate-300 leading-relaxed">
                <span className="text-slate-300 dark:text-slate-600 font-mono mt-0.5 select-none">///</span>
                <span>{fact}</span>
              </li>
            ))}
          </ul>

          <h4 className="text-[10px] font-mono font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-2">
            Sources
          </h4>
          <div className="flex flex-wrap items-center text-[11px] font-mono text-slate-500 dark:text-slate-400">
            {sources.map((source, index) => (
              <span key={index} className="uppercase tracking-wider">
                {source}
                {index < sources.length - 1 && (
                  <span className="mx-2 text-slate-300 dark:text-slate-700 select-none">|</span>
                )}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
