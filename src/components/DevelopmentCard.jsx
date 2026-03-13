import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

export function DevelopmentCard({ development }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-white dark:bg-slate-900 rounded-xl p-4 shadow-sm border border-slate-100 dark:border-slate-800 transition-all duration-200">
      <div
        className="flex items-start justify-between cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex gap-3 items-start">
          <div className="text-2xl mt-0.5">{development.icon}</div>
          <div>
            <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-lg leading-tight mb-1">
              {development.headline}
            </h3>
            <p className="text-slate-600 dark:text-slate-400 text-sm leading-snug">
              {development.executive_summary}
            </p>
          </div>
        </div>
        <div className="ml-2 text-slate-400">
          {expanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
        </div>
      </div>

      {expanded && (
        <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Key Facts</h4>
          <ul className="space-y-2 mb-4">
            {development.key_facts.map((fact, index) => (
              <li key={index} className="flex gap-2 text-sm text-slate-700 dark:text-slate-300">
                <span className="text-slate-400">•</span>
                <span>{fact}</span>
              </li>
            ))}
          </ul>

          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">Sources</h4>
          <div className="flex flex-wrap gap-2 text-xs text-slate-500">
            {development.sources.map((source, index) => (
              <span key={index} className="bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded-md">
                {source}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
