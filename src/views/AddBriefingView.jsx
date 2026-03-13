import { Database, AlertTriangle } from 'lucide-react';

export function AddBriefingView({ jsonInput, error, onJsonChange, onImport, onLoadSample }) {
  return (
    <div className="pb-24 max-w-2xl mx-auto pt-8 px-4 animate-in fade-in duration-300">
      <header className="mb-8 border-b-2 border-slate-900 dark:border-white pb-4">
        <div className="flex items-center gap-3 mb-2">
          <Database size={24} strokeWidth={2} className="text-slate-900 dark:text-white" />
          <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white uppercase tracking-tight">
            Import Intelligence
          </h1>
        </div>
        <p className="text-[11px] font-mono text-slate-500 dark:text-slate-400 uppercase tracking-widest">
          Secure JSON Ingestion Protocol
        </p>
      </header>

      {error && (
        <div className="bg-transparent text-red-600 dark:text-red-400 p-4 mb-6 border-l-4 border-red-600 flex items-start gap-3">
          <AlertTriangle size={18} className="mt-0.5 shrink-0" />
          <div className="text-[12px] font-mono font-medium leading-relaxed">{error}</div>
        </div>
      )}

      <div className="relative group">
        <div className="absolute top-0 left-0 w-full h-8 bg-slate-200 dark:bg-slate-800 rounded-t-sm flex items-center px-4 border border-b-0 border-slate-300 dark:border-slate-700">
          <span className="text-[10px] font-mono font-bold uppercase tracking-widest text-slate-500 dark:text-slate-400">
            data.json
          </span>
        </div>
        <textarea
          value={jsonInput}
          onChange={(event) => onJsonChange(event.target.value)}
          placeholder="Paste generated JSON schema here..."
          className="w-full h-[400px] mt-8 bg-slate-50 dark:bg-[#05080f] border border-slate-300 dark:border-slate-700 rounded-b-sm p-4 font-mono text-[13px] text-slate-800 dark:text-slate-300 focus:outline-none focus:border-slate-900 dark:focus:border-slate-400 focus:ring-1 focus:ring-slate-900 dark:focus:ring-slate-400 resize-none transition-colors"
          spellCheck={false}
        />
      </div>

      <div className="flex gap-4 mt-6">
        <button
          onClick={onImport}
          className="flex-1 bg-slate-900 dark:bg-white text-white dark:text-slate-900 font-bold py-3.5 px-4 rounded-sm active:scale-[0.98] transition-all uppercase text-[12px] font-mono tracking-widest"
        >
          Execute Import
        </button>
        <button
          onClick={onLoadSample}
          className="px-6 py-3.5 bg-transparent text-slate-700 dark:text-slate-300 font-bold rounded-sm border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 active:scale-[0.98] transition-all uppercase text-[12px] font-mono tracking-widest"
        >
          Load Test Data
        </button>
      </div>
    </div>
  );
}
